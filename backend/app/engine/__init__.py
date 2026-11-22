"""The pure game engine: stdlib and pydantic only, no I/O, no clock, randomness only from a
passed-in seed (`app.engine.demand.series`; callers draw seeds with `demand.new_seed`).

`app.engine.check.conservation` checks the bookkeeping of a list of Week states (FR-29).
`app.engine.rule_based.order` is the Rule-based player's Order for one `SeatView` (FR-33).
`app.engine.near_optimal.order` is the near-optimal reference Order from the whole chain state
and demand series, which no player sees (FR-79).
`app.engine.scripted.REGISTRY` holds the closed set of scripted Order policies (AD-22).
`app.engine.rules` holds one package per rules version; `advance` and `initial_state` take the
`rules_version` to run (AD-4), and `app.engine.replay.replay` replays a stored Game (FR-29).
`app.engine.scenario` holds the Replay scenario template: `default_replay_template` derives the
default, `replay_settings(template, seed)` resolves one per Student (Story 10.1, FR-49)."""

from app.engine.check import Violation
from app.engine.demand import (
    SEED_MAX,
    DemandFixed,
    DemandPattern,
    DemandRandom,
    DemandStep,
    DemandStepNoise,
)
from app.engine.errors import UnknownRulesVersionError
from app.engine.guided import guided_order
from app.engine.rule_based import RuleBasedParams
from app.engine.rules import RULES_VERSION
from app.engine.scenario import (
    IntRange,
    ReplayFixed,
    ReplayRandom,
    ReplayStep,
    ReplayTemplate,
    default_replay_template,
    replay_settings,
    replay_template_admits,
    validate_template,
)
from app.engine.settings import (
    CAPACITY_RANGE,
    DEMAND_RANGES,
    RANGES,
    ROLES,
    GameSettings,
    InfoVisibility,
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
    neighbour_numbers,
    placed_orders,
    seat_detail,
    seat_view,
)
from app.engine.week import GameFinishedError, InvalidOrdersError, advance, initial_state

__all__ = [
    "CAPACITY_RANGE",
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
    "InfoVisibility",
    "IntRange",
    "InvalidOrdersError",
    "NeighbourNumber",
    "OrderPreview",
    "Range",
    "ReplayFixed",
    "ReplayRandom",
    "ReplayStep",
    "ReplayTemplate",
    "Role",
    "RuleBasedParams",
    "SeatDetail",
    "SeatState",
    "SeatView",
    "SettingsError",
    "SettingsWarning",
    "SupplyLineSlot",
    "UnknownRulesVersionError",
    "Violation",
    "WeekState",
    "WeekValues",
    "advance",
    "demand_change_reaches_retailer",
    "default_replay_template",
    "demand_series",
    "guided_order",
    "initial_state",
    "neighbour_numbers",
    "placed_orders",
    "replay_settings",
    "replay_template_admits",
    "seat_detail",
    "seat_view",
    "validate",
    "validate_demand",
    "validate_template",
    "warnings",
]
