"""Game settings: one versioned model whose defaults are the Classic game (FR-11).

The model guards types and signs only. `RANGES`, `validate` and `warnings` say what is allowed
and what is risky (FR-12); callers decide when to run them, construction never does.
"""

from collections.abc import Mapping
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from app.engine.demand import (
    SEED_MAX,
    SEEDED_KINDS,
    DemandFixed,
    DemandPattern,
    DemandStep,
    series,
)


class Role(StrEnum):
    RETAILER = "retailer"
    WHOLESALER = "wholesaler"
    DISTRIBUTOR = "distributor"
    FACTORY = "factory"


ROLES: tuple[Role, ...] = (Role.RETAILER, Role.WHOLESALER, Role.DISTRIBUTOR, Role.FACTORY)
"""The Classic chain, downstream first: the first Role serves the customer, the last produces."""

Units = Annotated[int, Field(strict=True, ge=0)]
Delay = Annotated[int, Field(strict=True, ge=1)]
Week = Annotated[int, Field(strict=True, ge=1)]
Rate = Annotated[Decimal, Field(ge=0)]

FROZEN = ConfigDict(frozen=True, extra="forbid")


class GameSettings(BaseModel):
    """Everything that defines a Game's arithmetic. `GameSettings()` is the Classic game."""

    model_config = FROZEN

    schema_version: Literal[1] = 1
    roles: tuple[Role, ...] = ROLES
    starting_inventory: Units = 12
    starting_backlog: Units = 0
    """Units every Seat owes downstream when the Game opens."""
    supply_line: Units = 4
    """Units (or Orders) in every pipeline slot when the Game opens."""
    order_delay: Delay = 2
    shipping_delay: Delay = 2
    production_delay: Delay = 2
    demand: DemandPattern = DemandStep(kind="step", start=4, new_level=8, change_week=5)
    demand_seed: Annotated[int, Field(strict=True)] | None = None
    """Seed of the demand series; required for `random` and `step+noise` (FR-13)."""
    holding_cost: Rate = Decimal("0.50")
    backorder_cost: Rate = Decimal("1.00")
    weeks: Week = 36
    guided_weeks: Units = 4
    max_order: Units = 999
    """A stated placeholder: large enough that it does not bind in normal play."""
    capacity: dict[Role, Annotated[int, Field(strict=True)]] | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    """Most units a Role can ship per Week (cut list, FR-12): one key per capped Role, so one
    Seat or every Seat. None (the default) caps no Seat and is left out of the dump, so settings
    without capacity serialise exactly as before. Range-checked by `validate`."""

    @field_validator("roles")
    @classmethod
    def _roles_form_a_chain(cls, roles: tuple[Role, ...]) -> tuple[Role, ...]:
        if not roles:
            raise ValueError("a chain needs at least one Role")
        if len(set(roles)) != len(roles):
            raise ValueError("each Role appears once in the chain")
        return roles

    @field_validator("capacity")
    @classmethod
    def _capacity_roles_in_chain(
        cls, capacity: dict[Role, int] | None, info: ValidationInfo
    ) -> dict[Role, int] | None:
        if not capacity:
            return None  # an empty map caps no Seat: the same as no capacity
        if "roles" not in info.data:
            return capacity  # the roles error is reported on its own
        for role in capacity:
            if role not in info.data["roles"]:
                raise ValueError(f"capacity names {role}, which is not a Role in this chain")
        return capacity

    def capacity_of(self, role: Role) -> int | None:
        """The Role's capacity, or None when it ships without a cap."""
        return (self.capacity or {}).get(role)


class Range(BaseModel):
    """The allowed values of one setting. `placeholder` bounds await the Class session screen."""

    model_config = FROZEN

    minimum: int | Decimal
    maximum: int | Decimal
    placeholder: bool
    decimal_places: int | None = None


def _units(maximum: int) -> Range:
    return Range(minimum=0, maximum=maximum, placeholder=True)


def _money() -> Range:
    return Range(
        minimum=Decimal("0.00"), maximum=Decimal("100.00"), placeholder=True, decimal_places=2
    )


