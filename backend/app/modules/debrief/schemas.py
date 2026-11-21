"""What the Debrief routes answer (Stories 9.2, 9.3, 9.4, AD-3)."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.engine.settings import Role


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


class DebriefStepOut(BaseModel):
    """A Debrief step after step 1, reached only with a saved Explanation (FR-41, FR-43). Step 2
    carries the reveal (Story 9.4); steps 3 to 5 get their content with Stories 9.5 to 9.9 and
    until then answer the step number only."""

    debrief_id: uuid.UUID
    step: int
    reveal: RevealOut | None = None
    """Step 2 only."""
