"""Story 2.6: every LLM Order inside its time budget (FR-32, NFR-2, NFR-4, AD-5, AD-6, AD-20).

Deadlines are tiny (a fraction of a second) or the rescue loop gets an injected `now`; the job
and the loop are driven directly, never with a multi-second sleep."""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import psycopg
import pytest
from sqlalchemy.exc import OperationalError

from app.ai import mock
from app.modules.games import commands, service
from app.modules.players import jobs as player_jobs
from app.modules.players import rescue
from app.platform import jobs
from app.platform.db import get_sessionmaker
from tests.ai.helpers import stored_config
from tests.games.helpers import execute, query
from tests.players.test_llm_jobs import FIRST, calls, llm_game, rows, seat_id

LATER = datetime.now(UTC) + timedelta(days=365)
"""A `now` past every deadline of these tests."""


def level(budget: float = 8, attempt: float = 4) -> list[dict]:
    return [{"name": "standard", "attempt_timeout_s": attempt, "order_time_budget_s": budget}]


async def config(budget: float = 8, attempt: float = 4) -> str:
    return await stored_config(effort_levels=level(budget, attempt))


def turn_times(url: str, game_id: str, week: int) -> dict[str, tuple]:
    """role -> (opened_at, ai_deadline_at, ordered_at) of `week`."""
    found = query(
        url,
        "SELECT s.role, t.opened_at, t.ai_deadline_at, t.ordered_at FROM seat_turns t "
        "JOIN seats s ON s.id = t.seat_id WHERE t.game_id = %s AND t.week = %s",
        (game_id, week),
    )
    return {role: rest for role, *rest in found}


def logged(url: str, game_id: str, role: str, week: int) -> tuple | None:
    """(decided_by, fallback, llm_call_ids, opened_at, ordered_at, ai_deadline_at) or None."""
    found = query(
        url,
        "SELECT w.decided_by, w.fallback, w.llm_call_ids, w.opened_at, w.ordered_at, "
        "w.ai_deadline_at FROM seat_weeks w JOIN seats s ON s.id = w.seat_id "
        "WHERE w.game_id = %s AND s.role = %s AND w.week = %s",
        (game_id, role, week),
    )
    return found[0] if found else None


async def test_an_llm_turn_gets_its_deadline_when_the_week_opens(games_db, ai_db):
    game_id = await llm_game(("retailer", "factory"), config_id=await config(budget=8))
    for week in range(1, FIRST):  # Guided Weeks ask no model, so nothing is due
        assert {deadline for _, deadline, _ in turn_times(games_db, game_id, week).values()} == {
            None
        }
    times = turn_times(games_db, game_id, FIRST)
    for role in ("retailer", "factory"):
        opened_at, deadline, _ = times[role]
        assert deadline == opened_at + timedelta(seconds=8)
    assert times["wholesaler"][1] is None and times["distributor"][1] is None  # Rule-based
    # All turns of a Week share the opening time.
    assert len({opened_at for opened_at, _, _ in times.values()}) == 1
    # A set deadline never changes.
    with pytest.raises(psycopg.errors.RestrictViolation, match="keeps its opening values"):
        execute(
            games_db, "UPDATE seat_turns SET ai_deadline_at = now() WHERE game_id = %s", (game_id,)
        )
    # The job's Order copies the deadline into the Decision log.
    await jobs.run_until_idle([jobs.AI_ORDERS])
    by, fallback, _, opened_at, _, deadline = logged(games_db, game_id, "retailer", FIRST)
    assert (by, fallback) == ("llm", "none")
    assert deadline == opened_at + timedelta(seconds=8)
    assert logged(games_db, game_id, "wholesaler", FIRST)[5] is None


