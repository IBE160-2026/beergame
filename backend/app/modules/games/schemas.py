"""Value types of the games module."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.engine import (
    CostLine,
    GameSettings,
    OrderPreview,
    SeatView,
    SupplyLineSlot,
    Violation,
    WeekValues,
)


class Purpose(StrEnum):
    """Why a Game exists (AD-13). `games.policy` says what each one means."""

    CLASS = "class"
    REPLAY = "replay"
    MAKEUP = "makeup"
    LECTURER_TEST = "lecturer_test"
    SIMULATION = "simulation"


class Lifecycle(StrEnum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    PLAYING_OUT = "playing_out"
    FINISHED = "finished"


class OccupantKind(StrEnum):
    """Who holds a Seat from a Week on (AD-5)."""

    STUDENT = "student"
    LLM = "llm"
    RULE_BASED = "rule_based"
    SCRIPTED = "scripted"


class OccupancyReason(StrEnum):
    INITIAL = "initial"
    TAKEOVER_INACTIVITY = "takeover_inactivity"
    TAKEOVER_STAFF = "takeover_staff"
    TAKEOVER_PEER = "takeover_peer"
    RECLAIM = "reclaim"
    GUARD_SWITCH = "guard_switch"
    COST_LIMIT = "cost_limit"
    PLAYOUT = "playout"


class DecidedBy(StrEnum):
    """Who decided an Order in the Decision log (AD-15)."""

    STUDENT = "student"
    LLM = "llm"
    RULE_BASED = "rule_based"
    SCRIPTED = "scripted"
    GUIDED = "guided"


class Fallback(StrEnum):
    """Why an Order is not the occupant's own decision (FR-32, AD-15): `none`, or the typed
    failure of the LLM call whose Week got the Rule-based reference Order instead. Kept apart
    from `decided_by`, which then says `rule_based`."""

    NONE = "none"
    TIMEOUT = "timeout"
    INVALID_OUTPUT = "invalid_output"
    BUDGET_EXHAUSTED = "budget_exhausted"
    PROVIDER_ERROR = "provider_error"


_FROZEN = ConfigDict(frozen=True, extra="forbid")


class SessionRuntime(BaseModel):
    """The runtime part of a Game's snapshot (AD-4). Later epics add fields here (Inactivity
    limit, prompt and content versions)."""

    model_config = _FROZEN

    schema_version: Literal[1] = 1
    ai_mode: Literal["llm", "rule_based"]
    rule_based_params: str
    """Id of the Rule-based parameter set every Rule-based player of the Game uses."""
    rule_based_params_version: int
    model_config_id: str | None = None
    """The model config every LLM player of the Game uses (AD-22, FR-78); None: no LLM player
    may hold a Seat."""
    effort_level: str | None = None
    """The config's Effort level the Game froze, set together with `model_config_id`."""
    play_guard_params: str | None = None
    """Id of the Play guard parameter set the Game froze (FR-79); None only on Games created
    before Story 2.10, for which the guard does not run."""
    play_guard_params_version: int | None = None

    @model_validator(mode="after")
    def _config_and_level(self) -> SessionRuntime:
        if (self.model_config_id is None) != (self.effort_level is None):
            raise ValueError("model_config_id and effort_level are set together")
        if (self.play_guard_params is None) != (self.play_guard_params_version is None):
            raise ValueError("play_guard_params and its version are set together")
        return self


class SeatOverview(BaseModel):
    model_config = _FROZEN

    id: str
    role: str
    occupant_kind: OccupantKind | None
    """The current occupant; None while the Seat is free."""
    policy_id: str | None
    user_id: str | None = None
    """The Student of a `student` occupant (Story 5.9); None for every other occupant."""


class GameOverview(BaseModel):
    """A stored Game as read back from the database."""

    model_config = _FROZEN

    id: str
    purpose: Purpose
    lifecycle: Lifecycle
    version: int
    demand_seed: int | None
    rules_version: int | None
    settings: GameSettings | None
    """The Game's frozen settings (AD-4); None, like the rest of the snapshot, on a Game whose
    policy takes it at the lock and that has not got it yet."""
    session_runtime: SessionRuntime | None
    class_session_id: str | None = None
    """The Class session of a Class game (Story 5.9), with its `game_number` in it."""
    game_number: int | None = None
    seats: tuple[SeatOverview, ...]


_Count = Annotated[int, Field(strict=True, ge=0)]
_Week = Annotated[int, Field(strict=True, ge=1)]
_Money = Annotated[Decimal, Field(allow_inf_nan=False)]


class SeatState(SeatView):
    """What one Seat sees in one opened Week: the single information boundary (AD-3, FR-23).

    The play screen, the LLM player's prompt and the Decision log (`state_seen`) all read this
    model, and a field is added here, never beside it. It holds numbers and Roles only: no
    names, no number of Weeks, no future demand and no other Seat's state beyond the
    `neighbour_numbers` that Information visibility allows (empty until Story 5.16 / 7.x).
    Every number comes from `engine.seat_view` and `engine.seat_detail`; engine functions that
    take a `SeatView` accept this model as it is."""

    schema_version: Literal[1] = 1
    week: _Week
    incoming_order: _Count
    """This Week's incoming order; customer demand for the Retailer."""
    incoming_delivery: _Count
    shipped: _Count
    supply_line_slots: tuple[SupplyLineSlot, ...]
    """Units ordered and not received, arrives soonest first, with their arrival Weeks."""
    overdue: _Count
    """Units the upstream Seat received an Order for but has not shipped yet."""
    position: int
    """Posisjon: inventory minus backlog plus the supply line."""
    cost_lines: tuple[CostLine, ...]
    week_cost: _Money
    total_cost: _Money
    """Running Total cost: the earlier Weeks plus this Week's."""
    history: tuple[WeekValues, ...]
    """The Seat's own earlier Weeks with their Orders, oldest first."""
    min_order: _Count
    max_order: _Count
    preview: OrderPreview


