"""The Replay scenario as a template (Story 10.1, FR-49, AD-1, AD-4).

A `ReplayTemplate` holds every `GameSettings` field, each whole-number field as a fixed value or
a whole-number range, and the demand as a level pattern with a spread of variation. One pure
function, `replay_settings(template, seed)`, turns a template and a Student's seed into the
`GameSettings` a Replay plays: every ranged value is drawn from `SHA-256("replay:{seed}:{field}")`
and the demand series from the seed (it becomes the settings' `demand_seed`), so the result
depends only on the template and the seed. No I/O, no clock.

`default_replay_template(settings)` derives the default scenario from a Class session's Game
settings, one rule per Demand pattern kind. `validate_template` judges a template with the same
`validate` as Game settings; `replay_template_admits` says whether settings are one draw of a
template (the Play guard's calibrated `replay_default` profile, FR-79).
"""

import hashlib
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from app.engine.demand import (
    SEED_MAX,
    DemandFixed,
    DemandRandom,
    DemandStep,
    DemandStepNoise,
    week_noise,
)
from app.engine.settings import (
    DEMAND_RANGES,
    RANGES,
    ROLES,
    GameSettings,
    InfoVisibility,
    Role,
    SettingsError,
    validate,
)

_FROZEN = ConfigDict(frozen=True, extra="forbid")

Whole = Annotated[int, Field(strict=True, ge=0)]
Level = Annotated[int, Field(strict=True, ge=0)]
Spread = Annotated[int, Field(strict=True, ge=0)]
Rate = Annotated[Decimal, Field(ge=0)]


class IntRange(BaseModel):
    """Every whole number from `minimum` to `maximum`, both included; one is drawn per seed."""

    model_config = _FROZEN

    minimum: Whole
    maximum: Whole


Ranged = Whole | IntRange
"""A whole-number setting of a template: one fixed value, or a range drawn per seed."""


class ReplayStep(BaseModel):
    """`start` until the change Week, then `new_level`, with variation of `spread` each Week.
    Spread 0 resolves to a `step` pattern, any other to `step+noise`."""

    model_config = _FROZEN

    kind: Literal["step"]
    start: Level
    new_level: Level
    change_week: Ranged
    spread: Spread


class ReplayRandom(BaseModel):
    """Demand around `mean` with variation of `spread` each Week (a `random` pattern)."""

    model_config = _FROZEN

    kind: Literal["random"]
    mean: Level
    spread: Spread


class ReplayFixed(BaseModel):
    """Each Week's value of `values` as the level, the last one held for Weeks beyond the series,
    with variation of `spread` each Week. Resolves to a `fixed` series of the drawn length."""

    model_config = _FROZEN

    kind: Literal["fixed"]
    values: Annotated[tuple[Level, ...], Field(min_length=1)]
    spread: Spread

    def level_for(self, week: int) -> int:
        return self.values[min(week, len(self.values)) - 1]


ReplayDemand = Annotated[ReplayStep | ReplayRandom | ReplayFixed, Field(discriminator="kind")]

RANGED_FIELDS: tuple[str, ...] = (
    "starting_inventory",
    "starting_backlog",
    "supply_line",
    "order_delay",
    "shipping_delay",
    "production_delay",
    "weeks",
    "guided_weeks",
    "max_order",
)
"""The top-level whole-number settings a template may range, in `RANGES` order."""

CHANGE_WEEK = "demand.change_week"


class ReplayTemplate(BaseModel):
    """A Replay scenario: every `GameSettings` field (the demand seed aside, which is the
    Student's), whole numbers fixed or ranged."""

    model_config = _FROZEN

    schema_version: Literal[1] = 1
    roles: tuple[Role, ...] = ROLES
    starting_inventory: Ranged
    starting_backlog: Ranged
    supply_line: Ranged
    order_delay: Ranged
    shipping_delay: Ranged
    production_delay: Ranged
    demand: ReplayDemand
    holding_cost: Rate
    backorder_cost: Rate
    weeks: Ranged
    guided_weeks: Ranged
    max_order: Ranged
    capacity: dict[Role, Annotated[int, Field(strict=True)]] | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    info_visibility: InfoVisibility = InfoVisibility()

    @field_validator("roles")
    @classmethod
    def _roles_form_a_chain(cls, roles: tuple[Role, ...]) -> tuple[Role, ...]:
        """The same rule as `GameSettings`, so a draw never fails on its chain."""
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
        """An empty map caps no Seat, and a capped Role is in the chain, as in `GameSettings`."""
        if not capacity:
            return None
        for role in capacity:
            if "roles" in info.data and role not in info.data["roles"]:
                raise ValueError(f"capacity names {role}, which is not a Role in this chain")
        return capacity


