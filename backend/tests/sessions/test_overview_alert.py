"""The Varselbånd's game (Stories 7.11 and 8.3, FR-39, AD-10): `overview._alert` picks from the
summaries the Class game an AI player takes over first, else the longest-waiting one, and within
it the Seat due first, else the one waited for longest. Pure: no database."""

import dataclasses
import uuid
from datetime import UTC, datetime, timedelta

from app.modules.games.service import ClassGameSummary, GameStatus, SummaryWait
from app.modules.sessions.overview import _alert

T = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)
NOAH = uuid.uuid4()
IDA = uuid.uuid4()
NAMES = {NOAH: "Noah", IDA: "Ida"}


def game(
    number: int,
    status: GameStatus = GameStatus.WAITING,
    waits: tuple[SummaryWait, ...] = (),
    started: datetime | None = None,
) -> ClassGameSummary:
    return ClassGameSummary(
        game_id=uuid.uuid4(),
        game_number=number,
        status=status,
        week=3,
        version=1,
        chain_cost=None,
        wait_started_at=started if started is not None else (waits[0].since if waits else None),
        waiting_for=waits,
        seats=(),
    )


def wait(role: str, user: uuid.UUID | None, since: datetime) -> SummaryWait:
    return SummaryWait(role=role, user_id=user, since=since)


def test_one_waiting_game_names_the_student_and_since_when():
    found = _alert([game(1, waits=(wait("wholesaler", NOAH, T),))], NAMES)
    assert found is not None
    assert (found.game_number, found.role, found.name, found.user_id, found.since) == (
        1,
        "wholesaler",
        "Noah",
        NOAH,
        T,
    )


def test_the_game_that_has_waited_longest_wins():
    first = game(1, waits=(wait("retailer", IDA, T),))
    second = game(2, waits=(wait("wholesaler", NOAH, T - timedelta(hours=1)),))
    assert _alert([first, second], NAMES).game_id == second.game_id


def test_a_tie_goes_to_the_lower_game_number():
    later = game(4, waits=(wait("retailer", IDA, T),))
    earlier = game(3, waits=(wait("wholesaler", NOAH, T),))
    assert _alert([later, earlier], NAMES).game_number == 3


def test_within_the_game_the_seat_waited_for_longest_then_chain_order():
    found = _alert(
        [
            game(
                1,
                waits=(
                    wait("retailer", IDA, T),
                    wait("wholesaler", NOAH, T - timedelta(minutes=5)),
                ),
                started=T - timedelta(minutes=5),
            )
        ],
        NAMES,
    )
    assert (found.role, found.name) == ("wholesaler", "Noah")
    same = _alert(
        [game(1, waits=(wait("retailer", IDA, T), wait("wholesaler", NOAH, T)))],
        NAMES,
    )
    assert same.role == "retailer"


def test_a_student_no_longer_in_the_class_is_named_by_role_with_no_user():
    found = _alert([game(1, waits=(wait("factory", uuid.uuid4(), T),))], NAMES)
    assert (found.role, found.name, found.user_id) == ("factory", None, None)


def test_no_band_when_nothing_waits_for_a_student():
    running = game(1, status=GameStatus.RUNNING)
    finished = game(2, status=GameStatus.FINISHED)
    empty_wait = game(3, waits=())
    assert _alert([running, finished, empty_wait], NAMES) is None
    assert _alert([], NAMES) is None


def test_a_waiting_game_without_a_waited_for_seat_is_skipped():
    empty_wait = game(1, waits=(), started=T - timedelta(days=1))
    named = game(2, waits=(wait("retailer", IDA, T),))
    assert _alert([empty_wait, named], NAMES).game_number == 2


def test_without_a_stored_wait_start_the_earliest_seat_counts_and_numbered_games_go_first():
    no_start = ClassGameSummary(
        game_id=uuid.uuid4(),
        game_number=5,
        status=GameStatus.WAITING,
        week=3,
        version=1,
        chain_cost=None,
        wait_started_at=None,
        waiting_for=(wait("retailer", IDA, T - timedelta(hours=2)),),
        seats=(),
    )
    started = game(1, waits=(wait("wholesaler", NOAH, T - timedelta(hours=1)),))
    assert _alert([started, no_start], NAMES).game_number == 5
    unnumbered = dataclasses.replace(no_start, game_id=uuid.uuid4(), game_number=None)
    assert _alert([unnumbered, no_start], NAMES).game_number == 5


