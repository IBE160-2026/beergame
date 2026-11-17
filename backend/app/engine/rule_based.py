"""The Rule-based player: anchoring and adjustment on the Seat's own numbers (FR-33, AD-1).

The rule, its parameters and the source the final values must come from are described in
`rule_based.md` next to this file. Parameters arrive as a `RuleBasedParams` set; the shell reads
the set's JSON file and `parse_params` validates it, so the engine reads no files.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from pydantic import BaseModel, Field

from app.engine.settings import FROZEN, GameSettings
from app.engine.view import SeatView

Weight = Annotated[Decimal, Field(ge=0, le=1, allow_inf_nan=False)]


class RuleBasedParams(BaseModel):
    """A named, versioned parameter set of the rule, held as configuration."""

    model_config = FROZEN

    id: Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9-]*$")]
    version: Annotated[int, Field(strict=True, ge=1)]
    verified: bool
    """False until the values come from the primary source."""
    source: Annotated[str, Field(min_length=1)]
    theta: Weight
    """Weight of the newest incoming order in the expected incoming order (smoothing)."""
    alpha_s: Weight
    """Share of the stock gap corrected in one Order."""
    beta: Weight
    """Weight of the supply-line gap relative to the stock gap."""
    desired_inventory: Annotated[int, Field(strict=True, ge=0)]
    """Effective inventory (inventory minus backlog) the Seat aims for, in units."""


def parse_params(text: str, set_id: str) -> RuleBasedParams:
    """Validate a parameter set's JSON text; its `id` must be the one asked for."""
    params = RuleBasedParams.model_validate_json(text)
    if params.id != set_id:
        raise ValueError(f"parameter set file {set_id!r} holds set {params.id!r}")
    return params


def expected_incoming_order(incoming_orders: tuple[int, ...], theta: Decimal) -> Decimal:
    """Exponential smoothing of the incoming orders, anchored on the first one."""
    expected = Decimal(incoming_orders[0])
    for value in incoming_orders[1:]:
        expected = theta * value + (1 - theta) * expected
    return expected


def lead_weeks(settings: GameSettings, seat_view: SeatView) -> int:
    """Weeks of demand in the supply line just before ordering when every Order equals demand."""
    if seat_view.role not in settings.roles:
        raise ValueError(f"{seat_view.role} is not a Role in this Game")
    goods = (
        settings.production_delay
        if seat_view.role == settings.roles[-1]
        else settings.shipping_delay
    )
    return settings.order_delay + goods - 1


def order(settings: GameSettings, seat_view: SeatView, params: RuleBasedParams) -> int:
    """The Rule-based Order for this Seat this Week: a whole number from 0 to `max_order`.

    Reads the Seat's own inventory, backlog, incoming orders and supply line, and the Game's
    delays and maximum Order; never `neighbour_numbers`.
    """
    lead = lead_weeks(settings, seat_view)
    expected = expected_incoming_order(seat_view.incoming_orders, params.theta)
    stock_gap = params.desired_inventory - (seat_view.inventory - seat_view.backlog)
    supply_line_gap = expected * lead - seat_view.supply_line
    indicated = expected + params.alpha_s * (stock_gap + params.beta * supply_line_gap)
    whole = int(indicated.quantize(Decimal(1), rounding=ROUND_HALF_UP))
    return min(max(whole, 0), settings.max_order)
