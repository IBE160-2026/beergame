"""What the Debrief routes answer (Stories 9.2 to 9.7, AD-3)."""

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


class DebriefStepOut(BaseModel):
    """A Debrief step after step 1, reached only with a saved Explanation (FR-41, FR-43). Step 2
    carries the reveal (Story 9.4), step 3 the whole chain (Story 9.5), step 4 the own moments
    (Story 9.7); step 5 gets its content with Story 9.9 and until then answers the step number
    only."""

    debrief_id: uuid.UUID
    step: int
    reveal: RevealOut | None = None
    """Step 2 only."""
    chain: ChainOut | None = None
    """Step 3 only."""
    moments: MomentsOut | None = None
    """Step 4 only."""


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
