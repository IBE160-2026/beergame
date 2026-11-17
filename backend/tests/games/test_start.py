"""Story 1.8: `games.commands.start` opens Week 1 with one turn per Seat."""

import asyncio
import json
import uuid

import psycopg
import pytest

from app.engine import GameSettings, WeekState, initial_state, rule_based, seat_view
from app.modules.games import commands, service
from app.platform.parameter_sets import read_parameter_set
from tests.conftest import libpq_dsn
from tests.games.helpers import execute, listening, query


async def new_game(**settings) -> str:
    return await commands.create("simulation", GameSettings(**settings), seed=1)


def state(url: str, game_id: str) -> tuple:
    """Lifecycle, version and the row counts `start` writes."""
    ((lifecycle, version),) = query(
        url, "SELECT lifecycle, version FROM games WHERE id = %s", (game_id,)
    )
    ((weeks, turns, occupancy),) = query(
        url,
        "SELECT (SELECT count(*) FROM game_weeks WHERE game_id = %s), "
        "(SELECT count(*) FROM seat_turns WHERE game_id = %s), "
        "(SELECT count(*) FROM seat_occupancy o JOIN seats s ON s.id = o.seat_id "
        "WHERE s.game_id = %s)",
        (game_id, game_id, game_id),
    )
    return lifecycle, version, weeks, turns, occupancy


def turns(url: str, game_id: str) -> list[tuple]:
    return query(
        url,
        "SELECT s.role, t.week, t.opened_at, t.ordered_at, t.rule_based_reference_order, t.id "
        "FROM seat_turns t JOIN seats s ON s.id = t.seat_id WHERE t.game_id = %s "
        "ORDER BY s.position",
        (game_id,),
    )


def default_params() -> rule_based.RuleBasedParams:
    set_id = rule_based.DEFAULT_SET_ID
    return rule_based.parse_params(read_parameter_set("rule_based", set_id), set_id)


async def test_start_opens_week_1_with_one_turn_per_seat(games_db):
    game_id = await new_game()
    for role in ("retailer", "wholesaler", "distributor", "factory"):
        await commands.assign_seat(game_id, role, "scripted", "constant-4")
    with listening(games_db) as events:
        week = await commands.start(game_id)
        received = events.drain()
    assert week == 1
    assert state(games_db, game_id) == ("running", 6, 1, 4, 4)
    assert received == [{"topic": "game", "id": game_id, "version": 6}]
    ((stored,),) = query(games_db, "SELECT state FROM game_weeks WHERE game_id = %s", (game_id,))
    settings = GameSettings(demand_seed=1)
    assert WeekState.model_validate(stored) == initial_state(settings)
    rows = turns(games_db, game_id)
    assert [row[:2] for row in rows] == [
        ("retailer", 1),
        ("wholesaler", 1),
        ("distributor", 1),
        ("factory", 1),
    ]
    assert len({row[2] for row in rows}) == 1  # one transaction, one `now()`
    assert all(row[2] is not None and row[3] is None for row in rows)
    assert all(uuid.UUID(str(row[5])).version == 7 for row in rows)
    params = default_params()
    expected = [
        rule_based.order(settings, seat_view(settings, [initial_state(settings)], [], r), params)
        for r in settings.roles
    ]
    assert [row[4] for row in rows] == expected
    game = await service.get_game(game_id)
    assert game is not None and game.lifecycle == "running"
    assert {seat.occupant_kind for seat in game.seats} == {"scripted"}  # kept as assigned


@pytest.mark.parametrize("assigned", [0, 1, 3])
async def test_start_gives_every_free_seat_a_rule_based_player(games_db, assigned):
    game_id = await new_game()
    roles = ["retailer", "wholesaler", "distributor", "factory"]
    for role in roles[:assigned]:
        await commands.assign_seat(game_id, role, "scripted", "constant-4")
    await commands.start(game_id)
    rows = query(
        games_db,
        "SELECT s.role, o.from_week, o.occupant_kind, o.policy_id, o.reason "
        "FROM seat_occupancy o JOIN seats s ON s.id = o.seat_id ORDER BY s.position",
    )
    assert rows == [(role, 1, "scripted", "constant-4", "initial") for role in roles[:assigned]] + [
        (role, 1, "rule_based", None, "initial") for role in roles[assigned:]
    ]
    assert state(games_db, game_id)[0] == "running"


async def test_starting_twice_answers_a_conflict_and_changes_nothing(games_db):
    game_id = await new_game()
    await commands.start(game_id)
    before = state(games_db, game_id)
    first = turns(games_db, game_id)
    with listening(games_db) as events:
        with pytest.raises(commands.CommandError) as caught:
            await commands.start(game_id)
        assert events.drain() == []
    assert (caught.value.code, caught.value.status) == ("game_already_started", 409)
    assert state(games_db, game_id) == before
    assert turns(games_db, game_id) == first


@pytest.mark.parametrize("game_id", ["nope", str(uuid.uuid7()), None, 5])
async def test_an_unknown_game_cannot_start(games_db, game_id):
    with pytest.raises(commands.CommandError) as caught:
        await commands.start(game_id)  # type: ignore[arg-type]
    assert (caught.value.code, caught.value.status) == ("game_not_found", 404)


