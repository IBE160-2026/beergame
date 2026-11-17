"""The bookkeeping check (FR-29, FR-28): pure, and never raises on bad data.

`conservation(settings, states, orders)` takes Week states as the engine produces them:
`states[0]` is Week 1 as `initial_state` opens it, `states[s] = advance(settings, states[s-1],
orders[s-1])`, so there is one Order mapping fewer than states. The list may stop at any opened
Week or end with the finished state. The result is every broken rule, empty when the books are
right.

Expected values are recomputed from the settings, the previous state and the Orders, never by
calling the engine, so an engine slip cannot hide itself. With `d` the order delay and `fill`
the supply line, a Role's Order history is `H = (fill,) * d + (its Orders...)`; after `s` Orders
its order slots hold `H[s : s + d]`, and the last Role's Order entering production in Week `t`
is `H[t - 1]`.

Rules (stable codes; `role` is None for the chain-level ones):

- `units_conserved`: units on hand and in transit (inventory plus goods slots of every Seat)
  equal the starting units plus units entered production minus units delivered to customers.
  Order slots hold Orders, not units. The finished state moves nothing, so units still in slots
  are counted and nothing is added.
- `in_transit`: the delivery is the previous first goods slot; the goods slots move up one and
  take the upstream Seat's shipment, or the Order entering production for the last Role.
- `shipment`: a Seat ships the smallest of what it has on hand (previous inventory plus
  delivery), what it owes (previous backlog plus incoming order) and its capacity, if the
  settings cap it. With valid starting values this keeps inventory, backlog and every slot at 0
  or above.
- `inventory_balance`, `backlog_balance`: inventory = previous + delivery - shipped; backlog =
  previous + incoming order - shipped.
- `incoming_order`: customer demand for the first Role, else the first incoming order slot.
- `order_slots`: the order slots match the Order history.
- `cost`: holding rate times inventory plus backorder rate times backlog.
- `total_cost`: a Seat's total is the sum of its costs of the opened Weeks before this state,
  so the finished total is the sum of every Week's cost and slots never cost.
- `chain_total_cost`: on the last state, the Seats' totals add up to the sum of those costs.
- `inventory_and_backlog`: never both positive on an uncapped Seat; a capped Seat may hold both,
  since units it cannot ship stay as backlog (FR-29).

The finished state repeats the last Week with the same Week number: its incoming order,
delivery, goods slots, shipped, inventory and backlog must equal Week N's, reported under
`incoming_order`, `in_transit` (delivery, goods slots), `inventory_balance` (shipped, inventory)
and `backlog_balance`; its order slots, cost and totals follow the rules above.

Shape rules, reported alone because the rules above cannot read malformed data:
`states_shape`, `week_sequence`, `seat_shape`, `orders_shape`, `demand_series`.
"""

from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import cast

from pydantic import BaseModel

from app.engine.settings import FROZEN, GameSettings, Role, demand_series
from app.engine.state import SeatState, WeekState

_UNITS = ("incoming_order", "incoming_delivery", "shipped", "inventory", "backlog")
_MONEY = ("cost", "total_cost")


class Violation(BaseModel):
    """One broken rule, in one Week (None: the whole list) and one Role (None: the chain)."""

    model_config = FROZEN

    rule: str
    week: int | None
    role: Role | None
    expected: str | None = None
    actual: str | None = None
    message: str


def conservation(
    settings: GameSettings,
    states: Sequence[WeekState],
    orders: Sequence[Mapping[str, object]],
) -> tuple[Violation, ...]:
    """Every bookkeeping rule the states break, in state order; `()` when the books are right."""
    shape = _shape(settings, states, orders)
    if shape:
        return tuple(shape)
    return tuple(_books(settings, states, orders))


def starting_units(settings: GameSettings) -> int:
    """Units on hand and in transit before Week 1 opens: 80 under the Classic settings."""
    n = len(settings.roles)
    return n * settings.starting_inventory + settings.supply_line * (
        (n - 1) * settings.shipping_delay + settings.production_delay
    )


def _slot_lengths(settings: GameSettings, i: int) -> dict[str, int]:
    last = len(settings.roles) - 1
    d = settings.order_delay
    return {
        "incoming_orders": d if i > 0 else 0,
        "goods_slots": settings.production_delay if i == last else settings.shipping_delay,
        "production_orders": d if i == last else 0,
    }


def _shape(
    settings: GameSettings,
    states: Sequence[WeekState],
    orders: Sequence[Mapping[str, object]],
) -> list[Violation]:
    found: list[Violation] = []
    if not states:
        return [Violation(rule="states_shape", week=None, role=None, message="no Week state")]
    for s, state in enumerate(states):
        if not isinstance(state, WeekState):
            found.append(
                Violation(
                    rule="states_shape",
                    week=None,
                    role=None,
                    message=f"item {s} is a {type(state).__name__}, not a Week state",
                )
            )
            continue
        found.extend(_week_shape(settings, states, s, state))
    found.extend(_orders_shape(settings, states, orders))
    try:
        demand_series(settings)
    except ValueError as error:
        found.append(
            Violation(
                rule="demand_series",
                week=None,
                role=None,
                message=f"the demand series cannot be built: {error}",
            )
        )
    return found