# Story 8.3: the game an AI player takes over first, by the stored `takeover_due_at`.


def due_game(number: int, *waits: SummaryWait, started: datetime | None = None) -> ClassGameSummary:
    """A waiting game whose `takeover_due_at` is its Seats' earliest, as `recompute` stores it."""
    dues = [w.takeover_due_at for w in waits if w.takeover_due_at is not None]
    return dataclasses.replace(
        game(number, waits=waits, started=started), takeover_due_at=min(dues, default=None)
    )


def due_wait(role: str, user: uuid.UUID | None, since: datetime, due: datetime | None):
    return SummaryWait(role=role, user_id=user, since=since, takeover_due_at=due)


def test_the_game_closest_to_takeover_beats_the_longest_wait():
    long_wait = due_game(
        1, due_wait("retailer", IDA, T - timedelta(hours=2), T + timedelta(hours=22))
    )
    soon = due_game(2, due_wait("wholesaler", NOAH, T - timedelta(hours=1), T + timedelta(hours=1)))
    found = _alert([long_wait, soon], NAMES)
    assert (found.game_id, found.name, found.takeover_due_at) == (
        soon.game_id,
        "Noah",
        T + timedelta(hours=1),
    )


def test_a_tie_on_the_due_time_goes_to_the_lower_game_number_whatever_the_wait():
    due = T + timedelta(hours=1)
    later = due_game(4, due_wait("retailer", IDA, T - timedelta(hours=3), due))
    earlier = due_game(3, due_wait("wholesaler", NOAH, T, due))
    assert _alert([later, earlier], NAMES).game_number == 3


def test_within_the_game_the_seat_due_first_is_named_whatever_its_wait():
    found = _alert(
        [
            due_game(
                1,
                due_wait("retailer", IDA, T - timedelta(hours=2), T + timedelta(hours=3)),
                due_wait("wholesaler", NOAH, T - timedelta(hours=1), T + timedelta(hours=1)),
            )
        ],
        NAMES,
    )
    assert (found.role, found.name, found.takeover_due_at) == (
        "wholesaler",
        "Noah",
        T + timedelta(hours=1),
    )


def test_without_any_due_time_the_longest_wait_wins_with_no_countdown():
    first = due_game(1, due_wait("retailer", IDA, T, None))
    second = due_game(2, due_wait("wholesaler", NOAH, T - timedelta(hours=1), None))
    found = _alert([first, second], NAMES)
    assert (found.game_id, found.takeover_due_at) == (second.game_id, None)


def test_a_game_with_a_due_time_beats_one_without():
    without = due_game(1, due_wait("retailer", IDA, T - timedelta(days=2), None))
    with_due = due_game(2, due_wait("wholesaler", NOAH, T, T + timedelta(hours=20)))
    assert _alert([without, with_due], NAMES).game_id == with_due.game_id


def test_an_older_row_without_seat_due_times_names_the_longest_wait_with_the_games_due():
    older = dataclasses.replace(
        game(
            1,
            waits=(
                wait("retailer", IDA, T),
                wait("wholesaler", NOAH, T - timedelta(minutes=5)),
            ),
            started=T - timedelta(minutes=5),
        ),
        takeover_due_at=T + timedelta(hours=2),
    )
    found = _alert([older], NAMES)
    assert (found.role, found.takeover_due_at) == ("wholesaler", T + timedelta(hours=2))


def test_a_due_time_already_passed_still_counts():
    passed = due_game(
        2, due_wait("retailer", IDA, T - timedelta(days=1), T - timedelta(seconds=20))
    )
    later = due_game(1, due_wait("wholesaler", NOAH, T - timedelta(days=2), T + timedelta(hours=1)))
    found = _alert([later, passed], NAMES)
    assert (found.game_id, found.takeover_due_at) == (passed.game_id, T - timedelta(seconds=20))
