"""Story 8.14: the Play deadline playout (FR-38, FR-28, FR-29, FR-32, AD-2, AD-5, AD-9, AD-13).

`games.commands.playout` takes an unfinished Class game over in one transaction under the Game
row lock: every Student-held Seat gets an AI occupant with reason `playout`, the Pause, «I rommet»
mark, queued Reclaims and open reminders go, and the Game plays on to `finish`. A person's command
on it then answers `play_deadline_passed`. The Play deadline and the clock are passed in, never
read from the host (Issue #63); no test plays a Classic game (8 Weeks, Rule-based players)."""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from structlog.testing import capture_logs

from app.ai import budget as ai_budget
from app.engine import demand_series
from app.modules.games import commands
from app.modules.games import service as games_service
from app.modules.ops import sweep
from app.modules.players import service as players
from app.modules.progress import service as progress
from app.modules.sessions import service as sessions_service
from app.platform import jobs
from app.platform.config import get_settings
from tests.ai.helpers import MOCK, stored_config
from tests.conftest import TEST_DATABASE_URL
from tests.games.helpers import class_game_copies, execute, query
from tests.games.test_in_room import mark
from tests.games.test_reclaim import occupancy
from tests.games.test_set_snapshot import SETTINGS, snapshot
from tests.games.test_staff_pause import LECTURER
from tests.games.test_takeover import _user, due_of

DEADLINE = datetime(2026, 12, 1, 12, 0, tzinfo=UTC)
"""The Play deadline of every test's Class session; `now` is this or later."""
SECOND = timedelta(seconds=1)


def class_session(deadline: datetime | None = DEADLINE) -> uuid.UUID:
    """A Class session row with this Play deadline (and its Class), written directly: the
    `class_game` step a finished game records refers to it."""
    institution, klass, session = uuid.uuid7(), uuid.uuid7(), uuid.uuid7()
    execute(
        TEST_DATABASE_URL,
        "INSERT INTO institutions (id, name, created_at, updated_at) VALUES (%s, %s, now(), now())",
        (institution, f"I {institution}"),
    )
    execute(
        TEST_DATABASE_URL,
        "INSERT INTO classes (id, name, institution_id, created_at) VALUES (%s, 'K', %s, now())",
        (klass, institution),
    )
    execute(
        TEST_DATABASE_URL,
        "INSERT INTO class_sessions (id, class_id, game_settings, ai_mode, debrief_mode, "
        "inactivity_limit_hours, obligatory, required_share_percent, created_at, play_deadline) "
        "VALUES (%s, %s, '{}', 'rule_based', 'group', 24, false, 80, now(), %s)",
        (session, klass, deadline),
    )
    return session


async def class_game(
    roles: tuple[str, ...] = ("retailer", "factory"),
    *,
    session: uuid.UUID | None = None,
    number: int = 1,
    stored: dict | None = None,
    start: bool = True,
    weeks: int = SETTINGS.weeks,
    guided_weeks: int = 0,
) -> tuple[str, dict[str, uuid.UUID]]:
    """A Class game of a real Class session (`weeks` Weeks, no Guided Week) whose `roles`
    Students hold, started unless `start` is False; the other Seats get Rule-based players."""
    session = session or class_session()
    game_id = await commands.create("class", class_session_id=session, game_number=number)
    students = {role: _user() for role in roles}
    for role, user in students.items():
        await commands.assign_seat(game_id, role, "student", user_id=user)
    settings = SETTINGS.model_copy(update={"guided_weeks": guided_weeks, "weeks": weeks})
    frozen = {
        **(stored or snapshot()),
        "settings": settings.model_dump(mode="json"),
        "demand_series": list(demand_series(settings)),
    }
    await commands.set_snapshot(game_id, frozen, keep_students=list(students.values()))
    if start:
        await commands.start(game_id)
    return game_id, students


def game_row(game_id: str) -> dict:
    [row] = query(
        TEST_DATABASE_URL,
        "SELECT lifecycle, played_out_at, paused_at, in_room_until, started_at, started_by, "
        "version, class_session_id FROM games WHERE id = %s",
        (game_id,),
    )
    keys = ("lifecycle", "played_out_at", "paused_at", "in_room_until", "started_at")
    return dict(zip((*keys, "started_by", "version", "session"), row, strict=True))


