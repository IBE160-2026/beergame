"""What one Seat can see, as numbers only (FR-23, FR-33, AD-3).

`SeatView` is the one type every engine function that looks at a single Seat takes. It holds no
names, not the number of Weeks, no future demand and no other Seat's state beyond the
`neighbour_numbers` that Information visibility allows.
"""

from collections.abc import Mapping, Sequence
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

from app.engine.settings import FROZEN, GameSettings, Role
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


def seat_view(
    settings: GameSettings,
    states: Sequence[WeekState],
    orders: Sequence[Mapping[str, int]],
    role: Role | str,
) -> SeatView:
    """The view of `role` in the last opened Week of `states`.

    `states` are the opened Weeks 1..t (as `initial_state` and `advance` return them) and
    `orders` the Order maps of Weeks 1..t-1. Neighbour numbers stay empty: no Information
    visibility setting exists yet.
    """
    role = Role(role)
    if role not in settings.roles:
        raise ValueError(f"{role} is not a Role in this Game")
    if not states:
        raise ValueError("a Seat view needs at least one opened Week")
    if len(orders) != len(states) - 1:
        raise ValueError(
            f"one Order map per earlier Week is needed ({len(states) - 1}), not {len(orders)}"
        )
    for index, state in enumerate(states):
        if state.finished or state.week != index + 1:
            raise ValueError(f"item {index} is not opened Week {index + 1}")
    seats = [state.seat(role) for state in states]
    history = tuple(week_orders[role] for week_orders in orders)
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
