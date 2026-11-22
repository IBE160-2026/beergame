"""Story 8.9: a Student's Tilrettelegging factor on the turn times (FR-17, FR-36, FR-89, AD-20).

`rules.turn_times` multiplies the Inactivity limit by the factor; with an agreed Pause time the
insert time is never before the Student's own extended limit, and with no clock running the agreed
time stands. `games.commands.recompute_turn_times` applies a changed factor to the open Week at
once; `_start_waits` and the Lecturer's Pause commands read the factor too. The factor comes from
`sessions.service.time_factors`, stubbed here (its store is `tests/sessions/test_adjustment.py`).
Times are read from the database, never compared with the host clock (Issue #63)."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.modules.games import commands, rules
from app.modules.games.schemas import OccupantKind
from app.modules.sessions import service as sessions_service
from app.platform.events.registry import COMMAND_TOPICS
from tests.conftest import TEST_DATABASE_URL
from tests.games.helpers import execute, listening, query
from tests.games.test_game_summaries import check
from tests.games.test_staff_pause import LECTURER, db_now, insert_of
from tests.games.test_takeover import class_game, due_of

HOUR = timedelta(hours=1)
LIMIT = 24 * HOUR

# `rules.turn_times` (pure): each factor, with and without an agreed time and a running clock.

START = datetime(2026, 11, 22, 12, tzinfo=UTC)
EARLY = START + 3 * HOUR  # before every limit
LATE = START + 80 * HOUR  # after every extended limit
STUDENT = rules.TurnSeat(occupant_kind=OccupantKind.STUDENT, opened_at=START)


def expected(factor: float | None, agreed: datetime | None, clock: bool):
    if not clock:
        return None, agreed  # no due time; an agreed time stands (open-assumptions, 8.9)
    due = START + LIMIT * max(factor or 1.0, 1.0)
    if agreed is None:
        return due, due
    if (factor or 1.0) > 1:
        return due, max(agreed, due)  # never before the own extended limit (FR-89)
    return due, agreed


@pytest.mark.parametrize("factor", [None, 1.0, 1.5, 2.0, 3.0])
@pytest.mark.parametrize("agreed", [None, EARLY, LATE], ids=["no-agreed", "early", "late"])
@pytest.mark.parametrize("clock", [True, False], ids=["clock", "no-clock"])
def test_each_factor_with_and_without_an_agreed_time_and_a_clock(factor, agreed, clock):
    times = rules.turn_times(
        rules.TurnGame(guided_week=False),
        STUDENT,
        rules.TurnInputs(
            clock_start=START if clock else None,
            inactivity_limit=LIMIT,
            time_factor=factor,
            agreed_time=agreed,
        ),
    )
    assert (times.takeover_due_at, times.insert_allowed_at) == expected(factor, agreed, clock)


def test_a_factor_below_one_never_shortens_the_limit():
    times = rules.turn_times(
        rules.TurnGame(guided_week=False),
        STUDENT,
        rules.TurnInputs(clock_start=START, inactivity_limit=LIMIT, time_factor=0.5),
    )
    assert times.takeover_due_at == START + LIMIT


# The commands, with the factor stubbed per Student.


@pytest.fixture
def factors(monkeypatch) -> dict[uuid.UUID, float]:
    """The factors `sessions.service.time_factors` answers, by Student; empty: nobody has one."""
    found: dict[uuid.UUID, float] = {}

    async def stub(session, class_session_id, user_ids):
        return {user: found[user] for user in user_ids if user in found}

    monkeypatch.setattr(sessions_service, "time_factors", stub)
    return found


def wait_of(game_id: str, role: str) -> datetime:
    [(at,)] = query(
        TEST_DATABASE_URL,
        "SELECT t.wait_started_at FROM seat_turns t JOIN seats s ON s.id = t.seat_id "
        "WHERE t.game_id = %s AND s.role = %s AND t.week = 1",
        (game_id, role),
    )
    return at


def announced(game_id: str) -> dict[str, bool]:
    """Per Student Seat with a turn in Week 1, whether the sweep's announcement mark is set."""
    return {
        role: at is not None
        for role, at in query(
            TEST_DATABASE_URL,
            "SELECT s.role, t.insert_announced_at FROM seat_turns t "
            "JOIN seats s ON s.id = t.seat_id WHERE t.game_id = %s AND t.week = 1 "
            "AND s.role IN ('retailer', 'wholesaler', 'factory')",
            (game_id,),
        )
    }


def version_of(game_id: str) -> int:
    [(version,)] = query(TEST_DATABASE_URL, "SELECT version FROM games WHERE id = %s", (game_id,))
    return version