DEFAULT_SPREAD = 2
"""The least variation of the default scenario's demand (FR-49): the Class session's own spread
where that is larger."""
DEFAULT_CHANGE_WEEK = IntRange(minimum=5, maximum=12)
DEFAULT_WEEKS = IntRange(minimum=30, maximum=40)


def default_replay_template(settings: GameSettings) -> ReplayTemplate:
    """The default Replay scenario of a Class session with `settings` (FR-49, FR-13): the Class
    game's demand levels with at least `DEFAULT_SPREAD` of variation each Week, a step Week of
    5 to 12 (step kinds only), 30 to 40 Weeks, no Guided Weeks, and every other setting as in
    `settings`. A fixed series keeps each Week's value as the level and holds the last one."""
    pattern = settings.demand
    demand: ReplayStep | ReplayRandom | ReplayFixed
    if isinstance(pattern, DemandStep | DemandStepNoise):
        demand = ReplayStep(
            kind="step",
            start=pattern.start,
            new_level=pattern.new_level,
            change_week=DEFAULT_CHANGE_WEEK,
            spread=max(DEFAULT_SPREAD, pattern.spread),
        )
    elif isinstance(pattern, DemandRandom):
        demand = ReplayRandom(
            kind="random", mean=pattern.mean, spread=max(DEFAULT_SPREAD, pattern.spread)
        )
    else:
        demand = ReplayFixed(kind="fixed", values=pattern.values, spread=DEFAULT_SPREAD)
    return ReplayTemplate(
        roles=settings.roles,
        starting_inventory=settings.starting_inventory,
        starting_backlog=settings.starting_backlog,
        supply_line=settings.supply_line,
        order_delay=settings.order_delay,
        shipping_delay=settings.shipping_delay,
        production_delay=settings.production_delay,
        demand=demand,
        holding_cost=settings.holding_cost,
        backorder_cost=settings.backorder_cost,
        weeks=DEFAULT_WEEKS,
        guided_weeks=0,
        max_order=settings.max_order,
        capacity=settings.capacity,
        info_visibility=settings.info_visibility,
    )


def _draw(seed: int, field: str, value: Ranged) -> int:
    if isinstance(value, int):
        return value
    if value.minimum > value.maximum:
        raise ValueError(f"{field}: the range {value.minimum} to {value.maximum} is inverted")
    digest = hashlib.sha256(f"replay:{seed}:{field}".encode("ascii")).digest()
    return value.minimum + int.from_bytes(digest, "big") % (value.maximum - value.minimum + 1)


def _check_seed(seed: object) -> int:
    if type(seed) is not int or not 0 <= seed <= SEED_MAX:
        raise ValueError(f"a Replay seed is a whole number from 0 to {SEED_MAX}, not {seed!r}")
    return seed


VALUES_MAX = int(DEMAND_RANGES["values"].maximum)
"""The highest demand value a fixed series may hold: a drawn value stays at or below it (or its
level, were that higher), as a drawn value below 0 becomes 0, so a draw of a valid template is
valid."""


def _bounded(level: int, value: int) -> int:
    return min(max(level, VALUES_MAX), max(0, value))


def _fixed_series(demand: ReplayFixed, weeks: int, seed: int) -> tuple[int, ...]:
    if demand.spread == 0:
        return tuple(demand.level_for(week) for week in range(1, weeks + 1))
    return tuple(
        _bounded(
            demand.level_for(week), demand.level_for(week) + week_noise(seed, week, demand.spread)
        )
        for week in range(1, weeks + 1)
    )


