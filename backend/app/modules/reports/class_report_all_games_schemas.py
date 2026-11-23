"""The answer of «Alle spill side om side» (Story 14.5, FR-86, AD-12, AD-14).

Game numbers, Roles, Weeks and Order amounts only: no name, no `user_id`, no Seat or Game id, no
occupant, no cost and no result, so nothing in it can name, rank or sort a team. A test holds the
field names to this list."""

from pydantic import BaseModel

from app.engine.settings import Role


class GameOrdersOut(BaseModel):
    """One Class game's Orders for one Role, Uke 1 first."""

    number: int
    """The game number, the only key a game has here."""
    own: bool
    """Whether it is the requesting Student's own Class game (`games.student_game`)."""
    orders: list[int | None]
    """`orders[i]` is the Order of Uke `i + 1`; None for a Week with no Order stored."""


class RoleOrdersOut(BaseModel):
    """Every Class game's Orders for one Role, in game-number order."""

    role: Role
    games: list[GameOrdersOut]


class ClassGamesOut(BaseModel):
    """The Class session's Class games side by side, per Role in chain order (Detaljist first)."""

    weeks: int
    """The highest Week with an Order in any listed game; 0 when none has one."""
    own_game: int | None
    """The game number of the Student's own Class game; None when it is not listed."""
    roles: list[RoleOrdersOut]
