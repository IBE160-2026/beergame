"""What the Debrief routes answer (Stories 9.2 to 9.10, AD-3)."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from app.engine.settings import Role
from app.modules.games import service as games


class DebriefOut(BaseModel):
    """The Student's Debrief session: its id (the `debrief:<id>` topic, AD-8), the game it
    reviews and the step pointer. Never the demand series, the number of Weeks or another
    Seat's numbers (FR-14): those come with the steps that reveal them, after the Explanation."""

    id: uuid.UUID
    class_session_id: uuid.UUID
    game_id: uuid.UUID
    game_number: int | None
    role: Role
    """The Student's own Role in the game."""
    step: int
    """The step pointer, 1 «Skriv Forklaringen først» to 5 «Debrief-quiz»."""
    group: GroupOut | None = None
    """Story 9.11: the Group debrief, None for a Personal debrief."""


class GroupMemberOut(BaseModel):
    """A joined Student of a Group debrief as the other joined Students see them (Story 9.11,
    FR-43): the Roster name now (None once no longer a Student of the Class), whether it is the
    caller, whether their Explanation is sent and whether they have finished the shared step. Never
    the text of their Explanation or answers."""

    name: str | None
    you: bool
    sent: bool
    done: bool


class GroupOut(BaseModel):
    """A Group debrief's shared step pointer (Story 9.11, FR-43): `step` 1 to 3 is shared, 4 means
    each Student works alone from the reflection questions on. `move_on_at` is when the opener may
    move every joined Student on (database time). `members` only for a joined caller, else
    empty. Story 9.12: `opener` is whoever may move on now (the earliest-joined Student still
    there once the opener has gone); `alone` says why the caller goes on as a Personal debrief
    (`left`, `dropout`, `fallback`, `missed`), from shared step `alone_from`; both None
    otherwise."""

    step: int
    joined: bool
    opener: bool
    step_opened_at: datetime | None
    move_on_at: datetime | None
    members: list[GroupMemberOut]
    alone: Literal["left", "dropout", "fallback", "missed"] | None = None
    alone_from: int | None = None


DebriefOut.model_rebuild()


class NetWeekOut(BaseModel):
    """One Uke of the Student's own Netto lager (Story 9.3): inventory minus backlog as their
    Seat saw it when ordering that Uke (the Decision log's `state_seen`)."""

    week: int
    net_inventory: int


class NetInventoryOut(BaseModel):
    """«Ditt netto lager, hele spillet» (Story 9.3, step 1): the Student's own Seat only, every
    logged Uke, oldest first. No demand and no other Seat (FR-14, FR-41)."""

    weeks: list[NetWeekOut]


class ExplanationIn(BaseModel):
    """«Send Forklaring»: the text as typed. It must hold more than white space and at most
    5000 characters (422 `validation_error`)."""

    text: str


class ExplanationOut(BaseModel):
    """A stored Explanation (FR-41, AD-14): the text as typed, its length in characters and when
    it was saved. Never changed after it is stored."""

    text: str
    length: int
    saved_at: datetime


class MyExplanationOut(BaseModel):
    """The Student's own Explanation in this Debrief, or None before it is sent."""

    explanation: ExplanationOut | None


class RevealWeekOut(BaseModel):
    """One Uke of the reveal (Story 9.4): what the customers ordered, the Order that reached the
    Student's own Seat (all they saw) and the Order they placed. From the Game's stored demand
    series and the Seat's own Decision log rows."""

    week: int
    demand: int
    """Kundene: the customers' order in this Uke."""
    incoming_order: int
    """Ordre inn: the Order that reached the Student's Seat («det eneste du så»)."""
    order: int
    """Din ordre: the Order the Seat placed."""


class LargestOrderOut(BaseModel):
    """The Student's largest Order and the first Uke they placed it («Din ordre, 24 i Uke 11»)."""

    week: int
    order: int


