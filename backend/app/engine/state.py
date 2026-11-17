"""The state the engine hands back: one opened Week, before any Order is placed.

Pipelines list "arrives soonest" first.
"""

from decimal import Decimal

from pydantic import BaseModel

from app.engine.settings import FROZEN, Role


class SeatState(BaseModel):
    """One Seat in an opened Week. The Week's fields are already settled; Orders cannot change
    them."""

    model_config = FROZEN

    role: Role
    incoming_order: int
    """Order received this Week: customer demand for the first Role, else `incoming_orders[0]`."""
    incoming_delivery: int
    """Units received into inventory when the Week opened."""
    shipped: int
    """Units sent downstream (to the customer for the first Role) this Week."""
    inventory: int
    backlog: int
    cost: Decimal
    """This Week's cost on the end-of-Week balances; charged to `total_cost` by `advance`."""
    total_cost: Decimal
    """Sum of the costs of the Weeks already advanced."""
    incoming_orders: tuple[int, ...]
    """Orders from downstream under the order delay; index 0 is the one received this Week.
    Empty for the first Role, whose incoming order is customer demand."""
    goods_slots: tuple[int, ...]
    """Units in transit to this Seat: shipping, or production for the last Role."""
    production_orders: tuple[int, ...]
    """Last Role only (else empty): its own Orders under the order delay; index 0 entered
    production when this Week opened. Orders, not units."""


class WeekState(BaseModel):
    model_config = FROZEN

    week: int
    finished: bool
    seats: tuple[SeatState, ...]

    def seat(self, role: Role | str) -> SeatState:
        for seat in self.seats:
            if seat.role == role:
                return seat
        raise KeyError(role)
