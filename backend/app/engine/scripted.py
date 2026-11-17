"""Scripted occupants: fixed, no-learning Order policies for simulation Games (AD-22).

`REGISTRY` is closed: a policy is added here, by id, and nowhere else. Each policy is pure and
takes only an `engine.SeatView`, so it sees exactly what any other player in the Seat sees.
"""

from collections.abc import Callable, Mapping
from types import MappingProxyType

from app.engine.view import SeatView

type ScriptedPolicy = Callable[[SeatView], int]
"""The Order for the Seat's open Week, from the Seat's own view only."""


def _constant(order: int) -> ScriptedPolicy:
    def policy(view: SeatView) -> int:
        return order

    return policy


REGISTRY: Mapping[str, ScriptedPolicy] = MappingProxyType({"constant-4": _constant(4)})
"""Every scripted policy by id. `constant-4` orders 4 every Week, whatever it sees."""
