"""The envelopes of «KI-kostnad»: the model configs with their measured Effort levels, the Class
sessions' model settings and the study freeze (Story 15.5, FR-68, FR-78, AD-19)."""

import uuid
from datetime import datetime
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