def _week_shape(
    settings: GameSettings, states: Sequence[WeekState], s: int, state: WeekState
) -> list[Violation]:
    found: list[Violation] = []
    week = getattr(state, "week", None)
    finished = getattr(state, "finished", None)
    label = week if type(week) is int else None
    if type(week) is not int or type(finished) is not bool:
        problem = "its Week is not a whole number or its finished flag is not a bool"
    elif finished and (s != len(states) - 1 or s != settings.weeks or week != settings.weeks):
        problem = f"a finished state must be the last, after Week {settings.weeks}, with its Week"
    elif not finished and (week != s + 1 or week > settings.weeks):
        problem = f"item {s} should open Week {s + 1} of {settings.weeks}, not Week {week}"
    else:
        problem = None
    if problem is not None:
        found.append(
            Violation(rule="week_sequence", week=label, role=None, message=f"item {s}: {problem}")
        )

    seats = getattr(state, "seats", None)
    roles = settings.roles
    if not isinstance(seats, tuple) or len(seats) != len(roles):
        found.append(
            Violation(
                rule="seat_shape",
                week=label,
                role=None,
                message=f"item {s} needs one Seat per Role ({len(roles)})",
            )
        )
        return found
    for i, (role, seat) in enumerate(zip(roles, seats, strict=True)):
        if not isinstance(seat, SeatState) or getattr(seat, "role", None) != role:
            bad = [f"Seat {i} is not the {role} Seat"]
        else:
            bad = _seat_fields(settings, i, seat)
        found.extend(
            Violation(rule="seat_shape", week=label, role=role, message=f"item {s}: {issue}")
            for issue in bad
        )
    return found


def _seat_fields(settings: GameSettings, i: int, seat: SeatState) -> list[str]:
    bad: list[str] = []
    for name in _UNITS:
        if type(getattr(seat, name, None)) is not int:
            bad.append(f"{name} is not a whole number")
    for name in _MONEY:
        value = getattr(seat, name, None)
        if not isinstance(value, Decimal) or not value.is_finite():
            bad.append(f"{name} is not a finite decimal")
    for name, length in _slot_lengths(settings, i).items():
        value = getattr(seat, name, None)
        if (
            not isinstance(value, tuple)
            or len(value) != length
            or any(type(item) is not int for item in value)
        ):
            bad.append(f"{name} is not {length} whole numbers")
    return bad


def _orders_shape(
    settings: GameSettings,
    states: Sequence[WeekState],
    orders: Sequence[Mapping[str, object]],
) -> list[Violation]:
    found: list[Violation] = []
    if len(orders) != len(states) - 1:
        found.append(
            Violation(
                rule="orders_shape",
                week=None,
                role=None,
                expected=str(len(states) - 1),
                actual=str(len(orders)),
                message=f"{len(states)} states need {len(states) - 1} Weeks of Orders",
            )
        )
    names = {role.value for role in settings.roles}
    for k, placed in enumerate(orders):
        week = k + 1
        if not isinstance(placed, Mapping):
            found.append(
                Violation(
                    rule="orders_shape", week=week, role=None, message="the Orders are not a map"
                )
            )
            continue
        given = {str(key): value for key, value in placed.items()}
        for key in sorted(given.keys() - names):
            found.append(
                Violation(
                    rule="orders_shape",
                    week=week,
                    role=None,
                    message=f"{key} is not a Role in this Game",
                )
            )
        for role in settings.roles:
            value = given.get(role.value)
            if type(value) is not int or not 0 <= value <= settings.max_order:
                found.append(
                    Violation(
                        rule="orders_shape",
                        week=week,
                        role=role,
                        actual=repr(value),
                        message=f"the Order must be a whole number from 0 to {settings.max_order}",
                    )
                )
    return found


class _Books:
    """Collects violations; `expect` records one when the stated value differs."""

    def __init__(self) -> None:
        self.found: list[Violation] = []

    def expect(
        self,
        rule: str,
        week: int,
        role: Role | None,
        what: str,
        expected: object,
        actual: object,
    ) -> None:
        if expected != actual:
            self.found.append(
                Violation(
                    rule=rule,
                    week=week,
                    role=role,
                    expected=str(expected),
                    actual=str(actual),
                    message=f"{what}: expected {expected}, found {actual}",
                )
            )


