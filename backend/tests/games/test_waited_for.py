"""Story 8.12: `games.rules.waited_for`, the one waiting predicate, and `game_status`, which gives
`waiting` from it (FR-24, FR-25, FR-37, AD-20). Pure: no database."""

from datetime import UTC, datetime

import pytest

from app.modules.games import rules
from app.modules.games.schemas import GameStatus

T = datetime(2026, 11, 22, 9, 0, tzinfo=UTC)
GAME = {"lifecycle": "running", "purpose": "class", "settings": {"weeks": 6, "guided_weeks": 1}}


def turn(kind="student", *, wait=None, ordered=None, viewed=None, week=2) -> dict:
    return {
        "occupant_kind": kind,
        "wait_started_at": wait,
        "ordered_at": ordered,
        "viewed_at": viewed,
        "week": week,
    }


@pytest.mark.parametrize(
    ("row", "guided", "expected"),
    [
        (turn(wait=T), False, True),  # waited for since T, no Order
        (turn(), False, False),  # no Student has ordered: no wait started
        (turn(wait=T, ordered=T), False, False),  # ordered since
        (turn("llm", wait=T), False, False),  # an AI player holds it
        (turn("rule_based", wait=T), False, False),
        (turn(wait=T, ordered=T), True, True),  # Guided Week: the fixed Order, not viewed
        (turn(wait=T, ordered=T, viewed=T), True, False),  # viewed counts as ordering
    ],
)
def test_waited_for_is_a_student_seat_whose_wait_has_started_and_that_has_not_ordered(
    row, guided, expected
):
    assert rules.waited_for(row, guided=guided) is expected


def test_the_status_is_waiting_exactly_when_a_turn_is_waited_for():
    ordered = turn(wait=None, ordered=T)
    assert rules.game_status(GAME, [ordered, turn(wait=T)]) is GameStatus.WAITING
    # Every Student has ordered: the game waits for no one.
    assert rules.game_status(GAME, [ordered, ordered]) is GameStatus.RUNNING
    # No wait started yet: nobody has ordered this Week.
    assert rules.game_status(GAME, [turn(), turn()]) is GameStatus.RUNNING
    # Only an AI player has not ordered: running.
    assert rules.game_status(GAME, [ordered, turn("llm", wait=T)]) is GameStatus.RUNNING
    # The Guided Uke 1: a fixed Order not yet viewed is waited for once a wait started.
    guided = [turn(ordered=T, viewed=T, week=1), turn(wait=T, ordered=T, week=1)]
    assert rules.game_status(GAME, guided) is GameStatus.WAITING
    # A Pause wins over waiting.
    paused = {**GAME, "paused_at": T}
    assert rules.game_status(paused, [ordered, turn(wait=T)]) is GameStatus.PAUSED
