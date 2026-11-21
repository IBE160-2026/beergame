"""What one Seat can see, as numbers only (FR-23, FR-33, AD-3).

`SeatView` is the one type every engine function that looks at a single Seat takes. It holds no
names, not the number of Weeks, no future demand and no other Seat's state beyond the
`neighbour_numbers` that Information visibility allows.
"""

from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

from app.engine.settings import FROZEN, GameSettings, Role
from app.engine.state import SeatState as EngineSeat
from app.engine.state import WeekState

Count = Annotated[int, Field(strict=True, ge=0)]
WeekNumber = Annotated[int, Field(strict=True, ge=1)]


class NeighbourNumber(BaseModel):
    """One number about a neighbouring Seat, labelled with its Role and the Week it refers to."""

    model_config = FROZEN

    role: Role
    week: WeekNumber
    quantity: Literal["inventory", "backlog"]
    value: Count


class SeatView(BaseModel):
    """One Seat in its open Week, seen from inside the Seat."""

    model_config = FROZEN

    role: Role
    inventory: Count
    backlog: Count
    incoming_orders: Annotated[tuple[Count, ...], Field(min_length=1)]
    """The Seat's incoming order of every opened Week, oldest first; the last is this Week's.
    Customer demand for the first Role."""
    supply_line: Count
    """Units the Seat has ordered and not yet received (ordered minus received)."""
    order_history: tuple[Count, ...]
    """The Seat's own Orders of the earlier Weeks, oldest first."""
    neighbour_numbers: tuple[NeighbourNumber, ...] = ()

    @model_validator(mode="after")
    def _one_order_per_earlier_week(self) -> SeatView:
        if len(self.order_history) != len(self.incoming_orders) - 1:
            raise ValueError(
                f"order_history needs one Order per earlier Week "
                f"({len(self.incoming_orders) - 1}), not {len(self.order_history)}"
            )
        return self


def starting_supply_line(settings: GameSettings, role: Role) -> int:
    """Units the Seat has ordered and not received before Week 1 opens: every order slot and
    every goods slot of its pipeline holds `supply_line`, and the upstream Seat's starting
    backlog is owed to it (the last Role's upstream is production, which owes nothing)."""
    if role == settings.roles[-1]:
        return settings.supply_line * (settings.order_delay + settings.production_delay)
    return (
        settings.supply_line * (settings.order_delay + settings.shipping_delay)
        + settings.starting_backlog
    )


def _check_opened(states: Sequence[WeekState]) -> None:
    if not states:
        raise ValueError("a Seat view needs at least one opened Week")
    for index, state in enumerate(states):
        if state.finished or state.week != index + 1:
            raise ValueError(f"item {index} is not opened Week {index + 1}")


def _checked(
    settings: GameSettings,
    states: Sequence[WeekState],
    orders: Sequence[Mapping[str, int]],
    role: Role | str,
) -> tuple[Role, list[EngineSeat], tuple[int, ...]]:
    """The Role, its Seat in every opened Week and its own Orders of the earlier Weeks."""
    role = Role(role)
    if role not in settings.roles:
        raise ValueError(f"{role} is not a Role in this Game")
    _check_opened(states)
    if len(orders) != len(states) - 1:
        raise ValueError(
            f"one Order map per earlier Week is needed ({len(states) - 1}), not {len(orders)}"
        )
    seats = [state.seat(role) for state in states]
    return role, seats, tuple(week_orders[role] for week_orders in orders)


def seat_view(
    settings: GameSettings,
    states: Sequence[WeekState],
    orders: Sequence[Mapping[str, int]],
    role: Role | str,
) -> SeatView:
    """The view of `role` in the last opened Week of `states`.

    `states` are the opened Weeks 1..t (as `initial_state` and `advance` return them) and
    `orders` the Order maps of Weeks 1..t-1. Neighbour numbers stay empty here: the Rule-based
    player reads this view and never uses them; `neighbour_numbers` gives them to the caller
    that may show them (Story 6.21).
    """
    role, seats, history = _checked(settings, states, orders, role)
    received = sum(seat.incoming_delivery for seat in seats)
    now = seats[-1]
    return SeatView(
        role=role,
        inventory=now.inventory,
        backlog=now.backlog,
        incoming_orders=tuple(seat.incoming_order for seat in seats),
        supply_line=starting_supply_line(settings, role) + sum(history) - received,
        order_history=history,
    )