class RevealOut(BaseModel):
    """Step 2, the reveal of customer demand (Story 9.4, FR-44, UX-DR32): the heading rendered by
    code from the demand series with the pinned sentence templates, and every logged Uke of the
    Student's own Seat, oldest first. Every number is the api's (AD-10)."""

    heading: str
    template_id: str
    """The sentence template the heading was rendered with (`demand-step` …)."""
    role: Role
    """The Student's own Role."""
    weeks: list[RevealWeekOut]
    largest_order: LargestOrderOut | None


class ChainWeekOut(BaseModel):
    """One Uke of one Role in the whole chain (Story 9.5): its Order and the Week state it saw
    when it ordered (the Decision log's `state_seen`, as the play screen showed it)."""

    week: int
    order: int
    incoming_order: int
    """The Order that reached the Role; for the Detaljist, the customers' order."""
    inventory: int
    backlog: int
    supply_line: int
    """På vei: ordered and not yet received."""


class ChainRoleOut(BaseModel):
    """One Role of the whole chain: every Uke, and from the stored facts set (Story 9.1, AD-7) its
    Forsterkning and the first Uke with an Order of `large_order` or more."""

    role: Role
    amplification: Decimal | None
    """Forsterkning: the spread of the Role's Orders over the spread of customer demand (`7.600`);
    None when customer demand never varied."""
    first_large_order_week: int | None
    capacity: int | None
    """The most the Role could ship per Uke when the Game capped it and `FEATURE_CAPACITY` is on;
    None otherwise."""
    weeks: list[ChainWeekOut]


class ChainOut(BaseModel):
    """Step 3, the whole chain (Story 9.5, FR-44, UX-DR33, UX-DR34): all four Roles, Fabrikk
    first (upstream first, the order the Ordrestolper rows and the scrubber's reading take), each
    with every logged Uke, oldest first. Every number is the api's (AD-10)."""

    own_role: Role
    last_week: int
    """The scrubber's range is Uke 1 to this Uke (the game is finished, so it is no secret)."""
    large_order: int
    """The Order size that marks a Role's first large Order (10, FR-44)."""
    roles: list[ChainRoleOut]


class SharedWeekOut(BaseModel):
    """One Uke of one Role on the shared screen (Story 9.13): its Order and the Week state it saw
    when it ordered (the Decision log's `state_seen`), with its Netto lager."""

    week: int
    order: int
    incoming_order: int
    """The Order that reached the Role; for the Detaljist, the customers' order."""
    inventory: int
    backlog: int
    supply_line: int
    net_inventory: int


class SharedRoleOut(BaseModel):
    """One Role on the shared screen: every Uke, and from the stored facts set (AD-7) its
    Forsterkning and its cost over the whole game, Lager and Restordre apart."""

    role: Role
    amplification: Decimal | None
    holding_cost: Decimal
    backorder_cost: Decimal
    total_cost: Decimal
    weeks: list[SharedWeekOut]


class SharedChainOut(BaseModel):
    """The whole chain as the shared screen draws it: four Roles, Fabrikk first, and the chain's
    cost («Kjeden»)."""

    last_week: int
    holding_cost: Decimal
    backorder_cost: Decimal
    total_cost: Decimal
    roles: list[SharedRoleOut]


class SharedOut(BaseModel):
    """«Delt skjerm: hele kjeden» (Story 9.13, FR-74, AD-21): a Group debrief's shared charts by
    Role, for a joined Student's display. Never a name, a user id, an Explanation, a reflection
    answer, a moment or any free text: the schema has no text field at all. `locked` while a joined
    Student has not sent their Explanation, and then `chain` is None (no demand, no chain data,
    FR-43). `step` is the group's shared pointer."""

    debrief_id: uuid.UUID
    class_session_id: uuid.UUID
    game_number: int | None
    step: int
    locked: bool
    chain: SharedChainOut | None


class RenderedTextOut(BaseModel):
    """Text the Debrief shows as written (AD-7): code-rendered text says `ai_generated` false and
    has no `llm_call_id`, and the web app shows it without the «KI-generert, kan ta feil:» prefix,
    which only `ai_generated` turns on."""

    text: str
    ai_generated: bool = False
    llm_call_id: uuid.UUID | None = None


class OtherSeenOut(BaseModel):
    """What another Role saw in the moment's Uke (the facts set's `others_seen`)."""

    role: Role
    incoming_order: int
    inventory: int
    backlog: int
    supply_line: int


