"""What the Replay walkthrough answers (Story 10.7, FR-50, AD-7, AD-10), and the another-round
question after it (Story 10.8).

Numbers and code-rendered text only; the web app computes nothing. `pending` carries no data:
the page shows «Gjennomgangen lages.» until the line is worded or the wait limit has passed."""

import uuid
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, StrictBool

from app.engine import Role

_FROZEN = ConfigDict(frozen=True)


class WalkthroughWeekOut(BaseModel):
    """One Uke of a run, as the Seat saw it when it ordered (its Decision log row)."""

    model_config = _FROZEN

    week: int
    net_inventory: int
    """Netto lager: inventory minus backlog."""
    order: int
    """The Seat's Order that Uke («Din ordre»)."""
    total_cost: Decimal
    """Kostnad så langt: the Seat's cost up to and with this Uke."""


class WalkthroughRunOut(BaseModel):
    """One run of the Student's Seat: every Uke, and its Totalkostnad (the last Uke's running
    sum, the facts set's own Total cost of the Role)."""

    model_config = _FROZEN

    weeks: list[WalkthroughWeekOut]
    total_cost: Decimal


class WalkthroughClassGameOut(WalkthroughRunOut):
    """The Student's own Class game, compared with: its number too («Spill 17»)."""

    game_number: int | None


class WalkthroughMomentOut(BaseModel):
    """One own moment of the Replay, rendered by code from its facts set (`analysis.moments`):
    the heading, «Dette regnet du», «Dette kostet det senere» and the pattern (or gap)
    sentences with the mechanism."""

    model_config = _FROZEN

    id: str
    week: int
    order: int
    heading: str
    reckoning: str
    later: str
    patterns: list[str]


class WalkthroughTextOut(BaseModel):
    """The line that ties the moments together (AD-7): `ai_generated` alone decides the
    «KI-generert, kan ta feil:» marking."""

    model_config = _FROZEN

    text: str
    ai_generated: bool = False
    llm_call_id: uuid.UUID | None = None


class ReplayWalkthroughOut(BaseModel):
    """`GET /api/me/games/{game_id}/walkthrough`. `pending`: the line is still being worded;
    only `retry_after_seconds` (the rest of the wait limit) is set. `ready`: the Replay run, the
    Class game beside it (None when that game was played mostly by AI players, `mostly_ai`), the
    moments shown and the line fixed at the Student's first ready view."""

    model_config = _FROZEN

    game_id: uuid.UUID
    role: Role
    state: Literal["pending", "ready"]
    retry_after_seconds: int | None = None
    replay: WalkthroughRunOut | None = None
    class_game: WalkthroughClassGameOut | None = None
    mostly_ai: bool = False
    """The Student's own Class game Seat has fewer than 10 Student Orders (FR-44): no comparison
    of own Orders, and at least three Replay moments."""
    moments: list[WalkthroughMomentOut] = []
    narration: WalkthroughTextOut | None = None


class AnotherRoundOut(BaseModel):
    """Whether the Student would have wanted to play another round (Story 10.8, FR-50, SM-10):
    their own answer, None until they give one. Never anyone else's."""

    model_config = _FROZEN

    answer: bool | None


class AnotherRoundIn(BaseModel):
    """«Send svar» on «Ville du spilt en runde til?»: yes or no."""

    model_config = ConfigDict(extra="forbid")

    answer: StrictBool
