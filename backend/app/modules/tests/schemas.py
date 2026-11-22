"""The Starting task as the Student reads and answers it (Story 6.3, FR-85, UX-DR63), the Lecturer's
question set and Scoring guide blocks (Stories 11.1, 11.2) and the Student's Individual test
(Stories 11.3, 11.4)."""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, JsonValue

from app.modules.content.schemas import GUIDE_TEXT_MAX
from app.modules.tests.models import Choice

_IN = ConfigDict(extra="forbid")


class GivenRowOut(BaseModel):
    label: str
    value: int


class SumTermOut(BaseModel):
    """One part of the sum the result shows: «0 − 13 + 16» is (+1, 0), (−1, 13), (+1, 16)."""

    sign: Literal[1, -1]
    value: int


class ItemResultOut(BaseModel):
    """The stored answer and its score. Only for an answered item: the answer key is never sent
    before."""

    answer: int
    correct: bool
    expected: int
    terms: list[SumTermOut]


class StartingTaskItemOut(BaseModel):
    id: str
    prompt: str
    hint: str | None
    column: str
    rows: list[GivenRowOut]
    asked_label: str
    result: ItemResultOut | None


class StartingTaskOut(BaseModel):
    """The Student's Starting task: the pinned content version, the items in order (answered
    ones with their result), the final question's choice and whether the task is done. The web
    app resumes at the first item without a result."""

    version: int
    items: list[StartingTaskItemOut]
    played_before: Choice | None
    done: bool


class AnswerIn(BaseModel):
    model_config = _IN

    item_id: Annotated[str, Field(min_length=1, max_length=40)]
    answer: Annotated[int, Field(strict=True, ge=-1_000_000, le=1_000_000)]


class FinalIn(BaseModel):
    model_config = _IN

    choice: Choice


# The «Spørsmål og vekter» block (Story 11.1, FR-52, FR-53, UX-DR49).

Weight = Annotated[int, Field(strict=True, ge=0, le=100)]
"""An Item weight in whole percent."""


class QuestionItemOut(BaseModel):
    """One Core item as the Lecturer reviews it: its type, its title (placeholder until issue
    #16), its weight in force and its default, whether it is taken out, and whether it measures
    quantities (taking it out warns, FR-52)."""

    id: str
    type: Literal["choice", "table", "number", "long"]
    title: str
    weight: int
    default_weight: int
    excluded: bool
    quantity: bool
    starting_task: bool


class AdaptedOut(BaseModel):
    """The Adapted items' one line: their total weight in force and its default (30 % in the
    shipped set), and how many replacement Core items a Student with fewer than 10 own Orders
    gets in their place, with the same total weight (FR-53)."""

    weight: int
    default_weight: int
    replacements: int


class QuestionSetOut(BaseModel):
    """The Class session's question set selection (Story 11.1): the version it uses, whether that
    version is a draft (issue #16), whether a selection saved on an older version no longer
    applies (`outdated`: the latest version's defaults are shown, and pinned at the lock),
    whether the lock has pinned it, whether it can still change (before the Start date), whether
    the User may change it, the items and the Adapted line, and the sum of the weights in force."""

    version: int
    draft: bool
    outdated: bool
    pinned: bool
    open: bool
    can_change: bool
    items: list[QuestionItemOut]
    adapted: AdaptedOut
    sum: int


class QuestionSetIn(BaseModel):
    """«Lagre vekter»: every Core item's weight, the items taken out and the Adapted total weight.
    The weights of the items left in plus the Adapted total must be 100."""

    model_config = _IN

    weights: Annotated[dict[str, Weight], Field(max_length=60)]
    excluded: Annotated[list[str], Field(max_length=60)]
    adapted_weight: Weight


class AdaptedPreviewItemOut(BaseModel):
    """One Adapted item template filled for the sample Student (Story 11.9): its id, the Game it
    reads (`game`, the Class game, or `replay`), its fact kind, its weight (its share of the
    Adapted total) and the code-rendered text; `text` is None when the sample has no such fact."""

    id: str
    source: Literal["game", "replay"]
    fact: Literal["moment", "pattern", "outcome"]
    weight: int
    text: str | None


