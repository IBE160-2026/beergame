"""Predicates on a Game's turns (AD-2, AD-20). Commands ask these and never decide themselves."""

from collections.abc import Mapping, Sequence

from app.engine import GameSettings
from app.modules.games.policy import GamePolicy


def guided_week(game_policy: GamePolicy, settings: GameSettings, week: int) -> bool:
    """Whether `week` is a Guided Week, in which every Seat orders `engine.guided_order`."""
    return game_policy.guided_weeks == "settings" and week <= settings.guided_weeks


def week_complete(turns: Sequence[Mapping[str, object]]) -> bool:
    """The one predicate for an advance: the open Week is complete when every Seat's turn in it
    has an Order (`ordered_at` set). `turns` are the open Week's `seat_turns` rows, one per
    Seat; no turns means there is nothing to complete."""
    return bool(turns) and all(turn["ordered_at"] is not None for turn in turns)
