"""The one mapping from who decided and who held a Seat to the mark its readers show (AD-15).

Exported through `games.service` (`seat_mark`) for every reader; it lives here because the read
models in `views` use it too, and `views` cannot import `service`."""

from app.modules.games.schemas import DecidedBy, Fallback, OccupancyReason, OccupantKind, SeatMark


def seat_mark(
    decided_by: DecidedBy | str | None,
    fallback: Fallback | str | None,
    occupant_kind: OccupantKind | str | None,
    reason: OccupancyReason | str | None,
) -> SeatMark | None:
    """The mark of a Seat, or of one of its Orders, from the Decision log's `decided_by` and
    `fallback` (None when no Order is in question) and the occupancy's `occupant_kind` and
    `reason`. Story 6.14 adds `guard_switch`: a Rule-based occupant the Play guard put in
    (FR-79, FR-34); later stories add the marks they need here. None: nothing to mark."""
    del decided_by, fallback  # no mark reads them yet; later marks will (AD-15)
    if occupant_kind == OccupantKind.RULE_BASED and reason == OccupancyReason.GUARD_SWITCH:
        return SeatMark.GUARD_SWITCH
    return None
