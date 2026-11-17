"""The Week sequence (FR-26, FR-28): pure functions from one opened Week to the next.

Opening Week t: each Seat receives `goods_slots[0]` into inventory; amount to ship = incoming
order + backlog; shipped = the smaller of inventory and that amount; the rest is backlog. Then
every goods pipeline moves up one slot and takes the upstream Seat's shipment (the last Role
takes the Order entering production). Cost is charged on these balances, which Orders cannot
change. `advance` takes the Orders, charges the Week's cost, moves the order slots and opens
the next Week, or finishes the Game after the last Week.
"""

from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import NamedTuple

from app.engine.settings import GameSettings, Role
from app.engine.state import SeatState, WeekState


class GameFinishedError(ValueError):
    """`advance` was called on a finished Game."""


class InvalidOrdersError(ValueError):
    """The Orders for a Week are incomplete or out of bounds; `role` names the culprit."""

    def __init__(self, role: str, reason: str) -> None:
        self.role = role
        super().__init__(f"{role}: {reason}")


class _Carry(NamedTuple):
    """What one Seat brings into a Week before it opens."""

    role: Role
    inventory: int
    backlog: int
    total_cost: Decimal
    incoming_orders: tuple[int, ...]
    goods_slots: tuple[int, ...]
    production_orders: tuple[int, ...]


def initial_state(settings: GameSettings) -> WeekState:
    """Open Week 1 from starting inventory, no backlog and `supply_line` in every slot."""
    last = len(settings.roles) - 1
    fill = settings.supply_line
    carries = [
        _Carry(
            role=role,
            inventory=settings.starting_inventory,
            backlog=0,
            total_cost=Decimal(0),
            incoming_orders=(fill,) * settings.order_delay if i > 0 else (),
            goods_slots=(fill,)
            * (settings.production_delay if i == last else settings.shipping_delay),
            production_orders=(fill,) * settings.order_delay if i == last else (),
        )
        for i, role in enumerate(settings.roles)
    ]
    return _open_week(settings, 1, carries)


def advance(settings: GameSettings, state: WeekState, orders: Mapping[str, object]) -> WeekState:
    """Place every Seat's Order for `state.week` and return the next opened Week.

    After the last Week the same Week comes back with `finished=True` and the costs charged.
    """
    if state.finished:
        raise GameFinishedError(f"the Game finished in Week {state.week}")
    placed = _check_orders(settings, orders)
    last = len(state.seats) - 1
    carries: list[_Carry] = []
    for i, seat in enumerate(state.seats):
        incoming_orders = (
            seat.incoming_orders[1:] + (placed[state.seats[i - 1].role],) if i > 0 else ()
        )
        production_orders = seat.production_orders[1:] + (placed[seat.role],) if i == last else ()
        carries.append(
            _Carry(
                role=seat.role,
                inventory=seat.inventory,
                backlog=seat.backlog,
                total_cost=seat.total_cost + seat.cost,
                incoming_orders=incoming_orders,
                goods_slots=seat.goods_slots,
                production_orders=production_orders,
            )
        )
    if state.week == settings.weeks:
        seats = tuple(
            seat.model_copy(
                update={
                    "total_cost": carry.total_cost,
                    "incoming_orders": carry.incoming_orders,
                    "production_orders": carry.production_orders,
                }
            )
            for seat, carry in zip(state.seats, carries, strict=True)
        )
        return WeekState(week=state.week, finished=True, seats=seats)
    return _open_week(settings, state.week + 1, carries)


def _check_orders(settings: GameSettings, orders: Mapping[str, object]) -> dict[Role, int]:
    names = {role.value for role in settings.roles}
    for key in orders:
        if str(key) not in names:
            raise InvalidOrdersError(str(key), "not a Role in this Game")
    given = {str(key): value for key, value in orders.items()}
    placed: dict[Role, int] = {}
    for role in settings.roles:
        if role.value not in given:
            raise InvalidOrdersError(role.value, "no Order given")
        value = given[role.value]
        if type(value) is not int:
            raise InvalidOrdersError(
                role.value, f"an Order is a whole number, not {type(value).__name__}"
            )
        if value < 0:
            raise InvalidOrdersError(role.value, f"an Order cannot be negative ({value})")
        if value > settings.max_order:
            raise InvalidOrdersError(
                role.value, f"an Order cannot exceed {settings.max_order} ({value})"
            )
        placed[role] = value
    return placed


def _open_week(settings: GameSettings, week: int, carries: Sequence[_Carry]) -> WeekState:
    last = len(carries) - 1
    received: list[tuple[int, int, int, int, int]] = []
    for i, carry in enumerate(carries):
        incoming_order = settings.demand.demand_for(week) if i == 0 else carry.incoming_orders[0]
        delivery = carry.goods_slots[0]
        on_hand = carry.inventory + delivery
        amount = incoming_order + carry.backlog
        shipped = min(on_hand, amount)
        received.append((incoming_order, delivery, shipped, on_hand - shipped, amount - shipped))

    seats: list[SeatState] = []
    for i, carry in enumerate(carries):
        incoming_order, delivery, shipped, inventory, backlog = received[i]
        arriving = carry.production_orders[0] if i == last else received[i + 1][2]
        seats.append(
            SeatState(
                role=carry.role,
                incoming_order=incoming_order,
                incoming_delivery=delivery,
                shipped=shipped,
                inventory=inventory,
                backlog=backlog,
                cost=settings.holding_cost * inventory + settings.backorder_cost * backlog,
                total_cost=carry.total_cost,
                incoming_orders=carry.incoming_orders,
                goods_slots=carry.goods_slots[1:] + (arriving,),
                production_orders=carry.production_orders,
            )
        )
    return WeekState(week=week, finished=False, seats=tuple(seats))