_DELAY = Range(minimum=1, maximum=3, placeholder=False)

RANGES: Mapping[str, Range] = MappingProxyType(
    {
        "starting_inventory": _units(100),
        "starting_backlog": _units(100),
        "supply_line": _units(100),
        "order_delay": _DELAY,
        "shipping_delay": _DELAY,
        "production_delay": _DELAY,
        "holding_cost": _money(),
        "backorder_cost": _money(),
        "weeks": Range(minimum=1, maximum=100, placeholder=True),
        "guided_weeks": _units(20),
        "max_order": Range(minimum=1, maximum=9999, placeholder=True),
    }
)
"""Allowed range of every checked setting, in the order `validate` reports them. Delays are
confirmed (FR-12); every other bound is a placeholder. Demand ranges are in DEMAND_RANGES."""

DEMAND_RANGES: Mapping[str, Range] = MappingProxyType(
    {
        "values": _units(100),
        "start": _units(100),
        "new_level": _units(100),
        "mean": _units(100),
        "spread": _units(20),
        "demand_seed": Range(minimum=0, maximum=SEED_MAX, placeholder=False),
    }
)
"""Allowed range of each Demand pattern field (`values` bounds every item) and of the seed, in
the order `validate` reports them. Placeholders except the seed. The step Week must fall in
the Game (1 to `weeks`) and a fixed series must have one value per Week; both bounds follow
from `weeks`, so they are not listed here."""

CAPACITY_RANGE = Range(minimum=1, maximum=100, placeholder=True)
"""Allowed capacity of a capped Role: a whole number above 0. The maximum is a placeholder."""

MAX_ORDER_PEAK_FACTOR = 10
"""Placeholder, like the RANGES bounds: a maximum Order below this many times peak demand may
bind in normal play (single Orders reached about ten times the average in one course, FR-12)."""


class SettingsError(BaseModel):
    """A setting that is not allowed. Range errors carry the range that applies."""

    model_config = FROZEN

    code: str
    field: str
    message: str
    minimum: int | Decimal | None = None
    maximum: int | Decimal | None = None
    placeholder: bool | None = None


class SettingsWarning(BaseModel):
    """A legal but risky setting; `values` holds the numbers behind it as strings."""

    model_config = FROZEN

    code: str
    field: str
    message: str
    values: dict[str, str]


def _range_error(code: str, field: str, message: str, allowed: Range) -> SettingsError:
    return SettingsError(
        code=code,
        field=field,
        message=message,
        minimum=allowed.minimum,
        maximum=allowed.maximum,
        placeholder=allowed.placeholder,
    )


def _check_range(field: str, value: int | Decimal, allowed: Range) -> SettingsError | None:
    if not allowed.minimum <= value <= allowed.maximum:
        return _range_error(
            "out_of_range",
            field,
            f"{field} must be from {allowed.minimum} to {allowed.maximum}, not {value}",
            allowed,
        )
    if allowed.decimal_places is not None and isinstance(value, Decimal):
        step = Decimal(1).scaleb(-allowed.decimal_places)
        if value != value.quantize(step):
            return _range_error(
                "too_many_decimal_places",
                field,
                f"{field} takes at most {allowed.decimal_places} decimal places, not {value}",
                allowed,
            )
    return None


