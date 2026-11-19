"""SQL for the sessions tables. Only `sessions.service` calls it, after it has checked the User may
read or manage the Class the rows belong to (AD-12)."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import RowMapping, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sessions.models import DATE_NAMES, class_sessions
from app.platform import authz

_number = (
    func.row_number()
    .over(partition_by=class_sessions.c.class_id, order_by=class_sessions.c.id)
    .label("number")
)
"""«Klasseøkt 2»: the place among the Class's sessions, oldest first (UUIDv7 ids sort by
creation). A session is never deleted, so the number stays."""
_numbered = select(class_sessions, _number).subquery()


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


async def number_of(session: AsyncSession, session_id: uuid.UUID, class_id: uuid.UUID) -> int:
    """The Class session's number within its Class."""
    return (
        await session.execute(
            select(func.count())
            .select_from(class_sessions)
            .where(class_sessions.c.class_id == class_id, class_sessions.c.id <= session_id)
        )
    ).scalar_one()


async def sessions_of(session: AsyncSession, class_id: uuid.UUID) -> list[RowMapping]:
    """The Class's sessions, newest first (UUIDv7 ids sort by creation), with their numbers."""
    result = await session.execute(
        select(_numbered.c.id, _numbered.c.number, _numbered.c.created_at, _numbered.c.saved_at)
        .where(_numbered.c.class_id == class_id)
        .order_by(_numbered.c.id.desc())
    )
    return list(result.mappings())


async def enrolled_sessions(session: AsyncSession, user: authz.Principal) -> list[RowMapping]:
    """The sessions of the Classes `user` is a Student in (`authz.classes_enrolled_by`), with
    their numbers: dates and the obligatory mark only, never the Game settings."""
    result = await session.execute(
        select(
            _numbered.c.id,
            _numbered.c.class_id,
            _numbered.c.number,
            _numbered.c.obligatory,
            *(_numbered.c[name] for name in DATE_NAMES),
        )
        .where(_numbered.c.class_id.in_(authz.classes_enrolled_by(user)))
        .order_by(_numbered.c.class_id, _numbered.c.id)
    )
    return list(result.mappings())


async def staff_sessions(
    session: AsyncSession, user: authz.Principal, class_ids: list[uuid.UUID]
) -> list[RowMapping]:
    """The sessions of these Classes that `user` is staff of (`authz.classes_visible_to`), with
    their numbers and dates, oldest first."""
    result = await session.execute(
        select(
            _numbered.c.id,
            _numbered.c.class_id,
            _numbered.c.number,
            *(_numbered.c[name] for name in DATE_NAMES),
        )
        .where(
            _numbered.c.class_id.in_(authz.classes_visible_to(user)),
            _numbered.c.class_id.in_(class_ids),
        )
        .order_by(_numbered.c.class_id, _numbered.c.id)
    )
    return list(result.mappings())


async def save(
    session: AsyncSession,
    session_id: uuid.UUID,
    *,
    now: datetime,
    ai_mode: str,
    model_config_id: uuid.UUID | None,
    dates: dict[str, datetime | None] | None,
    game_settings: dict[str, Any] | None = None,
) -> None:
    values: dict[str, Any] = {**(dates or {})}
    if game_settings is not None:
        values["game_settings"] = game_settings
    await session.execute(
        update(class_sessions)
        .where(class_sessions.c.id == session_id)
        .values(saved_at=now, ai_mode=ai_mode, model_config_id=model_config_id, **values)
    )
