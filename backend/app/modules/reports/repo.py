"""Reads and writes of `makeup_games` (Story 13.4), in the caller's session."""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reports.models import makeup_games


@dataclass(frozen=True)
class Makeup:
    """A Student's Oppfølgingsspill: its row id, its Game, who gave it (None once that User is
    deleted) and when."""

    id: uuid.UUID
    game_id: uuid.UUID
    given_by: uuid.UUID | None
    given_at: datetime


async def makeup_of(
    session: AsyncSession, user_id: uuid.UUID, class_session_id: uuid.UUID
) -> Makeup | None:
    """The Student's Oppfølgingsspill in the Class session, or None."""
    row = (
        await session.execute(
            select(
                makeup_games.c.id,
                makeup_games.c.game_id,
                makeup_games.c.given_by,
                makeup_games.c.given_at,
            ).where(
                makeup_games.c.user_id == user_id,
                makeup_games.c.class_session_id == class_session_id,
            )
        )
    ).first()
    return None if row is None else Makeup(*row)


async def makeup_game_of(
    session: AsyncSession, user_id: uuid.UUID, class_session_id: uuid.UUID
) -> uuid.UUID | None:
    """The id of the Student's Oppfølgingsspill Game in the Class session, or None."""
    found = await makeup_of(session, user_id, class_session_id)
    return None if found is None else found.game_id


async def insert_makeup(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    class_session_id: uuid.UUID,
    game_id: uuid.UUID,
    given_by: uuid.UUID,
    given_at: datetime,
) -> uuid.UUID | None:
    """Name `game_id` the Student's Oppfølgingsspill in the Class session and answer the row id.
    None, storing nothing, when they have one already: a press that ran at the same moment waits
    here on the unique key until the other commits, then finds its row."""
    return await session.scalar(
        insert(makeup_games)
        .values(
            id=uuid.uuid7(),
            user_id=user_id,
            class_session_id=class_session_id,
            game_id=game_id,
            given_by=given_by,
            given_at=given_at,
        )
        .on_conflict_do_nothing(index_elements=["user_id", "class_session_id"])
        .returning(makeup_games.c.id)
    )
