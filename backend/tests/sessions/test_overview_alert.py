"""The Varselbånd's game (Story 7.11, FR-39, AD-10): `overview._alert` picks the longest-waiting
Class game from the summaries, and within it the Seat waited for longest. Pure: no database."""

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
