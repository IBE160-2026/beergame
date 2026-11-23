"""The api shapes of `modules/reports` (Story 13.2: the Studentside's record; Story 13.3: a
correction of a Completion step; Story 13.7: the Student report's state)."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, StrictBool

from app.modules.tests.service import StaffAssessmentOut

CompletionStepName = Literal["class_game", "debrief", "quiz_passed", "replay", "test_submitted"]


class CorrectionOut(BaseModel):
    """The correction of a step that applies, the latest (Story 13.3): the status it set, the
    Lecturer's reason, when, and who made it by their name now (None when the name is no longer
    known in the Class). For the staff of the Class only; never served to a Student."""

    done: bool
    reason: str
    at: datetime
    by: str | None


class CompletionStepOut(BaseModel):
    """One step of the «Fullføring» block: whether its step event is recorded and when, whether it
    counts as done after the share, the minimums and any correction, and whether a correction
    decided it (Story 13.1), with that correction (Story 13.3)."""

    step: CompletionStepName
    recorded: bool
    recorded_at: datetime | None
    done: bool
    corrected: bool
    correction: CorrectionOut | None = None


REASON_MAX_LENGTH = 1000
"""The longest «Begrunnelse», in characters after trimming [ASSUMPTION]."""


class CorrectionIn(BaseModel):
    """«Lagre retting» (Story 13.3, FR-17): the step, its new status and the required reason."""

    model_config = ConfigDict(extra="forbid")

    step: CompletionStepName
    done: StrictBool
    reason: str


class CompletionOut(BaseModel):
    """The Student's Completion status as `reports.service.completion_status` gives it (FR-17).
    `requirement_met` is None when the Class session is not obligatory. The shares are whole
    percents rounded down, None without a Class game snapshot; `required_share` is the one that
    applies to this Student, `adjusted` whether it is their own (Story 8.9)."""

    obligatory: bool
    requirement_met: bool | None
    required_share: int
    adjusted: bool
    ordered_share: int | None
    playout_share: int | None
    share_game: Literal["class", "makeup"] | None = None
    """Story 13.4: which game the shares come from when the Student has an Oppfølgingsspill (the
    one with the higher share); None without one."""
    steps: list[CompletionStepOut]


class ParticipationOut(BaseModel):
    """Participation signals, information only: they never change the Completion status (FR-17).
    The seconds spent on the Student's own Orders, how many own Orders there are, and whether the
    own Orders after the Guided Weeks were constant (None with fewer than two)."""

    own_orders: int
    seconds: int
    constant: bool | None
    after_guided: int
    """How many of the own Orders came after the Guided Weeks: what `constant` is about."""


GameState = Literal["not_ready", "ready", "running", "finished", "ended"]


class RecordGameOut(BaseModel):
    """The Student's Class game (`games.service.student_game`): its id for the link to
    Spillinnsikt, number, the Student's Role and where it stands (`ended`: closed without its last
    Week, Story 10.6), with when it finished. `makeup`: it is the Student's finished
    Oppfølgingsspill, which became their game (Story 13.5); it has no Spillinnsikt."""

    game_id: uuid.UUID
    number: int | None
    role: str
    state: GameState
    played_out: bool
    finished_at: datetime | None
    makeup: bool = False


class RecordDebriefOut(BaseModel):
    """The Explanation and the Debrief summary (`debrief.service.staff_summary`): the Explanation's
    text and time, and when the Debrief was finished and whether after the Debrief deadline."""

    explanation: str | None
    explanation_saved_at: datetime | None
    finished_at: datetime | None
    late: bool
    moments: int


class RecordQuizAttemptOut(BaseModel):
    """A Debrief quiz attempt: its number, time and result; never the answers."""

    number: int
    submitted_at: datetime
    passed: bool


class RecordReplayOut(BaseModel):
    """The Student's Replay Game (`replay.service.replay_game_of`) and when it finished."""

    game_id: uuid.UUID
    finished_at: datetime | None


class RecordMakeupOut(BaseModel):
    """The Student's Oppfølgingsspill (Story 13.4): its Game, when it was given, the Student's
    effective Test deadline it is open until, and where it stands (`ended`: closed at that
    deadline without its last Week)."""

    game_id: uuid.UUID
    given_at: datetime
    open_until: datetime | None
    state: GameState


class RecordTestOut(BaseModel):
    """The Student's Individual test attempt (`tests.service.attempt_summary`): its status, when it
    was handed in and which parts hold content. Never an answer."""

    status: Literal["open", "submitted", "auto_submitted"]
    submitted_at: datetime | None
    parts: dict[str, bool]