def neighbour_numbers(
    settings: GameSettings, state: WeekState, role: Role | str
) -> tuple[NeighbourNumber, ...]:
    """The numbers of `role`'s neighbours that Information visibility shows in the opened Week
    `state` (FR-83, Story 6.21): for each view that is on, the neighbour Seat's inventory, then
    its backlog, as they stand in that Week. The upstream neighbour (the Role it orders from)
    comes first, then the downstream one (the Role that orders from it). The last Role has no
    upstream neighbour and the first none downstream, so their view on that side gives nothing.
    Nothing else of any Seat is read."""
    role = Role(role)
    if role not in settings.roles:
        raise ValueError(f"{role} is not a Role in this Game")
    if state.finished:
        raise ValueError(f"Week {state.week} is not an opened Week")
    roles, views = settings.roles, settings.info_visibility
    index = roles.index(role)
    shown: list[Role] = []
    if views.upstream and index < len(roles) - 1:
        shown.append(roles[index + 1])
    if views.downstream and index > 0:
        shown.append(roles[index - 1])
    numbers: list[NeighbourNumber] = []
    for neighbour in shown:
        seat = state.seat(neighbour)
        numbers.append(
            NeighbourNumber(
                role=neighbour, week=state.week, quantity="inventory", value=seat.inventory
            )
        )
        numbers.append(
            NeighbourNumber(role=neighbour, week=state.week, quantity="backlog", value=seat.backlog)
        )
    return tuple(numbers)


Money = Annotated[Decimal, Field(allow_inf_nan=False)]


class SupplyLineSlot(BaseModel):
    """Units the Seat has ordered and not received, with the Week they can reach inventory.

    `ordered`: an Order the upstream Seat (or production, for the last Role) has not received
    yet; its arrival Week assumes the upstream Seat ships it in full. `in_transit` (shipping)
    and `in_production` (last Role) are goods on their way."""

    model_config = FROZEN

    stage: Literal["ordered", "in_transit", "in_production"]
    quantity: Count
    arrival_week: WeekNumber


class CostLine(BaseModel):
    """One part of this Week's cost: units on the end-of-Week balance times the rate."""

    model_config = FROZEN

    kind: Literal["holding", "backorder"]
    units: Count
    rate: Money
    amount: Money


class WeekValues(BaseModel):
    """One earlier Week of the Seat, as it stood when its Order was placed."""

    model_config = FROZEN

    week: WeekNumber
    incoming_order: Count
    incoming_delivery: Count
    shipped: Count
    inventory: Count
    backlog: Count
    net_inventory: int
    """Netto lager: inventory minus backlog (FR-23)."""
    supply_line: Count
    position: int
    cost: Money
    holding_cost: Money
    """The part of `cost` charged on inventory: the holding rate times `inventory`."""
    backorder_cost: Money
    """The part of `cost` charged on backlog: the backorder rate times `backlog`."""
    total_cost: Money
    """The Seat's running Total cost through this Week (Story 6.16): every `cost` up to it."""
    total_holding_cost: Money
    """The running sum of `holding_cost` through this Week."""
    total_backorder_cost: Money
    """The running sum of `backorder_cost` through this Week."""
    order: Count


class OrderPreview(BaseModel):
    """Coefficients for the live Order preview (AD-10): with a typed Order x, the supply line
    becomes `supply_line_base + x` and the position `position_base + x`; the Order reaches
    inventory in `order_arrival_week` if the upstream Seat ships it in full."""

    model_config = FROZEN

    order_arrival_week: WeekNumber
    supply_line_base: Count
    position_base: int


class SeatDetail(BaseModel):
    """The numbers of one Seat in its open Week beyond `SeatView`, from its own data only."""

    model_config = FROZEN

    week: WeekNumber
    incoming_order: Count
    incoming_delivery: Count
    shipped: Count
    supply_line_slots: tuple[SupplyLineSlot, ...]
    overdue: Count
    """Units ordered that the upstream Seat received but has not shipped (its backlog)."""
    net_inventory: int
    """Netto lager: inventory minus backlog (FR-23)."""
    position: int
    """Inventory minus backlog plus the supply line (Posisjon, FR-23)."""
    cost_lines: tuple[CostLine, ...]
    week_cost: Money
    total_cost: Money
    """Cost of the earlier Weeks plus this Week's, which Orders cannot change."""
    total_holding_cost: Money
    """The part of `total_cost` charged on inventory, this Week's included (Story 6.16)."""
    total_backorder_cost: Money
    """The part of `total_cost` charged on backlog, this Week's included."""
    history: tuple[WeekValues, ...]
    min_order: Count
    max_order: Count
    preview: OrderPreview