async def test_a_killed_job_gets_the_fallback_within_the_budget_plus_one_interval(games_db, ai_db):
    budget, interval = 0.3, 0.05
    game_id = await llm_game(("retailer",), config_id=await config(budget=budget, attempt=budget))
    retailer = seat_id(games_db, game_id, "retailer")
    with mock.script(mock.TIMEOUT):  # the model hangs
        job = asyncio.create_task(player_jobs.place_llm_order(game_id, retailer, FIRST))
        await asyncio.sleep(0.1)  # the call first reads the config and reserves its cost
        job.cancel()  # the worker dies mid-call
        with pytest.raises(asyncio.CancelledError):
            await job
    assert logged(games_db, game_id, "retailer", FIRST) is None
    stop = asyncio.Event()
    loop = asyncio.create_task(rescue.run(interval_s=interval, stop=stop))
    try:
        async with asyncio.timeout(2):
            while logged(games_db, game_id, "retailer", FIRST) is None:  # noqa: ASYNC110
                await asyncio.sleep(0.01)  # polls the database, which signals no event
    finally:
        stop.set()
        await loop
    by, fallback, ids, opened_at, ordered_at, deadline = logged(
        games_db, game_id, "retailer", FIRST
    )
    assert (by, fallback, ids) == ("rule_based", "timeout", [])
    assert deadline <= ordered_at
    # Within the budget plus one loop interval (and a little for the pass itself).
    assert ordered_at - opened_at <= timedelta(seconds=budget + interval + 0.2)
    # Issue #52: the attempt in flight still has its row, tied to the turn by its caller ref.
    [(outcome, caller)] = query(games_db, "SELECT outcome, caller_ref FROM llm_call")
    assert outcome == "cancelled"
    assert caller == {"game": game_id, "seat": retailer, "week": FIRST}
    # The Week the fallback completed has moved on.
    assert (await service.open_turn(game_id, "retailer")).week == FIRST + 1


async def test_a_late_answer_meets_order_exists_and_the_fallback_stands(
    games_db, ai_db, monkeypatch
):
    game_id = await llm_game(("retailer",))
    retailer = seat_id(games_db, game_id, "retailer")
    real_run = player_jobs.gateway.run

    async def late(*args, **kwargs):
        answer = await real_run(*args, **kwargs)
        assert (await rescue.rescue_once(LATER)).placed == 1  # the deadline passed meanwhile
        return answer

    monkeypatch.setattr(player_jobs.gateway, "run", late)
    await player_jobs.place_llm_order(game_id, retailer, FIRST)
    by, fallback, ids, *_ = logged(games_db, game_id, "retailer", FIRST)
    assert (by, fallback, ids) == ("rule_based", "timeout", [])
    [(outcome, tokens, cost, caller)] = query(
        games_db, "SELECT outcome, output_tokens, cost_usd, caller_ref FROM llm_call"
    )
    assert outcome == "ok" and tokens > 0 and cost > 0
    assert caller == {"game": game_id, "seat": retailer, "week": FIRST}


async def test_the_rescue_loop_skips_a_turn_that_waits_for_no_llm_order(games_db, ai_db):
    game_id = await llm_game(("retailer",))
    retailer = seat_id(games_db, game_id, "retailer")
    execute(
        games_db,
        "INSERT INTO seat_occupancy (id, seat_id, from_week, occupant_kind, reason) "
        "VALUES (%s, %s, %s, 'student', 'takeover_staff')",
        (uuid.uuid7(), retailer, FIRST),
    )
    assert await rescue.rescue_once(LATER) == rescue.RescuePass()
    assert logged(games_db, game_id, "retailer", FIRST) is None
    # Before the deadline nothing is overdue either.
    other = await llm_game(("factory",))
    assert await rescue.rescue_once() == rescue.RescuePass()
    assert logged(games_db, other, "factory", FIRST) is None


