"""API shapes of `modules/sessions` (Stories 5.1 and 5.2)."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Literal

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
    """«Lagre Klasseøkt». The screen sends the AI mode as it stands (Story 5.5 adds the choice)
    and the four dates (Story 5.2); without `dates` the dates stay as they are."""

    model_config = ConfigDict(extra="forbid")

    ai_mode: AiMode
    dates: DatesIn | None = None


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