def validate(
    settings: GameSettings, *, capacity_enabled: bool = False
) -> tuple[SettingsError, ...]:
    """Every rule `settings` breaks: RANGES order first, then the Demand pattern, then
    capacity, then cross-field rules.

    At most one error per field: a range error suppresses that field's cross-field error.
    `capacity_enabled` is the caller's `FEATURE_CAPACITY` flag: when it is off, any capacity is
    refused with `capacity_disabled` (fails closed when a caller leaves it out).
    """
    errors: list[SettingsError] = []
    for field, allowed in RANGES.items():
        error = _check_range(field, getattr(settings, field), allowed)
        if error is not None:
            errors.append(error)
    errors.extend(validate_demand(settings.demand, settings.weeks, settings.demand_seed))
    errors.extend(_validate_capacity(settings, capacity_enabled))
    flagged = {error.field for error in errors}

    if (
        "starting_backlog" not in flagged
        and settings.starting_inventory > 0
        and settings.starting_backlog > 0
    ):
        errors.append(
            SettingsError(
                code="starting_inventory_and_backlog",
                field="starting_backlog",
                message=(
                    f"a Seat cannot start with both inventory ({settings.starting_inventory}) "
                    f"and backlog ({settings.starting_backlog})"
                ),
            )
        )

    if "guided_weeks" not in flagged:
        change = settings.demand.first_change_week
        if change is not None and settings.guided_weeks >= change:
            errors.append(
                SettingsError(
                    code="guided_weeks_not_before_demand_change",
                    field="guided_weeks",
                    message=(
                        f"Guided Weeks ({settings.guided_weeks}) must end before demand "
                        f"changes in Week {change}"
                    ),
                )
            )
        elif settings.guided_weeks >= settings.weeks:
            errors.append(
                SettingsError(
                    code="guided_weeks_leave_no_weeks_to_play",
                    field="guided_weeks",
                    message=(
                        f"Guided Weeks ({settings.guided_weeks}) leave no Weeks to play "
                        f"in a Game of {settings.weeks} Weeks"
                    ),
                )
            )
    return tuple(errors)


def _validate_capacity(settings: GameSettings, enabled: bool) -> list[SettingsError]:
    if settings.capacity is None:
        return []
    if not enabled:
        return [
            SettingsError(
                code="capacity_disabled",
                field="capacity",
                message="capacity is switched off (FEATURE_CAPACITY)",
            )
        ]
    errors: list[SettingsError] = []
    for role in settings.roles:
        value = settings.capacity_of(role)
        if value is not None and not CAPACITY_RANGE.minimum <= value <= CAPACITY_RANGE.maximum:
            errors.append(
                _range_error(
                    "out_of_range",
                    f"capacity.{role.value}",
                    f"the capacity of the {role.value} must be a whole number from "
                    f"{CAPACITY_RANGE.minimum} to {CAPACITY_RANGE.maximum}, not {value}",
                    CAPACITY_RANGE,
                )
            )
    return errors


def validate_demand(
    pattern: DemandPattern, weeks: int, seed: int | None
) -> tuple[SettingsError, ...]:
    """Every rule the Demand pattern and its seed break in a Game of `weeks` Weeks (FR-13).

    One error per field, in this order: `demand.values`, then the range checks of `start`,
    `new_level`, `mean` and `spread`, then `demand.change_week`, then `demand_seed`.
    """
    errors: list[SettingsError] = []
    if isinstance(pattern, DemandFixed):
        allowed = DEMAND_RANGES["values"]
        if len(pattern.values) != weeks:
            errors.append(
                _range_error(
                    "fixed_series_length",
                    "demand.values",
                    f"a fixed series needs one value per Week ({weeks}), not {len(pattern.values)}",
                    Range(minimum=weeks, maximum=weeks, placeholder=False),
                )
            )
        else:
            for week, value in enumerate(pattern.values, start=1):
                if not allowed.minimum <= value <= allowed.maximum:
                    errors.append(
                        _range_error(
                            "out_of_range",
                            "demand.values",
                            f"demand in Week {week} must be from {allowed.minimum} to "
                            f"{allowed.maximum}, not {value}",
                            allowed,
                        )
                    )
                    break
    for name in ("start", "new_level", "mean", "spread"):
        if name in type(pattern).model_fields:
            error = _check_range(f"demand.{name}", getattr(pattern, name), DEMAND_RANGES[name])
            if error is not None:
                errors.append(error)
    change_week = getattr(pattern, "change_week", None)
    if change_week is not None and change_week > weeks:
        errors.append(
            _range_error(
                "demand_change_week_outside_game",
                "demand.change_week",
                f"the demand change in Week {change_week} falls outside a Game of {weeks} Weeks",
                Range(minimum=1, maximum=weeks, placeholder=False),
            )
        )
    if pattern.kind in SEEDED_KINDS and seed is None:
        errors.append(
            SettingsError(
                code="demand_seed_required",
                field="demand_seed",
                message=f"a {pattern.kind} Demand pattern needs a seed",
            )
        )
    elif seed is not None:
        error = _check_range("demand_seed", seed, DEMAND_RANGES["demand_seed"])
        if error is not None:
            errors.append(error)
    return tuple(errors)