def reclaims(game_id: str) -> int:
    [(count,)] = query(
        TEST_DATABASE_URL, "SELECT count(*) FROM seat_reclaims WHERE game_id = %s", (game_id,)
    )
    return count


def decisions(game_id: str, role: str) -> list[tuple]:
    """(week, decided_by, reason) of the Seat's Decision log rows."""
    return query(
        TEST_DATABASE_URL,
        "SELECT w.week, w.decided_by, w.reason FROM seat_weeks w JOIN seats s ON s.id = w.seat_id "
        "WHERE w.game_id = %s AND s.role = %s ORDER BY w.week",
        (game_id, role),
    )


@pytest.fixture
def held(monkeypatch):
    """The Game stays in `playing_out` after the command: no settle, so its state can be read."""

    async def later(game_id: str) -> None:
        return None

    monkeypatch.setattr(commands, "_settle", later)
    return monkeypatch


async def test_the_playout_takes_every_student_seat_and_clears_what_held_the_game(
    games_db, mail_db, held
):
    game_id, students = await class_game(("retailer", "wholesaler", "factory"))
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    await commands.takeover(
        game_id, "factory", actor="system", now=due_of(game_id, "factory") + SECOND
    )
    # The factory Seat was taken over in Week 1; once the wholesaler orders, Week 2 opens and the
    # factory's Student asks for the Seat back.
    await commands.place_order(game_id, "wholesaler", 1, 4, "student", actor=students["wholesaler"])
    assert await commands.request_reclaim(game_id, "factory", actor=students["factory"])
    await commands.place_order(game_id, "retailer", 2, 4, "student", actor=students["retailer"])
    assert await mark(game_id, 10)
    await commands.pause(game_id, actor=LECTURER, staff=True)
    before = game_row(game_id)

    assert await commands.playout(game_id, now=DEADLINE, latest=DEADLINE)
    after = game_row(game_id)
    assert after["lifecycle"] == "playing_out" and after["played_out_at"] is not None
    assert (after["paused_at"], after["in_room_until"]) == (None, None)
    assert after["version"] == before["version"] + 1
    assert reclaims(game_id) == 0
    # The retailer ordered Week 2: its Order stands, the AI player takes Week 3 on.
    assert occupancy(game_id, "retailer")[-1][:3] == (3, "rule_based", "playout")
    # The wholesaler had not ordered: the AI player takes Week 2 and orders it at once.
    assert occupancy(game_id, "wholesaler")[-1][:3] == (2, "rule_based", "playout")
    assert decisions(game_id, "wholesaler")[-1] == (2, "rule_based", "playout")
    # The factory Seat was held by an AI player already: nothing is appended.
    assert [row[2] for row in occupancy(game_id)] == ["initial", "takeover_inactivity"]
    # No reminder is left open, and a second call changes nothing.
    assert query(
        TEST_DATABASE_URL,
        "SELECT count(*) FROM seat_turns WHERE game_id = %s AND reminder_due_at IS NOT NULL "
        "AND reminder_queued_at IS NULL",
        (game_id,),
    ) == [(0,)]
    assert not await commands.playout(game_id, now=DEADLINE, latest=DEADLINE)
    assert game_row(game_id)["version"] == after["version"]

    held.undo()
    assert await commands.advance(game_id)
    assert game_row(game_id)["lifecycle"] == "finished"
    assert [w for w, *_ in decisions(game_id, "retailer")] == list(range(1, SETTINGS.weeks + 1))
    assert all(by in ("rule_based", "llm") for _, by, _ in decisions(game_id, "retailer")[2:])
    # The finished-game check of Story 6.18 replays it and passes.
    check = await games_service.verify_finished(game_id)
    assert check.ok, check.violations
    # Every Student ever seated has the Class game step: the one played out and the one taken
    # over earlier and never given the Seat back (Story 6.18, AD-16).
    for student in students.values():
        assert await progress.has_step(student, game_row(game_id)["session"], "class_game")