class StudentRecordOut(BaseModel):
    """The Studentside's record of one Student of a Class session (Story 13.2, FR-63, UX-DR55),
    for the Lecturers and Assistant lecturers of its Class. `can_manage`: the reader is a Lecturer
    of the Class, so the page also shows «Tilrettelegging» and «Frister» (`getStudentPage`).
    `completion` is None for a Student the reports leave out (`reports.scope`). The Student report
    the staff download (Story 13.12) is read from its own endpoint, `getStudentReport`."""

    class_session_id: uuid.UUID
    class_id: uuid.UUID
    class_name: str
    session_number: int
    user_id: uuid.UUID
    name: str
    can_manage: bool
    can_correct: bool = False
    """Story 13.3: the reader may correct a step («Rett Klassespill»): a Lecturer of the Class,
    the Class session obligatory and the Class not archived."""
    can_give_makeup: bool = False
    """Story 13.4: the reader may give an Oppfølgingsspill («Gi oppfølgingsspill»): a Lecturer of
    the Class, the Class not archived, the Class session locked, the Student's Test deadline set
    and not passed, the Student counted by the reports and without one already."""
    test_deadline: datetime | None = None
    """Story 13.4: the Student's effective Test deadline, which an Oppfølgingsspill is open
    until."""
    completion: CompletionOut | None
    participation: ParticipationOut | None
    game: RecordGameOut | None
    makeup: RecordMakeupOut | None = None
    """Story 13.4: the Oppfølgingsspill a Lecturer gave the Student; None without one."""
    debrief: RecordDebriefOut
    quiz: list[RecordQuizAttemptOut]
    replay: RecordReplayOut | None
    test: RecordTestOut | None
    assessment: StaffAssessmentOut | None
    """Story 12.5's «KI-vurdering» as the staff read it (states, items, feedback, the Student's
    flags); None only where `ai_assessments.read` is not granted. A self-enabled Indicative letter
    is never served to staff (FR-56, AD-12)."""


class ReportStateOut(BaseModel):
    """The Student's own Student report (Story 13.7, FR-57): when it opens (their effective Test
    deadline; None while the Class session has none), whether it is open now, the latest
    request's status, and when the PDF that can be downloaded was made (None without one).
    `failed` covers a render that failed and one that never ended; a new press tries again.
    Story 13.12: the staff's download of one Student's report answers the same shape, always
    `open`, with `opens_at` None."""

    opens_at: datetime | None
    open: bool
    status: Literal["none", "pending", "ready", "failed"]
    generated_at: datetime | None
    ai: bool = False
    """Story 13.11: this state is the report with the AI assessment section (asked with `ai`
    while the Student's AI assessment is ready); false for the standard report."""
    ai_available: bool = False
    """Story 13.11: the Student's AI assessment is ready, so the section may be added (the
    Bryter is offered)."""
    deleted: bool = False
    """Story 13.12: the Student's data in the Class session is deleted (its deletion date has
    come), so no report is built; the staff's action says so."""


class ReportRequestIn(BaseModel):
    """«Lag Studentrapport» (Story 13.11): `ai` adds the AI assessment section; off by default."""

    model_config = ConfigDict(extra="forbid")

    ai: StrictBool = False


class ZipStateOut(BaseModel):
    """The ZIP of all Student reports of the Class session (Story 13.13, FR-59): the latest
    request's status (`failed` covers a job that failed and one that never ended; a new press
    tries again), when the ZIP that can be downloaded was made and how many Student reports it
    holds (None without one). `deleted` once the Class session's Student data is deleted. The ZIP
    never holds the AI assessment."""

    status: Literal["none", "pending", "ready", "failed"]
    generated_at: datetime | None
    students: int | None
    deleted: bool = False
    completion_export: bool = False
    """Story 13.14: whether the reader may download the Completion export (the Class's
    Lecturers; never an Assistant lecturer), so the «Eksport» block offers it."""


# «Mine data» (Story 15.1, FR-75, AD-12, AD-14).

MyDataCategory = Literal[
    "account",
    "orders",
    "game",
    "explanation",
    "reflection",
    "follow_ups",
    "debrief",
    "quiz",
    "starting_task",
    "test",
    "assessment",
    "letter",
    "adjustments",
    "messages",
    "completion",
]


class MyDataFieldOut(BaseModel):
    """One stored value: `key` and, for `kind` `code`, the value are labelled by the page from
    `nb.ts`; `datetime` and `date` values are ISO 8601; `bool` is `true` or `false`."""

    key: str
    kind: Literal["text", "number", "bool", "datetime", "date", "code"]
    value: str | None


class MyDataItemOut(BaseModel):
    """One stored row of the Student: what it is (`kind`), the Class and Klasseøkt it belongs to
    (null for the account), when it was stored, and its fields."""

    kind: str
    class_name: str | None
    session_number: int | None
    at: datetime | None
    fields: list[MyDataFieldOut]


class MyDataCategoryOut(BaseModel):
    key: MyDataCategory
    items: list[MyDataItemOut]


class MyDataOut(BaseModel):
    """Everything the product stores about the caller, by «Mine data» category in page order.
    `adjustments` is left out when the Student has no Tilrettelegging."""

    categories: list[MyDataCategoryOut]
