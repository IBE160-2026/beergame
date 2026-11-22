"""Story 2.6: `games.rules.turn_times`, the one computation of a turn's AI deadline (AD-20,
NFR-2). Pure: table-driven, no database."""

from datetime import UTC, datetime, timedelta

import pytest

from app.modules.games.rules import TurnGame, TurnInputs, TurnSeat, turn_times
from app.modules.games.schemas import OccupantKind

OPENED = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)
LLM, RULE, SCRIPTED, STUDENT = (
    OccupantKind.LLM,
    OccupantKind.RULE_BASED,
    OccupantKind.SCRIPTED,
    OccupantKind.STUDENT,
)
FREE = TurnGame(guided_week=False)
GUIDED = TurnGame(guided_week=True)


@pytest.mark.parametrize(
    ("game", "kind", "since", "budget", "deadline"),
    [
        # An LLM player outside a Guided Week is due the budget after the Week opened.
        (FREE, LLM, None, 8.0, OPENED + timedelta(seconds=8)),
        (FREE, LLM, None, 0.25, OPENED + timedelta(seconds=0.25)),
        # It took the Seat later in the Week: the budget counts from that moment.
        (FREE, LLM, OPENED + timedelta(minutes=3), 8.0, OPENED + timedelta(minutes=3, seconds=8)),
        # An occupancy older than the Week does not move the start.
        (FREE, LLM, OPENED - timedelta(days=1), 8.0, OPENED + timedelta(seconds=8)),
        # No deadline: a Guided Week, no budget (no config, or a playout), any other occupant.
        (GUIDED, LLM, None, 8.0, None),
        (FREE, LLM, None, None, None),
        (FREE, RULE, None, 8.0, None),
        (FREE, SCRIPTED, None, 8.0, None),
        (FREE, STUDENT, None, 8.0, None),
    ],
)
def test_turn_times(game, kind, since, budget, deadline):
    seat = TurnSeat(occupant_kind=kind, opened_at=OPENED, occupied_since=since)
    assert turn_times(game, seat, TurnInputs(ai_order_budget_s=budget)).ai_deadline_at == deadline


def test_the_inputs_default_to_no_deadline():
    assert turn_times(FREE, TurnSeat(LLM, OPENED), TurnInputs()).ai_deadline_at is None


START = OPENED + timedelta(minutes=7)


@pytest.mark.parametrize(
    ("game", "kind", "since", "start", "waiting"),
    [
        # Story 6.14: a Seat that has not ordered is waited for from the clock start, for every
        # occupant and also in a Guided Week (a Student who has not viewed it).
        (FREE, STUDENT, None, START, START),
        (GUIDED, STUDENT, None, START, START),
        (FREE, LLM, None, START, START),
        (FREE, RULE, None, START, START),
        # An occupant that took the Seat after the clock start is waited for from then.
        (FREE, STUDENT, START + timedelta(minutes=2), START, START + timedelta(minutes=2)),
        (FREE, STUDENT, START - timedelta(minutes=2), START, START),
        # No clock start: no Student has ordered yet, nothing is waited for.
        (FREE, STUDENT, None, None, None),
    ],
)
def test_the_wait_starts_at_the_clock_start(game, kind, since, start, waiting):
    seat = TurnSeat(occupant_kind=kind, opened_at=OPENED, occupied_since=since)
    times = turn_times(game, seat, TurnInputs(clock_start=start))
    assert times.wait_started_at == waiting
    assert times.ai_deadline_at is None


def test_the_clock_start_leaves_the_ai_deadline_alone():
    times = turn_times(FREE, TurnSeat(LLM, OPENED), TurnInputs(8.0, clock_start=START))
    assert times.ai_deadline_at == OPENED + timedelta(seconds=8)
    assert times.wait_started_at == START


# Story 8.1: the FR-36 due times of a Student's turn, from the clock start and the limit in force.
DAY = timedelta(hours=24)
AGREED = START + timedelta(hours=30)
EARLY = START + timedelta(hours=2)