async def test_the_rescue_loop_advances_a_complete_week_left_open(games_db, ai_db):
    game_id = await llm_game(("retailer",))
    retailer = seat_id(games_db, game_id, "retailer")
    # The Order is written but the process stops before the advance.
    async with get_sessionmaker().begin() as session:
        await commands.place_order(
            game_id,
            retailer,
            FIRST,
            (await service.open_turn(game_id, "retailer")).rule_based_reference_order,
            "rule_based",
            fallback="timeout",
            within=service.OpenGame(session=session, game_id=uuid.UUID(game_id)),
        )
    assert await service.complete_running_games() == [game_id]
    assert await rescue.rescue_once() == rescue.RescuePass(advanced=1)
    assert (await service.open_turn(game_id, "retailer")).week == FIRST + 1
    assert await service.complete_running_games() == []


async def test_a_database_error_while_writing_the_order_is_tried_again(
    games_db, ai_db, monkeypatch
):
    """Issue #54."""
    game_id = await llm_game(("retailer",))
    retailer = seat_id(games_db, game_id, "retailer")
    real_place = player_jobs.games_commands.place_order
    failures = [OperationalError("INSERT", {}, Exception("connection lost"))]

    async def flaky(*args, **kwargs):
        if failures:
            raise failures.pop()
        return await real_place(*args, **kwargs)

    monkeypatch.setattr(player_jobs, "RETRY_DELAYS_S", (0, 0))
    monkeypatch.setattr(player_jobs.games_commands, "place_order", flaky)
    await player_jobs.place_llm_order(game_id, retailer, FIRST)
    assert logged(games_db, game_id, "retailer", FIRST)[:2] == ("llm", "none")
    assert calls(games_db) == 1  # the model is asked once


async def test_a_lasting_database_error_leaves_the_order_to_the_rescue_loop(
    games_db, ai_db, monkeypatch
):
    game_id = await llm_game(("retailer",))
    retailer = seat_id(games_db, game_id, "retailer")
    tries = []

    async def broken(*args, **kwargs):
        tries.append(args)
        raise OperationalError("INSERT", {}, Exception("connection lost"))

    monkeypatch.setattr(player_jobs, "RETRY_DELAYS_S", (0, 0))
    monkeypatch.setattr(player_jobs.games_commands, "place_order", broken)
    with pytest.raises(OperationalError):
        await player_jobs.place_llm_order(game_id, retailer, FIRST)
    assert len(tries) == 3 and calls(games_db) == 1
    monkeypatch.undo()
    assert (await rescue.rescue_once(LATER)).placed == 1
    assert logged(games_db, game_id, "retailer", FIRST)[:2] == ("rule_based", "timeout")


async def test_a_failing_item_is_counted_and_the_pass_goes_on(games_db, ai_db, monkeypatch):
    one = await llm_game(("retailer",))
    two = await llm_game(("retailer",))
    real_place = rescue.games_commands.place_order

    async def first_fails(game_id, *args, **kwargs):
        if game_id == one:
            raise RuntimeError("boom")
        return await real_place(game_id, *args, **kwargs)

    monkeypatch.setattr(rescue.games_commands, "place_order", first_fails)
    done = await rescue.rescue_once(LATER)
    assert (done.placed, done.failed) == (1, 1)
    assert logged(games_db, two, "retailer", FIRST)[:2] == ("rule_based", "timeout")


async def test_time_per_attempt_and_per_order_are_read_per_effort_level_from_rows(games_db, ai_db):
    """A finished simulated Game: latency per attempt and `ordered_at - opened_at` per Order,
    per Effort level, from stored rows alone (SQL, no code)."""
    game_id = await llm_game()
    await jobs.run_until_idle([jobs.AI_ORDERS])
    assert (await service.get_game(game_id)).lifecycle == "finished"
    attempts = query(
        games_db,
        "SELECT effort_level, count(*), avg(latency_ms) FROM llm_call "
        "WHERE caller_ref->>'game' = %s GROUP BY effort_level",
        (game_id,),
    )
    orders = query(
        games_db,
        "SELECT g.session_runtime->>'effort_level', count(*), "
        "avg(extract(epoch FROM w.ordered_at - w.opened_at)) "
        "FROM seat_weeks w JOIN games g ON g.id = w.game_id "
        "WHERE w.game_id = %s AND w.decided_by = 'llm' GROUP BY 1",
        (game_id,),
    )
    assert [(level, count) for level, count, _ in attempts] == [("standard", 8)]
    assert [(level, count) for level, count, _ in orders] == [("standard", 8)]
    assert attempts[0][2] >= 0 and orders[0][2] >= 0
    assert len(rows(games_db, game_id)) == 12