async def test_a_never_started_game_is_started_with_no_actor_and_played_out(games_db, mail_db):
    game_id, _ = await class_game(("retailer",), start=False)

    assert await commands.playout(game_id, now=DEADLINE, latest=DEADLINE)
    row = game_row(game_id)
    assert row["lifecycle"] == "finished"
    assert row["started_at"] is not None and row["started_by"] is None
    assert {reason for _, _, reason in decisions(game_id, "retailer")} == {"playout"}


async def test_a_game_without_a_snapshot_or_before_the_deadline_is_left_alone(games_db):
    game_id = await commands.create("class", class_session_id=uuid.uuid7(), game_number=1)
    with pytest.raises(commands.CommandError) as refused:
        await commands.playout(game_id, now=DEADLINE, latest=DEADLINE)
    assert refused.value.code == "game_not_ready"
    assert game_row(game_id)["lifecycle"] == "not_started"

    started, _ = await class_game()
    for latest in (None, DEADLINE + timedelta(seconds=1)):
        with pytest.raises(commands.CommandError) as refused:
            await commands.playout(started, now=DEADLINE, latest=latest)
        assert refused.value.code == "play_deadline_not_passed"

    async def extended(session) -> datetime:  # read in the command's own transaction
        return DEADLINE + timedelta(days=1)

    with pytest.raises(commands.CommandError) as refused:
        await commands.playout(started, now=DEADLINE, latest=extended)
    assert refused.value.code == "play_deadline_not_passed"
    assert game_row(started)["played_out_at"] is None

    simulation = await commands.create("simulation", SETTINGS, seed=3)
    with pytest.raises(commands.CommandError) as refused:
        await commands.playout(simulation, now=DEADLINE, latest=DEADLINE)
    assert refused.value.code == "playout_not_allowed"


async def test_a_persons_command_after_the_playout_answers_play_deadline_passed(
    games_db, mail_db, held
):
    game_id, students = await class_game(("retailer", "wholesaler", "factory"))
    assert await commands.playout(game_id, now=DEADLINE, latest=DEADLINE)
    retailer = students["retailer"]
    attempts = [
        commands.place_order(game_id, "retailer", 2, 4, "student", actor=retailer),
        # Week 1's Order is stored: the playout's AI player placed it, not the Student.
        commands.place_order(game_id, "retailer", 1, 4, "student", actor=retailer),
        commands.pause(game_id, actor=retailer),
        commands.pause(game_id, actor=LECTURER, staff=True),
        commands.takeover(game_id, "factory", actor="staff", actor_user_id=LECTURER),
        commands.request_reclaim(game_id, "factory", actor=students["factory"]),
        commands.view_week(game_id, "retailer", 1, actor=retailer),
    ]
    for attempt in attempts:
        with pytest.raises(commands.CommandError) as refused:
            await attempt
        assert refused.value.code == "play_deadline_passed"
    # A Takeover the sweep found just before the playout took the Game is skipped quietly.
    [(factory,)] = query(
        TEST_DATABASE_URL,
        "SELECT id FROM seats WHERE game_id = %s AND role = 'factory'",
        (game_id,),
    )
    assert await sweep._take_over((game_id, str(factory)), DEADLINE) is False
    # The playout's own AI players order on.
    held.undo()
    assert await commands.advance(game_id)
    assert game_row(game_id)["lifecycle"] == "finished"


async def test_an_order_racing_the_playout_has_one_consistent_outcome(games_db, mail_db):
    game_id, students = await class_game(("retailer", "factory"))
    order = commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    placed, played = await asyncio.gather(
        order, commands.playout(game_id, now=DEADLINE, latest=DEADLINE), return_exceptions=True
    )
    assert played is True
    [first, *_] = decisions(game_id, "retailer")
    last = occupancy(game_id, "retailer")[-1]
    if isinstance(placed, commands.CommandError):
        assert placed.code == "play_deadline_passed"
        assert first == (1, "rule_based", "playout") and last[0] == 1
    else:
        assert first == (1, "student", "initial") and last[:3] == (2, "rule_based", "playout")
    assert game_row(game_id)["lifecycle"] == "finished"