class MomentOut(BaseModel):
    """One own moment (Story 9.7, FR-44): its texts rendered by code from the stored facts set,
    the other Roles' numbers that Uke, and `seen`, the Seat's Week as it saw it when it ordered
    (the Decision log's `state_seen`, for «Dette så du»)."""

    id: str
    """`moment:<role>:<week>`, from the facts set."""
    week: int
    order: int
    chosen_by: Literal["pattern", "order_gap"]
    heading: RenderedTextOut
    reckoning: RenderedTextOut
    """«Dette regnet du»: the Posisjon sum."""
    later: RenderedTextOut
    """«Dette kostet det senere»."""
    patterns: list[RenderedTextOut]
    """Each Detected pattern of the Uke and its mechanism, or the gap sentence when none."""
    others: list[OtherSeenOut]
    """«Dette så de andre i Uke N», in chain order."""
    seen: games.SeatState


class MomentsOut(BaseModel):
    """Step 4, the Student's own moments (Story 9.7, FR-44, UX-DR31), from the facts set stored
    for them (AD-7). With fewer than 10 own Orders the game was played mostly by AI players:
    `mostly_ai`, no heading and no moments; the rest of the Debrief stays open."""

    role: Role
    student_orders: int
    mostly_ai: bool
    heading: RenderedTextOut | None
    """Rendered from the first moment («Ditt øyeblikk: Uke 11. …»)."""
    moments: list[MomentOut]
    """By Uke; three when not `mostly_ai`."""
    narration: RenderedTextOut | None = None
    """Story 9.14: the line that ties the moments together. The AI's (`ai_generated`, with its
    `llm_call_id`) when it was stored before the Student's first view of this step, else the code
    text, fixed from that view on; None without moments."""


class SimulatedRowOut(BaseModel):
    """One «Simulert, samme kunder» row: the chain's cost over the whole simulated Game."""

    counts_supply_line: Literal["own", "all"]
    """`own`: only the viewer's Seat counts På vei; `all`: all four Seats do."""
    holding_cost: Decimal
    backorder_cost: Decimal
    total_cost: Decimal


class SimulatedOut(BaseModel):
    """«Simulert, samme kunder» (Story 9.8, FR-44, UX-DR36): the two rows stored in the facts set,
    played with the Rule-based parameter set `params_id` (placeholders, issues #8, #17)."""

    params_id: str
    rows: list[SimulatedRowOut]
    """`own`, then `all`."""


class BillOut(BaseModel):
    """The Debrief's extra lines under Kjedens regning (Story 9.8, FR-44, UX-DR36), every number
    from the stored facts set of the Student's own Seat (AD-7). The Role rows and Kjedens kostnad
    over tid are the game result's (`/api/me/games/{id}/result`, Story 6.18)."""

    role: Role
    total_cost: Decimal
    """The chain's Total cost."""
    backorder_cost: Decimal
    """The chain's backorder cost."""
    backorder_share_percent: int | None
    """Backorder cost as a whole percent of the chain's Total cost (half up); None when the chain
    cost nothing."""
    backorder_costs_double: bool
    """Whether a unit in backlog costs twice a unit in inventory (the Classic 1,00 and 0,50)."""
    ai_held_cost: Decimal
    """The part of the chain's cost incurred in Weeks a Seat was held by an AI player."""
    ai_held_share_percent: int | None
    """`ai_held_cost` as a whole percent of the Total cost (half up); None when it cost nothing."""
    simulated: SimulatedOut | None
    """None for a facts set stored before the simulation (analysis version 1)."""


class DebriefStepOut(BaseModel):
    """A Debrief step after step 1, reached only with a saved Explanation (FR-41, FR-43). Step 2
    carries the reveal (Story 9.4), step 3 the whole chain (Story 9.5), step 4 the own moments
    (Story 9.7) and the Debrief's lines under Kjedens regning (Story 9.8); step 5, the Debrief quiz,
    has routes of its own (`/quiz`, Story 9.9) and answers the step number only here."""

    debrief_id: uuid.UUID
    step: int
    reveal: RevealOut | None = None
    """Step 2 only."""
    chain: ChainOut | None = None
    """Step 3 only."""
    moments: MomentsOut | None = None
    """Step 4 only."""
    bill: BillOut | None = None
    """Step 4 only."""