def _books(
    settings: GameSettings,
    states: Sequence[WeekState],
    orders: Sequence[Mapping[str, object]],
) -> list[Violation]:
    roles = settings.roles
    n = len(roles)
    last = n - 1
    d = settings.order_delay
    fill = settings.supply_line
    demand = demand_series(settings)
    history = {
        role: (fill,) * d + tuple(_order(placed, role) for placed in orders) for role in roles
    }
    start_units = starting_units(settings)
    books = _Books()
    entered = 0
    delivered = 0
    cost_sums = [Decimal(0)] * n

    for s, state in enumerate(states):
        week = state.week
        if state.finished:
            _finished_week(books, states[s - 1], state)
        else:
            entering = history[roles[last]][week - 1]
            entered += entering
            delivered += state.seats[0].shipped
            _opened_week(books, settings, states, s, entering, demand[week - 1])
        for i, seat in enumerate(state.seats):
            role = seat.role
            if i > 0:
                books.expect(
                    "order_slots",
                    week,
                    role,
                    "incoming order slots",
                    history[roles[i - 1]][s : s + d],
                    seat.incoming_orders,
                )
            if i == last:
                books.expect(
                    "order_slots",
                    week,
                    role,
                    "production order slots",
                    history[role][s : s + d],
                    seat.production_orders,
                )
            books.expect(
                "cost",
                week,
                role,
                "cost on the end-of-Week balances",
                settings.holding_cost * seat.inventory + settings.backorder_cost * seat.backlog,
                seat.cost,
            )
            books.expect(
                "total_cost", week, role, "sum of earlier Week costs", cost_sums[i], seat.total_cost
            )
            if seat.inventory > 0 and seat.backlog > 0 and settings.capacity_of(role) is None:
                books.found.append(
                    Violation(
                        rule="inventory_and_backlog",
                        week=week,
                        role=role,
                        actual=f"inventory {seat.inventory}, backlog {seat.backlog}",
                        message="an uncapped Seat holds inventory and backlog at once",
                    )
                )
        books.expect(
            "units_conserved",
            week,
            None,
            "units on hand and in transit",
            start_units + entered - delivered,
            sum(seat.inventory + sum(seat.goods_slots) for seat in state.seats),
        )
        if s == len(states) - 1:
            books.expect(
                "chain_total_cost",
                week,
                None,
                "chain total cost",
                sum(cost_sums, Decimal(0)),
                sum((seat.total_cost for seat in state.seats), Decimal(0)),
            )
        else:
            for i, seat in enumerate(state.seats):
                cost_sums[i] += seat.cost
    return books.found


def _order(placed: Mapping[str, object], role: Role) -> int:
    """The Role's Order; the shape pass has made sure it is a whole number."""
    return cast(int, {str(key): value for key, value in placed.items()}[role.value])


def _opened_week(
    books: _Books,
    settings: GameSettings,
    states: Sequence[WeekState],
    s: int,
    entering: int,
    demand: int,
) -> None:
    state = states[s]
    week = state.week
    last = len(state.seats) - 1
    for i, seat in enumerate(state.seats):
        role = seat.role
        if s == 0:
            inventory = settings.starting_inventory
            backlog = settings.starting_backlog
            goods = (settings.supply_line,) * len(seat.goods_slots)
        else:
            before = states[s - 1].seats[i]
            inventory, backlog, goods = before.inventory, before.backlog, before.goods_slots
        books.expect(
            "incoming_order",
            week,
            role,
            "incoming order",
            demand if i == 0 else seat.incoming_orders[0],
            seat.incoming_order,
        )
        books.expect("in_transit", week, role, "delivery", goods[0], seat.incoming_delivery)
        can_ship = min(inventory + seat.incoming_delivery, backlog + seat.incoming_order)
        capacity = settings.capacity_of(role)
        if capacity is not None:
            can_ship = min(can_ship, capacity)
        books.expect(
            "shipment",
            week,
            role,
            "shipped (the smallest of on hand, owed and capacity)",
            can_ship,
            seat.shipped,
        )
        arriving = entering if i == last else state.seats[i + 1].shipped
        books.expect(
            "in_transit", week, role, "goods slots", goods[1:] + (arriving,), seat.goods_slots
        )
        books.expect(
            "inventory_balance",
            week,
            role,
            "inventory",
            inventory + seat.incoming_delivery - seat.shipped,
            seat.inventory,
        )
        books.expect(
            "backlog_balance",
            week,
            role,
            "backlog",
            backlog + seat.incoming_order - seat.shipped,
            seat.backlog,
        )


_FINISHED_RULES = (
    ("incoming_order", "incoming_order"),
    ("incoming_delivery", "in_transit"),
    ("goods_slots", "in_transit"),
    ("shipped", "inventory_balance"),
    ("inventory", "inventory_balance"),
    ("backlog", "backlog_balance"),
)


def _finished_week(books: _Books, before: WeekState, state: WeekState) -> None:
    """The finished state repeats the last Week: nothing moves, nothing is shipped again."""
    for seat, last_week in zip(state.seats, before.seats, strict=True):
        for name, rule in _FINISHED_RULES:
            books.expect(
                rule,
                state.week,
                seat.role,
                f"{name} after the last Week",
                getattr(last_week, name),
                getattr(seat, name),
            )
