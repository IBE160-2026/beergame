"""The time rules of an Individual test attempt (Story 11.12, FR-51, FR-17, AD-9): pure functions,
no I/O.

`effective_deadline` is only the Class session's Test deadline or the Student's extension (AD-9);
a timed sitting never changes it. `sitting_ends_at` is the opening time plus the Student's time
limit, and answering ends at whichever of the two comes first."""

import math
from collections.abc import Mapping
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

__all__ = ["answering_ends_at", "limit", "limit_minutes", "sitting_end", "sitting_ended"]


def limit(minutes: int, factor: Decimal) -> timedelta:
    """The Student's time limit: the Class session's whole minutes times their time factor
    (Story 8.9's Tilrettelegging; 1 without one), to the whole second."""
    return timedelta(seconds=int(Decimal(minutes * 60) * factor))


def limit_minutes(minutes: int, factor: Decimal) -> int:
    """The Student's time limit in whole minutes as the statement says it, rounded up."""
    return math.ceil(limit(minutes, factor).total_seconds() / 60)


def sitting_end(opened_at: datetime, minutes: int, factor: Decimal) -> datetime:
    """When a timed sitting opened at `opened_at` ends."""
    return opened_at + limit(minutes, factor)


def answering_ends_at(attempt: Mapping[str, Any]) -> datetime | None:
    """When the Student can no longer answer: the earlier of the attempt's `sitting_ends_at` and
    its `effective_deadline`; either may be unset, and None when both are."""
    ends = [t for t in (attempt["sitting_ends_at"], attempt["effective_deadline"]) if t is not None]
    return min(ends) if ends else None


def sitting_ended(attempt: Mapping[str, Any], now: datetime) -> bool:
    """Whether the attempt's timed sitting has ended at `now` before its `effective_deadline`: the
    case `commands.end_sitting` hands in. A sitting that would end at or after the deadline ends
    with the deadline instead, which `commands.close_attempt` hands in."""
    ends = attempt["sitting_ends_at"]
    if ends is None or ends > now:
        return False
    deadline = attempt["effective_deadline"]
    return deadline is None or ends < deadline