class SummaryAnswerOut(BaseModel):
    """A reflection answer as the Debrief summary stored it, with its question's prompt."""

    question_id: str
    prompt: str
    text: str


class SummaryMomentOut(BaseModel):
    """A key moment of the summary, rendered by code from the cited facts set (AD-7)."""

    id: str
    week: int
    heading: RenderedTextOut
    reckoning: RenderedTextOut
    later: RenderedTextOut
    patterns: list[RenderedTextOut]


class SummaryOut(BaseModel):
    """A Student's finished Debrief (Story 9.8, FR-47): the facts set it cites, the key moments,
    the reflection answers in the order asked, when it was finished and whether that was after
    the Student's Debrief deadline (`late`, from the stored time)."""

    fact_set_id: uuid.UUID
    finished_at: datetime
    late: bool
    moments: list[SummaryMomentOut]
    """Empty when the game was played mostly by AI players."""
    reflection: list[SummaryAnswerOut]
    quiz_attempts: int
    """Debrief quiz attempts (Story 9.9): until and with the passing one, or all so far."""
    quiz_passed_at: datetime | None
    """When the passing attempt was stored; None while the quiz is not passed."""


class MySummaryOut(BaseModel):
    """The Student's own Debrief summary, `summary` None until «Fullfør Debriefen»."""

    summary: SummaryOut | None


class StaffAttemptOut(BaseModel):
    """One of a Student's Debrief quiz attempts as the staff see it (Story 9.10): its number,
    time and whether it passed; never the answers."""

    number: int
    submitted_at: datetime
    passed: bool


class StaffQuizAttemptsOut(BaseModel):
    """A Student's Debrief quiz attempts for the Class's staff (Story 9.10, FR-46, FR-47): every
    attempt, oldest first, and when the quiz was passed (None while not)."""

    attempts: list[StaffAttemptOut]
    passed_at: datetime | None


class StaffSummaryOut(BaseModel):
    """A Student's Explanation and Debrief summary for the Class's staff (Story 9.8, FR-47,
    AD-12); each None while not sent or not finished. Story 9.10 adds the Student's Roster name,
    read now and never stored (AD-14; None once they are no longer a Student of the Class), and
    their Debrief quiz attempts."""

    student_id: uuid.UUID
    name: str | None
    game_id: uuid.UUID | None
    game_number: int | None
    role: Role | None
    explanation: ExplanationOut | None
    summary: SummaryOut | None
    quiz: StaffQuizAttemptsOut


class ReflectionAnswerIn(BaseModel):
    """«Fortsett» on a reflection question: the answer as typed. It must hold more than white
    space and at most 2000 characters (422 `validation_error`)."""

    text: str


class ReflectionAnswerOut(BaseModel):
    """A stored reflection answer (FR-45, AD-14): as typed, its length in characters and when it
    was saved. Never changed after it is stored."""

    text: str
    length: int
    saved_at: datetime


class ReflectionQuestionOut(BaseModel):
    """One reflection question (Story 9.6) with the Student's own answer, None until answered."""

    id: str
    kind: Literal["feelings", "evidence", "structure"]
    prompt: str
    hint: str | None
    answer: ReflectionAnswerOut | None


class ReflectionOut(BaseModel):
    """The reflection questions between steps 3 and 4 (Story 9.6, FR-45): the version the Class
    session pinned at the lock, its questions in the order asked (feelings, evidence, structure),
    each with the caller's own answer only (FR-43)."""

    version: int
    questions: list[ReflectionQuestionOut]


class QuizChoiceOut(BaseModel):
    id: str
    text: str


class QuizQuestionOut(BaseModel):
    """A Debrief quiz question as asked (Story 9.9): its prompt and choices in the order shown.
    Never its answer key."""

    id: str
    prompt: str
    choices: list[QuizChoiceOut]