class AdaptedPreviewOut(BaseModel):
    """The Adapted item preview (Story 11.9, FR-53, UX-DR70): the template version the Class
    session pins (pinned once locked, the latest before), whether it is a draft (issue #16),
    whether the lock has pinned it, the Adapted total weight in force, and each template filled
    from the static sample facts set («Demodata»)."""

    version: int
    draft: bool
    pinned: bool
    adapted_weight: int
    items: list[AdaptedPreviewItemOut]


# The «Sensorveiledning» block (Story 11.2, FR-81, UX-DR49).


class GuideCriterionOut(BaseModel):
    """One coded criterion, read-only in v1: its code, its wording and its weight in %."""

    code: str
    text: str
    weight: int


class GuideQuestionOut(BaseModel):
    """One question of the Scoring guide as the Lecturer reads it: a long-answer question or an
    Adapted item template, its title, its guide text in force, the default text it derives from,
    whether the two differ («Endret», else «Standard») and its criteria."""

    id: str
    kind: Literal["long", "adapted"]
    title: str
    guide: str
    standard_guide: str
    changed: bool
    criteria: list[GuideCriterionOut]


class ScaleStepOut(BaseModel):
    step: int
    label: str


class ScoringGuideOut(BaseModel):
    """The Class session's Scoring guide in force (Story 11.2): its version id and number,
    whether it is a draft (issue #16), whether it is an edit made for a Class session, whether a
    newer default was published after the edit (`outdated`: the edit stays in force), whether a
    Control test has checked it (`content.service.is_checked`), whether the Test-deadline lock has
    pinned it, whether it can still change (before the original Test deadline), whether the User
    may change it, the one five-step scale and the questions."""

    version_id: uuid.UUID
    version: int
    draft: bool
    edited: bool
    outdated: bool
    checked: bool
    pinned: bool
    open: bool
    can_change: bool
    scale: list[ScaleStepOut]
    questions: list[GuideQuestionOut]


class ScoringGuideIn(BaseModel):
    """«Lagre sensorveiledning»: the guide text of each question the Lecturer changed, by question
    id. The criteria, the scale and the titles never change."""

    model_config = _IN

    guides: Annotated[
        dict[
            Annotated[str, Field(min_length=1, max_length=40)],
            Annotated[str, Field(max_length=GUIDE_TEXT_MAX)],
        ],
        Field(min_length=1, max_length=40),
    ]


class StoredAnswerOut(BaseModel):
    """The Student's saved answer to one item (Story 11.4, AD-10): its value, its revision (the
    highest saved) and when it was saved. No score and no right or wrong state (FR-54)."""

    value: JsonValue
    revision: int
    saved_at: datetime


class TableColumnOut(BaseModel):
    """A given column of a value table: its heading and one number per row."""

    label: str
    values: list[int]


class TableOut(BaseModel):
    """A «Fyll inn kolonnen» item's value table (Story 11.5, FR-80, UX-DR38): its prompt and
    hint, the table's caption, one row label per Uke, the given columns, the asked column's label
    (one answer cell per Uke) and whether a value may be negative. No expected value."""

    prompt: str
    hint: str | None
    caption: str
    rows: list[str]
    columns: list[TableColumnOut]
    asked_label: str
    negative: bool


class ColumnRowOut(BaseModel):
    """A given row of a number item's column."""

    label: str
    value: int


class ColumnOut(BaseModel):
    """A number item's column (Story 11.5): a Starting task item from the Class session's pinned
    Starting task (`starting_task`), or an Interactive number item's own column. Its prompt and
    hint, the column's heading, the given rows, the asked row's label and whether the answer may
    be negative. No expected value and no result."""

    prompt: str
    hint: str | None
    caption: str
    rows: list[ColumnRowOut]
    asked_label: str
    negative: bool
    starting_task: bool


class WordingOut(BaseModel):
    """An Adapted item's text as it travels (Story 11.7, AD-7): code-rendered text has
    `ai_generated` false and no `llm_call_id`; AI-worded text (Story 11.8) names its call."""

    text: str
    ai_generated: bool
    llm_call_id: str | None


