"""The one AD-15 mapping, `games.service.seat_mark` (Story 6.14, extended by Story 7.7, FR-34,
FR-62): a mark for every occupancy `reason` but `initial` and `moved`, Epic 8's Takeover reasons
included, and for every `fallback` but `none`. A pure function: no database."""

import pytest

from app.modules.games import service
from app.modules.games.schemas import (
    DecidedBy,
    Fallback,
    OccupancyReason,
    OccupantKind,
    SeatMark,
)

REASONS = {
    OccupancyReason.INITIAL: None,
    OccupancyReason.MOVED: None,
    OccupancyReason.COST_LIMIT: SeatMark.COST_LIMIT,
    OccupancyReason.TAKEOVER_INACTIVITY: SeatMark.TAKEOVER_INACTIVITY,
    OccupancyReason.TAKEOVER_STAFF: SeatMark.TAKEOVER_STAFF,
    OccupancyReason.TAKEOVER_PEER: SeatMark.TAKEOVER_PEER,
    OccupancyReason.RECLAIM: SeatMark.RECLAIM,
    OccupancyReason.PLAYOUT: SeatMark.PLAYOUT,
}
FALLBACKS = {
    Fallback.NONE: None,
    Fallback.TIMEOUT: SeatMark.FALLBACK_TIMEOUT,
    Fallback.INVALID_OUTPUT: SeatMark.FALLBACK_INVALID_OUTPUT,
    Fallback.BUDGET_EXHAUSTED: SeatMark.FALLBACK_BUDGET_EXHAUSTED,
    Fallback.PROVIDER_ERROR: SeatMark.FALLBACK_PROVIDER_ERROR,
}


def test_every_reason_and_fallback_is_mapped():
    assert set(REASONS) | {OccupancyReason.GUARD_SWITCH} == set(OccupancyReason)
    assert set(FALLBACKS) == set(Fallback)


@pytest.mark.parametrize(("reason", "expected"), list(REASONS.items()))
def test_each_occupancy_reason_has_its_mark(reason, expected):
    kind = None if reason == OccupancyReason.MOVED else OccupantKind.RULE_BASED
    assert service.seat_mark(None, None, kind, reason) == expected
    # The stored strings map the same as the enum members.
    assert service.seat_mark(None, None, kind and str(kind), str(reason)) == expected


def test_a_guard_switch_marks_only_a_rule_based_occupant():
    mark = service.seat_mark
    assert mark(None, None, OccupantKind.RULE_BASED, OccupancyReason.GUARD_SWITCH) == (
        SeatMark.GUARD_SWITCH
    )
    assert mark(None, None, OccupantKind.LLM, OccupancyReason.GUARD_SWITCH) is None


@pytest.mark.parametrize(("fallback", "expected"), list(FALLBACKS.items()))
def test_each_fallback_has_its_mark(fallback, expected):
    assert service.seat_mark(DecidedBy.RULE_BASED, fallback, None, None) == expected
    assert service.seat_mark("rule_based", str(fallback), None, None) == expected


def test_a_replaced_order_marks_before_the_occupancy():
    assert (
        service.seat_mark(
            DecidedBy.RULE_BASED, Fallback.TIMEOUT, OccupantKind.LLM, OccupancyReason.PLAYOUT
        )
        == SeatMark.FALLBACK_TIMEOUT
    )
    assert service.seat_mark(DecidedBy.STUDENT, Fallback.NONE, "student", "initial") is None
