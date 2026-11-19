"""SQL for the sessions tables. Only `sessions.service` calls it, after it has checked the User may
read or manage the Class the rows belong to (AD-12)."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import RowMapping, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sessions.models import class_sessions


async def insert_session(session: AsyncSession, **values: Any) -> None:
    await session.execute(insert(class_sessions).values(**values))


async def session_row(
    session: AsyncSession, session_id: uuid.UUID, *, lock: bool = False
) -> RowMapping | None:
    """The Class session, or None; with `lock` its row is locked until the transaction ends."""
    query = select(class_sessions).where(class_sessions.c.id == session_id)
    if lock:
        query = query.with_for_update()
    return (await session.execute(query)).mappings().one_or_none()


async def sessions_of(session: AsyncSession, class_id: uuid.UUID) -> list[RowMapping]:
    """The Class's sessions, newest first (UUIDv7 ids sort by creation)."""
    result = await session.execute(
        select(class_sessions.c.id, class_sessions.c.created_at, class_sessions.c.saved_at)
        .where(class_sessions.c.class_id == class_id)
        .order_by(class_sessions.c.id.desc())
    )
    return list(result.mappings())


async def save(
    session: AsyncSession,
    session_id: uuid.UUID,
    *,
    now: datetime,
    ai_mode: str,
    model_config_id: uuid.UUID | None,
) -> None:
    await session.execute(
        update(class_sessions)
        .where(class_sessions.c.id == session_id)
        .values(saved_at=now, ai_mode=ai_mode, model_config_id=model_config_id)
    )