class IndividualItemOut(BaseModel):
    """One item of the Student's frozen Individual test (Story 11.3), in order: its number from 1,
    its type and its text; a choice item's option ids (Story 11.4, `[]` for other types), a table
    item's value table or a number item's column (Story 11.5, null otherwise or when the item has
    none) and the Student's saved answer (null before the first save). An Adapted item (Story
    11.7) is answered as a long answer; its `title` is its frozen text, and `wording` carries that
    text with whether an AI wrote it (null for every other type). No weight, no answer key, no
    rule, no fact and no score are sent to the Student."""

    id: str
    number: int
    type: Literal["choice", "table", "number", "long", "adapted"]
    title: str
    options: list[str]
    table: TableOut | None
    column: ColumnOut | None
    wording: WordingOut | None
    answer: StoredAnswerOut | None


TEST_REVISION_MAX = 1_000_000


class TestAnswerIn(BaseModel):
    """One autosave of an item's answer (Story 11.4, AD-10): the value (a choice item: one of its
    option ids; a table item: one whole number or null per row; a number item: a whole number or
    null, Story 11.5; a long-answer item: its text as typed, Story 11.6; an Adapted item: the
    same, Story 11.7) and the answer's revision, which rises by one per change on the Student's
    device."""

    __test__ = False  # not a pytest class
    model_config = _IN

    value: JsonValue
    revision: Annotated[int, Field(strict=True, ge=1, le=TEST_REVISION_MAX)]


class SavedAnswerOut(StoredAnswerOut):
    """The answer stored for the item after a save: the one just sent, or the one with a higher
    revision stored already (then nothing changed, and it is no error)."""

    item_id: str


class MyTestOut(BaseModel):
    """The Student's Individual test (Story 11.3, FR-51): `statement` until they accept the
    own-work statement (no item is served), `open` once they have (the items of their attempt in
    order; the statement is not asked again), `closed` when their Test deadline passed with no
    attempt. `test_deadline` is the Student's effective Test deadline (none set: null);
    `opened_at` when they accepted the statement. Once handed in (Story 11.10), `submitted` by
    the Student or `auto_submitted` at the deadline (Story 11.11), with `submitted_at`: the items
    and saved answers stay readable, never with a score (FR-54).

    In one timed sitting (Story 11.12): `time_limit_minutes` is the Student's own limit (their
    time factor applied, whole minutes rounded up; null when the test is not timed),
    `sitting_ends_at` when their sitting ends once opened, `answering_ends_at` the earlier of that
    and the Test deadline, `server_now` the API's clock for the time left, and `sitting_ended`
    whether the sweep handed the attempt in at the sitting's end."""

    state: Literal["statement", "open", "closed", "submitted", "auto_submitted"]
    test_deadline: datetime | None
    opened_at: datetime | None
    submitted_at: datetime | None
    items: list[IndividualItemOut]
    time_limit_minutes: int | None = None
    sitting_ends_at: datetime | None = None
    answering_ends_at: datetime | None = None
    server_now: datetime
    sitting_ended: bool = False


class DeadlineExtensionIn(BaseModel):
    """«Lagre frist» on the Studentside (Story 11.13, FR-18): the Student's own Test deadline,
    with its time zone. There is no field for a reason."""

    model_config = ConfigDict(extra="forbid")

    test_deadline: AwareDatetime


class ComputedCriterionOut(BaseModel):
    """One coded criterion of an Interactive item as the computed rule scored it (FR-80): met or
    not, and the computed explanation in words."""

    code: str
    met: bool
    explanation: str


class ComputedScoreOut(BaseModel):
    """The computed score of an answer-key or Interactive item (Story 12.2, FR-80), as `tests`
    stored it at the hand-in: `result` is `right` (full credit), `partly` (some), `wrong` (none) or
    `not_answered`; an Interactive item carries each criterion. Never recomputed for the view."""

    result: Literal["right", "partly", "wrong", "not_answered"]
    criteria: list[ComputedCriterionOut]


