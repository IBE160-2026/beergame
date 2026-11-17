"""Game settings: one versioned model whose defaults are the Classic game (FR-11).

The model guards types and signs only. `RANGES`, `validate` and `warnings` say what is allowed
and what is risky (FR-12); callers decide when to run them, construction never does.
"""

from collections.abc import Mapping
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class DemandStep(BaseModel):
    """Customer demand `start` until `change_week`, then `new_level` from that Week on."""

    model_config = FROZEN

    kind: Literal["step"]
    start: Units
    new_level: Units
    change_week: Week

    def demand_for(self, week: int) -> int:
        return self.new_level if week >= self.change_week else self.start

    @property
    def first_change_week(self) -> int | None:
        """The first Week whose demand differs from `start`, or None when demand is flat."""
        return self.change_week if self.new_level != self.start else None

    @property
    def peak(self) -> int:
        return max(self.start, self.new_level)


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
    demand: DemandStep = DemandStep(kind="step", start=4, new_level=8, change_week=5)
    holding_cost: Rate = Decimal("0.50")
    backorder_cost: Rate = Decimal("1.00")
    weeks: Week = 36
    guided_weeks: Units = 4
    max_order: Units = 999
    """A stated placeholder: large enough that it does not bind in normal play."""

    @field_validator("roles")
    @classmethod
    def _roles_form_a_chain(cls, roles: tuple[Role, ...]) -> tuple[Role, ...]:
        if not roles:
            raise ValueError("a chain needs at least one Role")
        if len(set(roles)) != len(roles):
            raise ValueError("each Role appears once in the chain")
        return roles


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
confirmed (FR-12); every other bound is a placeholder. Demand ranges come with Story 1.4."""

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


def validate(settings: GameSettings) -> tuple[SettingsError, ...]:
    """Every rule `settings` breaks: RANGES order first, then cross-field rules.

    At most one error per field: a range error suppresses that field's cross-field error.
    """
    errors: list[SettingsError] = []
    for field, allowed in RANGES.items():
        error = _check_range(field, getattr(settings, field), allowed)
        if error is not None:
            errors.append(error)
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
    start = settings.demand.start
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
    return tuple(found)