def demand_series(settings: GameSettings) -> tuple[int, ...]:
    """The customer demand of every Week of the Game, from its pattern and seed."""
    return series(settings.demand, settings.weeks, settings.demand_seed)


def demand_change_reaches_retailer(settings: GameSettings) -> int | None:
    """The Week the demand change first reaches the Retailer through the whole chain.

    Each Seat passes the change on in the Week it sees it: n Order hops, production, and n-1
    shipping hops back down. None when demand is flat.
    """
    change = settings.demand.first_change_week
    if change is None:
        return None
    n = len(settings.roles)
    return (
        change
        + n * settings.order_delay
        + settings.production_delay
        + (n - 1) * settings.shipping_delay
    )


def warnings(settings: GameSettings) -> tuple[SettingsWarning, ...]:
    """Legal but risky choices, in a fixed order. Never blocks a Game."""
    found: list[SettingsWarning] = []
    start = settings.demand.starting_level
    if settings.supply_line != start:
        found.append(
            SettingsWarning(
                code="supply_line_differs_from_demand",
                field="supply_line",
                message=(
                    f"the supply line ({settings.supply_line}) differs from starting demand "
                    f"({start}), so the chain does not start in balance"
                ),
                values={"supply_line": str(settings.supply_line), "starting_demand": str(start)},
            )
        )
    if settings.backorder_cost <= settings.holding_cost:
        found.append(
            SettingsWarning(
                code="backorder_not_above_holding",
                field="backorder_cost",
                message=(
                    f"backorder cost ({settings.backorder_cost}) is not above holding cost "
                    f"({settings.holding_cost}), so running short costs no more than stock"
                ),
                values={
                    "backorder_cost": str(settings.backorder_cost),
                    "holding_cost": str(settings.holding_cost),
                },
            )
        )
    peak = settings.demand.peak
    threshold = MAX_ORDER_PEAK_FACTOR * peak
    if settings.max_order < threshold:
        found.append(
            SettingsWarning(
                code="max_order_may_bind",
                field="max_order",
                message=(
                    f"the maximum Order ({settings.max_order}) is below {threshold}, "
                    f"{MAX_ORDER_PEAK_FACTOR} times "
                    f"peak demand ({peak}), and may bind in normal play"
                ),
                values={
                    "max_order": str(settings.max_order),
                    "peak_demand": str(peak),
                    "threshold": str(threshold),
                },
            )
        )
    arrival = demand_change_reaches_retailer(settings)
    if arrival is not None and arrival > settings.weeks:
        found.append(
            SettingsWarning(
                code="too_few_weeks_for_demand_change",
                field="weeks",
                message=(
                    f"if every Seat passes the demand change on at once, the first units the "
                    f"Factory makes for it reach the Retailer in Week {arrival}, after the "
                    f"last Week ({settings.weeks})"
                ),
                values={"arrival_week": str(arrival), "weeks": str(settings.weeks)},
            )
        )
    for role in settings.roles:
        capacity = settings.capacity_of(role)
        if capacity is not None and capacity < peak:
            found.append(
                SettingsWarning(
                    code="capacity_below_peak_demand",
                    field=f"capacity.{role.value}",
                    message=(
                        f"the {role.value} can ship at most {capacity} a Week, below peak "
                        f"demand ({peak}), so it cannot keep up while demand is at its peak"
                    ),
                    values={
                        "role": role.value,
                        "capacity": str(capacity),
                        "peak_demand": str(peak),
                    },
                )
            )
    return tuple(found)
