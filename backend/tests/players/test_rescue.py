"""Story 2.6: every LLM Order inside its time budget (FR-32, NFR-2, NFR-4, AD-5, AD-6, AD-20).

The rescue loop mostly gets an injected `now`; the job and the loop are driven directly, never
with a multi-second sleep. Tests wait for events rather than fixed sleeps, the gateway's clock
stands still where a job's time left matters, and real spans are measured on this process's
monotonic clock with a generous `SLACK_S`, so a busy machine cannot change the outcome."""

import asyncio
import time
import uuid
from datetime import UTC, datetime, timedelta

import psycopg
import pytest
from sqlalchemy.exc import OperationalError

from app.ai import gateway, mock, ratelimit
from app.modules.games import commands, service
from app.modules.players import jobs as player_jobs
from app.modules.players import rescue
from app.platform import jobs
from app.platform.db import get_sessionmaker
from tests.ai.helpers import StoppedClock, stop_attempts, stored_config
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


SLACK_S = 2.0
"""Seconds a step may take on a busy machine on top of the time the code under test allows,
measured on this process's monotonic clock. The database clock is no measure of short spans:
the local Postgres VM's clock runs slow, steps forward a few seconds every half minute and now
and then back by its whole offset."""


def db_now(url: str) -> datetime:
    """The database clock, which stamps `opened_at`, `ai_deadline_at` and `ordered_at`."""
    ((now,),) = query(url, "SELECT clock_timestamp()")
    return now


async def started_attempt(job: asyncio.Task, monkeypatch) -> None:
    """Wait until `job` is inside its model call (the gateway's `_attempt`)."""
    entered = asyncio.Event()
    real = gateway._attempt

    async def watched(*args, **kwargs):
        entered.set()
        return await real(*args, **kwargs)

    monkeypatch.setattr(gateway, "_attempt", watched)
    waiting = asyncio.create_task(entered.wait())
    await asyncio.wait({job, waiting}, return_when=asyncio.FIRST_COMPLETED)
    waiting.cancel()
    assert entered.is_set(), "the job ended before its model call"


async def test_a_killed_job_gets_the_fallback_within_the_budget_plus_one_interval(
    games_db, ai_db, monkeypatch
):
    budget, interval = 1.0, 0.05
    game_id = await llm_game(("retailer",), config_id=await config(budget=budget, attempt=budget))
    retailer = seat_id(games_db, game_id, "retailer")
    # The killed job's own deadline is not under test here (the next test covers it): without
    # one it reaches its model call however slow the machine is, and is killed there.
    monkeypatch.setattr(player_jobs, "_deadline", lambda turn: None)
    with mock.script(mock.TIMEOUT):  # the model hangs
        job = asyncio.create_task(player_jobs.place_llm_order(game_id, retailer, FIRST))
        await started_attempt(job, monkeypatch)
        job.cancel()  # the worker dies mid-call
        with pytest.raises(asyncio.CancelledError):
            await job
    assert logged(games_db, game_id, "retailer", FIRST) is None
    # Each pass of the loop: its start on the database clock (the clock it compares deadlines
    # on), its start and end on this process's monotonic clock, and the Orders it placed.
    passes: list[tuple[datetime, float, float, int]] = []
    real_once = rescue.rescue_once

    async def timed_once(now=None):
        # The monotonic start first: the gap measured below must not hold this test's own query.
        start = time.monotonic()
        began = db_now(games_db)
        done = await real_once(now)
        passes.append((began, start, time.monotonic(), done.placed))
        return done

    monkeypatch.setattr(rescue, "rescue_once", timed_once)
    stop = asyncio.Event()
    loop = asyncio.create_task(rescue.run(interval_s=interval, stop=stop))
    try:
        async with asyncio.timeout(budget + 60):  # only a guard against a hang
            while logged(games_db, game_id, "retailer", FIRST) is None:  # noqa: ASYNC110
                await asyncio.sleep(0.01)  # polls the database, which signals no event
    finally:
        stop.set()
        await loop
    by, fallback, ids, opened_at, ordered_at, deadline = logged(
        games_db, game_id, "retailer", FIRST
    )
    assert (by, fallback, ids) == ("rule_based", "timeout", [])
    assert deadline == opened_at + timedelta(seconds=budget) and deadline <= ordered_at
    # The first pass after the deadline placed the fallback: every pass before it began before
    # the deadline, and it began one loop interval after the pass before it ended.
    placing = next(i for i, (*_, placed) in enumerate(passes) if placed)
    assert passes[placing][3] == 1
    assert all(began < deadline for began, *_ in passes[:placing])
    if placing:  # the loop was running before the deadline
        assert passes[placing][1] - passes[placing - 1][2] <= interval + SLACK_S
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
    # Latency is measured on the process's monotonic clock; the span per Order is two stamps of
    # the database clock, which may step back between them (Issue #63, `SLACK_S`): it must be
    # readable, its sign is no property of the code.
    assert attempts[0][2] >= 0 and orders[0][2] is not None
    assert len(rows(games_db, game_id)) == 12


