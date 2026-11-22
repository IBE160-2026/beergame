"""Story 9.1: `games.facts` stores one facts set per Seat of a finished Game (FR-44, AD-7, AD-14,
AD-23), and `python -m app.sim facts` prints them (AD-22).

Three golden Games fix the sets: the addendum §B reference trace (constant demand 4, every Order
4), a Class game with a Takeover, and the Classic Game played fully by Rule-based players. Each
Seat's stored payload must equal its file in `tests/golden/facts/`, and every number in it must
equal the value this file recomputes from the raw `seat_weeks` rows. After a deliberate change of
the rules, rewrite the files with `UPDATE_GOLDEN=1 uv run pytest -n0 tests/games/test_facts.py`
and review the diff."""

import asyncio
import json
import os
import re
import statistics
import uuid
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path
from unittest import mock

import pytest

from app import sim
from app.analysis.facts import ANALYSIS_VERSION, FactSet
from app.analysis.moments import position
from app.analysis.moments import render as render_moments
from app.analysis.patterns import PatternSet
from app.analysis.simulated import simulate
from app.engine import ROLES, RULES_VERSION, DemandFixed, GameSettings, demand_series
from app.modules.content import service as content
from app.modules.games import commands, facts
from app.modules.games.views import ViewError
from app.sim import load_rule_based_params
from tests.analysis.test_moments import TEMPLATES as MOMENT_TEMPLATES
from tests.analysis.test_moments import assert_every_number_from_the_facts
from tests.analysis.test_patterns import V1
from tests.conftest import TEST_DATABASE_URL
from tests.content.test_content import UNSHIPPED
from tests.games.helpers import (
    classic_game,
    execute,
    play_to_end,
    played_once,
    query,
    tamper,
)

GOLDEN = Path(__file__).parents[1] / "golden" / "facts"
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
PLACES = Decimal("0.001")
TAKEOVER_ORDERS = (4, 6, 12, 16, 16, 12, 8, 2, 0, 4, 8, 8)
"""The Student's Orders in Weeks 3-14 of the Takeover Game; a Rule-based player from Week 15."""


@pytest.fixture(autouse=True)
def only_version_1(test_database):
    execute(TEST_DATABASE_URL, UNSHIPPED)
    yield
    execute(TEST_DATABASE_URL, UNSHIPPED)


def _snapshot(settings: GameSettings, pins: dict | None) -> dict:
    runtime = commands.default_runtime(
        model_config_id=None, effort_level=None, inactivity_limit_hours=24, pins=pins
    )
    return {
        "settings": settings.model_dump(mode="json"),
        "demand_series": list(demand_series(settings)),
        "demand_seed": settings.demand_seed,
        "rules_version": RULES_VERSION,
        "session_runtime": runtime.model_dump(mode="json"),
    }


async def reference_trace() -> str:
    """Addendum §B: constant demand 4 and every Order 4 (scripted `constant-4` Seats), 8 Weeks."""

    async def play() -> str:
        demand = DemandFixed(kind="fixed", values=(4,) * 8)
        settings = GameSettings(weeks=8, guided_weeks=2, demand=demand)
        game_id = await commands.create("simulation", settings, seed=1)
        for role in ROLES:
            await commands.assign_seat(game_id, role, "scripted", "constant-4")
        await commands.start(game_id)
        await play_to_end(game_id)
        return game_id

    return await played_once(TEST_DATABASE_URL, "facts reference trace", play)


async def class_game(weeks: int, pins: dict | None, orders: tuple[int, ...]) -> str:
    """A Class game with a Student on the Retailer: Guided Weeks 1-2 viewed, `orders` from Week
    3, then a Takeover (`takeover_inactivity`) and Rule-based Orders to the end."""
    settings = GameSettings(weeks=weeks, guided_weeks=2, demand_seed=11)
    game_id = await commands.create("class", class_session_id=uuid.uuid7(), game_number=1)
    user = uuid.uuid7()
    await commands.assign_seat(game_id, "retailer", "student", user_id=user)
    await commands.set_snapshot(game_id, _snapshot(settings, pins), keep_students=[user])
    # No Class session or User row stands behind the ids: `finish` records no step here.
    with mock.patch.object(commands.progress, "record_step", mock.AsyncMock()):
        await commands.start(game_id)
        for week in (1, 2):
            await commands.view_week(game_id, "retailer", week, actor=user)
        for week, order in enumerate(orders, start=3):
            await commands.place_order(game_id, "retailer", week, order, "student", actor=user)
        await commands.switch_to_rule_based(game_id, "retailer", "takeover_inactivity")
        await play_to_end(game_id)
    return game_id


