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


def has_ordered(turn: Mapping[str, object], *, guided: bool) -> bool:
    """Whether the Seat has ordered in the turn's Week: its Order is placed (`ordered_at` set)
    and, in a Guided Week, a turn of a Seat a Student holds in that Week has also been viewed
    (`viewed_at` set, Story 6.10, FR-24): there viewing counts as ordering. `turn` is a
    `seat_turns` row with the `occupant_kind` in force that Week."""
    return turn["ordered_at"] is not None and not (
        guided and turn["occupant_kind"] == OccupantKind.STUDENT and turn["viewed_at"] is None
    )


def week_complete(turns: Sequence[Mapping[str, object]], *, guided: bool) -> bool:
    """The one predicate for an advance: the open Week is complete when every Seat's turn in it
    `has_ordered`. `turns` are the open Week's `seat_turns` rows, one per Seat, each with the
    `occupant_kind` in force that Week (`repo.week_turns_with_occupant`); no turns means there
    is nothing to complete."""
    return bool(turns) and all(has_ordered(turn, guided=guided) for turn in turns)


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
    """The named inputs of the turn times. Later stories add theirs (the FR-36 inputs of Story
    8.1)."""

    ai_order_budget_s: float | None = None
    """The per-Order time budget of the Effort level in the Game's `SessionRuntime`; None when
    the Game has no model config, or for a call with no deadline (Epic 8's playout)."""
    clock_start: datetime | None = None
    """When the first Student ordered in the turn's Week, or viewed it in a Guided Week (Story
    6.14, FR-25): from then on the game waits for every Seat that has not ordered. None before
    that, or for a call that does not ask for the wait."""


@dataclass(frozen=True)
class TurnTimes:
    ai_deadline_at: datetime | None
    """When an LLM player's Order is due; None when the turn waits for no LLM Order."""
    wait_started_at: datetime | None = None
    """When the game began to wait for the Seat (Story 6.14): the clock start, or when its
    occupant took the Seat if that came later; None without a clock start."""


def turn_times(game: TurnGame, seat: TurnSeat, inputs: TurnInputs) -> TurnTimes:
    """The one computation of a turn's due times (AD-20, NFR-2). Pure: no I/O, no clock.

    An `llm` occupant outside a Guided Week with a per-Order time budget is due that budget
    after the Week opened, or after it took the Seat when that came later (AD-5). With a clock
    start the Seat is waited for from then, or from when its occupant took it if that came later
    (Story 6.14, FR-25); the caller asks only for a turn that has not ordered."""
    waiting = None
    if inputs.clock_start is not None:
        waiting = _later(inputs.clock_start, seat.occupied_since)
    if (
        seat.occupant_kind is not OccupantKind.LLM
        or game.guided_week
        or inputs.ai_order_budget_s is None
    ):
        return TurnTimes(ai_deadline_at=None, wait_started_at=waiting)
    start = _later(seat.opened_at, seat.occupied_since)
    return TurnTimes(
        ai_deadline_at=start + timedelta(seconds=inputs.ai_order_budget_s),
        wait_started_at=waiting,
    )


def _later(start: datetime, since: datetime | None) -> datetime:
    return since if since is not None and since > start else start