class TurnOverview(BaseModel):
    """One Seat's turn in one opened Week (AD-20)."""

    model_config = _FROZEN

    week: int
    guided: bool
    """A Guided Week: the Order is `engine.guided_order`, placed with `decided_by = guided`."""
    opened_at: datetime
    ordered_at: datetime | None
    rule_based_reference_order: int
    near_optimal_reference_order: int | None = None
    """Computed from the whole chain when the Week opened (FR-79); None only on turns opened
    before Story 2.9."""
    near_optimal_algorithm_version: str | None = None
    """The algorithm that computed it (`engine.near_optimal.ALGORITHM_VERSION`)."""


class PendingTurn(BaseModel):
    """A Seat's turn in the open Week as the order source sees it inside the running command's
    transaction (AD-5): who holds the Seat in that Week and what it may order from."""

    model_config = _FROZEN

    game_id: str
    seat_id: str
    role: str
    week: int
    guided: bool
    """A Guided Week: every non-student occupant orders `guided_order`."""
    guided_order: int
    occupant_kind: OccupantKind
    """The occupant in force in `week` (`from_week <= week`, newest)."""
    policy_id: str | None
    rule_based_reference_order: int
    """Stored on the turn when the Week opened; never recomputed."""
    ordered: bool
    """The Seat already has an Order for `week`."""
    ai_deadline_at: datetime | None = None
    """When the LLM player's Order is due (`games.rules.turn_times`); None: no deadline."""
    read_at: datetime | None = None
    """The database clock when the turn was read (`llm_turn`): the clock `ai_deadline_at` is
    on, so `ai_deadline_at - read_at` is the time left on any other clock."""
    seat_state: SeatState


class OrderPlaced(BaseModel):
    """What `place_order` did: the Decision log row and the Week that is open after it."""

    model_config = _FROZEN

    seat_week_id: str
    week: int
    """The Week the Order was placed in."""
    open_week: int | None
    """The Week open after the command: `week`, or the next one if it advanced; None once the
    Game has finished."""
    lifecycle: Lifecycle


class DecisionLogRow(BaseModel):
    """One `seat_weeks` row as read back (AD-15)."""

    model_config = _FROZEN

    week: int
    role: str
    seat_id: str
    order: int
    decided_by: DecidedBy
    fallback: Fallback
    occupant_kind: OccupantKind
    reason: OccupancyReason
    opened_at: datetime
    ordered_at: datetime
    ai_deadline_at: datetime | None = None
    """When an LLM player's Order was due (AD-20); None for every other Order."""
    rule_based_reference_order: int
    near_optimal_reference_order: int | None = None
    """Copied from the turn (FR-67, FR-79); None only on rows written before Story 2.9."""
    near_optimal_algorithm_version: str | None = None
    """The algorithm that computed it, copied from the turn."""
    llm_call_ids: tuple[str, ...] = ()
    """The LLM call rows behind the Order: every attempt of an LLM Order or of the failed call
    behind a fallback Order (FR-67)."""
    effort_level: str | None = None
    """The Effort level the Game froze, on rows an `llm` occupant ordered (FR-78); None on every
    other row and on rows written before Story 2.11."""
    state_seen: SeatState


class OccupancyRow(BaseModel):
    """One row of a Seat's append-only occupancy history (AD-5): who holds the Seat from
    `from_week` on, and why. A Play guard switch is a `guard_switch` row whose `from_week` is
    the Week after the Order that caused it (FR-79, FR-67)."""

    model_config = _FROZEN

    role: str
    seat_id: str
    from_week: int
    occupant_kind: OccupantKind
    policy_id: str | None
    reason: OccupancyReason


class SimulationBatch(BaseModel):
    """One `simulation_batches` row with its Games (Story 2.11, AD-22)."""

    model_config = _FROZEN

    id: str
    batch_file: dict[str, Any]
    """The batch file as it was played (`model_config` filled in)."""
    pass_lines: dict[str, Any]
    """The pass lines from the batch file; empty when it has none."""
    mock: bool
    """The batch's LLM Seats were answered by the mock provider."""
    started_at: datetime
    game_ids: tuple[str, ...]
    """The batch's Games in the order they were created."""


class GameCheck(BaseModel):
    """One `game_checks` row: the result of replaying and checking a finished Game (AD-9)."""

    model_config = _FROZEN

    id: str
    game_id: str
    rules_version: int
    """The stored `rules_version` the Game was replayed at."""
    ok: bool
    checked_at: datetime
    violations: tuple[Violation, ...]
    """Every broken rule with its Week and Role; empty when `ok`."""


class GameSummary(BaseModel):
    """A finished Game in numbers, read from `game_weeks`, the Decision log and `game_checks`
    (AD-22)."""

    model_config = _FROZEN

    game_id: str
    demand_seed: int
    weeks: int
    """The last Week, which ran in full."""
    total_cost: tuple[tuple[str, Decimal], ...]
    """Each Role's Total cost in chain order, from the finished Week state."""
    chain_cost: Decimal
    orders: tuple[tuple[DecidedBy, int], ...]
    """Decision log rows per `decided_by`, in `DecidedBy` order; zero counts left out."""
    check: GameCheck | None
    """The finished-game check, or None when it has not run."""