async def test_llm_seats_play_out_on_llm_batch_without_a_deadline_and_a_lost_job_is_deferred_again(
    games_db, ai_db, mail_db, held
):
    config_id = await stored_config()
    level = MOCK["effort_levels"][0]["name"]
    game_id, _ = await class_game(stored=snapshot(config_id, level))
    assert await commands.playout(game_id, now=DEADLINE, latest=DEADLINE)
    taken = query(
        TEST_DATABASE_URL,
        "SELECT s.id, t.ai_deadline_at FROM seat_turns t JOIN seats s ON s.id = t.seat_id "
        "WHERE t.game_id = %s AND t.week = 1 AND s.role IN ('retailer', 'factory')",
        (game_id,),
    )
    assert [deadline for _, deadline in taken] == [None, None]
    locks = {f"llm-batch:{game_id}:1:{seat}" for seat, _ in taken}
    waiting = query(
        TEST_DATABASE_URL,
        "SELECT queue_name, queueing_lock FROM procrastinate_jobs WHERE queue_name = 'llm-batch'",
    )
    assert {lock for _, lock in waiting} == locks
    assert await games_service.stalled_playout_turns() == []

    # A lost job: the sweep finds the turn and defers it again.
    execute(TEST_DATABASE_URL, "DELETE FROM procrastinate_jobs WHERE queue_name = 'llm-batch'")
    stalled = await games_service.stalled_playout_turns()
    assert {seat for _, seat in stalled} == {str(seat) for seat, _ in taken}
    await sweep.run(DEADLINE)
    assert {
        lock
        for (lock,) in query(
            TEST_DATABASE_URL,
            "SELECT queueing_lock FROM procrastinate_jobs WHERE queue_name = 'llm-batch'",
        )
    } == locks

    held.undo()
    await jobs.run_until_idle([jobs.AI_ORDERS, jobs.LLM_BATCH])
    assert game_row(game_id)["lifecycle"] == "finished"


async def test_a_game_playing_out_too_long_is_logged_once(games_db, mail_db, held, monkeypatch):
    game_id, _ = await class_game()
    assert await commands.playout(game_id, now=DEADLINE, latest=DEADLINE)
    started = game_row(game_id)["played_out_at"]
    allowed = timedelta(minutes=get_settings().playout_allowed_minutes)
    monkeypatch.setattr(sweep, "_overdue_logged", set())
    with capture_logs() as logs:
        await sweep.run(started + allowed - timedelta(seconds=1))
        await sweep.run(started + allowed)
        await sweep.run(started + allowed + timedelta(minutes=1))
    overdue = [e for e in logs if e["event"] == "playout_overdue"]
    assert [(e["log_level"], e["game_id"]) for e in overdue] == [("error", game_id)]


async def test_the_sweep_plays_out_every_unfinished_class_game_at_the_live_deadline(
    games_db, mail_db, monkeypatch
):
    session = class_session()
    running, _ = await class_game(session=session, number=1)
    never, _ = await class_game(session=session, number=2, start=False)
    unready = await commands.create("class", class_session_id=session, game_number=3)
    # Another Class session whose Lecturer moved the Play deadline a day on.
    later, _ = await class_game(session=class_session(DEADLINE + timedelta(days=1)))
    monkeypatch.setattr(sessions_service, "_refused_playouts", set())

    await sweep.run(DEADLINE - SECOND)
    assert {game_row(g)["played_out_at"] for g in (running, never, later)} == {None}
    with capture_logs() as logs:
        await sweep.run(DEADLINE)
        await sweep.run(DEADLINE + SECOND)
    lifecycles = {g: game_row(g)["lifecycle"] for g in (running, never, unready, later)}
    assert lifecycles == {
        running: "finished",
        never: "finished",
        unready: "not_started",
        later: "running",
    }
    # The Game with no snapshot is logged once, with its id, and the others are not held up.
    unready_logs = [e for e in logs if e["event"] == "playout_game_not_ready"]
    assert [(e["log_level"], e["game_id"]) for e in unready_logs] == [("error", unready)]
    # The finished-game check ran in the same sweep and passed.
    assert query(
        TEST_DATABASE_URL,
        "SELECT game_id::text, ok FROM game_checks WHERE game_id IN (%s, %s) ORDER BY game_id",
        (running, never),
    ) == sorted([(running, True), (never, True)])


