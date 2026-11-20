"""Predicates on a Game's turns (AD-2, AD-20). Commands ask these and never decide themselves."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.engine import GameSettings
from app.modules.games.policy import GamePolicy
from app.modules.games.schemas import OccupantKind


def guided_week(game_policy: GamePolicy, settings: GameSettings, week: int) -> bool:
    """Whether `week` is a Guided Week, in which every Seat orders `engine.guided_order`."""
    return game_policy.guided_weeks == "settings" and week <= settings.guided_weeks


def week_complete(turns: Sequence[Mapping[str, object]], *, guided: bool) -> bool:
    """The one predicate for an advance: the open Week is complete when every Seat's turn in it
    has an Order (`ordered_at` set) and, in a Guided Week, every turn of a Seat a Student holds
    in that Week has been viewed (`viewed_at` set, Story 6.10, FR-24): there viewing counts as
    ordering. `turns` are the open Week's `seat_turns` rows, one per Seat, each with the
    `occupant_kind` in force that Week (`repo.week_turns_with_occupant`); no turns means there
    is nothing to complete."""
    return bool(turns) and all(
        turn["ordered_at"] is not None
        and not (
            guided and turn["occupant_kind"] == OccupantKind.STUDENT and turn["viewed_at"] is None
        )
        for turn in turns
    )


@dataclass(frozen=True)
class TurnGame:
    """What `turn_times` needs of the Game in the turn's Week."""

    guided_week: bool
    """A Guided Week: every Seat orders the Guided Order when the Week opens."""


@dataclass(frozen=True)
class TurnSeat:
    """What `turn_times` needs of the Seat's turn."""

    occupant_kind: OccupantKind
    """The occupant in force in the turn's Week."""
    opened_at: datetime
    occupied_since: datetime | None = None
    """When that occupant took the Seat, if it did after the Week opened (a mid-Week Takeover,
    Epic 8); None otherwise."""


@dataclass(frozen=True)
class TurnInputs:
    """The named inputs of the turn times. Later stories add theirs (the clock start of Story
    6.14, the FR-36 inputs of Story 8.1)."""

    ai_order_budget_s: float | None = None
    """The per-Order time budget of the Effort level in the Game's `SessionRuntime`; None when
    the Game has no model config, or for a call with no deadline (Epic 8's playout)."""


@dataclass(frozen=True)
class TurnTimes:
    ai_deadline_at: datetime | None
    """When an LLM player's Order is due; None when the turn waits for no LLM Order."""


def turn_times(game: TurnGame, seat: TurnSeat, inputs: TurnInputs) -> TurnTimes:
    """The one computation of a turn's due times (AD-20, NFR-2). Pure: no I/O, no clock.

    An `llm` occupant outside a Guided Week with a per-Order time budget is due that budget
    after the Week opened, or after it took the Seat when that came later (AD-5)."""
    if (
        seat.occupant_kind is not OccupantKind.LLM
        or game.guided_week
        or inputs.ai_order_budget_s is None
    ):
        return TurnTimes(ai_deadline_at=None)
    start = seat.opened_at
    if seat.occupied_since is not None and seat.occupied_since > start:
        start = seat.occupied_since
    return TurnTimes(ai_deadline_at=start + timedelta(seconds=inputs.ai_order_budget_s))
