"""The Matrisevegg's class median and chain cost rows (Story 7.4, FR-39, AD-1, AD-10).

Pure: no I/O, no clock. `wall_aggregates` takes each Game's stored Week states (and, for the
Ordre cells, its placed Orders) and returns per Uke the median of one Role's cell value with the
middle half of the Games, the mean chain cost of that Uke, and how many Games each is taken over.
Each Uke counts the Games that have reached it, so a short game never pulls the later Uker toward
zero. The Lecturer overview serves it per filter combination; the Class report (Epic 13) reuses it.
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from app.engine.state import WeekState

__all__ = ["Cells", "PlayedGame", "WallWeek", "quartiles", "wall_aggregates"]

_CENT = Decimal("0.01")


class Cells(StrEnum):
    """What a wall cell shows for its Role and Uke."""

    NET = "net"
    """Netto lager: inventory minus backlog as stored."""
    ORDER = "order"
    """The Order placed in that Uke; an open Uke without one has no value."""
    COST = "cost"
    """Kost per uke: the Uke's cost on its end-of-Week balances."""


@dataclass(frozen=True)
class PlayedGame:
    """One Game's stored play: its Week states in any order (a finished state is skipped) and
    its placed Orders by (Uke, Role)."""

    states: Sequence[WeekState]
    orders: Mapping[tuple[int, str], int] = field(default_factory=dict)


@dataclass(frozen=True)
class WallWeek:
    """One Uke of the aggregate rows. `games` counts the Games with a cell value that Uke (the
    median's base); `chain_games` those that reached it (the mean's base). The median and the
    quartiles are None when no Game has a value, the mean when none reached the Uke; the mean is
    quantized to øre."""

    week: int
    games: int
    median: Decimal | None
    lower_quartile: Decimal | None
    upper_quartile: Decimal | None
    chain_games: int
    chain_cost_mean: Decimal | None


def quartiles(values: Iterable[Decimal | int]) -> tuple[Decimal, Decimal, Decimal] | None:
    """The lower quartile, median and upper quartile of `values` by linear interpolation between
    the order statistics (the inclusive method: position p·(n − 1)), or None for no value. One
    value is all three."""
    ordered = sorted(Decimal(value) for value in values)
    if not ordered:
        return None

    def at(share: Decimal) -> Decimal:
        position = share * (len(ordered) - 1)
        low = int(position)
        fraction = position - low
        if fraction == 0:
            return ordered[low]
        return ordered[low] + fraction * (ordered[low + 1] - ordered[low])

    return _plain(at(Decimal("0.25"))), _plain(at(Decimal("0.5"))), _plain(at(Decimal("0.75")))


def _plain(value: Decimal) -> Decimal:
    """`value` without trailing zeros and never in exponent form («12.0» → «12», «5.50» → «5.5»)."""
    if value == value.to_integral_value():
        return value.quantize(Decimal(1))
    return value.normalize()


def _value(state: WeekState, role: str, cells: Cells, orders: Mapping[tuple[int, str], int]):
    if cells is Cells.ORDER:
        return orders.get((state.week, role))
    seat = state.seat(role)
    if cells is Cells.NET:
        return seat.inventory - seat.backlog
    return seat.cost


def wall_aggregates(games: Iterable[PlayedGame], role: str, cells: Cells) -> list[WallWeek]:
    """Per Uke from 1 to the furthest any Game has reached: the median and middle half of
    `role`'s `cells` value over the Games that have one that Uke, and the mean of the chain's
    cost (the four Seats' Kost per uke summed) over the Games that reached it. No Game, no Uke."""
    values: dict[int, list[Decimal | int]] = {}
    chain: dict[int, list[Decimal]] = {}
    for game in games:
        for state in game.states:
            if state.finished:
                continue
            chain.setdefault(state.week, []).append(sum((s.cost for s in state.seats), Decimal(0)))
            value = _value(state, role, cells, game.orders)
            if value is not None:
                values.setdefault(state.week, []).append(value)
    weeks: list[WallWeek] = []
    for week in range(1, max(chain, default=0) + 1):
        found = values.get(week, [])
        costs = chain.get(week, [])
        spread = quartiles(found)
        weeks.append(
            WallWeek(
                week=week,
                games=len(found),
                median=spread[1] if spread else None,
                lower_quartile=spread[0] if spread else None,
                upper_quartile=spread[2] if spread else None,
                chain_games=len(costs),
                chain_cost_mean=(
                    (sum(costs, Decimal(0)) / len(costs)).quantize(_CENT, ROUND_HALF_UP)
                    if costs
                    else None
                ),
            )
        )
    return weeks
