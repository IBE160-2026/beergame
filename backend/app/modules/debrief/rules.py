"""Whether a Student's Debrief is open (Story 9.2, FR-42, AD-25): the one rule every Debrief
route, Hjem's Stegene and «Spillet er ferdig» use.

- `not_open`: the Student's game (`games.service.student_game`, the one way to find it) has not
  finished.
- `held`: it has, but the Lecturer holds every Debrief until all Class games have finished, and
  one Game of `games.service.class_games` (Lecturer-overview purposes, so never a test Game) has
  not. Once all have finished the Debrief is open, also before the sweep's release.
- `open` otherwise.

Game status is read only through `games.service`. `sessions` reaches this rule through the
provider registered below, so it never imports `debrief`."""

import uuid
from dataclasses import dataclass
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.games import service as games
from app.modules.sessions import service as sessions
from app.platform import authz
from app.platform.db import get_sessionmaker

State = Literal["open", "not_open", "held"]


async def all_class_games_finished(session: AsyncSession, class_session_id: uuid.UUID) -> bool:
    """Whether every Class game of the session has finished (and there is one)."""
    found = await games.class_games(session, class_session_id)
    return bool(found) and all(game.lifecycle == games.Lifecycle.FINISHED for game in found)


async def state(
    session: AsyncSession, user_id: uuid.UUID, class_session_id: uuid.UUID, hold: bool
) -> State | None:
    """The Student's Debrief state in the Class session, read in the caller's `session`; None
    when they have no Class game there."""
    found = await games.student_game(session, user_id, class_session_id)
    if found is None:
        return None
    if (await games.play_status(session, found.game_id)).status != "finished":
        return "not_open"
    if hold and not await all_class_games_finished(session, class_session_id):
        return "held"
    return "open"


@dataclass(frozen=True)
class Availability:
    """`available`'s answer: the state and, when the Student has one, their game."""

    state: State
    game: games.StudentGame


async def available(user: authz.Principal, class_session_id: uuid.UUID) -> Availability | None:
    """The User's Debrief in the Class session: None when the session is not one of their own
    locked sessions or they have no Class game in it (the routes answer `forbidden`)."""
    async with get_sessionmaker()() as s:
        found = await sessions.debrief_session_of(s, user, class_session_id)
        if found is None:
            return None
        game = await games.student_game(s, user.id, class_session_id)
        if game is None:
            return None
        judged = await state(s, user.id, class_session_id, found.hold)
    if judged is None:
        return None
    return Availability(judged, game)


sessions.register_debrief_state(state)
