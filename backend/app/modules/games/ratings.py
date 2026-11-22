"""How believable a Student found the AI players (Story 10.8, FR-70, AD-13, AD-15).

`believability(game_id, user_id)` says whether the Student is asked about a Game and returns
their own answer; `rate_believability` stores it once, with the Game's purpose and the AI mode
its snapshot froze. Whether a Game asks is its policy's `believability`: never, when an AI player
held some Seat in some Week (the Decision log, `seat_weeks`), or always. A Game that has not
finished, or was closed at the Test deadline, asks nobody. The caller has checked that the Game
is the Student's own (`authz.own_seat`); this module never reads or returns anyone else's answer.
The answer is no game state, so it is written here and not by `games.commands`; it emits no event
(the page that sent it has it)."""

import uuid
from collections.abc import Mapping
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.games import repo
from app.modules.games.policy import policy
from app.modules.games.schemas import Believability, Lifecycle, SessionRuntime
from app.platform.db import get_sessionmaker

__all__ = ["BelievabilityRefused", "believability", "rate_believability"]


class BelievabilityRefused(Exception):
    """An answer the api refuses: `not_offered` (the Game asks nobody, or not yet) or
    `already_answered` (the Student's first answer stands); both 409."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


async def _offered(session: AsyncSession, game: Mapping[str, Any]) -> bool:
    if game["lifecycle"] != Lifecycle.FINISHED or game["end_reason"] is not None:
        return False
    if game["session_runtime"] is None:
        return False
    asks = policy(game["purpose"]).believability
    if asks == "ai_held":
        return await repo.ai_held_some_seat(session, game["id"])
    return asks == "always"


async def believability(game_id: uuid.UUID, user_id: uuid.UUID) -> Believability | None:
    """The question of the Game for the Student, or None when the Game does not exist."""
    async with get_sessionmaker()() as s:
        game = await repo.get_game(s, game_id)
        if game is None:
            return None
        return Believability(
            offered=await _offered(s, game),
            rating=await repo.believability_rating(s, game_id, user_id),
        )


async def rate_believability(
    game_id: uuid.UUID, user_id: uuid.UUID, rating: int
) -> Believability | None:
    """Store the Student's answer once (1 to 5, the route has checked it), with the Game's
    purpose and its frozen AI mode. None when the Game does not exist; raises
    `BelievabilityRefused` when it asks nobody or the Student has answered already."""
    async with get_sessionmaker().begin() as s:
        game = await repo.get_game(s, game_id)
        if game is None:
            return None
        if not await _offered(s, game):
            raise BelievabilityRefused("not_offered")
        runtime = SessionRuntime.model_validate(game["session_runtime"])
        stored = await repo.insert_believability_rating(
            s, game_id, user_id, game["purpose"], runtime.ai_mode, rating
        )
    if not stored:
        raise BelievabilityRefused("already_answered")
    return Believability(offered=True, rating=rating)