def _resolve(
    template: ReplayTemplate, values: dict[str, int], seed: int, *, noise: bool = True
) -> GameSettings:
    """The settings with the whole numbers `values` (every RANGED_FIELD and, for a step, the
    change Week) and the demand drawn from `seed`; without `noise` a fixed series is its levels
    (validation judges the levels, as `validate` does for the other kinds)."""
    demand = template.demand
    pattern: dict[str, Any]
    if isinstance(demand, ReplayStep):
        pattern = {
            "kind": "step" if demand.spread == 0 else "step+noise",
            "start": demand.start,
            "new_level": demand.new_level,
            "change_week": values[CHANGE_WEEK],
        }
        if demand.spread:
            pattern["spread"] = demand.spread
    elif isinstance(demand, ReplayRandom):
        pattern = {"kind": "random", "mean": demand.mean, "spread": demand.spread}
    else:
        levels = demand if noise else demand.model_copy(update={"spread": 0})
        pattern = {"kind": "fixed", "values": _fixed_series(levels, values["weeks"], seed)}
    return GameSettings.model_validate(
        {
            "roles": template.roles,
            **{field: values[field] for field in RANGED_FIELDS},
            "demand": pattern,
            "demand_seed": seed,
            "holding_cost": template.holding_cost,
            "backorder_cost": template.backorder_cost,
            "capacity": template.capacity,
            "info_visibility": template.info_visibility,
        }
    )


def _ranged(template: ReplayTemplate) -> dict[str, Ranged]:
    found: dict[str, Ranged] = {field: getattr(template, field) for field in RANGED_FIELDS}
    if isinstance(template.demand, ReplayStep):
        found[CHANGE_WEEK] = template.demand.change_week
    return found


def replay_settings(template: ReplayTemplate, seed: int) -> GameSettings:
    """The `GameSettings` of a Replay with `template` and the Student's `seed` (0 to `SEED_MAX`):
    each ranged value drawn from the seed, the seed as the demand seed. The same template and
    seed always give the same settings and demand series. Raises `ValueError` for a bad seed or
    an inverted range; it does not run `validate` (callers judge the template once with
    `validate_template`)."""
    seed = _check_seed(seed)
    values = {field: _draw(seed, field, value) for field, value in _ranged(template).items()}
    return _resolve(template, values, seed)


def _bounds(value: Ranged) -> tuple[int, int]:
    return (value, value) if isinstance(value, int) else (value.minimum, value.maximum)


def validate_template(
    template: ReplayTemplate,
    *,
    capacity_enabled: bool = False,
    info_visibility_enabled: bool = False,
) -> tuple[SettingsError, ...]:
    """Every rule a draw of `template` could break, with the field and its allowed range (FR-12).

    An inverted range is `range_inverted`. Otherwise each range's bounds are checked against
    `RANGES`, and then `engine.validate` judges four corner draws (all minima; all maxima; the
    fewest Weeks with the latest change Week and the most Guided Weeks; the fewest Weeks with
    the earliest change Week and the most Guided Weeks), which reach every cross-field rule of
    `validate`. At most one error per field, the first found."""
    ranged = _ranged(template)
    errors: dict[str, SettingsError] = {}
    for field, value in ranged.items():
        low, high = _bounds(value)
        if low > high:
            errors[field] = SettingsError(
                code="range_inverted",
                field=field,
                message=f"{field}: the lowest value ({low}) is above the highest ({high})",
                minimum=low,
                maximum=high,
            )
    if errors:
        return tuple(errors.values())
    bounds = {field: _bounds(value) for field, value in ranged.items()}
    lows = {field: low for field, (low, _) in bounds.items()}
    highs = {field: high for field, (_, high) in bounds.items()}
    corners = [lows, highs]
    for change in (highs, lows):
        corner = dict(lows)
        corner["guided_weeks"] = highs["guided_weeks"]
        if CHANGE_WEEK in bounds:
            corner[CHANGE_WEEK] = change[CHANGE_WEEK]
        corners.append(corner)
    for corner in corners:
        # Bounds that `GameSettings` itself refuses (a delay or Week count of 0, a change Week
        # of 0) are reported with their range here, before a draw is built.
        found = _bound_errors(corner)
        if not found:
            settings = _resolve(template, corner, 0, noise=False)
            found = list(
                validate(
                    settings,
                    capacity_enabled=capacity_enabled,
                    info_visibility_enabled=info_visibility_enabled,
                )
            )
        for error in found:
            errors.setdefault(error.field, error)
    if isinstance(template.demand, ReplayFixed):
        for error in _fixed_noise_errors(template.demand, highs["guided_weeks"]):
            errors.setdefault(error.field, error)
    return tuple(errors.values())