class FeedbackPartOut(BaseModel):
    """A piece of an item's written feedback (Story 12.3): code-rendered `text`, or a `quote` of
    the Student's own answer, cut from their original text by the stored span."""

    kind: Literal["text", "quote"]
    text: str


class FeedbackOut(BaseModel):
    """An item's written feedback (Story 12.3, FR-54, AD-7): `ai_generated` marks it «KI-generert,
    kan ta feil:»; `text` is the whole with the quotes as «…», `parts` the same in pieces so the
    view sets each quote apart."""

    ai_generated: bool
    text: str
    parts: list[FeedbackPartOut]


class AiScoreOut(BaseModel):
    """The AI's overall score of a long-answer or Adapted item (Story 12.2, FR-54): the step on
    the Scoring guide's five-step scale and its label, or `assessed` false with no step. Story
    12.3: its written feedback when there is one, and `feedback_dropped` when the feedback was
    rejected twice and left out (the score stands)."""

    assessed: bool
    step: int | None
    top: int
    label: str | None
    feedback: FeedbackOut | None = None
    feedback_dropped: bool = False
    flagged: bool = False
    """Story 12.5 (FR-55): the Student marked this feedback as wrong («Marker som feil»)."""


class AssessedItemOut(BaseModel):
    """One item of the Student's «KI-vurdering» in the test's order: its number, type and question
    (an Adapted item's frozen `wording`), its Item weight and its points (the weight times its
    share, null while it has no score), and either its computed score or the AI's score."""

    id: str
    number: int
    type: Literal["choice", "table", "number", "long", "adapted"]
    title: str
    wording: WordingOut | None
    weight: int
    points: float | None
    computed: ComputedScoreOut | None
    ai: AiScoreOut | None


class MyAssessmentOut(BaseModel):
    """The Student's «KI-vurdering» of their Individual test (Story 12.2, FR-54, FR-55, FR-61):

    - `no_test`: they have no attempt in the Class session;
    - `not_ready`: the test is not closed yet, or no run of the assessment has finished;
    - `switched_off`: the Lecturer switched the AI assessment off for the Class session;
    - `incomplete`: some items have no AI score yet; `items` and `unassessed` (their numbers), no
      total;
    - `failed`: no AI assessment could be made; no items, no total;
    - `ready`: every item scored, with `total` out of `total_max` from `analysis.total_score`.

    There is no pass or fail and no letter. Every number is the api's; the web app adds nothing."""

    state: Literal["no_test", "not_ready", "switched_off", "incomplete", "failed", "ready"]
    items: list[AssessedItemOut]
    unassessed: list[int]
    total: float | None
    total_max: int | None
    checked: bool = False
    """Story 12.3 (FR-81, AD-27): whether a Control test has checked the pinned Scoring guide
    version with the assessment's model config (`content.service.is_checked`); while false the
    view says «Ikke kontrollert med en Kontrolltest.»."""


AssessmentState = Literal["no_test", "not_ready", "switched_off", "incomplete", "failed", "ready"]


class StaffAssessmentOut(BaseModel):
    """A Student's «KI-vurdering» as the staff of their Class read it on the Studentside (Story
    12.5, FR-55, AD-12): the Student's own view field by field (same states, items, feedback,
    notes, `flagged` and `checked`). Its own schema, so a field only the Student sees (Story
    12.6's letter choice) is never served here unless added on purpose."""

    state: AssessmentState
    items: list[AssessedItemOut]
    unassessed: list[int]
    total: float | None
    total_max: int | None
    checked: bool = False


class AssessmentRowOut(BaseModel):
    """One Student in the Klasseøkt's list of AI assessments (Story 12.5): their Roster name,
    the state of their assessment as their own view reads it, and how many pieces of feedback they
    flagged."""

    user_id: uuid.UUID
    name: str
    state: AssessmentState
    flags: int


class AssessmentListOut(BaseModel):
    """The Students of the Class session with their AI assessment, by name (Story 12.5)."""

    students: list[AssessmentRowOut]
