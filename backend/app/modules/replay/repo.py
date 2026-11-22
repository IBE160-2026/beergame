"""Reads and writes of `replays` (Story 10.3) and `replay_another_round` (Story 10.8), in the
caller's session."""

import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.replay.models import replay_another_round, replays


async def replay_game(
    session: AsyncSession, user_id: uuid.UUID, class_session_id: uuid.UUID
) -> uuid.UUID | None:
    """The id of the Student's Replay Game in the Class session, or None."""
    return await session.scalar(
        select(replays.c.game_id).where(
            replays.c.user_id == user_id, replays.c.class_session_id == class_session_id
        )
    )


async def replay_owner(
    session: AsyncSession, game_id: uuid.UUID
) -> tuple[uuid.UUID, uuid.UUID] | None:
    """The Student and Class session whose Replay `game_id` is, or None for any other Game."""
    row = (
        await session.execute(
            select(replays.c.user_id, replays.c.class_session_id).where(
                replays.c.game_id == game_id
            )
        )
    ).first()
    return None if row is None else (row[0], row[1])


async def replay_games(
    session: AsyncSession, user_ids: list[uuid.UUID], class_session_id: uuid.UUID
) -> dict[uuid.UUID, uuid.UUID]:
    """The Replay Game of each of these Students in the Class session, by Student; one read."""
    if not user_ids:
        return {}
    result = await session.execute(
        select(replays.c.user_id, replays.c.game_id).where(
            replays.c.class_session_id == class_session_id, replays.c.user_id.in_(user_ids)
        )
    )
    return {user_id: game_id for user_id, game_id in result.all()}


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


async def another_round(
    session: AsyncSession, user_id: uuid.UUID, class_session_id: uuid.UUID
) -> bool | None:
    """The Student's another-round answer in the Class session (Story 10.8), or None."""
    return await session.scalar(
        select(replay_another_round.c.answer).where(
            replay_another_round.c.user_id == user_id,
            replay_another_round.c.class_session_id == class_session_id,
        )
    )


async def insert_another_round(
    session: AsyncSession, user_id: uuid.UUID, class_session_id: uuid.UUID, answer: bool
) -> bool:
    """Store the answer once; False, storing nothing, when the Student has one already."""
    result = await session.execute(
        insert(replay_another_round)
        .values(user_id=user_id, class_session_id=class_session_id, answer=answer)
        .on_conflict_do_nothing(index_elements=["user_id", "class_session_id"])
        .returning(replay_another_round.c.answer)
    )
    return result.first() is not None
