"""Story 13.2 (FR-17, AD-1, AD-16): `analysis.participation`, and that it never moves Completion."""

import pytest

from app.analysis.completion import (
    COMPLETION_STEPS,
    CompletionSettings,
    DecisionLogSummary,
    LoggedWeek,
    StepInputs,
    completion,
)
from app.analysis.participation import Participation, TimedOrder, participation


def row(week: int, quantity: int = 4, seconds: int = 60, by: str = "student", why: str = "initial"):
    return TimedOrder(week=week, decided_by=by, reason=why, quantity=quantity, seconds=seconds)


@pytest.mark.parametrize(
    ("rows", "expected"),
    [
        pytest.param([], Participation(0, 0, None, 0), id="no-orders"),
        pytest.param(
            [row(1, 9), row(2, 9), row(3, 4), row(4, 4), row(5, 4)],
            Participation(5, 300, True, 3),
            id="constant-after-guided-only",
        ),
        pytest.param([row(3, 4), row(4, 5)], Participation(2, 120, False, 2), id="varied"),
        pytest.param(
            [row(1), row(2), row(3)], Participation(3, 180, None, 1), id="one-after-guided"
        ),
        pytest.param(
            [
                row(3, 4, 100),
                row(4, 8, 500, by="ai", why="takeover_inactivity"),
                row(5, 8, 500, why="takeover_peer"),
                row(6, 8, 500, why="playout"),
                row(7, 4, 50),
            ],
            Participation(2, 150, True, 2),
            id="takeover-and-playout-not-own",
        ),
        pytest.param([row(3, seconds=-5), row(4)], Participation(2, 60, True, 2), id="clock-skew"),
    ],
)
def test_participation(rows, expected):
    assert participation(rows, guided_weeks=2) == expected


def test_participation_never_changes_the_completion_status():
    """The same Decision log with other times and other quantities: Completion is identical, the
    participation signals differ (FR-17: information only)."""
    weeks = [(week, "student", "initial") for week in range(1, 11)]
    fast_constant = [TimedOrder(w, by, why, 4, 5) for w, by, why in weeks]
    slow_varied = [TimedOrder(w, by, why, w * 3, 3600) for w, by, why in weeks]
    assert participation(fast_constant, 2) != participation(slow_varied, 2)

    def status(rows: list[TimedOrder]):
        log = DecisionLogSummary(
            weeks=10,
            guided_weeks=2,
            rows=tuple(LoggedWeek(r.week, r.decided_by, r.reason) for r in rows),
        )
        return completion(
            StepInputs(events=dict.fromkeys(COMPLETION_STEPS, 1), explanation_length=80),
            log,
            (),
            CompletionSettings(
                obligatory=True,
                required_share=80,
                explanation_min_length=50,
                test_required_parts=(),
            ),
        )

    assert status(fast_constant) == status(slow_varied)
    assert status(fast_constant).requirement_met is True
