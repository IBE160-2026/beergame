"""The finished-game check (Story 1.10, AD-9, FR-29): replay, conservation, one immutable row."""

import asyncio
import sys
import types
from decimal import Decimal

import psycopg
import pytest
from structlog.testing import capture_logs

from app.engine import GameSettings, Role
from app.engine.rules import v1
from app.modules.games import commands, service
from tests.games.helpers import (
    classic_game,
    execute,
    listening,
    play_to_end,
    play_week,
    query,
    tamper,
)

GAME_TABLES = ("seats", "seat_occupancy", "game_weeks", "seat_turns", "seat_weeks")


async def finished_game(url: str) -> str:
    """The Classic Game of seed 7, played once per session; each call stores its own copy."""
    return await classic_game(url)


def game_rows(url: str, game_id: str) -> dict[str, list]:
    """Every stored row of the Game, for proving the check changes nothing."""
    snapshot = {"games": query(url, "SELECT * FROM games WHERE id = %s", (game_id,))}
    for table in GAME_TABLES:
        if table == "seat_occupancy":
            sql = (
                "SELECT o.* FROM seat_occupancy o JOIN seats s ON s.id = o.seat_id "
                "WHERE s.game_id = %s ORDER BY o.id"
            )
        else:
            sql = f"SELECT * FROM {table} WHERE game_id = %s ORDER BY 1, 2, 3"
        snapshot[table] = query(url, sql, (game_id,))
    return snapshot


def check_rows(url: str, game_id: str) -> list[tuple]:
    return query(
        url,
        "SELECT id, rules_version, ok, violations, checked_at FROM game_checks WHERE game_id = %s",
        (game_id,),
    )


def keys(check) -> set[tuple]:
    return {(v.rule, v.week, v.role) for v in check.violations}


async def test_a_finished_game_passes_and_stores_one_row(games_db):
    game_id = await finished_game(games_db)
    before = game_rows(games_db, game_id)
    with listening(games_db) as events, capture_logs() as logs:
        check = await service.verify_finished(game_id)
        assert events.drain() == []
    assert (check.ok, check.violations, check.rules_version, check.game_id) == (
        True,
        (),
        1,
        game_id,
    )
    ((row_id, version, ok, violations, checked_at),) = check_rows(games_db, game_id)
    assert (str(row_id), version, ok, violations, checked_at) == (
        check.id,
        1,
        True,
        [],
        check.checked_at,
    )
    assert game_rows(games_db, game_id) == before
    assert [entry["log_level"] for entry in logs] == ["info"]
    assert logs[0]["event"] == "game_check_passed"


async def test_a_second_call_returns_the_stored_result(games_db):
    game_id = await finished_game(games_db)
    first = await service.verify_finished(game_id)
    with capture_logs() as logs:
        second = await service.verify_finished(game_id)
    assert second == first
    assert len(check_rows(games_db, game_id)) == 1
    assert logs == []


async def test_concurrent_calls_store_one_row(games_db):
    game_id = await finished_game(games_db)
    results = await asyncio.gather(*(service.verify_finished(game_id) for _ in range(3)))
    assert len({result.id for result in results}) == 1
    assert len(check_rows(games_db, game_id)) == 1


async def test_a_changed_week_state_is_recorded_and_logged_with_ids_only(games_db):
    game_id = await finished_game(games_db)
    tamper(
        games_db,
        "UPDATE game_weeks SET state = jsonb_set(state, '{seats,0,inventory}', "
        "to_jsonb((state #>> '{seats,0,inventory}')::int + 1)) "
        "WHERE game_id = %s AND week = 10 AND NOT finished",
        (game_id,),
    )
    before = game_rows(games_db, game_id)
    with listening(games_db) as events, capture_logs() as logs:
        check = await service.verify_finished(game_id)
        assert events.drain() == []
    assert not check.ok
    found = keys(check)
    assert ("replay", 10, Role.RETAILER) in found
    assert ("inventory_balance", 10, Role.RETAILER) in found
    assert ("units_conserved", 10, None) in found
    ((_, _, ok, violations, _),) = check_rows(games_db, game_id)
    assert ok is False and len(violations) == len(check.violations)
    assert {"rule", "week", "role"} <= violations[0].keys()
    assert game_rows(games_db, game_id) == before
    errors = [entry for entry in logs if entry["log_level"] == "error"]
    assert errors == [
        {
            "event": "game_check_failed",
            "log_level": "error",
            "game_id": game_id,
            "check_id": check.id,
            "violation_count": len(check.violations),
        }
    ]