async def test_the_job_keeps_a_hanging_model_inside_the_turns_deadline(games_db, ai_db):
    """The job hands the turn's `ai_deadline_at` to the gateway: a hanging model is cut at
    the deadline and the job places the `timeout` fallback itself."""
    budget = 0.3
    game_id = await llm_game(("retailer",), config_id=await config(budget=budget, attempt=budget))
    retailer = seat_id(games_db, game_id, "retailer")
    with mock.script(*[mock.TIMEOUT] * 6):
        await player_jobs.place_llm_order(game_id, retailer, FIRST)
    by, fallback, ids, opened_at, ordered_at, _ = logged(games_db, game_id, "retailer", FIRST)
    assert (by, fallback, len(ids)) == ("rule_based", "timeout", 1)
    assert ordered_at - opened_at <= timedelta(seconds=budget + 0.3)
    assert query(games_db, "SELECT outcome FROM llm_call") == [("timeout",)]


async def test_the_loop_survives_a_failed_pass(games_db, ai_db, monkeypatch):
    game_id = await llm_game(("retailer",))
    real = rescue.games_service.overdue_llm_turns
    failures = [OperationalError("SELECT", {}, Exception("database away"))]

    async def flaky(now=None):
        if failures:
            raise failures.pop()
        return await real(LATER)

    monkeypatch.setattr(rescue.games_service, "overdue_llm_turns", flaky)
    stop = asyncio.Event()
    loop = asyncio.create_task(rescue.run(interval_s=0.01, stop=stop))
    try:
        async with asyncio.timeout(2):
            while logged(games_db, game_id, "retailer", FIRST) is None:  # noqa: ASYNC110
                await asyncio.sleep(0.01)  # polls the database, which signals no event
    finally:
        stop.set()
        await loop
    assert logged(games_db, game_id, "retailer", FIRST)[:2] == ("rule_based", "timeout")


async def test_a_fallback_order_is_also_tried_again_and_keeps_its_failure_type(
    games_db, ai_db, monkeypatch
):
    game_id = await llm_game(("retailer",))
    retailer = seat_id(games_db, game_id, "retailer")
    real_place = player_jobs.games_commands.place_order
    failures = [OperationalError("INSERT", {}, Exception("connection lost"))]

    async def flaky(*args, **kwargs):
        if failures:
            raise failures.pop()
        return await real_place(*args, **kwargs)

    monkeypatch.setattr(player_jobs, "RETRY_DELAYS_S", (0, 0))
    monkeypatch.setattr(player_jobs.games_commands, "place_order", flaky)
    with mock.outage():
        await player_jobs.place_llm_order(game_id, retailer, FIRST)
    assert logged(games_db, game_id, "retailer", FIRST)[:2] == ("rule_based", "provider_error")


async def test_a_lasting_error_that_is_not_transient_is_not_tried_again(
    games_db, ai_db, monkeypatch
):
    from sqlalchemy.exc import IntegrityError

    game_id = await llm_game(("retailer",))
    retailer = seat_id(games_db, game_id, "retailer")
    tries = []

    async def broken(*args, **kwargs):
        tries.append(args)
        raise IntegrityError("INSERT", {}, Exception("restrict_violation"))

    monkeypatch.setattr(player_jobs.games_commands, "place_order", broken)
    with pytest.raises(IntegrityError):
        await player_jobs.place_llm_order(game_id, retailer, FIRST)
    assert len(tries) == 1
