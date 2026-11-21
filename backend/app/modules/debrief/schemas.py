"""What the Debrief routes answer (Story 9.2, AD-3)."""

import uuid

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
