"""The pure game engine: stdlib and pydantic only, no I/O, no clock, randomness only from a
passed-in seed (`app.engine.demand.series`; callers draw seeds with `demand.new_seed`).

`app.engine.check.conservation` checks the bookkeeping of a list of Week states (FR-29).
`app.engine.rule_based.order` is the Rule-based player's Order for one `SeatView` (FR-33)."""

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
from app.engine.view import NeighbourNumber, SeatView, seat_view
from app.engine.week import GameFinishedError, InvalidOrdersError, advance, initial_state

__all__ = [
    "DEMAND_RANGES",
    "RANGES",
    "ROLES",
    "SEED_MAX",
    "DemandFixed",
    "DemandPattern",
    "DemandRandom",
    "DemandStep",
    "DemandStepNoise",
    "GameFinishedError",
    "GameSettings",
    "InvalidOrdersError",
    "NeighbourNumber",
    "Range",
    "Role",
    "RuleBasedParams",
    "SeatState",
    "SeatView",
    "SettingsError",
    "SettingsWarning",
    "Violation",
    "WeekState",
    "advance",
    "demand_change_reaches_retailer",
    "demand_series",
    "guided_order",
    "initial_state",
    "seat_view",
    "validate",
    "validate_demand",
    "warnings",
]