async def takeover_game() -> str:
    async def play() -> str:
        return await class_game(16, {"detected_patterns": {"version": 1}}, TAKEOVER_ORDERS)

    return await played_once(TEST_DATABASE_URL, "facts takeover", play)


async def stored_sets(game_id: str) -> dict[str, facts.StoredFactSet]:
    return {role.value: await facts.get_or_create(game_id, role.value) for role in ROLES}


def raw_rows(game_id: str) -> dict[tuple[int, str], dict]:
    """The Game's `seat_weeks` rows straight from SQL, by (Week, Role)."""
    found = query(
        TEST_DATABASE_URL,
        'SELECT w.week, s.role, w."order", w.decided_by, w.occupant_kind, w.state_seen '
        "FROM seat_weeks w JOIN seats s ON s.id = w.seat_id WHERE w.game_id = %s",
        (game_id,),
    )
    return {
        (week, role): {"order": order, "decided_by": by, "occupant_kind": kind, "seen": seen}
        for week, role, order, by, kind, seen in found
    }


def _money(value: object) -> Decimal:
    return Decimal(str(value))


def _cost(seen: dict, kind: str) -> Decimal:
    return sum((_money(c["amount"]) for c in seen["cost_lines"] if c["kind"] == kind), Decimal(0))


def _std(values: list[int]) -> Decimal:
    return statistics.pstdev([Decimal(v) for v in values])


def _q(value: Decimal) -> str:
    return str(value.quantize(PLACES, rounding=ROUND_HALF_EVEN))


def _seen(role: str, raw: dict) -> dict:
    seen = raw["seen"]
    keys = ("incoming_order", "incoming_delivery", "shipped", "inventory", "backlog")
    return {
        "role": role,
        **{key: seen[key] for key in keys},
        "supply_line": seen["supply_line"],
        "week_cost": str(_money(seen["week_cost"])),
    }


def _matching(raw: dict[tuple[int, str], dict], role: str, weeks: int) -> set[str]:
    """The pattern ids version 1's thresholds give, recomputed here."""
    surge, large, low = V1["patterns"]
    found = set()
    for week in range(1, weeks + 1):
        row = raw[(week, role)]
        if row["decided_by"] == "guided":
            continue
        seen, order = row["seen"], row["order"]
        inc = seen["incoming_order"]
        backlogs = [raw[(w, role)]["seen"]["backlog"] for w in range(max(1, week - 2), week + 1)]
        above = order >= Decimal("1.5") * inc and order - inc >= 4
        if above and any(backlogs):
            found.add(f"{surge['id']}:{role}:{week}")
        if above and seen["supply_line"] >= 6 * max(inc, 1):
            found.add(f"{large['id']}:{role}:{week}")
        if (
            order <= Decimal("0.5") * inc
            and inc - order >= 2
            and seen["inventory"] >= 4 * max(inc, 1)
        ):
            found.add(f"{low['id']}:{role}:{week}")
    return found


