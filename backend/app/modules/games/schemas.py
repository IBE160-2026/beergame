"""Value types of the games module."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict


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
    session_runtime: SessionRuntime
    seats: tuple[SeatOverview, ...]
