"""Reads and writes of `replays` (Story 10.3), in the caller's session."""

import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.replay.models import replays


async def replay_game(
    session: AsyncSession, user_id: uuid.UUID, class_session_id: uuid.UUID
) -> uuid.UUID | None:
    """The id of the Student's Replay Game in the Class session, or None."""
    return await session.scalar(
        select(replays.c.game_id).where(
            replays.c.user_id == user_id, replays.c.class_session_id == class_session_id
        )
    )


async def insert_replay(
    session: AsyncSession, user_id: uuid.UUID, class_session_id: uuid.UUID, game_id: uuid.UUID
) -> bool:
    """Name `game_id` the Student's Replay in the Class session. False, storing nothing, when they
    have one already: a start that ran at the same moment waits here on the unique key until the
    other commits, then finds its row."""
    result = await session.execute(
        insert(replays)
        .values(
            id=uuid.uuid7(), user_id=user_id, class_session_id=class_session_id, game_id=game_id
        )
        .on_conflict_do_nothing(constraint="uq_replays_student")
        .returning(replays.c.id)
    )
    return result.first() is not None
