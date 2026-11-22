"""Participation signals on the Studentside (Story 13.2, FR-17, AD-1).

Pure: no I/O, no clock. Staff see two signals that never change a Student's Completion status:
the time the Student spent on their own Orders and whether those Orders were constant. Neither is
an input of `analysis.completion`; both are information only.

- Time spent: the sum, over the Student's own Orders in every Week, Guided Weeks included, of the
  seconds from the Week's `opened_at` to its `ordered_at` (`seat_weeks`). An own Order is one
  with `decided_by = student` that no Takeover or playout placed (`completion.NOT_OWN_REASONS`):
  Completion's rule for an own Order, though Completion counts only the Weeks after the Guided
  Weeks.
- Constant: every own Order after the Guided Weeks has the same quantity. None with fewer than two
  such Orders, since one Order is neither constant nor varied.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from app.analysis.completion import NOT_OWN_REASONS

__all__ = ["Participation", "TimedOrder", "participation"]


@dataclass(frozen=True)
class TimedOrder:
    """One Decision log row of the Student's Seat: its Week, who decided it, why the occupant held
    the Seat, the quantity ordered and the whole seconds from the Week's opening to the Order."""

    week: int
    decided_by: str
    reason: str
    quantity: int
    seconds: int


@dataclass(frozen=True)
class Participation:
    """The Student's own Orders: how many, the seconds spent on them in all, how many came after the
    Guided Weeks, and whether those were constant (None with fewer than two)."""

    own_orders: int
    seconds: int
    constant: bool | None
    after_guided: int = 0


def _own(row: TimedOrder) -> bool:
    return row.decided_by == "student" and row.reason not in NOT_OWN_REASONS


def participation(rows: Sequence[TimedOrder], guided_weeks: int) -> Participation:
    """The participation signals of one Seat's Decision log. See the module docstring."""
    own = [row for row in rows if _own(row)]
    later = [row.quantity for row in own if row.week > guided_weeks]
    return Participation(
        own_orders=len(own),
        seconds=sum(max(row.seconds, 0) for row in own),
        constant=None if len(later) < 2 else len(set(later)) == 1,
        after_guided=len(later),
    )
