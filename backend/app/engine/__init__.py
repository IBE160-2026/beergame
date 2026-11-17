"""The pure game engine: stdlib and pydantic only, no I/O, no clock, randomness only from a
passed-in seed (`app.engine.demand.series`; callers draw seeds with `demand.new_seed`)."""

from app.engine.demand import (
    SEED_MAX,
    DemandFixed,
    DemandPattern,
    DemandRandom,
    DemandStep,
    DemandStepNoise,
)
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
    "Range",
    "Role",
    "SeatState",
    "SettingsError",
    "SettingsWarning",
    "WeekState",
    "advance",
    "demand_change_reaches_retailer",
    "demand_series",
    "initial_state",
    "validate",
    "validate_demand",
    "warnings",
]