async def test_a_changed_order_is_recorded_from_the_week_it_reaches(games_db):
    game_id = await finished_game(games_db)
    tamper(
        games_db,
        'UPDATE seat_weeks w SET "order" = w."order" + 3 FROM seats s '
        "WHERE s.id = w.seat_id AND w.game_id = %s AND w.week = 7 AND s.role = 'wholesaler'",
        (game_id,),
    )
    check = await service.verify_finished(game_id)
    replayed = {(week, role) for rule, week, role in keys(check) if rule == "replay"}
    assert replayed and min(week for week, _ in replayed) == 8
    assert (8, Role.DISTRIBUTOR) in replayed


async def test_a_changed_cost_is_recorded_with_week_and_role(games_db):
    game_id = await finished_game(games_db)
    tamper(
        games_db,
        "UPDATE game_weeks SET state = jsonb_set(state, '{seats,2,cost}', '\"99.00\"') "
        "WHERE game_id = %s AND week = 12 AND NOT finished",
        (game_id,),
    )
    tamper(
        games_db,
        "UPDATE seat_weeks w SET state_seen = jsonb_set(state_seen, '{week_cost}', '\"77.00\"') "
        "FROM seats s WHERE s.id = w.seat_id AND w.game_id = %s AND w.week = 20 "
        "AND s.role = 'factory'",
        (game_id,),
    )
    found = keys(await service.verify_finished(game_id))
    assert {
        ("replay", 12, Role.DISTRIBUTOR),
        ("cost", 12, Role.DISTRIBUTOR),
        ("decision_log", 20, Role.FACTORY),
    } <= found


async def test_an_unreadable_decision_log_row_is_recorded(games_db):
    game_id = await finished_game(games_db)
    tamper(
        games_db,
        "UPDATE seat_weeks w SET state_seen = '{}' FROM seats s WHERE s.id = w.seat_id "
        "AND w.game_id = %s AND w.week = 3 AND s.role = 'retailer'",
        (game_id,),
    )
    check = await service.verify_finished(game_id)
    assert keys(check) == {("decision_log", 3, Role.RETAILER)}
    assert "state_seen" in check.violations[0].message


async def test_a_broken_snapshot_or_week_state_is_recorded(games_db):
    series = await finished_game(games_db)
    tamper(
        games_db,
        "UPDATE games SET demand_series = demand_series || '[1]'::jsonb WHERE id = %s",
        (series,),
    )
    assert ("snapshot", None, None) in keys(await service.verify_finished(series))

    settings = await finished_game(games_db)
    tamper(
        games_db,
        "UPDATE games SET settings = settings || '{\"weeks\": -1}'::jsonb WHERE id = %s",
        (settings,),
    )
    assert keys(await service.verify_finished(settings)) == {("snapshot", None, None)}

    state = await finished_game(games_db)
    tamper(
        games_db,
        "UPDATE game_weeks SET state = '{\"week\": 1}' WHERE game_id = %s AND week = 6",
        (state,),
    )
    tamper(
        games_db,
        "UPDATE game_weeks SET state = jsonb_set(state, '{week}', '8') "
        "WHERE game_id = %s AND week = 7",
        (state,),
    )
    assert keys(await service.verify_finished(state)) == {
        ("stored_state", 6, None),
        ("stored_state", 7, None),
    }


async def test_a_missing_decision_log_row_skips_the_log_check(games_db):
    game_id = await finished_game(games_db)
    tamper(
        games_db,
        "DELETE FROM seat_weeks w USING seats s WHERE s.id = w.seat_id AND w.game_id = %s "
        "AND w.week = 30 AND s.role = 'factory'",
        (game_id,),
    )
    found = keys(await service.verify_finished(game_id))
    assert ("orders_shape", 30, Role.FACTORY) in found
    assert ("replay", 30, Role.FACTORY) in found
    assert not any(rule == "decision_log" for rule, _, _ in found)


@pytest.mark.parametrize("game_id", ["nope", "01a1eb10-f299-75a6-8ec2-a251c50791e1", None])
async def test_an_unknown_game_is_refused(games_db, game_id):
    with pytest.raises(service.ViewError) as caught:
        await service.verify_finished(game_id)
    assert (caught.value.code, caught.value.status) == ("game_not_found", 404)


async def test_an_unfinished_game_is_refused_and_nothing_is_stored(games_db):
    from tests.games.helpers import seat_student

    game_id = await commands.create("simulation", GameSettings(), seed=7)
    seat_student(games_db, game_id, "retailer")  # the Game waits for the Student
    await commands.start(game_id)
    await play_week(game_id)
    with pytest.raises(service.ViewError) as caught:
        await service.verify_finished(game_id)
    assert (caught.value.code, caught.value.status) == ("game_not_finished", 409)
    assert check_rows(games_db, game_id) == []


