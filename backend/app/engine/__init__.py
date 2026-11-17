"""The pure game engine: stdlib and pydantic only, no I/O, no clock, randomness only from a
passed-in seed (`app.engine.demand.series`; callers draw seeds with `demand.new_seed`).

`app.engine.check.conservation` checks the bookkeeping of a list of Week states (FR-29).
`app.engine.rule_based.order` is the Rule-based player's Order for one `SeatView` (FR-33).
`app.engine.scripted.REGISTRY` holds the closed set of scripted Order policies (AD-22)."""

from app.engine.check import Violation
from app.engine.demand import (
    SEED_MAX,
    DemandFixed,
    DemandPattern,
    DemandRandom,
    DemandStep,
    DemandStepNoise,
)
from app.engine.guided import guided_order
from app.engine.rule_based import RuleBasedParams
from app.engine.settings import (
    DEMAND_RANGES,
    RANGES,
    ROLES,
    GameSettings,
    Range,
    Role,
    SettingsError,
    SettingsWarning,
    demand_change_reaches_retailer,
    demand_series,
    validate,
    validate_demand,
    warnings,
)
from app.engine.state import SeatState, WeekState
from app.engine.view import (
    CostLine,
    NeighbourNumber,
    OrderPreview,
    SeatDetail,
    SeatView,
    SupplyLineSlot,
    WeekValues,
    placed_orders,
    seat_detail,
    seat_view,
)
from app.engine.week import GameFinishedError, InvalidOrdersError, advance, initial_state

RULES_VERSION = 1
"""Version of the game rules this engine computes. A Game stores it at creation (AD-4); an edit
that changes any output is a new version."""

__all__ = [
    "DEMAND_RANGES",
    "RANGES",
    "ROLES",
    "RULES_VERSION",
    "SEED_MAX",
    "CostLine",
    "DemandFixed",
    "DemandPattern",
    "DemandRandom",
    "DemandStep",
    "DemandStepNoise",
    "GameFinishedError",
    "GameSettings",
    "InvalidOrdersError",
    "NeighbourNumber",
    "OrderPreview",
    "Range",
    "Role",
    "RuleBasedParams",
    "SeatDetail",
    "SeatState",
    "SeatView",
    "SettingsError",
    "SettingsWarning",
    "SupplyLineSlot",
    "Violation",
    "WeekState",
    "WeekValues",
    "advance",
    "demand_change_reaches_retailer",
    "demand_series",
    "guided_order",
    "initial_state",
    "placed_orders",
    "seat_detail",
    "seat_view",
    "validate",
    "validate_demand",
    "warnings",
]