def _fixed_noise_errors(demand: ReplayFixed, guided_weeks: int) -> list[SettingsError]:
    """What a fixed series' variation adds to the corner draws, which judge its levels: the
    spread's own range, and Guided Weeks that must end before Week 2, where the drawn demand may
    first differ from Week 1 (`validate`'s Guided Weeks rule reads the drawn series)."""
    if demand.spread == 0:
        return []
    allowed = DEMAND_RANGES["spread"]
    found = []
    if demand.spread > allowed.maximum:
        found.append(
            SettingsError(
                code="out_of_range",
                field="demand.spread",
                message=(
                    f"demand.spread must be from {allowed.minimum} to {allowed.maximum}, "
                    f"not {demand.spread}"
                ),
                minimum=allowed.minimum,
                maximum=allowed.maximum,
                placeholder=allowed.placeholder,
            )
        )
    if guided_weeks >= 2:
        found.append(
            SettingsError(
                code="guided_weeks_not_before_demand_change",
                field="guided_weeks",
                message=(f"Guided Weeks ({guided_weeks}) must end before demand varies in Week 2"),
                minimum=0,
                maximum=1,
                placeholder=False,
            )
        )
    return found


def _bound_errors(values: dict[str, int]) -> list[SettingsError]:
    found = []
    for field in ("order_delay", "shipping_delay", "production_delay", "weeks"):
        allowed = RANGES[field]
        if values[field] < 1:
            found.append(
                SettingsError(
                    code="out_of_range",
                    field=field,
                    message=(
                        f"{field} must be from {allowed.minimum} to {allowed.maximum}, "
                        f"not {values[field]}"
                    ),
                    minimum=allowed.minimum,
                    maximum=allowed.maximum,
                    placeholder=allowed.placeholder,
                )
            )
    if values.get(CHANGE_WEEK, 1) < 1:
        found.append(
            SettingsError(
                code="out_of_range",
                field=CHANGE_WEEK,
                message=f"the change Week must be 1 or later, not {values[CHANGE_WEEK]}",
                minimum=1,
                maximum=values["weeks"],
                placeholder=False,
            )
        )
    return found


def _within(value: int, ranged: Ranged) -> bool:
    low, high = _bounds(ranged)
    return low <= value <= high


def replay_template_admits(template: ReplayTemplate, settings: GameSettings) -> bool:
    """Whether `settings` are one draw of `template`, whatever the seed: every fixed setting
    equal, every ranged one inside its range, and the demand of the template's kind with its
    levels and spread (a fixed series: each Week within the spread of its level)."""
    if any(
        not _within(getattr(settings, field), getattr(template, field)) for field in RANGED_FIELDS
    ):
        return False
    if (
        settings.roles,
        settings.holding_cost,
        settings.backorder_cost,
        settings.capacity,
        settings.info_visibility,
    ) != (
        template.roles,
        template.holding_cost,
        template.backorder_cost,
        template.capacity,
        template.info_visibility,
    ):
        return False
    demand, pattern = template.demand, settings.demand
    if isinstance(demand, ReplayStep):
        wanted = DemandStep if demand.spread == 0 else DemandStepNoise
        return (
            type(pattern) is wanted
            and (pattern.start, pattern.new_level, pattern.spread)
            == (demand.start, demand.new_level, demand.spread)
            and _within(pattern.change_week, demand.change_week)
        )
    if isinstance(demand, ReplayRandom):
        return isinstance(pattern, DemandRandom) and (pattern.mean, pattern.spread) == (
            demand.mean,
            demand.spread,
        )
    return (
        isinstance(pattern, DemandFixed)
        and len(pattern.values) == settings.weeks
        and all(
            _bounded(demand.level_for(week), demand.level_for(week) - demand.spread)
            <= value
            <= _bounded(demand.level_for(week), demand.level_for(week) + demand.spread)
            for week, value in enumerate(pattern.values, start=1)
        )
    )
