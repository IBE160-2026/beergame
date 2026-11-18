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