def assert_recomputed(game_id: str, sets: dict[str, facts.StoredFactSet]) -> None:
    """Every number of every Seat's set equals the value recomputed from the raw rows."""
    raw = raw_rows(game_id)
    weeks = max(week for week, _ in raw)
    assert len(raw) == weeks * len(ROLES)
    demand = [raw[(w, "retailer")]["seen"]["incoming_order"] for w in range(1, weeks + 1)]
    demand_std = _std(demand)
    chains = {
        json.dumps(s.facts.chain.model_dump(mode="json"), sort_keys=True) for s in sets.values()
    }
    assert len(chains) == 1, "the chain part differs between Seats"
    chain = next(iter(sets.values())).facts.chain.model_dump(mode="json")
    assert chain["weeks"] == weeks and chain["demand"] == demand
    assert chain["demand_std"] == _q(demand_std)
    for got in chain["by_role"]:
        rows = [raw[(w, got["role"])] for w in range(1, weeks + 1)]
        orders = [row["order"] for row in rows]
        assert got["orders_std"] == _q(_std(orders))
        expected = _q(_std(orders) / demand_std) if demand_std else None
        assert got["amplification"] == expected
        large = [w for w, o in enumerate(orders, start=1) if o >= 10]
        assert got["first_large_order_week"] == (large[0] if large else None)
        assert got["holding_cost"] == str(
            sum((_cost(r["seen"], "holding") for r in rows), Decimal(0))
        )
        assert got["backorder_cost"] == str(
            sum((_cost(r["seen"], "backorder") for r in rows), Decimal(0))
        )
        assert got["total_cost"] == str(
            sum((_money(r["seen"]["week_cost"]) for r in rows), Decimal(0))
        )
    total = sum((_money(r["seen"]["week_cost"]) for r in raw.values()), Decimal(0))
    ai = sum(
        (_money(r["seen"]["week_cost"]) for r in raw.values() if r["occupant_kind"] != "student"),
        Decimal(0),
    )
    assert (chain["total_cost"], chain["ai_held_cost"]) == (str(total), str(ai))
    assert chain["ai_held_share"] == (_q(ai / total) if total else None)
    # The engine's own Total cost of the finished Game agrees.
    [(finished,)] = query(
        TEST_DATABASE_URL,
        "SELECT state FROM game_weeks WHERE game_id = %s AND finished",
        (game_id,),
    )
    assert sum((_money(seat["total_cost"]) for seat in finished["seats"]), Decimal(0)) == total

    for role, stored in sets.items():
        seat = stored.facts.seat.model_dump(mode="json")
        own = [raw[(w, role)] for w in range(1, weeks + 1)]
        students = sum(1 for row in own if row["decided_by"] == "student")
        assert (seat["role"], seat["student_orders"]) == (role, students)
        assert seat["sm_excluded"] is (students < 10)
        assert {o["id"] for o in seat["patterns"]} == _matching(raw, role, weeks)
        for item in seat["patterns"] + seat["moments"]:
            week = item["week"]
            row = raw[(week, role)]
            assert item["order"] == row["order"]
            assert item["state_seen"] == _seen(role, row)
            later = [raw[(w, role)] for w in range(week + 1, min(week + 4, weeks) + 1)]
            assert item["later_weeks"] == len(later)
            assert item["later_cost"] == str(
                sum((_money(r["seen"]["week_cost"]) for r in later), Decimal(0))
            )
            others = [_seen(r.value, raw[(week, r.value)]) for r in ROLES if r.value != role]
            assert item["others_seen"] == others
        for moment in seat["moments"]:
            assert raw[(moment["week"], role)]["decided_by"] == "student"
        if not seat["sm_excluded"]:
            assert len(seat["moments"]) == 3
    assert_simulated(game_id, sets)


def assert_simulated(game_id: str, sets: dict[str, facts.StoredFactSet]) -> None:
    """Story 9.8: each Seat's «Simulert, samme kunder» rows are `analysis.simulated` run over the
    Game's own snapshot and frozen Rule-based set; the `all` row is the same for every Seat."""
    [(settings, rules_version, series, runtime)] = query(
        TEST_DATABASE_URL,
        "SELECT settings, rules_version, demand_series, session_runtime FROM games WHERE id = %s",
        (game_id,),
    )
    params = load_rule_based_params(runtime["rule_based_params"])
    assert params.version == runtime["rule_based_params_version"]
    every = set()
    for role, stored in sets.items():
        found = stored.facts.seat.simulated
        assert found is not None
        assert found == simulate(
            GameSettings.model_validate(settings), rules_version, series, params, role
        )
        every.add(found.rows[1])
    assert len(every) == 1


def assert_golden(name: str, sets: dict[str, facts.StoredFactSet]) -> None:
    payloads = {
        role: {"patterns_version": s.patterns_version, "facts": s.facts.model_dump(mode="json")}
        for role, s in sets.items()
    }
    path = GOLDEN / f"{name}.json"
    if os.environ.get("UPDATE_GOLDEN") == "1":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payloads, indent=2, ensure_ascii=False) + "\n", "utf-8")
    assert payloads == json.loads(path.read_text(encoding="utf-8"))


async def test_the_reference_trace_golden_facts(games_db):
    game_id = await reference_trace()
    sets = await stored_sets(game_id)
    assert_golden("reference-trace", sets)
    assert_recomputed(game_id, sets)
    chain = sets["retailer"].facts.chain
    assert chain.demand_std == 0 and all(r.amplification is None for r in chain.by_role)
    assert all(r.total_cost == Decimal("48.00") for r in chain.by_role)  # 8 Weeks at 6.00


