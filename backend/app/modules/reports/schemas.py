"""The api shapes of `modules/reports` (Story 13.2: the Studentside's record)."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

CompletionStepName = Literal["class_game", "debrief", "quiz_passed", "replay", "test_submitted"]


class CompletionStepOut(BaseModel):
    """One step of the «Fullføring» block: whether its step event is recorded and when, whether it
    counts as done after the share, the minimums and any correction, and whether a correction
    decided it (Story 13.1)."""

    step: CompletionStepName
    recorded: bool
    recorded_at: datetime | None
    done: bool
    corrected: bool


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
    Week, Story 10.6), with when it finished."""

    game_id: uuid.UUID
    number: int | None
    role: str
    state: GameState
    played_out: bool
    finished_at: datetime | None


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


class RecordTestOut(BaseModel):
    """The Student's Individual test attempt (`tests.service.attempt_summary`): its status, when it
    was handed in and which parts hold content. Never an answer."""

    status: Literal["open", "submitted", "auto_submitted"]
    submitted_at: datetime | None
    parts: dict[str, bool]


class RecordAssessmentOut(BaseModel):
    """The AI assessment part, as far as this branch has it: `off` when the Class session's
    «KI-vurdering» switch is off, else `not_ready`. Story 12.5's «KI-vurdering» block replaces this
    part. A self-enabled Indicative letter is never served to staff, so there is no field for one
    (FR-56, AD-12)."""

    state: Literal["off", "not_ready"]


class StudentRecordOut(BaseModel):
    """The Studentside's record of one Student of a Class session (Story 13.2, FR-63, UX-DR55),
    for the Lecturers and Assistant lecturers of its Class. `can_manage`: the reader is a Lecturer
    of the Class, so the page also shows «Tilrettelegging» and «Frister» (`getStudentPage`).
    `completion` is None for a Student the reports leave out (`reports.scope`); `report` is the
    slot for the link to the Student report, None until Story 13.12."""

    class_session_id: uuid.UUID
    class_id: uuid.UUID
    class_name: str
    session_number: int
    user_id: uuid.UUID
    name: str
    can_manage: bool
    completion: CompletionOut | None
    participation: ParticipationOut | None
    game: RecordGameOut | None
    debrief: RecordDebriefOut
    quiz: list[RecordQuizAttemptOut]
    replay: RecordReplayOut | None
    test: RecordTestOut | None
    assessment: RecordAssessmentOut
    report: None = None
