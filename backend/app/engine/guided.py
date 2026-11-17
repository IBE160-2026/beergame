"""Guided Weeks (FR-11): every Seat orders the starting demand; no rule is consulted."""

from app.engine.settings import GameSettings


def guided_order(settings: GameSettings) -> int:
    """The Order of every Seat in a Guided Week: the Demand pattern's starting level.

    It can exceed a very low maximum Order; `warnings` reports `max_order_may_bind` then."""
    return settings.demand.starting_level
