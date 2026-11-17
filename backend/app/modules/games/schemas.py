"""Value types of the games module."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

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
    """Why an Order is not the occupant's own decision; Epic 2 adds the fallback reasons."""

    NONE = "none"


_FROZEN = ConfigDict(frozen=True, extra="forbid")


class SessionRuntime(BaseModel):
    """The runtime part of a Game's snapshot (AD-4). Later epics add fields here (Effort level,
    Inactivity limit, model config, prompt and content versions)."""

    model_config = _FROZEN

    schema_version: Literal[1] = 1
    ai_mode: Literal["llm", "rule_based"]
    rule_based_params: str
    """Id of the Rule-based parameter set every Rule-based player of the Game uses."""
    rule_based_params_version: int


class SeatOverview(BaseModel):
    model_config = _FROZEN

    id: str
    role: str
    occupant_kind: OccupantKind | None
    """The current occupant; None while the Seat is free."""
    policy_id: str | None


class GameOverview(BaseModel):
    """A stored Game as read back from the database."""

    model_config = _FROZEN

    id: str
    purpose: Purpose
    lifecycle: Lifecycle
    version: int
    demand_seed: int
    rules_version: int
    settings: GameSettings
    """The Game's frozen settings (AD-4)."""
    session_runtime: SessionRuntime
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
    rule_based_reference_order: int
    state_seen: SeatState


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
