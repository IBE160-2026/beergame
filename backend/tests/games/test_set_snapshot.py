"""`games.commands.set_snapshot` (Story 5.12, FR-7, FR-30, AD-2, AD-4, AD-5, AD-8): a Class game
takes its Class session's frozen snapshot, and in the same transaction every free Seat, and every
Seat of a Student no longer in the Roster, gets the AI player the AI mode gives. A Game that has
its snapshot is never changed, and `assign_seat` replaces an occupant only when asked to."""

import asyncio
import uuid

import pytest

from app.ai import config
from app.engine import RULES_VERSION, GameSettings, demand_series
from app.modules.games import commands, service
from app.platform.events.registry import COMMAND_TOPICS
from tests.games.helpers import listening, query
from tests.games.test_assign_seat import assert_refused, version
from tests.games.test_class_games import SESSION, class_game

A = uuid.UUID("01900000-0000-7000-8000-0000000000a1")
B = uuid.UUID("01900000-0000-7000-8000-0000000000b2")
SETTINGS = GameSettings(weeks=8, guided_weeks=2, demand_seed=11)


def snapshot(model_config_id: str | None = None, level: str | None = None) -> dict:
    """What `sessions.build_snapshot` stores, for Rule-based or LLM players."""
    runtime = commands.default_runtime(
        model_config_id=model_config_id, effort_level=level, inactivity_limit_hours=24, pins={}
    )
    return {
        "settings": SETTINGS.model_dump(mode="json"),
        "demand_series": list(demand_series(SETTINGS)),
        "demand_seed": SETTINGS.demand_seed,
        "rules_version": RULES_VERSION,
        "session_runtime": runtime.model_dump(mode="json"),
    }


async def llm_snapshot() -> dict:
    from tests.ai.helpers import stored_config

    config_id = await stored_config()
    found = await config.get(config_id)
    assert found is not None
    return snapshot(str(config_id), found.spec.effort_levels[0].name)


def seats(url: str, game_id: str) -> list[tuple]:
    """Each Seat's occupancy rows in order: (role, kind, reason, user id)."""
    return query(
        url,
        "SELECT s.role, o.occupant_kind, o.reason, o.user_id::text FROM seat_occupancy o "
        "JOIN seats s ON s.id = o.seat_id WHERE s.game_id = %s ORDER BY s.position, o.id",
        (game_id,),
    )


async def test_free_seats_get_rule_based_players_and_students_stay(games_db):
    game_id = await class_game()
    await commands.assign_seat(game_id, "retailer", "student", user_id=A)
    with listening(games_db) as events:
        assert await commands.set_snapshot(game_id, snapshot(), keep_students=[A]) is True
        received = events.drain()
    assert seats(games_db, game_id) == [
        ("retailer", "student", "initial", str(A)),
        ("wholesaler", "rule_based", "initial", None),
        ("distributor", "rule_based", "initial", None),
        ("factory", "rule_based", "initial", None),
    ]
    game = await service.get_game(game_id)
    assert game.settings == SETTINGS and game.demand_seed == 11
    assert game.session_runtime.inactivity_limit_hours == 24
    # One version step, its Class session told, and the seated Student's pages reload.
    assert version(games_db, game_id) == 3
    assert {(e["topic"], e["id"]) for e in received} == {
        ("game", game_id),
        ("session", str(SESSION)),
        ("user", str(A)),
    }
    assert {e["topic"] for e in received} == COMMAND_TOPICS["games.set_snapshot"]
    # A second call changes nothing: no row, no version, no event.
    with listening(games_db) as events:
        assert await commands.set_snapshot(game_id, snapshot(), keep_students=[]) is False
        assert events.drain() == []
    assert version(games_db, game_id) == 3
    assert len(seats(games_db, game_id)) == 4
    # Now it starts, and the Student's Seat waits in Week 1 with no Rule-based fill.
    assert await commands.start(game_id) == 1


async def test_llm_mode_fills_with_llm_players_and_replaces_a_removed_student(games_db, ai_db):
    game_id = await class_game()
    await commands.assign_seat(game_id, "retailer", "student", user_id=A)
    await commands.assign_seat(game_id, "factory", "student", user_id=B)
    with listening(games_db) as events:
        await commands.set_snapshot(game_id, await llm_snapshot(), keep_students=[A])
        received = events.drain()
    assert seats(games_db, game_id) == [
        ("retailer", "student", "initial", str(A)),
        ("wholesaler", "llm", "initial", None),
        ("distributor", "llm", "initial", None),
        # The removed Student's row stays in the history, under the AI player.
        ("factory", "student", "initial", str(B)),
        ("factory", "llm", "initial", None),
    ]
    assert {e["id"] for e in received if e["topic"] == "user"} == {str(A), str(B)}


async def test_start_racing_set_snapshot_never_fills_against_the_ai_mode(games_db, ai_db):
    frozen = await llm_snapshot()
    for number in (1, 2, 3):
        game_id = await class_game(number)
        await commands.assign_seat(game_id, "retailer", "student", user_id=uuid.uuid7())
        started, opened = await asyncio.gather(
            commands.start(game_id),
            commands.set_snapshot(game_id, frozen, keep_students=[]),
            return_exceptions=True,
        )
        assert opened is True
        kinds = {kind for _, kind, _, _ in seats(games_db, game_id)}
        assert kinds == {"student", "llm"}  # never a Rule-based fill
        if isinstance(started, commands.CommandError):
            assert (started.code, started.status) == ("game_not_ready", 409)
            assert (await service.get_game(game_id)).lifecycle == "not_started"
        else:
            assert started == 1
            assert (await service.get_game(game_id)).lifecycle == "running"


async def test_set_snapshot_refusals(games_db):
    simulation = await commands.create("simulation", SETTINGS, seed=1)
    await assert_refused(
        games_db,
        simulation,
        "snapshot_not_allowed",
        422,
        commands.set_snapshot(simulation, snapshot(), keep_students=[]),
    )
    game_id = await class_game()
    broken = {**snapshot(), "demand_series": [1, 2, 3]}
    missing = {k: v for k, v in snapshot().items() if k != "rules_version"}
    for bad in (broken, missing, {**snapshot(), "settings": {"weeks": -1}}):
        await assert_refused(
            games_db,
            game_id,
            "invalid_snapshot",
            422,
            commands.set_snapshot(game_id, bad, keep_students=[]),
        )
    with pytest.raises(commands.CommandError) as caught:
        await commands.set_snapshot(str(uuid.uuid7()), snapshot(), keep_students=[])
    assert caught.value.code == "game_not_found"


async def test_assign_seat_replaces_only_when_asked_and_only_before_the_start(games_db):
    game_id = await class_game()
    await commands.assign_seat(game_id, "retailer", "student", user_id=A)
    await assert_refused(
        games_db,
        game_id,
        "seat_occupied",
        409,
        commands.assign_seat(game_id, "retailer", "rule_based"),
    )
    await commands.assign_seat(game_id, "retailer", "rule_based", replace=True)
    assert seats(games_db, game_id) == [
        ("retailer", "student", "initial", str(A)),
        ("retailer", "rule_based", "initial", None),
    ]
    await commands.set_snapshot(game_id, snapshot(), keep_students=[])
    await commands.start(game_id)
    await assert_refused(
        games_db,
        game_id,
        "game_already_started",
        409,
        commands.assign_seat(game_id, "retailer", "student", user_id=B, replace=True),
    )
