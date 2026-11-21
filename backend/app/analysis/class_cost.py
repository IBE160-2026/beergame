"""«Klassens kostnad» on the Oversikt (Story 7.6, FR-39, AD-1, AD-10, UX-DR72).

Pure: no I/O, no clock. `class_cost` takes each finished Class game's chain Total cost and each
Role's cost split into lager (inventory) and restordre (backlog), and returns the median and the
middle half of the chain costs (for the Kostnadsfordeling) and the mean split per finished game,
for the chain and per Role («Snitt per ferdig spill, per Rolle»). The Lecturer overview serves
it; the Class report (Epic 13) can reuse it.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.analysis.wall import quartiles

__all__ = ["ClassCost", "FinishedGame", "RoleMean", "class_cost"]

_CENT = Decimal("0.01")


@dataclass(frozen=True)
class FinishedGame:
    """One finished Game: its chain Total cost and, by Role, the (lager, restordre) parts of that
    Role's Total cost."""

    chain_cost: Decimal
    roles: Mapping[str, tuple[Decimal, Decimal]]


@dataclass(frozen=True)
class RoleMean:
    """One Role's mean cost per finished Game, split into lager and restordre; `total_cost` is
    their sum. In kroner, rounded to the øre."""

    role: str
    holding_cost: Decimal
    backorder_cost: Decimal
    total_cost: Decimal


@dataclass(frozen=True)
class ClassCost:
    """The cost picture of the finished Games: how many, the median and quartiles of their chain
    costs (the inclusive method of `quartiles`), the chain's mean lager and restordre per Game and
    each Role's mean in `roles` order. In kroner; the means are rounded to the øre."""

    games: int
    median: Decimal
    lower_quartile: Decimal
    upper_quartile: Decimal
    holding_cost: Decimal
    backorder_cost: Decimal
    roles: tuple[RoleMean, ...]


def _mean(values: Sequence[Decimal]) -> Decimal:
    return (sum(values, Decimal(0)) / len(values)).quantize(_CENT, ROUND_HALF_UP)


def class_cost(games: Sequence[FinishedGame], roles: Sequence[str]) -> ClassCost | None:
    """The cost picture of `games` with a mean for each of `roles` in that order (a Role a Game
    lacks counts 0 for it), or None for no Game."""
    spread = quartiles(game.chain_cost for game in games)
    if spread is None:
        return None
    zero = (Decimal(0), Decimal(0))
    means = []
    for role in roles:
        holding = _mean([game.roles.get(role, zero)[0] for game in games])
        backorder = _mean([game.roles.get(role, zero)[1] for game in games])
        means.append(RoleMean(role, holding, backorder, holding + backorder))
    return ClassCost(
        games=len(games),
        median=spread[1],
        lower_quartile=spread[0],
        upper_quartile=spread[2],
        holding_cost=_mean([sum((h for h, _ in g.roles.values()), Decimal(0)) for g in games]),
        backorder_cost=_mean([sum((b for _, b in g.roles.values()), Decimal(0)) for g in games]),
        roles=tuple(means),
    )
