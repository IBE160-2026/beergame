"""«Ville du spilt en runde til?» after the Replay-gjennomgang (Story 10.8, FR-50, SM-10).

One optional yes or no per Student and Class session, stored once in `replay_another_round` and
returned only to the Student who gave it. It is asked where the walkthrough is: a closed Replay
(Story 10.6) has none (`replay_closed`), an unfinished one not yet (`replay_not_finished`). The
answer blocks nothing and emits no event (the page that sent it has it). The believability
question beside it belongs to `games` (`games.service.rate_believability`)."""

import uuid

from app.modules.games import service as games_service
from app.modules.replay import repo
from app.modules.replay.schemas import AnotherRoundOut
from app.modules.replay.walkthrough import Unavailable
from app.platform import authz
from app.platform.db import get_sessionmaker

__all__ = ["AlreadyAnswered", "another_round", "answer_another_round"]


class AlreadyAnswered(Exception):
    """The Student has answered already; the first answer stands (409 `already_answered`)."""


async def _own_finished_replay(user: authz.Principal, game_id: str) -> uuid.UUID | None:
    """The Class session of the User's own finished Replay `game_id`; None for any Game that is
    not their Replay. Raises `Unavailable` for a closed or unfinished one."""
    try:
        game_uuid = uuid.UUID(game_id)
    except ValueError:
        return None
    async with get_sessionmaker()() as s:
        owner = await repo.replay_owner(s, game_uuid)
    if owner is None or owner[0] != user.id:
        return None
    game = await games_service.get_game(game_id)
    if game is None:
        return None
    if game.end_reason is not None:
        raise Unavailable("replay_closed")
    if game.lifecycle != games_service.Lifecycle.FINISHED:
        raise Unavailable("replay_not_finished")
    return owner[1]


async def another_round(user: authz.Principal, game_id: str) -> AnotherRoundOut | None:
    """The Student's own answer after their finished Replay, None until given; None (the route's
    403) for any Game that is not their Replay."""
    class_session_id = await _own_finished_replay(user, game_id)
    if class_session_id is None:
        return None
    async with get_sessionmaker()() as s:
        return AnotherRoundOut(answer=await repo.another_round(s, user.id, class_session_id))


async def answer_another_round(
    user: authz.Principal, game_id: str, answer: bool
) -> AnotherRoundOut | None:
    """Store the Student's answer once per Class session. None (403) for any Game that is not
    their Replay; raises `Unavailable` or `AlreadyAnswered`."""
    class_session_id = await _own_finished_replay(user, game_id)
    if class_session_id is None:
        return None
    async with get_sessionmaker().begin() as s:
        stored = await repo.insert_another_round(s, user.id, class_session_id, answer)
    if not stored:
        raise AlreadyAnswered
    return AnotherRoundOut(answer=answer)
