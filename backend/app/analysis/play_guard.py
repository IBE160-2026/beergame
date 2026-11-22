"""The Play guard: does an LLM player's ordering stay inside the accepted band? (FR-79, AD-1)

Pure: no I/O, no clock. The band, its parameters and their status (placeholders, issue #20) are
described in `play_guard.md` next to this file. Parameters arrive as a `PlayGuardParams` set;
the shell reads the set's JSON file and `parse_params` validates it.

`evaluate` reads only Orders with `decided_by = llm`, so Guided Weeks and fallback Orders (which
equal the Rule-based reference) never count. `is_calibrated` says whether the full band applies
to a Game's settings; the list of calibrated settings profiles is data in the set, so a new
profile (such as `replay_default`) is a new version of the set, not a code change here.
"""

from collections.abc import Iterable
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.engine.scenario import ReplayTemplate, replay_template_admits
from app.engine.settings import GameSettings

_FROZEN = ConfigDict(frozen=True, extra="forbid")
_Count = Annotated[int, Field(strict=True, ge=0)]
_Share = Annotated[Decimal, Field(ge=0, le=1, allow_inf_nan=False)]
_Weeks = Annotated[int, Field(strict=True, ge=1)]


class PlayGuardParams(BaseModel):
    """A named, versioned parameter set of the Play guard, held as configuration."""

    model_config = _FROZEN

    id: Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9-]*$")]
    version: Annotated[int, Field(strict=True, ge=1)]
    verified: bool
    """False while the values are placeholders (issue #20)."""
    source: Annotated[str, Field(min_length=1)]
    distance: Literal["absolute_units"]
    """How far an Order is from a reference: `absolute_units` = |Order − reference| in units."""
    window_weeks: _Weeks
    """The rolling window: the Seat's newest `llm` Orders the limits are checked over."""
    minimum_weeks: _Weeks
    """No switch before the Seat has this many `llm` Orders."""
    lower_distance: _Count
    """An Order this close to the Rule-based reference counts as sensible play."""
    lower_share: _Share
    """Least share of the window's Orders within `lower_distance` of the Rule-based reference."""
    upper_margin: _Share
    """Least mean normalised distance to the near-optimal reference (0 = at it, 1 = at the
    Rule-based reference), over the window's Weeks where the two references differ."""
    large_distance: _Count
    """On settings the band was not calibrated for: what counts as a large deviation from the
    Rule-based reference (replaces `lower_distance`; the upper limit is not applied)."""
    calibrated_profiles: Annotated[
        dict[str, Annotated[GameSettings | ReplayTemplate, Field(union_mode="left_to_right")]],
        Field(min_length=1),
    ]
    """The Game settings the band was calibrated for, by name; `demand_seed` is ignored. A
    profile is one `GameSettings`, or a `ReplayTemplate` whose every draw counts (Story 10.1:
    `replay_default`, the default Replay scenario of the Classic settings)."""


def parse_params(text: str, set_id: str) -> PlayGuardParams:
    """Validate a parameter set's JSON text; its `id` must be the one asked for."""
    params = PlayGuardParams.model_validate_json(text)
    if params.id != set_id:
        raise ValueError(f"parameter set file {set_id!r} holds set {params.id!r}")
    return params


class GuardRow(BaseModel):
    """One Decision log row as the guard reads it."""

    model_config = _FROZEN

    week: _Weeks
    order: _Count
    decided_by: str
    rule_based_reference_order: _Count
    near_optimal_reference_order: _Count | None = None


class GuardDecision(StrEnum):
    WITHIN_BAND = "within_band"
    SWITCH = "switch"


Statistic = Literal["lower_share", "upper_closeness", "large_deviation"]


class GuardResult(BaseModel):
    """The guard's verdict on one Seat, with the statistic that caused a switch."""

    model_config = _FROZEN

    decision: GuardDecision
    statistic: Statistic | None = None
    """What caused the switch; None when within the band."""
    value: Decimal | None = None
    """The causing statistic's value."""
    llm_weeks: int
    """The Seat's `llm` Orders so far."""
    lower_share: Decimal | None = None
    """Share of the window within the lower (or large) distance; None below the minimum."""
    upper_closeness: Decimal | None = None
    """Mean normalised distance to the near-optimal reference; None when not applied or when
    the references coincide in every Week of the window."""


def is_calibrated(settings: GameSettings, params: PlayGuardParams) -> bool:
    """Whether `settings` are one of the set's calibrated profiles (the demand seed aside): equal
    to a `GameSettings` profile, or one draw of a `ReplayTemplate` profile."""
    wanted = settings.model_dump(exclude={"demand_seed"})
    return any(
        replay_template_admits(profile, settings)
        if isinstance(profile, ReplayTemplate)
        else profile.model_dump(exclude={"demand_seed"}) == wanted
        for profile in params.calibrated_profiles.values()
    )


def _distance(order: int, reference: int) -> int:
    return abs(order - reference)


def evaluate(
    seat_weeks: Iterable[GuardRow], params: PlayGuardParams, *, calibrated: bool = True
) -> GuardResult:
    """The Play guard over one Seat's Decision log rows (FR-79).

    Only `decided_by = llm` rows count. Below `minimum_weeks` of them the Seat is never
    switched. Over the newest `window_weeks` of them: the lower limit (share within the
    distance of the Rule-based reference) is checked first, then, on calibrated settings only,
    the upper limit (not on average too close to the near-optimal reference, over the Weeks
    where the two references differ)."""
    rows = sorted((row for row in seat_weeks if row.decided_by == "llm"), key=lambda r: r.week)
    if len(rows) < params.minimum_weeks:
        return GuardResult(decision=GuardDecision.WITHIN_BAND, llm_weeks=len(rows))
    window = rows[-params.window_weeks :]
    limit = params.lower_distance if calibrated else params.large_distance
    within = sum(_distance(r.order, r.rule_based_reference_order) <= limit for r in window)
    share = Decimal(within) / len(window)
    if share < params.lower_share:
        return GuardResult(
            decision=GuardDecision.SWITCH,
            statistic="lower_share" if calibrated else "large_deviation",
            value=share,
            llm_weeks=len(rows),
            lower_share=share,
        )
    closeness = None
    if calibrated:
        differing = [
            Decimal(_distance(r.order, r.near_optimal_reference_order))
            / _distance(r.rule_based_reference_order, r.near_optimal_reference_order)
            for r in window
            if r.near_optimal_reference_order is not None
            and r.near_optimal_reference_order != r.rule_based_reference_order
        ]
        if differing:
            closeness = sum(differing) / len(differing)
            if closeness < params.upper_margin:
                return GuardResult(
                    decision=GuardDecision.SWITCH,
                    statistic="upper_closeness",
                    value=closeness,
                    llm_weeks=len(rows),
                    lower_share=share,
                    upper_closeness=closeness,
                )
    return GuardResult(
        decision=GuardDecision.WITHIN_BAND,
        llm_weeks=len(rows),
        lower_share=share,
        upper_closeness=closeness,
    )