async def test_the_job_keeps_a_hanging_model_inside_the_turns_deadline(
    games_db, ai_db, monkeypatch
):
    """The job hands the turn's `ai_deadline_at` to the gateway: a hanging model is cut at
    the deadline and the job places the `timeout` fallback itself.

    The turn is read `left` seconds before its deadline (its `read_at` is set so), and the
    gateway's clock stands still while the job prepares, so the time the attempt gets depends
    neither on the machine's speed nor on the database clock's jumps."""
    left, budget = 0.3, 60.0
    game_id = await llm_game(("retailer",), config_id=await config(budget=budget, attempt=budget))
    retailer = seat_id(games_db, game_id, "retailer")
    clock = StoppedClock()
    real_turn = service.llm_turn

    async def read_late(*args):
        turn = await real_turn(*args)
        clock.at = datetime.now(UTC)  # the job turns `left` into a deadline after this
        return turn.model_copy(update={"read_at": turn.ai_deadline_at - timedelta(seconds=left)})

    monkeypatch.setattr(service, "llm_turn", read_late)
    stop_attempts(monkeypatch, clock)
    start = time.monotonic()
    with ratelimit.use_clock(clock), mock.script(*[mock.TIMEOUT] * 6):
        await player_jobs.place_llm_order(game_id, retailer, FIRST)
    took = time.monotonic() - start
    by, fallback, ids, *_ = logged(games_db, game_id, "retailer", FIRST)
    assert (by, fallback, len(ids)) == ("rule_based", "timeout", 1)
    assert query(games_db, "SELECT outcome FROM llm_call") == [("timeout",)]
    # The one attempt got the time left before the deadline (plus the moment the job took to
    # turn it into a deadline), not its own 60 s timeout, and no retry followed.
    [seconds] = clock.given
    assert left <= seconds < left + SLACK_S
    assert took < left + 2 * SLACK_S  # one cut attempt, far from 6 x 60 s


async def test_the_loop_survives_a_failed_pass(games_db, ai_db, monkeypatch):
    game_id = await llm_game(("retailer",))
    real = rescue.games_service.overdue_llm_turns
    failures = [OperationalError("SELECT", {}, Exception("database away"))]

    async def flaky(now=None):
        if failures:
            raise failures.pop()
        return await real(LATER)

    monkeypatch.setattr(rescue.games_service, "overdue_llm_turns", flaky)
    # The pass that places the Order signals it: the test waits for that event, not for a span
    # of real time a busy machine could overrun.
    placed = asyncio.Event()
    real_once = rescue.rescue_once

    async def watched_once(now=None):
        done = await real_once(now)
        if done.placed:
            placed.set()
        return done

    monkeypatch.setattr(rescue, "rescue_once", watched_once)
    stop = asyncio.Event()
    loop = asyncio.create_task(rescue.run(interval_s=0.01, stop=stop))
    try:
        async with asyncio.timeout(60):  # only a guard against a hang
            await placed.wait()
    finally:
        stop.set()
        await loop
    assert failures == []  # the first pass failed, and the loop went on to the next
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