@pytest.mark.long
async def test_a_hundred_unfinished_class_games_all_finish_in_one_sweep(games_db, mail_db):
    """NFR-3, NFR-4: 100 unfinished Class games of one Class session (one Week each, so the test
    stays short; Rule-based players, never started) are all finished by one sweep at the Play
    deadline."""
    session = class_session()
    first, _ = await class_game((), session=session, start=False, weeks=1)
    class_game_copies(TEST_DATABASE_URL, session, first, range(2, 101))  # rows copied, not built
    await sweep.run(DEADLINE)
    assert query(
        TEST_DATABASE_URL,
        "SELECT lifecycle, count(*) FROM games WHERE class_session_id = %s GROUP BY lifecycle",
        (session,),
    ) == [("finished", 100)]


async def test_in_a_guided_week_an_unviewed_seat_is_taken_from_it_and_a_viewed_one_from_the_next(
    games_db, mail_db, held
):
    game_id, students = await class_game(guided_weeks=2)
    assert await commands.view_week(game_id, "retailer", 1, actor=students["retailer"])
    assert await commands.playout(game_id, now=DEADLINE, latest=DEADLINE)
    # Viewing counts as ordering in a Guided Week (FR-24): the retailer's Week 1 stands.
    assert occupancy(game_id, "retailer")[-1][:3] == (2, "rule_based", "playout")
    assert occupancy(game_id, "factory")[-1][:3] == (1, "rule_based", "playout")
    held.undo()
    assert await commands.advance(game_id)
    assert game_row(game_id)["lifecycle"] == "finished"
    assert (await games_service.verify_finished(game_id)).ok


async def test_a_never_started_game_with_llm_seats_plays_out_with_no_ai_deadline(
    games_db, ai_db, mail_db, held
):
    config_id = await stored_config()
    level = MOCK["effort_levels"][0]["name"]
    game_id, _ = await class_game(stored=snapshot(config_id, level), start=False)
    assert await commands.playout(game_id, now=DEADLINE, latest=DEADLINE)
    row = game_row(game_id)
    assert (row["lifecycle"], row["started_by"]) == ("playing_out", None)
    assert row["started_at"] is not None
    assert query(
        TEST_DATABASE_URL,
        "SELECT count(*) FROM seat_turns WHERE game_id = %s AND ai_deadline_at IS NOT NULL",
        (game_id,),
    ) == [(0,)]
    queues = query(
        TEST_DATABASE_URL,
        "SELECT DISTINCT queue_name FROM procrastinate_jobs WHERE args->>'game_id' = %s",
        (game_id,),
    )
    assert queues == [("llm-batch",)]


async def test_a_class_game_playing_out_asks_the_model_and_the_cost_limit_reaches_it(
    games_db, ai_db, mail_db, held
):
    """Epic 8 close-out (follow-up reviews of 8.2 and 8.14): a Class game's LLM player reaches the
    model through its session's scope (it fell back with `provider_error` before), and the cost
    limit switch finds a Game that is playing out."""
    config_id = await stored_config()
    level = MOCK["effort_levels"][0]["name"]
    session = class_session()
    await ai_budget.set_budget(ai_budget.BudgetScope.class_session(session))
    game_id, _ = await class_game(stored=snapshot(config_id, level), session=session)
    assert await commands.playout(game_id, now=DEADLINE, latest=DEADLINE)
    await jobs.run_until_idle([jobs.LLM_BATCH])
    marks = query(
        TEST_DATABASE_URL,
        "SELECT DISTINCT w.decided_by, w.fallback FROM seat_weeks w WHERE w.game_id = %s",
        (game_id,),
    )
    assert ("llm", "none") in marks
    assert ("llm", "provider_error") not in marks

    scope = await games_service.budget_scope(game_id)
    assert game_row(game_id)["lifecycle"] == "playing_out"
    assert await games_service.games_charged_to(scope) == [game_id]
    assert await players.apply_cost_limit(game_id) == 4  # every Seat an LLM player held
    assert occupancy(game_id, "retailer")[-1][1:3] == ("rule_based", "cost_limit")
    assert await players.apply_cost_limit(game_id) == 0  # nothing left to switch
