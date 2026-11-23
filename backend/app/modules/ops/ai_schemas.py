"""The envelopes of «KI-kostnad»: the model configs with their measured Effort levels, the Class
sessions' model settings and the study freeze (Story 15.5, FR-68, FR-78, AD-19)."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

FREEZE_SESSIONS_MAX = 50
"""The most Class sessions one study freeze takes."""


class MeasurementOut(BaseModel):
    """The newest measurement of an Effort level that counts here, as the approval of Story 2.12
    stored it: decimal strings, never recomputed. A mock measurement has no
    figures."""

    mock: bool
    games: int | None
    cost_per_game_usd: str | None
    fallback_share: str | None
    """LLM-path Orders with any fallback over all LLM-path Orders, 0 to 1."""
    switched_share: str | None
    """`llm` Seats the Play guard switched over all `llm` Seats, 0 to 1."""
    time_per_order_p95_s: str | None
    approved_at: datetime


class EffortLevelEntryOut(BaseModel):
    name: str
    label: str | None
    offered: bool
    """Offered to a Class session here: measured and its endpoint may answer (FR-78)."""
    measurement: MeasurementOut | None


class ModelConfigOut(BaseModel):
    id: uuid.UUID
    name: str
    provider: str
    endpoint: str
    region: str
    model_version: str
    quantisation: str
    prompts: dict[str, int]
    referenced: bool
    may_answer: bool
    """False where its provider has no key here (AD-17): a Class session with LLM players and
    this config cannot be locked."""
    pinnable: bool
    """At least one Effort level is measured here."""
    active_default: bool
    frozen: bool
    """The config of the freeze in force."""
    effort_levels: list[EffortLevelEntryOut]


class ModelConfigListOut(BaseModel):
    items: list[ModelConfigOut]


class FrozenSettingOut(BaseModel):
    """What the lock froze in `SessionRuntime` (AD-4), read-only."""

    model_config_id: uuid.UUID
    model_name: str | None
    model_version: str | None
    endpoint: str | None
    effort_level: str | None
    prompt_versions: dict[str, int]


class ModelSessionOut(BaseModel):
    """A saved Class session with its model setting."""

    id: uuid.UUID
    number: int
    class_name: str
    institution_name: str | None
    start_at: datetime | None
    locked: bool
    """Locked, or its Start date has passed: the model can no longer change."""
    ai_mode: str
    model_config_id: uuid.UUID | None
    model_name: str | None
    model_version: str | None
    effort_level: str | None
    in_freeze: bool
    """One of the Class sessions of the freeze in force."""
    frozen: FrozenSettingOut | None
    warnings: list[str]
    """`provider_key_missing`: LLM players, not locked, and the config may not answer here."""


class ModelSessionListOut(BaseModel):
    items: list[ModelSessionOut]


class PinIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_config_id: uuid.UUID


class FreezeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_config_id: uuid.UUID
    class_session_ids: Annotated[
        list[uuid.UUID], Field(min_length=1, max_length=FREEZE_SESSIONS_MAX)
    ]


class FreezeOut(BaseModel):
    id: uuid.UUID
    model_config_id: uuid.UUID
    model_name: str | None
    model_version: str | None
    class_session_ids: list[uuid.UUID]
    frozen_at: datetime
    lifted_at: datetime | None


class FreezeStateOut(BaseModel):
    """The freeze in force, or null."""

    active: FreezeOut | None


class DaySessionSpendOut(BaseModel):
    """One Class session's AI spend on the day, named as the Admin names it (no Student data)."""

    class_session_id: uuid.UUID
    label: str
    """«class-of-1994 · Klasseøkt 2»."""
    institution_name: str | None
    usd: str
    calls: int


class DailySpendOut(BaseModel):
    """The AI spend of one Europe/Oslo day and its alert (Story 15.7, FR-69): decimal strings as
    summed by `ai.calls.day_spend`, unrounded."""

    day: date
    today: date
    """Today in Europe/Oslo, so the page offers no later day."""
    total_usd: str
    calls: int
    evaluation_usd: str
    """What simulation runs spent, apart from Class sessions (AD-22)."""
    alert_usd: str | None
    """`AI_DAILY_ALERT_USD`; null when no daily alert is set."""
    passed: bool
    """The day's spend is above the alert amount."""
    alerted_at: datetime | None
    """When the sweep alerted the Admins about this day; null when it did not."""
    sessions: list[DaySessionSpendOut]
    """The dearest Class sessions, dearest first, at most ten."""
    session_count: int


# «KI-kostnad per Klasseøkt» (Story 15.6, FR-69, AD-6): decimal strings with eight places, summed
# unrounded by `ai.calls`; the budget row read through `ai.budget`. No Student data.


class BudgetOut(BaseModel):
    """A budget row as `ai.budget` holds it."""

    limit_usd: str
    reserve_usd: str
    spent_usd: str
    reserved_usd: str
    """The worst-case cost of the attempts under way."""
    players_exhausted_at: datetime | None
    """When the players' limit was reached and the LLM players switched to Rule-based players."""


class SessionCostOut(BaseModel):
    """One saved Class session's AI cost against its budget."""

    class_session_id: uuid.UUID
    label: str
    """«class-of-1994 · Klasseøkt 2»."""
    institution_name: str | None
    ai_mode: str
    budget: BudgetOut | None
    """None: the Class session has no budget row yet (made when it is saved with LLM players or
    pinned)."""
    total_usd: str
    calls: int
    games: int
    """Its Class games."""
    students: int
    """The Students who hold a Seat in its Class games."""
    per_game_usd: str | None
    """What the calls that name a Game cost per Class game; null without a Game."""
    per_student_usd: str | None
    """The total per Student; null without a Student."""
    per_game_above: bool
    """Above the USD 0.10 per Game target (C-3)."""
    per_student_above: bool
    """Above the USD 0.50 per Student target (C-3)."""


class EvaluationCostOut(BaseModel):
    """A model config's evaluation budget (simulation runs, AD-22), apart from Class sessions."""

    model_config_id: uuid.UUID
    model_name: str
    budget: BudgetOut


class CostListOut(BaseModel):
    game_target_usd: str
    student_target_usd: str
    sessions: list[SessionCostOut]
    """Every saved Class session, newest first."""
    evaluations: list[EvaluationCostOut]


class GameCostOut(BaseModel):
    game_id: uuid.UUID | None
    """Null: the calls that name no Game (the Debrief, follow-ups, the AI assessment)."""
    number: int | None
    """The Class game's number; null for a Game outside the Class games (a test Game) or none."""
    usd: str
    calls: int
    above: bool
    """A Game above the USD 0.10 target."""


class DayCostOut(BaseModel):
    day: date
    usd: str
    calls: int


class SessionCostDetailOut(SessionCostOut):
    """One Class session's cost per Game and per day, with its cost-limit state."""

    per_game: list[GameCostOut]
    per_day: list[DayCostOut]
    reserve_used_up: bool
    """The players' limit is reached and what is left cannot pay the next Debrief or assessment
    call: the Debrief runs from code and the AI assessment waits for the Admin."""
    assessment_stopped_at: datetime | None
    """When the AI assessment of the Class session was stopped (Story 12.4)."""
    can_stop: bool
    """Whether «Stopp KI-vurderingen» is offered: the reserve is used up and it runs."""


class LimitIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit_usd: Decimal = Field(ge=0, max_digits=18, decimal_places=8)
