"""«Simulert, samme kunder» (Story 9.8, FR-44, UX-DR36, AD-1): the same chain, the same customers,
played by the Rule-based rule twice.

`simulate(settings, rules_version, demand, params, role)` runs `engine.advance` from Week 1 over the
Game's settings, whose demand must equal the Game's stored demand series, with every Seat ordering
by `rule_based.order` with the Game's frozen parameter set (Guided Weeks order the starting demand,
as in play). Two rows:

- `own`: only the viewer's Seat (`role`) counts På vei; the three others order with `beta` 0, so
  the supply line they have ordered and not received does not enter their Order.
- `all`: all four Seats count På vei with the set's `beta`.

Each row holds the chain's cost over the whole Game, split as the play screen splits it: inventory
× holding cost and backlog × backorder cost of every Seat in every Week. The rule's parameters are
placeholders until issues #8 and #17 deliver the paper's values, so a row shows the connection, not
an answer («Simulert viser sammenhengen, ikke en fasit.»).

Pure: no I/O, no clock, no randomness; stdlib, pydantic and `app.engine` only."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.engine import (
    GameSettings,
    Role,
    RuleBasedParams,
    WeekState,
    advance,
    demand_series,
    guided_order,
    initial_state,
    seat_view,
)
from app.engine import rule_based as rule

__all__ = ["SimulatedChain", "SimulatedRow", "SimulationInput", "simulate"]

_FROZEN = ConfigDict(frozen=True, extra="forbid")
_Money = Annotated[Decimal, Field(allow_inf_nan=False)]


@dataclass(frozen=True)
class SimulationInput:
    """What a simulation runs on: the Game's snapshot (settings, rules version, stored demand
    series) and its frozen Rule-based parameter set."""

    settings: GameSettings
    rules_version: int
    demand: tuple[int, ...]
    params: RuleBasedParams


class SimulatedRow(BaseModel):
    """The chain's cost over the whole simulated Game."""

    model_config = _FROZEN

    counts_supply_line: Literal["own", "all"]
    """`own`: only the viewer's Seat counts På vei; `all`: every Seat does."""
    holding_cost: _Money
    backorder_cost: _Money
    total_cost: _Money


class SimulatedChain(BaseModel):
    model_config = _FROZEN

    params_id: str
    """The Rule-based parameter set the rows were played with (the Game's frozen one)."""
    params_version: Annotated[int, Field(strict=True, ge=1)]
    rows: tuple[SimulatedRow, SimulatedRow]
    """`own`, then `all`."""


def _orders(
    settings: GameSettings,
    states: Sequence[WeekState],
    placed: Sequence[Mapping[str, int]],
    params: Mapping[Role, RuleBasedParams],
) -> dict[str, int]:
    if states[-1].week <= settings.guided_weeks:
        return {role.value: guided_order(settings) for role in settings.roles}
    return {
        role.value: rule.order(settings, seat_view(settings, states, placed, role), params[role])
        for role in settings.roles
    }


def _play(
    settings: GameSettings, rules_version: int, params: Mapping[Role, RuleBasedParams]
) -> tuple[Decimal, Decimal]:
    """The chain's holding and backorder cost of one simulated Game."""
    state = initial_state(settings, rules_version)
    states: list[WeekState] = []
    placed: list[Mapping[str, int]] = []
    holding = backorder = Decimal(0)
    while not state.finished:
        states.append(state)
        for seat in state.seats:
            held = settings.holding_cost * seat.inventory
            short = settings.backorder_cost * seat.backlog
            if held + short != seat.cost:
                raise ValueError(f"Week {state.week} {seat.role}: the cost parts do not add up")
            holding += held
            backorder += short
        orders = _orders(settings, states, placed, params)
        placed.append(orders)
        state = advance(settings, state, orders, rules_version)
    return holding, backorder


def _row(
    counts: Literal["own", "all"],
    settings: GameSettings,
    rules_version: int,
    params: Mapping[Role, RuleBasedParams],
) -> SimulatedRow:
    holding, backorder = _play(settings, rules_version, params)
    return SimulatedRow(
        counts_supply_line=counts,
        holding_cost=holding,
        backorder_cost=backorder,
        total_cost=holding + backorder,
    )


def simulate(
    settings: GameSettings,
    rules_version: int,
    demand: Sequence[int],
    params: RuleBasedParams,
    role: Role | str,
) -> SimulatedChain:
    """The two «Simulert, samme kunder» rows for the viewer's Seat `role`. Raises `ValueError`
    when `role` is not in the chain or `demand` is not the series the settings give."""
    viewer = Role(role)
    if viewer not in settings.roles:
        raise ValueError(f"{viewer} is not a Role in this Game")
    if tuple(demand) != demand_series(settings):
        raise ValueError("the stored demand series is not the one the settings give")
    blind = params.model_copy(update={"beta": Decimal(0)})
    own = {each: params if each == viewer else blind for each in settings.roles}
    every = dict.fromkeys(settings.roles, params)
    return SimulatedChain(
        params_id=params.id,
        params_version=params.version,
        rows=(
            _row("own", settings, rules_version, own),
            _row("all", settings, rules_version, every),
        ),
    )