async def assert_start_refused(url: str, game_id: str, code: str, status: int) -> None:
    before = state(url, game_id)
    with listening(url) as events:
        with pytest.raises(commands.CommandError) as caught:
            await commands.start(game_id)
        assert events.drain() == []
    assert (caught.value.code, caught.value.status) == (code, status)
    assert state(url, game_id) == before
    assert before[0] == "not_started"


async def test_a_tampered_demand_series_is_refused(games_db):
    game_id = await new_game()
    execute(
        games_db,
        "UPDATE games SET demand_series = jsonb_set(demand_series, '{4}', '9') WHERE id = %s",
        (game_id,),
    )
    await assert_start_refused(games_db, game_id, "snapshot_mismatch", 409)


async def test_an_unknown_rules_version_is_refused(games_db):
    game_id = await new_game()
    execute(games_db, "UPDATE games SET rules_version = 99 WHERE id = %s", (game_id,))
    await assert_start_refused(games_db, game_id, "rules_version_unsupported", 409)


async def test_a_changed_parameter_set_version_is_refused(games_db):
    game_id = await new_game()
    execute(
        games_db,
        "UPDATE games SET session_runtime = jsonb_set(session_runtime, "
        "'{rule_based_params_version}', '999') WHERE id = %s",
        (game_id,),
    )
    await assert_start_refused(games_db, game_id, "parameter_set_changed", 409)


async def test_a_vanished_parameter_set_is_refused(games_db):
    game_id = await new_game()
    runtime = json.dumps(
        {
            "schema_version": 1,
            "ai_mode": "rule_based",
            "rule_based_params": "gone",
            "rule_based_params_version": 1,
        }
    )
    execute(
        games_db, "UPDATE games SET session_runtime = %s::jsonb WHERE id = %s", (runtime, game_id)
    )
    await assert_start_refused(games_db, game_id, "unknown_parameter_set", 422)


async def test_the_reference_order_and_opening_can_never_change(games_db):
    game_id = await new_game()
    await new_game()  # a second Game to move a turn to
    await commands.start(game_id)
    for statement in (
        "UPDATE seat_turns SET rule_based_reference_order = rule_based_reference_order + 1",
        "UPDATE seat_turns SET opened_at = now() - interval '1 hour'",
        "UPDATE seat_turns SET week = 2",
        "UPDATE seat_turns SET seat_id = (SELECT id FROM seats LIMIT 1)",
        "UPDATE seat_turns SET game_id = (SELECT id FROM games WHERE id <> %s LIMIT 1)",
        "DELETE FROM seat_turns",
    ):
        with pytest.raises(psycopg.errors.RestrictViolation, match="keeps its opening values"):
            execute(games_db, statement, (game_id,) if "%s" in statement else ())
    execute(games_db, "UPDATE seat_turns SET ordered_at = now()")  # Story 1.9 sets this
    assert all(row[3] is not None for row in turns(games_db, game_id))
    with pytest.raises(psycopg.errors.RestrictViolation, match="keeps its opening values"):
        execute(games_db, "UPDATE seat_turns SET ordered_at = now() - interval '1 hour'")
    with pytest.raises(psycopg.errors.RestrictViolation, match="keeps its opening values"):
        execute(games_db, "UPDATE seat_turns SET ordered_at = NULL")


async def test_start_waits_for_the_game_row_lock(games_db):
    game_id = await new_game()
    with psycopg.connect(libpq_dsn(games_db)) as holder:
        holder.execute("SELECT 1 FROM games WHERE id = %s FOR UPDATE", (game_id,))
        task = asyncio.create_task(commands.start(game_id))
        await asyncio.sleep(0.5)
        assert not task.done()
        holder.rollback()
        await asyncio.wait_for(task, timeout=5)
    assert state(games_db, game_id)[0] == "running"


async def test_two_starts_racing_open_week_1_once(games_db):
    game_id = await new_game()
    results = await asyncio.gather(
        commands.start(game_id), commands.start(game_id), return_exceptions=True
    )
    errors = [r for r in results if isinstance(r, commands.CommandError)]
    assert len(errors) == 1 and errors[0].code == "game_already_started"
    assert state(games_db, game_id) == ("running", 2, 1, 4, 4)


async def test_assign_after_start_is_refused(games_db):
    game_id = await new_game()
    await commands.start(game_id)
    with pytest.raises(commands.CommandError) as caught:
        await commands.assign_seat(game_id, "retailer", "rule_based")
    assert caught.value.code == "game_already_started"


async def test_each_turn_holds_the_reference_order_of_its_own_seat(games_db):
    # The Factory's starting supply line leaves out the backlog, so its Week 1 view differs.
    settings = {"starting_inventory": 0, "starting_backlog": 20}
    game_id = await new_game(**settings)
    await commands.start(game_id)
    effective = GameSettings(**settings, demand_seed=1)
    first = initial_state(effective)
    expected = [
        rule_based.order(effective, seat_view(effective, [first], [], role), default_params())
        for role in effective.roles
    ]
    assert len(set(expected)) > 1  # the Seats' Week 1 views differ
    assert [row[4] for row in turns(games_db, game_id)] == expected
