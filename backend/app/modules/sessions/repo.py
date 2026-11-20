"""SQL for the sessions tables. Only `sessions.service` calls it, after it has checked the User may
read or manage the Class the rows belong to (AD-12)."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import RowMapping, delete, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sessions.models import DATE_NAMES, allocation_drafts, class_sessions, lab_hours
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
    their numbers, dates and whether their allocation is confirmed (`confirmed`),
    oldest first."""
    confirmed = (
        select(allocation_drafts.c.id)
        .where(
            allocation_drafts.c.class_session_id == _numbered.c.id,
            allocation_drafts.c.confirmed_at.is_not(None),
        )
        .exists()
        .label("confirmed")
    )
    result = await session.execute(
        select(
            _numbered.c.id,
            _numbered.c.class_id,
            _numbered.c.number,
            *(_numbered.c[name] for name in DATE_NAMES),
            confirmed,
        )
        .where(
            _numbered.c.class_id.in_(authz.classes_visible_to(user)),
            _numbered.c.class_id.in_(class_ids),
        )
        .order_by(_numbered.c.class_id, _numbered.c.id)
    )
    return list(result.mappings())


async def insert_lab_hour(session: AsyncSession, **values: Any) -> None:
    await session.execute(insert(lab_hours).values(**values))


async def lab_hour_row(
    session: AsyncSession, lab_hour_id: uuid.UUID, *, lock: bool = False
) -> RowMapping | None:
    """The Lab hour, cancelled or not, or None; with `lock` its row is locked."""
    query = select(lab_hours).where(lab_hours.c.id == lab_hour_id)
    if lock:
        query = query.with_for_update()
    return (await session.execute(query)).mappings().one_or_none()


async def lab_hours_of(
    session: AsyncSession, session_ids: list[uuid.UUID], *, ending_after: datetime | None = None
) -> list[RowMapping]:
    """The Lab hours of these Class sessions that were not removed, by start; with
    `ending_after` only those that end after it."""
    if not session_ids:
        return []
    query = select(lab_hours).where(
        lab_hours.c.class_session_id.in_(session_ids), lab_hours.c.cancelled_at.is_(None)
    )
    if ending_after is not None:
        query = query.where(lab_hours.c.ends_at > ending_after)
    query = query.order_by(lab_hours.c.starts_at, lab_hours.c.id)
    return list((await session.execute(query)).mappings())


async def lab_hour_in_progress(
    session: AsyncSession, class_session_id: uuid.UUID, now: datetime
) -> RowMapping | None:
    """The Lab hour of the Class session that is on at `now`, the earliest started if several."""
    result = await session.execute(
        select(lab_hours)
        .where(
            lab_hours.c.class_session_id == class_session_id,
            lab_hours.c.cancelled_at.is_(None),
            lab_hours.c.starts_at <= now,
            lab_hours.c.ends_at > now,
        )
        .order_by(lab_hours.c.starts_at, lab_hours.c.id)
        .limit(1)
    )
    return result.mappings().one_or_none()


async def update_lab_hour(
    session: AsyncSession, lab_hour_id: uuid.UUID, **values: Any
) -> RowMapping:
    """Changes the Lab hour and returns it as stored."""
    result = await session.execute(
        update(lab_hours).where(lab_hours.c.id == lab_hour_id).values(**values).returning(lab_hours)
    )
    return result.mappings().one()


async def save(
    session: AsyncSession,
    session_id: uuid.UUID,
    *,
    now: datetime,
    ai_mode: str,
    model_config_id: uuid.UUID | None,
    effort_level: str | None,
    debrief_mode: str,
    dates: dict[str, datetime | None] | None,
    game_settings: dict[str, Any] | None = None,
    obligatory: bool,
    required_share_percent: int,
    inactivity_limit_hours: int,
) -> None:
    values: dict[str, Any] = {**(dates or {})}
    if game_settings is not None:
        values["game_settings"] = game_settings
    await session.execute(
        update(class_sessions)
        .where(class_sessions.c.id == session_id)
        .values(
            saved_at=now,
            ai_mode=ai_mode,
            model_config_id=model_config_id,
            effort_level=effort_level,
            debrief_mode=debrief_mode,
            obligatory=obligatory,
            required_share_percent=required_share_percent,
            inactivity_limit_hours=inactivity_limit_hours,
            **values,
        )
    )


async def draft_of(session: AsyncSession, class_session_id: uuid.UUID) -> RowMapping | None:
    """The Class session's current allocation draft, or None (Story 5.8)."""
    result = await session.execute(
        select(allocation_drafts).where(allocation_drafts.c.class_session_id == class_session_id)
    )
    return result.mappings().one_or_none()


async def delete_draft(session: AsyncSession, class_session_id: uuid.UUID) -> None:
    """Removes the Class session's draft, if any."""
    await session.execute(
        delete(allocation_drafts).where(allocation_drafts.c.class_session_id == class_session_id)
    )


async def update_draft(session: AsyncSession, class_session_id: uuid.UUID, **values: Any) -> None:
    """Changes the Class session's draft in place, under the same id (Story 5.9)."""
    await session.execute(
        update(allocation_drafts)
        .where(allocation_drafts.c.class_session_id == class_session_id)
        .values(**values)
    )


async def replace_draft(session: AsyncSession, class_session_id: uuid.UUID, **values: Any) -> None:
    """Stores `values` as the Class session's one current draft, removing the one before. The
    caller holds the Class session's row lock, so two draws never race."""
    await delete_draft(session, class_session_id)
    await session.execute(
        insert(allocation_drafts).values(class_session_id=class_session_id, **values)
    )
