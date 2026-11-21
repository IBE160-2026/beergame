"""Predicates on a Game's turns (AD-2, AD-20). Commands ask these and never decide themselves."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from app.engine import GameSettings
from app.modules.games.policy import GamePolicy, policy
from app.modules.games.schemas import GameStatus, Lifecycle, OccupantKind


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


def is_paused(game: Mapping[str, object]) -> bool:
    """Whether a Pause is in force on the Game (Story 8.6, FR-89): its `paused_at` is set. A row
    read without the column (a caller's own mapping) is not paused."""
    return game.get("paused_at") is not None


TakeoverActor = Literal["system", "staff"]
"""Who asks for a Takeover: `system`, the sweep's automatic Takeover after the Inactivity limit
(Story 8.2); `staff`, a Lecturer or Assistant lecturer from Spillstyring (Story 8.5). Peer
Takeovers (8.8) extend this one check."""

TAKEOVER_REASONS = frozenset({"takeover_inactivity", "takeover_staff", "takeover_peer"})
"""The occupancy reasons of a Takeover: a Seat whose latest row has one is taken over already."""


def can_take_over(
    game: Mapping[str, object],
    turn: Mapping[str, object] | None,
    actor: TakeoverActor,
    now: datetime,
    *,
    guided: bool,
    seat: Mapping[str, object] | None = None,
) -> str | None:
    """The one eligibility check of a Takeover (FR-36, FR-37, AD-2, AD-13): None when `actor` may
    hand the Seat of `turn` to an AI player at `now`, else the stable refusal code.

    `game` is a `games` row (`lifecycle`, `purpose`); `turn` the Seat's `seat_turns` row in the
    open Week with the `occupant_kind` in force (`repo.week_turns_with_occupant`), None when the
    Seat has none; `seat` the Seat's latest occupancy row (`occupant_kind`, `reason`), which may
    apply from the next Week. The Game must be running and its policy have inactivity Takeover.
    While the Game is paused (`is_paused`) the `system` actor gets `game_paused` (FR-89, Story
    8.6): no automatic Takeover, and the stored due time is not moved; staff are not limited.
    A Seat whose latest row is an AI player's is `takeover_exists` when a Takeover put it there,
    else `seat_not_student_held`; so is a Seat not Student-held in the open Week. For the `system`
    actor the Seat must not have ordered (`has_ordered`: in a Guided Week the view counts), and
    its stored `takeover_due_at` must be set, which happens only once another Student has ordered
    (Story 8.1), and lie at or before `now`. The `staff` actor needs no due time and may act on a
    Seat that has ordered: its AI player then takes the next Week (the command decides when).
    Pure: no I/O, no clock."""
    if actor not in ("system", "staff"):
        raise ValueError(f"unknown Takeover actor {actor!r}")
    if game["lifecycle"] != Lifecycle.RUNNING:
        return "game_not_running"
    if not policy(str(game["purpose"])).inactivity_takeover:
        return "takeover_not_allowed"
    if actor == "system" and is_paused(game):
        return "game_paused"
    if seat is not None and seat["occupant_kind"] != OccupantKind.STUDENT:
        return "takeover_exists" if seat["reason"] in TAKEOVER_REASONS else "seat_not_student_held"
    if turn is None or turn["occupant_kind"] != OccupantKind.STUDENT:
        return "seat_not_student_held"
    if actor == "staff":
        return None
    if has_ordered(turn, guided=guided):
        return "order_exists"
    due = turn["takeover_due_at"]
    if not isinstance(due, datetime) or due > now:
        return "takeover_not_due"
    return None


def game_status(game: Mapping[str, object], turns: Sequence[Mapping[str, object]]) -> GameStatus:
    """The one definition of a Game's status (AD-2, FR-39); `game_summaries` stores its result.

    `game` is a `games` row (`lifecycle`, `purpose`, `settings`); `turns` are its open Week's
    `seat_turns` rows, each with the `occupant_kind` in force that Week
    (`repo.week_turns_with_occupant`). A Game that runs is `waiting` when at least one Student has
    ordered in the open Week and at least one Student-held Seat has not (FR-25); in a Guided Week
    viewing counts as ordering (FR-24). A Game that runs with a Pause in force is `paused` (FR-89,
    Story 8.6), whoever it waits for. Otherwise it is `running`. Pure: no I/O, no clock."""
    lifecycle = game["lifecycle"]
    if lifecycle == Lifecycle.NOT_STARTED:
        return GameStatus.NOT_STARTED
    if lifecycle == Lifecycle.FINISHED:
        return GameStatus.FINISHED
    if is_paused(game):
        return GameStatus.PAUSED
    students = [turn for turn in turns if turn["occupant_kind"] == OccupantKind.STUDENT]
    if not students:
        return GameStatus.RUNNING
    week = students[0]["week"]
    assert isinstance(week, int)  # every turn of the open Week carries it
    guided = guided_week(
        policy(str(game["purpose"])), GameSettings.model_validate(game["settings"]), week
    )
    ordered = [has_ordered(turn, guided=guided) for turn in students]
    return GameStatus.WAITING if any(ordered) and not all(ordered) else GameStatus.RUNNING


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
    """The named inputs of the turn times: the AI budget (Story 2.6), the clock start (Story
    6.14) and the FR-36 inputs (Story 8.1); the per-Student factor, the agreed time and the
    in-room limit stay empty until Stories 8.9, 8.7 and 8.11 pass them."""

    ai_order_budget_s: float | None = None
    """The per-Order time budget of the Effort level in the Game's `SessionRuntime`; None when
    the Game has no model config, or for a call with no deadline (Epic 8's playout)."""
    clock_start: datetime | None = None
    """When the first Student ordered in the turn's Week, or viewed it in a Guided Week (Story
    6.14, FR-25): from then on the game waits for every Seat that has not ordered. None before
    that, or for a call that does not ask for the wait."""
    inactivity_limit: timedelta | None = None
    """The Inactivity limit in the Game's `SessionRuntime` (FR-36, Story 8.1); None when the
    Game's policy has no inactivity Takeover (AD-13) or the snapshot holds no limit: then no due
    time is set."""
    time_factor: float | None = None
    """The Student's Tilrettelegging factor (FR-17, Story 8.9): it multiplies the limit and only
    extends it; None (or below 1) is 1."""
    agreed_time: datetime | None = None
    """The agreed time a Lecturer set on a Pause (FR-89, Story 8.7); None without one."""
    in_room_limit: timedelta | None = None
    """The shorter limit of a Game marked as in the room (FR-36, Story 8.11); it replaces the
    Inactivity limit. None when the Game is not marked."""


@dataclass(frozen=True)
class TurnTimes:
    ai_deadline_at: datetime | None
    """When an LLM player's Order is due; None when the turn waits for no LLM Order."""
    wait_started_at: datetime | None = None
    """When the game began to wait for the Seat (Story 6.14): the clock start, or when its
    occupant took the Seat if that came later; None without a clock start."""
    takeover_due_at: datetime | None = None
    """When an AI player takes the Student's Seat over (FR-36, Story 8.1): the wait start plus
    the limit in force times the Student's factor; None for any other occupant, without a clock
    start or without a limit."""
    insert_allowed_at: datetime | None = None
    """From when another Student may put an AI player in the Seat (FR-89): the agreed time if one
    is set, never before the Student's own extended limit when they have a factor above 1;
    otherwise `takeover_due_at`."""


def turn_times(game: TurnGame, seat: TurnSeat, inputs: TurnInputs) -> TurnTimes:
    """The one computation of a turn's due times (AD-20, NFR-2). Pure: no I/O, no clock.

    An `llm` occupant outside a Guided Week with a per-Order time budget is due that budget
    after the Week opened, or after it took the Seat when that came later (AD-5). With a clock
    start the Seat is waited for from then, or from when its occupant took it if that came later
    (Story 6.14, FR-25); the caller asks only for a turn that has not ordered. A `student`
    occupant waited for under a limit also gets its FR-36 due times (`_due_times`), in a Guided
    Week too (FR-24)."""
    waiting = None
    if inputs.clock_start is not None:
        waiting = _later(inputs.clock_start, seat.occupied_since)
    takeover_due, insert_allowed = _due_times(seat, inputs, waiting)
    ai_deadline = None
    if (
        seat.occupant_kind is OccupantKind.LLM
        and not game.guided_week
        and inputs.ai_order_budget_s is not None
    ):
        start = _later(seat.opened_at, seat.occupied_since)
        ai_deadline = start + timedelta(seconds=inputs.ai_order_budget_s)
    return TurnTimes(
        ai_deadline_at=ai_deadline,
        wait_started_at=waiting,
        takeover_due_at=takeover_due,
        insert_allowed_at=insert_allowed,
    )


def _due_times(
    seat: TurnSeat, inputs: TurnInputs, waiting: datetime | None
) -> tuple[datetime | None, datetime | None]:
    """FR-36 and FR-89: the Takeover due time is the wait start plus the limit in force (the
    in-room limit when the Game is marked, else the Inactivity limit) times the Student's factor,
    which only extends it. The insert time is the agreed time when one is set, but a Student with
    a factor above 1 never gets one before their own extended limit; otherwise the due time.
    With no clock running yet (nobody else has ordered) there is no due time, but an agreed time
    stands as the insert time (Story 8.7; open-assumptions: also with Tilrettelegging)."""
    if seat.occupant_kind is not OccupantKind.STUDENT:
        return None, None
    limit = inputs.in_room_limit if inputs.in_room_limit is not None else inputs.inactivity_limit
    if waiting is None or limit is None:
        return None, inputs.agreed_time
    factor = max(inputs.time_factor or 1.0, 1.0)
    due = waiting + limit * factor
    if inputs.agreed_time is None:
        return due, due
    if factor > 1.0:
        return due, max(inputs.agreed_time, due)
    return due, inputs.agreed_time


def _later(start: datetime, since: datetime | None) -> datetime:
    return since if since is not None and since > start else start
