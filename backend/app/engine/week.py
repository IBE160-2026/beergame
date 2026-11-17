"""The Week sequence, at a chosen rules version (AD-4).

`initial_state` and `advance` run the rules package of `rules_version` (default: the version
new Games are created under). The arithmetic itself lives in `app.engine.rules.v<N>`.
"""

from collections.abc import Mapping

from app.engine import rules
from app.engine.errors import GameFinishedError, InvalidOrdersError
from app.engine.settings import GameSettings
from app.engine.state import WeekState

__all__ = ["GameFinishedError", "InvalidOrdersError", "advance", "initial_state"]


def initial_state(settings: GameSettings, rules_version: int = rules.RULES_VERSION) -> WeekState:
    """Open Week 1 under `rules_version`."""
    state: WeekState = rules.package(rules_version).initial_state(settings)
    return state


def advance(
    settings: GameSettings,
    state: WeekState,
    orders: Mapping[str, object],
    rules_version: int = rules.RULES_VERSION,
) -> WeekState:
    """Place every Seat's Order for `state.week` under `rules_version` and return the next
    opened Week, or the finished state after the last Week."""
    following: WeekState = rules.package(rules_version).advance(settings, state, orders)
    return following