@pytest.mark.parametrize(
    ("game", "kind", "inputs", "due", "insert"),
    [
        # The Inactivity limit counts from the clock start, in a Guided Week too (FR-24).
        (FREE, STUDENT, TurnInputs(clock_start=START, inactivity_limit=DAY), START + DAY, None),
        (GUIDED, STUDENT, TurnInputs(clock_start=START, inactivity_limit=DAY), START + DAY, None),
        # The per-Student factor multiplies the limit and only extends it (FR-17).
        (
            FREE,
            STUDENT,
            TurnInputs(clock_start=START, inactivity_limit=DAY, time_factor=1.5),
            START + DAY * 1.5,
            None,
        ),
        (
            FREE,
            STUDENT,
            TurnInputs(clock_start=START, inactivity_limit=DAY, time_factor=0.5),
            START + DAY,
            None,
        ),
        # A Game marked as in the room uses its shorter limit instead (FR-36).
        (
            FREE,
            STUDENT,
            TurnInputs(
                clock_start=START, inactivity_limit=DAY, in_room_limit=timedelta(minutes=10)
            ),
            START + timedelta(minutes=10),
            None,
        ),
        # An agreed time is the insert time, earlier or later than the limit (FR-89) ...
        (
            FREE,
            STUDENT,
            TurnInputs(clock_start=START, inactivity_limit=DAY, agreed_time=AGREED),
            START + DAY,
            AGREED,
        ),
        (
            FREE,
            STUDENT,
            TurnInputs(clock_start=START, inactivity_limit=DAY, agreed_time=EARLY),
            START + DAY,
            EARLY,
        ),
        # ... but never before the own extended limit of a Student with a factor.
        (
            FREE,
            STUDENT,
            TurnInputs(clock_start=START, inactivity_limit=DAY, time_factor=2.0, agreed_time=EARLY),
            START + DAY * 2,
            START + DAY * 2,
        ),
        (
            FREE,
            STUDENT,
            TurnInputs(
                clock_start=START,
                inactivity_limit=DAY,
                time_factor=1.25,
                agreed_time=START + DAY * 3,
            ),
            START + DAY * 1.25,
            START + DAY * 3,
        ),
        # No due time: no clock start, no limit (an excluded purpose), or no Student occupant.
        (FREE, STUDENT, TurnInputs(inactivity_limit=DAY), None, None),
        (FREE, STUDENT, TurnInputs(clock_start=START), None, None),
        (FREE, LLM, TurnInputs(clock_start=START, inactivity_limit=DAY), None, None),
        (FREE, RULE, TurnInputs(clock_start=START, inactivity_limit=DAY), None, None),
        (FREE, SCRIPTED, TurnInputs(clock_start=START, inactivity_limit=DAY), None, None),
    ],
)
def test_the_due_times_follow_the_limit_in_force(game, kind, inputs, due, insert):
    times = turn_times(game, TurnSeat(kind, OPENED), inputs)
    assert times.takeover_due_at == due
    assert times.insert_allowed_at == (insert if insert is not None else due)


def test_a_student_who_took_the_seat_after_the_clock_start_is_due_from_then():
    since = START + timedelta(hours=1)
    seat = TurnSeat(STUDENT, OPENED, occupied_since=since)
    times = turn_times(FREE, seat, TurnInputs(clock_start=START, inactivity_limit=DAY))
    assert times.wait_started_at == since
    assert times.takeover_due_at == since + DAY


def test_the_due_times_leave_the_ai_deadline_alone():
    inputs = TurnInputs(8.0, clock_start=START, inactivity_limit=DAY)
    times = turn_times(FREE, TurnSeat(LLM, OPENED), inputs)
    assert times.ai_deadline_at == OPENED + timedelta(seconds=8)
    assert times.takeover_due_at is None


DELAY = timedelta(hours=2)
LIMIT = timedelta(hours=24)


@pytest.mark.parametrize(
    ("game", "kind", "inputs", "reminder"),
    [
        # Story 8.13 (FR-27): a Student waited for under a limit is reminded the delay after the
        # wait start, in a Guided Week too; neither the factor nor the in-room limit moves it.
        (FREE, STUDENT, TurnInputs(clock_start=START, inactivity_limit=LIMIT), START + DELAY),
        (GUIDED, STUDENT, TurnInputs(clock_start=START, inactivity_limit=LIMIT), START + DELAY),
        (
            FREE,
            STUDENT,
            TurnInputs(clock_start=START, inactivity_limit=LIMIT, time_factor=1.5),
            START + DELAY,
        ),
        (
            FREE,
            STUDENT,
            TurnInputs(clock_start=START, in_room_limit=timedelta(minutes=10)),
            START + DELAY,
        ),
        # None: nobody else has ordered, no limit (no inactivity rules, AD-13), no delay asked,
        # or an AI player in the Seat.
        (FREE, STUDENT, TurnInputs(inactivity_limit=LIMIT), None),
        (FREE, STUDENT, TurnInputs(clock_start=START), None),
        (FREE, LLM, TurnInputs(clock_start=START, inactivity_limit=LIMIT), None),
        (FREE, RULE, TurnInputs(clock_start=START, inactivity_limit=LIMIT), None),
    ],
)
def test_the_reminder_is_due_the_delay_after_the_wait_start(game, kind, inputs, reminder):
    seat = TurnSeat(occupant_kind=kind, opened_at=OPENED)
    with_delay = TurnInputs(**{**inputs.__dict__, "reminder_delay": DELAY})
    assert turn_times(game, seat, with_delay).reminder_due_at == reminder
    assert turn_times(game, seat, inputs).reminder_due_at is None
