"""API shapes of `modules/sessions` (Stories 5.1 to 5.4)."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict

from app.engine import GameSettings


class AiMode(StrEnum):
    """Who holds the AI Seats of the Class session's games (FR-15)."""

    llm = "llm"
    rule_based = "rule_based"


class DebriefMode(StrEnum):
    group = "group"
    personal = "personal"


LlmUnavailable = Literal["no_default_model"]
"""Why LLM players cannot be chosen now: no model config is pinned as the default (FR-15)."""


DateName = Literal["start_at", "play_deadline", "debrief_deadline", "test_deadline"]
"""The four dates of a Class session in their order: Startdato, Spillfrist, Debrieffrist and
Testfrist (FR-18)."""

DateKind = Literal["start", "play", "debrief", "test"]
"""A date by what it is, for «Neste frist»."""


class SettingProblem(BaseModel):
    """Why one Game setting is refused (Story 5.3, FR-12): the engine's stable code and the range
    that applies, its bounds as decimal strings («1», «100.00»), or None when the rule has none."""

    code: str
    minimum: str | None
    maximum: str | None
    decimal_places: int | None
    """For a cost rate: the most decimal places it takes."""


class SettingWarning(BaseModel):
    """A legal but unusual Game setting (FR-12): the engine's code, the setting it stands under,
    and the numbers behind it as decimal strings. It never blocks a save."""

    code: str
    field: str
    values: dict[str, str]


class SettingsCheckIn(BaseModel):
    """A draft of the Game settings to judge without saving: the editable settings, laid
    over the stored settings. Values are sent as typed, so the engine judges them all."""

    model_config = ConfigDict(extra="forbid")

    game_settings: dict[str, Any]


class SettingsCheckOut(BaseModel):
    """What the engine says of a draft (FR-12): the errors by setting, which block a save, and the
    warnings, which do not."""

    errors: dict[str, SettingProblem]
    warnings: list[SettingWarning]


class DemandSeriesOut(BaseModel):
    """The customer demand of Weeks 1 to the last, as the engine materialises it from the stored
    Demand pattern and seed (Story 5.4, FR-13): `demand[w - 1]` is the demand in Week w. For the
    Class's staff only; no Student-facing answer carries it (AD-3)."""

    demand: list[int]


class ClassSessionOut(BaseModel):
    """One Class session as its Class's staff read it."""

    id: uuid.UUID
    class_id: uuid.UUID
    class_name: str
    number: int
    """«Klasseøkt 2»: its place among its Class's sessions, oldest first, from 1."""
    game_settings: GameSettings
    """The engine's `GameSettings` the Class session holds, its demand seed included."""
    is_classic: bool
    """Whether the Game settings are the Classic preset (the demand seed aside): «Alt er fylt ut
    med standardene.» shows only then. The server decides; the web app compares nothing."""
    ai_mode: AiMode
    debrief_mode: DebriefMode
    inactivity_limit_hours: int
    obligatory: bool
    llm_unavailable: LlmUnavailable | None
    """Set while LLM players cannot be chosen; the screen says why (FR-15, AD-17)."""
    saved_at: datetime | None
    """When «Lagre Klasseøkt» last saved it; None while it was never saved."""
    created_at: datetime
    can_manage: bool
    """Whether the User may change it: an owner of the Class, while the Class is not archived."""
    start_at: datetime | None
    play_deadline: datetime | None
    debrief_deadline: datetime | None
    test_deadline: datetime | None
    """The four dates in UTC, None until set (Story 5.2). The web app shows them in Europe/Oslo."""
    locked: bool
    """`service.is_locked`: the Start date has passed. Settings no longer change; deadlines that
    have not passed still move."""
    passed_dates: list[DateName]
    """The dates that are set and have passed by the server's clock; they no longer move."""
    play_time_warning: bool
    """The time between the Start date and the Play deadline is shorter than the configured
    least playing time per Week times the Weeks. Never true while that value is unset (SM-11)."""
    settings_warnings: list[SettingWarning]
    """The engine's warnings on the stored Game settings, in its order (Story 5.3)."""
    calibrated_settings: GameSettings
    """The settings the product's content and Play guard were calibrated for: the Classic
    preset, so the web app holds no copy of it (FR-12)."""


class ClassSessionListItem(BaseModel):
    id: uuid.UUID
    number: int
    """«Klasseøkt 2»: its place among its Class's sessions, oldest first, from 1."""
    created_at: datetime
    saved_at: datetime | None


class ClassSessionListOut(BaseModel):
    """The Class sessions of one Class, newest first. No paging: a Class has a handful."""

    items: list[ClassSessionListItem]


class DatesIn(BaseModel):
    """The four dates as the Lecturer set them, each an instant with its offset or None."""

    model_config = ConfigDict(extra="forbid")

    start_at: AwareDatetime | None
    play_deadline: AwareDatetime | None
    debrief_deadline: AwareDatetime | None
    test_deadline: AwareDatetime | None


class ClassSessionSaveIn(BaseModel):
    """«Lagre Klasseøkt». The screen sends the AI mode as it stands (Story 5.5 adds the choice),
    the four dates (Story 5.2) and the Game settings (Story 5.3) with the Demand pattern and its
    seed (Story 5.4); without `dates` or `game_settings` they stay as they are. `game_settings`
    is laid over the stored settings, so a field left out keeps its value."""

    model_config = ConfigDict(extra="forbid")

    ai_mode: AiMode
    dates: DatesIn | None = None
    game_settings: dict[str, Any] | None = None


class NextDeadline(BaseModel):
    kind: DateKind
    at: datetime


class EnrolledSessionOut(BaseModel):
    """A Class session as its Student reads it (Story 5.2, FR-18, AD-3): the dates and the next
    deadline that applies. Never the Game settings, the number of Weeks or the demand."""

    id: uuid.UUID
    class_id: uuid.UUID
    class_name: str
    number: int
    start_at: datetime | None
    play_deadline: datetime | None
    debrief_deadline: datetime | None
    """The Student's own Debrief deadline (`service.effective_debrief_deadline`)."""
    test_deadline: datetime | None
    """The Student's own Test deadline (`service.effective_test_deadline`)."""
    next_deadline: NextDeadline | None
    """The earliest of the Play, Debrief and Test deadline still ahead; None when none is."""
    obligatory: bool


class EnrolledSessionListOut(BaseModel):
    items: list[EnrolledSessionOut]


class SessionRef(BaseModel):
    id: uuid.UUID
    number: int


class WaitingClass(BaseModel):
    """A Class with Class sessions that still lack a date."""

    class_id: uuid.UUID
    class_name: str
    sessions: list[SessionRef]


class NextDate(BaseModel):
    kind: DateKind
    at: datetime
    session_id: uuid.UUID
    number: int
    class_id: uuid.UUID
    class_name: str


class LecturerOverviewOut(BaseModel):
    """The Lærerhjem's «Venter» and «Neste frist» (Story 5.2, UX-DR56): over the User's Classes
    that are not archived."""

    waiting: list[WaitingClass]
    next_date: NextDate | None
