"""The answer of «Alle spill i plenum» (Story 14.6, FR-86, AD-12, AD-14).

Game numbers, Roles, Weeks, Netto lager and Order amounts only: no name, no `user_id`, no Seat or
Game id, no occupant, no status or wait, no cost and no result, so nothing private can reach the
projector by mistake and nothing in it can rank a team. A test holds the field names to this
list."""

from pydantic import BaseModel

from app.engine.settings import Role


class PlenaryGameOut(BaseModel):
    """One Class game's values for one Role, Uke 1 first."""

    number: int
    """The game number, the only key a game has here."""
    net: list[int]
    """`net[i]` is the Netto lager (inventory minus backlog) of Uke `i + 1` as the Oversikt's
    Matrisevegg shows it (the stored Week state), for the game's opened Weeks only: empty before it
    starts."""
    orders: list[int | None]
    """`orders[i]` is the Order of Uke `i + 1`; None for a Week with no Order stored. Always
    `weeks` long."""


class PlenaryRoleOut(BaseModel):
    """Every Class game's values for one Role, in game-number order."""

    role: Role
    games: list[PlenaryGameOut]


class PlenaryOut(BaseModel):
    """The Class session's Class games for the plenary, per Role in chain order (Detaljist
    first)."""

    weeks: int
    """The highest opened Week of any listed game; 0 when none has started."""
    roles: list[PlenaryRoleOut]
