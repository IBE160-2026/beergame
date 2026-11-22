"""The one mapping from who decided and who held a Seat to the mark its readers show (AD-15).

Exported through `games.service` (`seat_mark`) for every reader; it lives here because the read
models in `views` use it too, and `views` cannot import `service`."""

from app.modules.games.schemas import DecidedBy, Fallback, OccupancyReason, OccupantKind, SeatMark

_REASON_MARKS: dict[str, SeatMark] = {
    OccupancyReason.COST_LIMIT: SeatMark.COST_LIMIT,
    OccupancyReason.TAKEOVER_INACTIVITY: SeatMark.TAKEOVER_INACTIVITY,
    OccupancyReason.TAKEOVER_STAFF: SeatMark.TAKEOVER_STAFF,
    OccupancyReason.TAKEOVER_PEER: SeatMark.TAKEOVER_PEER,
    OccupancyReason.RECLAIM: SeatMark.RECLAIM,
    OccupancyReason.PLAYOUT: SeatMark.PLAYOUT,
}
"""`initial` and `moved` mark nothing; `guard_switch` needs its Rule-based occupant (below)."""

_FALLBACK_MARKS: dict[str, SeatMark] = {
    Fallback.TIMEOUT: SeatMark.FALLBACK_TIMEOUT,
    Fallback.INVALID_OUTPUT: SeatMark.FALLBACK_INVALID_OUTPUT,
    Fallback.BUDGET_EXHAUSTED: SeatMark.FALLBACK_BUDGET_EXHAUSTED,
    Fallback.PROVIDER_ERROR: SeatMark.FALLBACK_PROVIDER_ERROR,
}
"""`none` marks nothing."""


def seat_mark(
    decided_by: DecidedBy | str | None,
    fallback: Fallback | str | None,
    occupant_kind: OccupantKind | str | None,
    reason: OccupancyReason | str | None,
) -> SeatMark | None:
    """The mark of a Seat, or of one of its Orders, from the Decision log's `decided_by` and
    `fallback` (None when no Order is in question) and the occupancy's `occupant_kind` and
    `reason` (None when only the Order is in question). An Order replaced by the fallback marks
    first; then the occupancy: Story 6.14's `guard_switch` (a Rule-based occupant the Play guard
    put in, FR-79, FR-34), and from Story 7.7 one mark per other switch or Takeover reason,
    Epic 8's included. None: nothing to mark."""
    del decided_by  # `fallback` says whether an Order was replaced; who decided is the occupant
    if fallback is not None and fallback in _FALLBACK_MARKS:
        return _FALLBACK_MARKS[fallback]
    if reason == OccupancyReason.GUARD_SWITCH:
        return SeatMark.GUARD_SWITCH if occupant_kind == OccupantKind.RULE_BASED else None
    if reason is not None and reason in _REASON_MARKS:
        return _REASON_MARKS[reason]
    return None
