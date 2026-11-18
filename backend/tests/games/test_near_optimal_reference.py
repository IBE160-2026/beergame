"""Story 2.9: every turn stores the near-optimal reference Order and its algorithm version when
the Week opens, and `place_order` copies both into the Decision log (FR-67, FR-79, AD-5)."""

import json
from pathlib import Path

import psycopg
import pytest

from app.engine import GameSettings, WeekState, demand_series, near_optimal
from app.engine.demand import DemandStep
from app.modules.games import commands, service
from tests.games.helpers import execute, play_week, query, seat_student

GOLDEN = Path(__file__).parents[1] / "engine" / "golden" / "near-optimal-classic-step.json"
WEEKS = 8
"""Stored Games are kept short; the engine test checks all 36 Weeks of the golden file."""


def stored_turns(url: str, game_id: str) -> list[tuple]:
    """(week, role, near-optimal Order, algorithm version) per turn."""
    return query(
        url,
        "SELECT t.week, s.role, t.near_optimal_reference_order, t.near_optimal_algorithm_version "
        "FROM seat_turns t JOIN seats s ON s.id = t.seat_id WHERE t.game_id = %s "
        "ORDER BY t.week, s.position",
        (game_id,),
    )


def week_states(url: str, game_id: str) -> dict[int, WeekState]:
    rows = query(url, "SELECT week, state FROM game_weeks WHERE game_id = %s", (game_id,))
    return {week: WeekState.model_validate(state) for week, state in rows}


async def test_every_seat_gets_the_engines_reference_whoever_holds_it(games_db):
    settings = GameSettings(demand_seed=1, guided_weeks=1)
    game_id = await commands.create("simulation", settings, seed=1)
    await commands.assign_seat(game_id, "wholesaler", "scripted", "constant-4")
    seat_student(games_db, game_id, "retailer", "factory")  # the distributor gets Rule-based
    await commands.start(game_id)
    for _ in range(2):  # past the Guided Week
        await play_week(game_id)
    turns = stored_turns(games_db, game_id)
    assert {row[0] for row in turns} == {1, 2, 3}
    states = week_states(games_db, game_id)
    series = demand_series(settings)
    for week, role, value, version in turns:
        assert value == near_optimal.order(settings, states[week], series, week, role)
        assert version == "placeholder-0"
    logged = await service.decision_log(game_id)
    assert len(logged) == 4 * 2 + 2  # in Week 3 the scripted and Rule-based Seats have ordered
    by_turn = {(week, role): (value, version) for week, role, value, version in turns}
    for row in logged:
        expected = by_turn[(row.week, row.role)]
        assert (row.near_optimal_reference_order, row.near_optimal_algorithm_version) == expected
    assert {row.occupant_kind for row in logged} == {"student", "scripted", "rule_based"}
    overview = await service.open_turn(game_id, "factory")
    assert (overview.near_optimal_reference_order, overview.near_optimal_algorithm_version) == (
        by_turn[(3, "factory")]
    )


async def test_a_classic_step_game_stores_both_golden_series(games_db):
    """The first WEEKS Weeks, to keep the test fast: demand is 8 from Week 5 to the end, so a
    shorter Game sees the same demand after its last Week and stores the same references."""
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    settings = GameSettings.model_validate({**golden["settings"], "weeks": WEEKS})
    game_id = await commands.create("simulation", settings, seed=1)
    await commands.start(game_id)  # four Rule-based players play it to the end
    logged = await service.decision_log(game_id)
    weeks = WEEKS
    assert len(logged) == 4 * weeks
    golden = {key: value[:weeks] for key, value in golden.items() if isinstance(value, list)} | {
        "algorithm_version": golden["algorithm_version"]
    }

    def series(field: str) -> list[dict[str, int]]:
        return [
            {row.role: getattr(row, field) for row in logged if row.week == week}
            for week in range(1, weeks + 1)
        ]

    assert series("order") == golden["orders"]
    assert series("rule_based_reference_order") == golden["rule_based"]
    assert series("near_optimal_reference_order") == golden["near_optimal"]
    assert {row.near_optimal_algorithm_version for row in logged} == {golden["algorithm_version"]}


async def test_the_references_coincide_in_every_stored_week_under_constant_demand(games_db):
    """All 36 Weeks, as the spec's matrix asks (the slowest test of this file)."""
    settings = GameSettings(demand=DemandStep(kind="step", start=4, new_level=4, change_week=5))
    game_id = await commands.create("simulation", settings, seed=1)
    await commands.start(game_id)
    logged = await service.decision_log(game_id)
    assert len(logged) == 4 * 36
    for row in logged:
        assert row.rule_based_reference_order == row.near_optimal_reference_order == 4


async def test_the_near_optimal_reference_can_never_change(games_db):
    game_id = await commands.create("simulation", GameSettings(demand_seed=1), seed=1)
    seat_student(games_db, game_id, "retailer", "wholesaler", "distributor", "factory")
    await commands.start(game_id)
    for statement in (
        "UPDATE seat_turns SET near_optimal_reference_order = near_optimal_reference_order + 1",
        "UPDATE seat_turns SET near_optimal_reference_order = NULL, "
        "near_optimal_algorithm_version = NULL",
        "UPDATE seat_turns SET near_optimal_algorithm_version = 'placeholder-1'",
    ):
        with pytest.raises(psycopg.errors.RestrictViolation, match="keeps its opening values"):
            execute(games_db, statement)
    with pytest.raises(psycopg.errors.CheckViolation, match="ck_seat_turns_near_optimal_pair"):
        execute(
            games_db,
            "INSERT INTO seat_turns (id, game_id, seat_id, week, rule_based_reference_order, "
            "near_optimal_reference_order) SELECT gen_random_uuid(), game_id, seat_id, 2, 4, 4 "
            "FROM seat_turns WHERE game_id = %s LIMIT 1",
            (game_id,),
        )