async def test_a_version_without_a_package_is_refused_and_listed(games_db):
    game_id = await finished_game(games_db)
    assert await service.rules_versions_without_package() == ()
    execute(games_db, "UPDATE games SET rules_version = 99 WHERE id = %s", (game_id,))
    with pytest.raises(service.ViewError) as caught:
        await service.verify_finished(game_id)
    assert (caught.value.code, caught.value.status) == ("rules_version_unsupported", 409)
    assert check_rows(games_db, game_id) == []
    assert await service.rules_versions_without_package() == (99,)


async def test_every_stored_rules_version_has_a_package(games_db):
    """AD-4: fails when a Game in the test database names a rules version with no package."""
    await finished_game(games_db)
    game_id = await commands.create("simulation", GameSettings(), seed=3)
    await commands.start(game_id)
    assert await service.rules_versions_without_package() == ()


async def test_a_game_finished_under_v1_verifies_and_replays_differently_at_v2(
    games_db, monkeypatch
):
    def advance_v2(settings, state, orders):
        following = v1.advance(settings, state, orders)
        seats = tuple(seat.model_copy(update={"cost": seat.cost * 2}) for seat in following.seats)
        return following.model_copy(update={"seats": seats})

    v2 = types.ModuleType("app.engine.rules.v2")
    v2.initial_state = v1.initial_state
    v2.advance = advance_v2
    monkeypatch.setitem(sys.modules, "app.engine.rules.v2", v2)

    under_v1 = await finished_game(games_db)
    assert (await service.verify_finished(under_v1)).ok
    at_v2 = await finished_game(games_db)
    execute(games_db, "UPDATE games SET rules_version = 2 WHERE id = %s", (at_v2,))
    check = await service.verify_finished(at_v2)
    assert not check.ok and check.rules_version == 2
    assert {v.rule for v in check.violations} >= {"replay"}
    assert ("replay", 2, Role.RETAILER) in keys(check)
    ((_, version, ok, _, _),) = check_rows(games_db, at_v2)
    assert (version, ok) == (2, False)


async def test_a_game_check_row_is_append_only(games_db):
    game_id = await finished_game(games_db)
    await service.verify_finished(game_id)
    for sql in (
        "UPDATE game_checks SET ok = false, violations = '[{}]' WHERE game_id = %s",
        "DELETE FROM game_checks WHERE game_id = %s",
    ):
        with pytest.raises(psycopg.errors.RestrictViolation):
            execute(games_db, sql, (game_id,))


@pytest.mark.parametrize(("ok", "violations"), [(True, "[{}]"), (False, "[]")])
async def test_ok_must_match_the_violations(games_db, ok, violations):
    game_id = await commands.create("simulation", GameSettings(), seed=1)
    with pytest.raises(psycopg.errors.CheckViolation):
        execute(
            games_db,
            "INSERT INTO game_checks (id, game_id, rules_version, ok, violations) "
            "VALUES (gen_random_uuid(), %s, 1, %s, %s)",
            (game_id, ok, violations),
        )


async def test_commands_run_the_stored_rules_version(games_db, monkeypatch):
    """AD-4: `start` and `place_order` use the Game's stored version, not the newest one."""

    def initial_v2(settings):
        state = v1.initial_state(settings)
        seats = tuple(seat.model_copy(update={"cost": seat.cost * 2}) for seat in state.seats)
        return state.model_copy(update={"seats": seats})

    def advance_v2(settings, state, orders):
        following = v1.advance(settings, state, orders)
        seats = tuple(seat.model_copy(update={"cost": seat.cost * 2}) for seat in following.seats)
        return following.model_copy(update={"seats": seats})

    v2 = types.ModuleType("app.engine.rules.v2")
    v2.initial_state = initial_v2
    v2.advance = advance_v2
    monkeypatch.setitem(sys.modules, "app.engine.rules.v2", v2)

    plain = await finished_game(games_db)
    game_id = await commands.create("simulation", GameSettings(), seed=7)
    execute(games_db, "UPDATE games SET rules_version = 2 WHERE id = %s", (game_id,))
    await commands.start(game_id)
    await play_to_end(game_id)
    sql = (
        "SELECT state #>> '{seats,0,cost}' FROM game_weeks "
        "WHERE game_id = %s AND week = 3 AND NOT finished"
    )
    ((cost_v1,),) = query(games_db, sql, (plain,))
    ((cost_v2,),) = query(games_db, sql, (game_id,))
    assert Decimal(cost_v2) == 2 * Decimal(cost_v1) != 0
    check = await service.verify_finished(game_id)
    assert check.rules_version == 2
    assert not any(v.rule == "replay" for v in check.violations)