def _goods_delay(settings: GameSettings, role: Role) -> int:
    if role == settings.roles[-1]:
        return settings.production_delay
    return settings.shipping_delay


def seat_detail(
    settings: GameSettings,
    states: Sequence[WeekState],
    orders: Sequence[Mapping[str, int]],
    role: Role | str,
) -> SeatDetail:
    """The numbers of `role` in the last opened Week of `states` that `SeatView` leaves out.

    Takes the same arguments as `seat_view` and reads only that Role's Seat."""
    role, seats, history = _checked(settings, states, orders, role)
    week = len(states)
    goods_delay = _goods_delay(settings, role)
    start = starting_supply_line(settings, role)
    received = 0
    held = owed = Decimal(0)
    rows: list[WeekValues] = []
    for number, seat in enumerate(seats, start=1):
        received += seat.incoming_delivery
        supply_line = start + sum(history[: number - 1]) - received
        position = seat.inventory - seat.backlog + supply_line
        held += settings.holding_cost * seat.inventory
        owed += settings.backorder_cost * seat.backlog
        if number < week:
            rows.append(
                WeekValues(
                    week=number,
                    incoming_order=seat.incoming_order,
                    incoming_delivery=seat.incoming_delivery,
                    shipped=seat.shipped,
                    inventory=seat.inventory,
                    backlog=seat.backlog,
                    net_inventory=seat.inventory - seat.backlog,
                    supply_line=supply_line,
                    position=position,
                    cost=seat.cost,
                    holding_cost=settings.holding_cost * seat.inventory,
                    backorder_cost=settings.backorder_cost * seat.backlog,
                    total_cost=seat.total_cost + seat.cost,
                    total_holding_cost=held,
                    total_backorder_cost=owed,
                    order=history[number - 1],
                )
            )
    now = seats[-1]
    ordered = [
        SupplyLineSlot(
            stage="ordered",
            quantity=history[placed - 1] if placed >= 1 else settings.supply_line,
            arrival_week=placed + settings.order_delay + goods_delay,
        )
        for placed in range(week - settings.order_delay + 1, week)
    ]
    goods_stage = "in_production" if role == settings.roles[-1] else "in_transit"
    goods = [
        SupplyLineSlot(stage=goods_stage, quantity=quantity, arrival_week=week + 1 + index)
        for index, quantity in enumerate(now.goods_slots)
    ]
    slots = tuple(goods + ordered)  # arrives soonest first
    return SeatDetail(
        week=week,
        incoming_order=now.incoming_order,
        incoming_delivery=now.incoming_delivery,
        shipped=now.shipped,
        supply_line_slots=slots,
        overdue=supply_line - sum(slot.quantity for slot in slots),
        net_inventory=now.inventory - now.backlog,
        position=position,
        cost_lines=(
            CostLine(
                kind="holding",
                units=now.inventory,
                rate=settings.holding_cost,
                amount=settings.holding_cost * now.inventory,
            ),
            CostLine(
                kind="backorder",
                units=now.backlog,
                rate=settings.backorder_cost,
                amount=settings.backorder_cost * now.backlog,
            ),
        ),
        week_cost=now.cost,
        total_cost=now.total_cost + now.cost,
        total_holding_cost=held,
        total_backorder_cost=owed,
        history=tuple(rows),
        min_order=0,
        max_order=settings.max_order,
        preview=OrderPreview(
            order_arrival_week=week + settings.order_delay + goods_delay,
            supply_line_base=supply_line,
            position_base=position,
        ),
    )


def placed_orders(
    settings: GameSettings, states: Sequence[WeekState]
) -> tuple[dict[Role, int], ...]:
    """The Order maps of Weeks 1..t-1, read back from the opened Weeks 1..t.

    An Order placed in Week w is the newest entry of the upstream Seat's order slots (the last
    Role's production slots) when Week w+1 opens."""
    _check_opened(states)
    last = len(settings.roles) - 1
    maps: list[dict[Role, int]] = []
    for state in states[1:]:
        placed: dict[Role, int] = {}
        for index, role in enumerate(settings.roles):
            if index == last:
                placed[role] = state.seat(role).production_orders[-1]
            else:
                placed[role] = state.seat(settings.roles[index + 1]).incoming_orders[-1]
        maps.append(placed)
    return tuple(maps)