async def test_a_new_factor_moves_the_open_weeks_due_times_at_once(games_db, mail_db, factors):
    game_id, students = await class_game(("retailer", "wholesaler", "factory"))
    # Jonas (Fabrikk) has 2 × from the start: the first Order's clock gives him his own limit.
    factors[students["factory"]] = 2.0
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    wait = wait_of(game_id, "factory")
    assert (due_of(game_id, "factory"), insert_of(game_id, "factory")) == (
        wait + 2 * LIMIT,
        wait + 2 * LIMIT,
    )
    assert due_of(game_id, "wholesaler") == wait + LIMIT
    assert due_of(game_id, "retailer") is None  # it has ordered

    # The sweep has announced his insert time (Story 8.8); a moved one is announced afresh.
    execute(
        TEST_DATABASE_URL,
        "UPDATE seat_turns SET insert_announced_at = clock_timestamp() WHERE game_id = %s",
        (game_id,),
    )

    # The Lecturer changes him to 3 ×: recomputed at once, with the Game's events.
    factors[students["factory"]] = 3.0
    before = version_of(game_id)
    with listening(games_db) as events:
        assert await commands.recompute_turn_times(game_id)
        received = events.drain()
    assert {e["topic"] for e in received} == COMMAND_TOPICS["games.recompute_turn_times"]
    assert {e["id"] for e in received if e["topic"] == "user"} == {
        str(u) for u in students.values()
    }
    assert version_of(game_id) == before + 1
    assert (due_of(game_id, "factory"), insert_of(game_id, "factory")) == (
        wait + 3 * LIMIT,
        wait + 3 * LIMIT,
    )
    assert wait_of(game_id, "factory") == wait  # the wait start never moves
    assert due_of(game_id, "distributor") is None  # an AI player's Seat gets no due time
    assert due_of(game_id, "wholesaler") == wait + LIMIT
    assert announced(game_id) == {"factory": False, "wholesaler": True, "retailer": True}
    summary = await check(game_id)  # the summary (the Varselbånd's source) follows
    assert summary["takeover_due_at"] == wait + LIMIT

    # Nothing changed: nothing written.
    assert not await commands.recompute_turn_times(game_id)
    assert version_of(game_id) == before + 1

    # Back to «Som klassen».
    del factors[students["factory"]]
    assert await commands.recompute_turn_times(game_id)
    assert (due_of(game_id, "factory"), insert_of(game_id, "factory")) == (
        wait + LIMIT,
        wait + LIMIT,
    )

    # An agreed Pause time earlier than his extended limit never gives him an earlier insert
    # time; the others get the agreed time.
    agreed = (db_now() + 2 * HOUR).replace(microsecond=0)
    await commands.pause(game_id, actor=LECTURER, staff=True, resume_at=agreed)
    assert insert_of(game_id, "factory") == agreed
    factors[students["factory"]] = 1.5
    assert await commands.recompute_turn_times(game_id)
    assert insert_of(game_id, "factory") == wait + 1.5 * LIMIT
    assert insert_of(game_id, "wholesaler") == agreed
    # The Lecturer's next agreed time also keeps his floor (`_recompute_insert_times`).
    later = agreed + HOUR
    await commands.set_agreed_time(game_id, later, actor=LECTURER)
    assert (insert_of(game_id, "factory"), insert_of(game_id, "wholesaler")) == (
        wait + 1.5 * LIMIT,
        later,
    )
    await check(game_id)


async def test_with_no_clock_an_agreed_time_stands_and_is_carried_past_the_pause(
    games_db, mail_db, factors
):
    game_id, students = await class_game(("retailer", "factory"))
    factors[students["factory"]] = 2.0
    agreed = (db_now() + HOUR).replace(microsecond=0)
    await commands.pause(game_id, actor=LECTURER, staff=True, resume_at=agreed)
    # Nobody has ordered: no FR-36 clock, so no extended limit to hold against.
    assert not await commands.recompute_turn_times(game_id)
    assert (due_of(game_id, "factory"), insert_of(game_id, "factory")) == (None, agreed)
    # He has no factor when the first Order ends the Pause and starts the clock: the agreed time
    # stays his insert time for this Week (Story 8.7), and a recompute keeps it.
    del factors[students["factory"]]
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    wait = wait_of(game_id, "factory")
    assert (due_of(game_id, "factory"), insert_of(game_id, "factory")) == (wait + LIMIT, agreed)
    assert not await commands.recompute_turn_times(game_id)
    assert insert_of(game_id, "factory") == agreed
    # Given 2 × after the Pause: the carried agreed time never undercuts his own limit.
    factors[students["factory"]] = 2.0
    assert await commands.recompute_turn_times(game_id)
    assert (due_of(game_id, "factory"), insert_of(game_id, "factory")) == (
        wait + 2 * LIMIT,
        wait + 2 * LIMIT,
    )
    missing = str(uuid.uuid7())
    with pytest.raises(commands.CommandError) as caught:
        await commands.recompute_turn_times(missing)
    assert (caught.value.code, caught.value.status) == ("game_not_found", 404)
