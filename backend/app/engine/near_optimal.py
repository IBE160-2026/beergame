"""The near-optimal reference Order: what a Seat would order with knowledge beyond its own view
(FR-79, AD-1).

It receives every Seat of the chain state and the whole demand series, which no player sees.
The placeholder reads the Seat, its supplier and the customer demand of the coming Weeks; it is
not a whole-chain optimiser. The algorithm is a placeholder until issue #20 settles it; it is
described in `near_optimal.md` next to this file. Every stored reference carries the
`ALGORITHM_VERSION` that produced it. A new algorithm is a new entry in `ALGORITHMS` and a new
`ALGORITHM_VERSION`; callers keep calling `order`.
"""

from collections.abc import Callable, Sequence

from app.engine.settings import GameSettings, Role
from app.engine.state import WeekState

Algorithm = Callable[[GameSettings, WeekState, Sequence[int], int, Role], int]


def supply_line(settings: GameSettings, chain_state: WeekState, role: Role) -> int:
    """Units `role` has ordered and not yet received, read from the chain state: its goods in
    transit, plus the Orders its supplier has not received yet and the supplier's backlog (for
    the last Role: its Orders not yet in production). Index 0 of an order queue was received
    when the Week opened, so it is already in the goods or the backlog."""
    index = settings.roles.index(role)
    seat = chain_state.seat(role)
    in_transit = sum(seat.goods_slots)
    if index == len(settings.roles) - 1:
        return in_transit + sum(seat.production_orders[1:])
    upstream = chain_state.seat(settings.roles[index + 1])
    return in_transit + sum(upstream.incoming_orders[1:]) + upstream.backlog


def _demand(demand_series: Sequence[int], week: int) -> int:
    """Customer demand in `week`; a Week after the series takes its last value."""
    return demand_series[min(week, len(demand_series)) - 1]


def _placeholder_0(
    settings: GameSettings,
    chain_state: WeekState,
    demand_series: Sequence[int],
    week: int,
    role: Role,
) -> int:
    """Order-up-to with known customer demand: bring the inventory position up to the opening
    effective inventory plus the demand of the Weeks before this Order can arrive."""
    goods_delay = (
        settings.production_delay if role == settings.roles[-1] else settings.shipping_delay
    )
    arrival = settings.order_delay + goods_delay
    cover = sum(_demand(demand_series, k) for k in range(week + 1, week + arrival + 1))
    target = settings.starting_inventory - settings.starting_backlog
    seat = chain_state.seat(role)
    position = seat.inventory - seat.backlog + supply_line(settings, chain_state, role)
    return target + cover - position


ALGORITHMS: dict[str, Algorithm] = {"placeholder-0": _placeholder_0}
"""Every near-optimal algorithm by its version label."""

ALGORITHM_VERSION = "placeholder-0"
"""The algorithm `order` runs; stored with every reference it produces."""


def order(
    settings: GameSettings,
    chain_state: WeekState,
    demand_series: Sequence[int],
    week: int,
    role: Role | str,
) -> int:
    """The near-optimal reference Order of `role` in the opened Week `week`: a whole number from
    0 to `max_order`. `chain_state` is that Week's state (every Seat) and `demand_series` the
    Game's customer demand of every Week."""
    role = Role(role)
    if role not in settings.roles:
        raise ValueError(f"{role} is not a Role in this Game")
    if chain_state.finished or chain_state.week != week:
        raise ValueError(f"the chain state is not opened Week {week}")
    if len(demand_series) < week:
        raise ValueError(f"the demand series has no Week {week}")
    wanted = ALGORITHMS[ALGORITHM_VERSION](settings, chain_state, demand_series, week, role)
    return min(max(wanted, 0), settings.max_order)