async def test_the_takeover_golden_facts(games_db):
    game_id = await takeover_game()
    sets = await stored_sets(game_id)
    assert_golden("takeover", sets)
    assert_recomputed(game_id, sets)
    retailer = sets["retailer"].facts.seat
    assert retailer.student_orders == len(TAKEOVER_ORDERS) and not retailer.sm_excluded
    assert {m.week for m in retailer.moments} <= set(range(3, 15))
    assert sets["retailer"].patterns_version == 1
    assert 0 < sets["retailer"].facts.chain.ai_held_share < 1


@pytest.mark.long
async def test_the_fully_rule_based_golden_facts(games_db):
    game_id = await classic_game(TEST_DATABASE_URL)
    sets = await stored_sets(game_id)
    assert_golden("classic-rule-based", sets)
    assert_recomputed(game_id, sets)
    for stored in sets.values():
        seat = stored.facts.seat
        assert (seat.student_orders, seat.sm_excluded, seat.moments) == (0, True, ())
    assert sets["factory"].facts.chain.ai_held_share == 1


def assert_rendered_from_the_rows(game_id: str, sets: dict[str, facts.StoredFactSet]) -> int:
    """Story 9.7 (NFR-9): every number in every rendered moment of every Seat is one of its facts
    set's numbers (or their documented sums), and each of those equals the raw `seat_weeks` row:
    the Order, what the Seat saw, Posisjon (`state_seen.position`) and the later cost (the
    following Weeks' `week_cost`). Returns how many moments were rendered."""
    raw = raw_rows(game_id)
    count = 0
    for role, stored in sets.items():
        shown = render_moments(stored.facts, MOMENT_TEMPLATES, PatternSet.model_validate(V1))
        assert_every_number_from_the_facts(stored.facts, shown)
        assert (shown.heading is None) == (stored.facts.seat.moments == ())
        for moment in stored.facts.seat.moments:
            row = raw[(moment.week, role)]
            seen = row["seen"]
            assert row["decided_by"] == "student" and moment.order == row["order"]
            for key in ("incoming_order", "inventory", "backlog", "supply_line"):
                assert getattr(moment.state_seen, key) == seen[key], key
            assert position(moment) == seen["position"]
            following = range(moment.week + 1, moment.week + 1 + moment.later_weeks)
            later = sum(
                (_money(raw[(w, role)]["seen"]["week_cost"]) for w in following), Decimal(0)
            )
            assert moment.later_cost == later
            assert moment.week + moment.later_weeks <= stored.facts.chain.weeks
            count += 1
    return count


async def test_every_number_of_every_rendered_moment_of_the_golden_games_is_a_row_value(games_db):
    takeover = await takeover_game()
    assert assert_rendered_from_the_rows(takeover, await stored_sets(takeover)) == 3
    # Scripted Seats only: no moments, no heading. (The fully Rule-based Game has none either,
    # as `test_the_fully_rule_based_golden_facts` asserts.)
    trace = await reference_trace()
    assert assert_rendered_from_the_rows(trace, await stored_sets(trace)) == 0


async def test_a_set_is_stored_once_and_returned_as_stored(games_db):
    game_id = await classic_game(TEST_DATABASE_URL)
    first, again = await asyncio.gather(
        facts.get_or_create(game_id, "wholesaler"), facts.get_or_create(game_id, "wholesaler")
    )
    [(seat_id,)] = query(
        TEST_DATABASE_URL,
        "SELECT id FROM seats WHERE game_id = %s AND role = 'wholesaler'",
        (game_id,),
    )
    third = await facts.get_or_create(game_id, str(seat_id))  # the Seat id works too
    assert first == again == third
    rows = query(
        TEST_DATABASE_URL,
        "SELECT id, analysis_version, payload FROM fact_sets WHERE game_id = %s",
        (game_id,),
    )
    assert len(rows) == 1 and str(rows[0][0]) == first.id and rows[0][1] == ANALYSIS_VERSION == 2
    # No names, no user ids, no Seat ids: no UUID at all in the payload.
    assert not UUID.search(json.dumps(rows[0][2]))
    assert set(rows[0][2]) == {"patterns_version", "facts"}