class QuizResultOut(BaseModel):
    """One question of a scored attempt, in the order shown: the Student's choice, the right one
    and, when the choice was wrong, the explanation (the content's text, then the sentence about
    the Student's own Game rendered by code from the facts set of their Seat, AD-7)."""

    question_id: str
    prompt: str
    choices: list[QuizChoiceOut]
    chosen: str
    right_choice: str
    correct: bool
    explanation: RenderedTextOut | None
    ai_explanation: RenderedTextOut | None = None
    """Story 9.14 (FR-46): under a wrong answer's explanation, the AI's line tying it to the
    Student's own Game (always `ai_generated`), when one was stored before this attempt; None
    otherwise, and the content's explanation stands alone."""


class QuizAttemptOut(BaseModel):
    """A scored attempt (Story 9.9, FR-46): its number from 1, when it was stored, how many of the
    asked questions were right and every question with its result."""

    number: int
    submitted_at: datetime
    passed: bool
    correct: int
    asked: int
    results: list[QuizResultOut]


class QuizOut(BaseModel):
    """Step 5, the Debrief quiz (Story 9.9, FR-46, UX-DR37): the version the Class session pinned
    at the lock, whether it is placeholder content (issue #16), the attempts so far and when it was
    passed, the questions of the next attempt (the order may change between attempts; none once
    passed) and the latest attempt's result."""

    version: int
    placeholder: bool
    attempts: int
    passed_at: datetime | None
    questions: list[QuizQuestionOut]
    last: QuizAttemptOut | None


class QuizAnswerIn(BaseModel):
    question_id: str
    choice_id: str


class QuizAttemptIn(BaseModel):
    """An attempt: one answer per asked question, in the order shown (422 `validation_error`
    otherwise)."""

    answers: list[QuizAnswerIn]


class StaffQuizQuestionOut(BaseModel):
    """A Debrief quiz question for the Class's staff (Story 9.10): with its answer key and
    whether it is taken out of the Class session's quiz."""

    id: str
    prompt: str
    choices: list[QuizChoiceOut]
    answer: str
    excluded: bool


class StaffQuizOut(BaseModel):
    """The Debrief quiz of a Class session for its staff (Story 9.10, FR-46, AD-23): the version
    its lock pinned (`pinned` False: the latest, which the lock will pin), the questions in order,
    whether the User may take questions out (`can_exclude`: an owner of a Class that is not
    archived) and whether exclusions can still change (`open`: until the Test deadline)."""

    version: int
    placeholder: bool
    pinned: bool
    can_exclude: bool
    open: bool
    test_deadline: datetime | None
    questions: list[StaffQuizQuestionOut]


class QuizExclusionsIn(BaseModel):
    """«Lagre quizvalg»: the ids of every question to take out; the others are asked."""

    excluded: list[str]


class FollowUpIn(BaseModel):
    """A follow-up question about the Student's own Game (Story 9.15): as typed. It must hold more
    than white space and at most 500 characters (422 `validation_error`)."""

    question: str


class FollowUpAnswerOut(BaseModel):
    """A follow-up question with its answer (Story 9.15, FR-45, AD-7): `answered` carries the hint
    text code rendered from the model's choice of templates and facts, marked by `ai_generated`;
    `declined` (outside the Game) and `unanswered` (no answer could be given: the call failed or
    its output was rejected) carry none, and the web app shows a fixed line. Only `answered` and
    `declined` are stored; `asked_at` is null for `unanswered`."""

    outcome: Literal["answered", "declined", "unanswered"]
    question: str
    answer: RenderedTextOut | None = None
    asked_at: datetime | None = None


class FollowUpOut(BaseModel):
    """The follow-up field under the reflection questions (Story 9.15, FR-45, FR-15): `off` when
    the Class session's Debrief AI text is off, no provider may answer, the pinned templates hold
    no hints or the Seat has no fact to point to (the field is not shown); `closed` after the
    Student's Test deadline or once their Individual test has opened; else `open`. `asked` holds
    the Student's own stored questions, oldest first."""

    state: Literal["off", "open", "closed"]
    asked: list[FollowUpAnswerOut]