async def test_a_stored_set_is_never_rebuilt_nor_changed(games_db):
    import psycopg

    game_id = await classic_game(TEST_DATABASE_URL)
    stored = await facts.get_or_create(game_id, "factory")
    # A new pattern version later changes nothing stored.
    await content.publish("detected_patterns", {**V1, "following_weeks": 1})
    assert await facts.get_or_create(game_id, "factory") == stored
    with pytest.raises(psycopg.errors.RestrictViolation):
        execute(TEST_DATABASE_URL, "UPDATE fact_sets SET analysis_version = 3")
    # A set stored under version 1 has no simulated rows and reads as stored (Story 9.8).
    [(payload,)] = query(
        TEST_DATABASE_URL, "SELECT payload FROM fact_sets WHERE game_id = %s", (game_id,)
    )
    del payload["facts"]["seat"]["simulated"]
    old = FactSet.model_validate(payload["facts"])
    assert old.seat.simulated is None and old.chain == stored.facts.chain


async def test_the_pinned_pattern_version_is_used_and_the_latest_without_a_pin(games_db):
    """The Takeover Game pinned version 1 at its lock; the simulation Game has no pin."""
    assert await content.publish("detected_patterns", {**V1, "following_weeks": 1}) == 2
    pinned = await facts.get_or_create(await takeover_game(), "retailer")
    latest = await facts.get_or_create(await classic_game(TEST_DATABASE_URL), "retailer")
    assert (pinned.patterns_version, latest.patterns_version) == (1, 2)
    later = {o.later_weeks for o in latest.facts.seat.patterns}
    assert later and later <= {0, 1}


async def test_refusals(games_db):
    game_id = await classic_game(TEST_DATABASE_URL)
    running = await commands.create("simulation", GameSettings(), seed=3)
    cases = [
        (game_id, "nope", ("seat_not_found", 404)),
        (str(uuid.uuid7()), "retailer", ("game_not_found", 404)),
        ("not-an-id", "retailer", ("game_not_found", 404)),
        (running, "retailer", ("game_not_finished", 409)),
    ]
    for game, seat, refused in cases:
        for call in (facts.get_or_create, facts.compute):
            with pytest.raises(ViewError) as error:
                await call(game, seat)
            assert (error.value.code, error.value.status) == refused
    assert query(TEST_DATABASE_URL, "SELECT count(*) FROM fact_sets") == [(0,)]


async def test_a_pinned_version_that_is_gone_or_a_broken_log_is_refused_typed(games_db):
    gone = await classic_game(TEST_DATABASE_URL)
    tamper(
        TEST_DATABASE_URL,
        "UPDATE games SET session_runtime = jsonb_set(session_runtime, '{pins}', "
        '\'{"detected_patterns": {"version": 9}}\') WHERE id = %s',
        (gone,),
    )
    broken = await classic_game(TEST_DATABASE_URL)
    tamper(TEST_DATABASE_URL, "DELETE FROM seat_weeks WHERE game_id = %s AND week = 3", (broken,))
    for game_id in (gone, broken):
        with pytest.raises(ViewError) as error:
            await facts.get_or_create(game_id, "retailer")
        assert (error.value.code, error.value.status) == ("facts_unavailable", 409)


def test_the_cli_prints_each_seat_of_a_simulation_game_and_stores_nothing(capsys, games_db):
    game_id = sim._run(_classic())
    capsys.readouterr()
    assert sim.main(["facts", game_id]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert list(printed) == [role.value for role in ROLES]
    assert {p["patterns_version"] for p in printed.values()} == {1}
    assert printed["factory"]["facts"]["seat"]["role"] == "factory"
    assert query(TEST_DATABASE_URL, "SELECT count(*) FROM fact_sets") == [(0,)]


async def _classic() -> str:
    from app.platform import db

    try:
        return await classic_game(TEST_DATABASE_URL)
    finally:
        await db.dispose()


@pytest.mark.parametrize(
    ("which", "error"),
    [("class", "error not_simulation: "), ("missing", "error game_not_found: ")],
)
def test_the_cli_refuses_other_games(capsys, games_db, which, error):
    async def make() -> str:
        from app.platform import db

        try:
            if which == "missing":
                return str(uuid.uuid7())
            return await takeover_game()
        finally:
            await db.dispose()

    game_id = sim._run(make())
    capsys.readouterr()
    assert sim.main(["facts", game_id]) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err.startswith(error)
