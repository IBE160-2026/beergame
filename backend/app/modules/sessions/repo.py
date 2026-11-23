"""SQL for the sessions tables. Only `sessions.service` calls it, after it has checked the User may
read or manage the Class the rows belong to (AD-12)."""

import uuid
from collections.abc import Collection
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import (
    Integer,
    RowMapping,
    Select,
    Text,
    and_,
    case,
    delete,
    exists,
    func,
    insert,
    literal,
    select,
    union_all,
    update,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sessions.models import (
    DATE_NAMES,
    DEADLINE_NAMES,
    allocation_drafts,
    class_sessions,
    deadline_reminders,
    lab_hours,
    student_adjustments,
    student_deadline_extensions,
)
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


def control_test_ids() -> Select[tuple[uuid.UUID]]:
    """The ids of the Control test Class sessions (Story 12.7, AD-27), as a subquery."""
    return select(class_sessions.c.id).where(class_sessions.c.kind == "control_test")


async def control_test_rows(session: AsyncSession) -> list[RowMapping]:
    """Every Control test Class session with its Class's id and creation, newest first."""
    result = await session.execute(
        select(
            class_sessions.c.id,
            class_sessions.c.class_id,
            class_sessions.c.model_config_id,
            class_sessions.c.created_by,
            class_sessions.c.created_at,
        )
        .where(class_sessions.c.kind == "control_test")
        .order_by(class_sessions.c.id.desc())
    )
    return list(result.mappings())


async def session_row(
    session: AsyncSession, session_id: uuid.UUID, *, lock: bool = False, share: bool = False
) -> RowMapping | None:
    """The Class session, or None; with `lock` its row is locked until the transaction ends, with
    `share` it is share-locked (it cannot change or go, others may still read it)."""
    query = select(class_sessions).where(class_sessions.c.id == session_id)
    if lock:
        query = query.with_for_update()
    elif share:
        query = query.with_for_update(read=True)
    return (await session.execute(query)).mappings().one_or_none()


async def class_ids_of(
    session: AsyncSession, session_ids: list[uuid.UUID]
) -> dict[uuid.UUID, uuid.UUID]:
    """The Class of each of these Class sessions, by session id; an unknown id is left out."""
    if not session_ids:
        return {}
    result = await session.execute(
        select(class_sessions.c.id, class_sessions.c.class_id).where(
            class_sessions.c.id.in_(session_ids)
        )
    )
    return {row.id: row.class_id for row in result}


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


async def evaluation_rows(
    session: AsyncSession, ids: list[uuid.UUID] | None = None
) -> list[RowMapping]:
    """The saved Class sessions (or these ones, saved or not) with their numbers, Classes, Start
    dates and Test deadlines, for the Admin's evaluation export (Story 15.4): no User's scope,
    the Admin names Class sessions by id and sees no Student data here."""
    query = select(
        _numbered.c.id,
        _numbered.c.class_id,
        _numbered.c.number,
        _numbered.c.start_at,
        _numbered.c.test_deadline,
        _numbered.c.deletion_date,
    ).order_by(_numbered.c.id.desc())
    if ids is None:
        query = query.where(_numbered.c.saved_at.is_not(None))
    else:
        query = query.where(_numbered.c.id.in_(ids))
    return list((await session.execute(query)).mappings())


async def model_setting_rows(
    session: AsyncSession, ids: list[uuid.UUID] | None = None
) -> list[RowMapping]:
    """The saved Class sessions (or these ones, saved or not) with their model setting, newest
    first, for the Admin's «KI-kostnad» (Story 15.5): AI mode, model config, Effort level, the
    lock and the snapshot's `session_runtime`. No User's scope and no Student data."""
    query = select(
        _numbered.c.id,
        _numbered.c.class_id,
        _numbered.c.number,
        _numbered.c.start_at,
        _numbered.c.locked_at,
        _numbered.c.ai_mode,
        _numbered.c.model_config_id,
        _numbered.c.effort_level,
        _numbered.c.kind,
        _numbered.c.snapshot["session_runtime"].label("session_runtime"),
    ).order_by(_numbered.c.id.desc())
    if ids is None:
        query = query.where(_numbered.c.saved_at.is_not(None))
    else:
        query = query.where(_numbered.c.id.in_(ids))
    return list((await session.execute(query)).mappings())


async def set_model_config(
    session: AsyncSession,
    session_id: uuid.UUID,
    *,
    model_config_id: uuid.UUID,
    effort_level: str | None,
) -> None:
    """The Admin's pin (Story 15.5): the model config and the Effort level in force with it."""
    await session.execute(
        update(class_sessions)
        .where(class_sessions.c.id == session_id)
        .values(model_config_id=model_config_id, effort_level=effort_level)
    )


async def enrolled_sessions(session: AsyncSession, user: authz.Principal) -> list[RowMapping]:
    """The sessions of the Classes `user` is a Student in (`authz.classes_enrolled_by`), with
    their numbers: dates and the obligatory mark, and the settings and the snapshot's settings
    (`snapshot_settings`; never its demand) only so that `service.game_rules` can pick the rules
    the briefing states (Story 6.2); the Student's answer never carries the Game settings. With
    the deletion date Hjem states (Story 13.9)."""
    result = await session.execute(
        select(
            _numbered.c.id,
            _numbered.c.class_id,
            _numbered.c.number,
            _numbered.c.obligatory,
            *(_numbered.c[name] for name in DATE_NAMES),
            _numbered.c.locked_at,
            _numbered.c.allocation_method,
            _numbered.c.debrief_release,
            _numbered.c.debrief_mode,
            _numbered.c.game_settings,
            _numbered.c.snapshot["settings"].label("snapshot_settings"),
            _numbered.c.deletion_date,
        )
        .where(_numbered.c.class_id.in_(authz.classes_enrolled_by(user)))
        .order_by(_numbered.c.class_id, _numbered.c.id)
    )
    return list(result.mappings())


async def session_pins(session: AsyncSession, class_session_id: uuid.UUID) -> Any:
    """The pins the lock stored in the session's snapshot (`session_runtime.pins`, AD-23); None
    before the lock (Story 6.3)."""
    return await session.scalar(
        select(class_sessions.c.snapshot["session_runtime"]["pins"]).where(
            class_sessions.c.id == class_session_id
        )
    )


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
            _numbered.c.locked_at,
            confirmed,
        )
        .where(
            _numbered.c.class_id.in_(authz.classes_visible_to(user)),
            _numbered.c.class_id.in_(class_ids),
        )
        .order_by(_numbered.c.class_id, _numbered.c.id)
    )
    return list(result.mappings())


async def copy_sources(
    session: AsyncSession, user: authz.Principal, class_ids: list[uuid.UUID]
) -> list[RowMapping]:
    """The sessions of these Classes that `user` is staff of (`authz.classes_visible_to`), with
    their numbers and Start dates, newest first: what a rerun may copy (Story 5.18, AD-12)."""
    result = await session.execute(
        select(_numbered.c.id, _numbered.c.class_id, _numbered.c.number, _numbered.c.start_at)
        .where(
            _numbered.c.class_id.in_(authz.classes_visible_to(user)),
            _numbered.c.class_id.in_(class_ids),
        )
        .order_by(_numbered.c.id.desc())
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
    debrief_release: str | None = None,
    debrief_ai_text: bool | None = None,
    game_settings: dict[str, Any] | None = None,
    obligatory: bool,
    required_share_percent: int,
    inactivity_limit_hours: int,
    allocation_method: str | None = None,
    replay: tuple[str, dict[str, Any] | None] | None = None,
) -> None:
    """`replay`, when given, is the Replay scenario choice and its own template (None for the
    default, Story 10.2); None keeps both."""
    values: dict[str, Any] = {**(dates or {})}
    if replay is not None:
        values["replay_scenario"], values["replay_template"] = replay
    if game_settings is not None:
        values["game_settings"] = game_settings
    if allocation_method is not None:
        values["allocation_method"] = allocation_method
    if debrief_release is not None:
        values["debrief_release"] = debrief_release
    if debrief_ai_text is not None:
        values["debrief_ai_text"] = debrief_ai_text
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


async def held_debrief_sessions(session: AsyncSession) -> list[uuid.UUID]:
    """The locked Class sessions whose Lecturer holds every Debrief until all Class games have
    finished (Story 9.2), by id: what the sweep's Debrief release judges."""
    result = await session.execute(
        select(class_sessions.c.id)
        .where(
            class_sessions.c.debrief_release == "hold",
            class_sessions.c.locked_at.is_not(None),
        )
        .order_by(class_sessions.c.id)
    )
    return list(result.scalars())


async def due_locks(session: AsyncSession, now: datetime) -> list[RowMapping]:
    """The Class sessions whose Start date has passed and that are not locked (Story 5.11), by
    id: id, Class and `lock_refused_at`, what the sweep's `sessions.lock` finder judges."""
    result = await session.execute(
        select(class_sessions.c.id, class_sessions.c.class_id, class_sessions.c.lock_refused_at)
        .where(class_sessions.c.start_at <= now, class_sessions.c.locked_at.is_(None))
        .order_by(class_sessions.c.id)
    )
    return list(result.mappings())


async def due_test_locks(session: AsyncSession, now: datetime) -> list[uuid.UUID]:
    """The Class sessions whose original Test deadline has passed and that the Test-deadline lock
    has not run for (Story 12.1), by id."""
    result = await session.execute(
        select(class_sessions.c.id)
        .where(class_sessions.c.test_deadline <= now, class_sessions.c.test_locked_at.is_(None))
        .order_by(class_sessions.c.id)
    )
    return list(result.scalars())


async def passed_play_deadlines(
    session: AsyncSession, now: datetime, among: Collection[uuid.UUID]
) -> list[uuid.UUID]:
    """Of the Class sessions `among`, those whose Play deadline lies at or before `now` (Story
    8.14), by id."""
    if not among:
        return []
    result = await session.execute(
        select(class_sessions.c.id)
        .where(class_sessions.c.id.in_(list(among)), class_sessions.c.play_deadline <= now)
        .order_by(class_sessions.c.id)
    )
    return list(result.scalars())


def test_locked_ids() -> Select[tuple[uuid.UUID]]:
    """The ids of the Class sessions the Test-deadline lock has run for, as a query another
    query can filter by (Story 11.11)."""
    return select(class_sessions.c.id).where(class_sessions.c.test_locked_at.is_not(None))


async def set_test_locked(session: AsyncSession, session_id: uuid.UUID, at: datetime) -> bool:
    """Mark the Test-deadline lock done (Story 12.1), once. True when this call marked it."""
    result = await session.execute(
        update(class_sessions)
        .where(class_sessions.c.id == session_id, class_sessions.c.test_locked_at.is_(None))
        .values(test_locked_at=at)
    )
    return bool(result.rowcount)


async def set_lock_refused(
    session: AsyncSession, session_id: uuid.UUID, at: datetime, reason: str
) -> bool:
    """Mark the first refusal of an unlocked session's lock (GitHub issue 109); a later refusal
    keeps the first time but stores its reason (Story 11.1). True when this call marked it."""
    await session.execute(
        update(class_sessions)
        .where(class_sessions.c.id == session_id, class_sessions.c.locked_at.is_(None))
        .values(lock_refused_reason=reason)
    )
    result = await session.execute(
        update(class_sessions)
        .where(
            class_sessions.c.id == session_id,
            class_sessions.c.locked_at.is_(None),
            class_sessions.c.lock_refused_at.is_(None),
        )
        .values(lock_refused_at=at)
    )
    return bool(result.rowcount)


async def locked_ids(session: AsyncSession, ids: list[uuid.UUID]) -> list[uuid.UUID]:
    """Those of `ids` that are locked Class sessions (Story 5.12)."""
    result = await session.execute(
        select(class_sessions.c.id).where(
            class_sessions.c.id.in_(ids), class_sessions.c.locked_at.is_not(None)
        )
    )
    return list(result.scalars())


async def confirmed_sessions(session: AsyncSession) -> list[RowMapping]:
    """The Class sessions whose allocation is confirmed (Story 5.13), by id: id, Class, Start
    date, `locked_at` and `snapshot`, what the late-seating finders judge."""
    result = await session.execute(
        select(
            class_sessions.c.id,
            class_sessions.c.class_id,
            class_sessions.c.start_at,
            class_sessions.c.locked_at,
            class_sessions.c.snapshot,
            class_sessions.c.allocation_method,
            class_sessions.c.kind,
        )
        .join(allocation_drafts, allocation_drafts.c.class_session_id == class_sessions.c.id)
        .where(allocation_drafts.c.confirmed_at.is_not(None))
        .order_by(class_sessions.c.id)
    )
    return list(result.mappings())


async def open_student_choice_sessions(session: AsyncSession) -> list[RowMapping]:
    """The Class sessions with Student choice that are not locked (Story 5.17), by id: id, Class,
    Start date and `locked_at`, what the sweep's `sessions.offer_student_choice` judges."""
    result = await session.execute(
        select(
            class_sessions.c.id,
            class_sessions.c.class_id,
            class_sessions.c.start_at,
            class_sessions.c.locked_at,
        )
        .where(
            class_sessions.c.allocation_method == "student_choice",
            class_sessions.c.locked_at.is_(None),
        )
        .order_by(class_sessions.c.id)
    )
    return list(result.mappings())


async def set_locked(
    session: AsyncSession, session_id: uuid.UUID, *, locked_at: datetime, snapshot: dict[str, Any]
) -> None:
    await session.execute(
        update(class_sessions)
        .where(class_sessions.c.id == session_id)
        .values(locked_at=locked_at, snapshot=snapshot)
    )


async def draft_of(session: AsyncSession, class_session_id: uuid.UUID) -> RowMapping | None:
    """The Class session's current allocation draft, or None (Story 5.8)."""
    result = await session.execute(
        select(allocation_drafts).where(allocation_drafts.c.class_session_id == class_session_id)
    )
    return result.mappings().one_or_none()


async def drafts_of(
    session: AsyncSession, class_session_ids: list[uuid.UUID]
) -> dict[uuid.UUID, RowMapping]:
    """The current drafts of these Class sessions, by session id (Story 5.17)."""
    if not class_session_ids:
        return {}
    result = await session.execute(
        select(allocation_drafts).where(allocation_drafts.c.class_session_id.in_(class_session_ids))
    )
    return {row["class_session_id"]: row for row in result.mappings()}


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


async def due_deadlines(session: AsyncSession, now: datetime, until: datetime) -> list[RowMapping]:
    """The deadlines in `(now, until]` with no reminder at their current time (Story 5.14): `id`,
    `class_id` and `deadline` (the column name), by session id and deadline order."""
    parts = []
    for order, name in enumerate(DEADLINE_NAMES):
        column = class_sessions.c[name]
        reminded = exists().where(
            deadline_reminders.c.class_session_id == class_sessions.c.id,
            deadline_reminders.c.deadline == name,
            deadline_reminders.c.deadline_at == column,
            deadline_reminders.c.user_id.is_(None),
        )
        parts.append(
            select(
                class_sessions.c.id,
                class_sessions.c.class_id,
                literal(name, Text).label("deadline"),
                literal(order, Integer).label("place"),
            ).where(and_(column > now, column <= until, ~reminded))
        )
    query = union_all(*parts).subquery()
    result = await session.execute(
        select(query.c.id, query.c.class_id, query.c.deadline).order_by(query.c.id, query.c.place)
    )
    return list(result.mappings())


async def insert_reminder(
    session: AsyncSession,
    *,
    class_session_id: uuid.UUID,
    deadline: str,
    deadline_at: datetime,
    now: datetime,
    user_id: uuid.UUID | None = None,
) -> uuid.UUID | None:
    """Records the reminder of `deadline` at `deadline_at` and returns its id, or None when that
    deadline time was reminded before (Story 5.14); with `user_id`, one Student's reminder of their
    own deadline (Story 11.13)."""
    result = await session.execute(
        pg_insert(deadline_reminders)
        .values(
            id=uuid.uuid7(),
            class_session_id=class_session_id,
            deadline=deadline,
            deadline_at=deadline_at,
            created_at=now,
            user_id=user_id,
        )
        .on_conflict_do_nothing(constraint="uq_deadline_reminders_deadline")
        .returning(deadline_reminders.c.id)
    )
    return result.scalar_one_or_none()


async def reminder_row(session: AsyncSession, reminder_id: uuid.UUID) -> RowMapping | None:
    """The deadline reminder, or None (Story 5.14)."""
    result = await session.execute(
        select(deadline_reminders).where(deadline_reminders.c.id == reminder_id)
    )
    return result.mappings().one_or_none()


# Story 11.13: one Student's own Test deadline and the Debrief deadline moved with it.

EXTENDED_DEADLINES = ("debrief_deadline", "test_deadline")
"""The deadlines an extension moves, as `class_sessions` and `student_deadline_extensions` name
them."""


async def extension_row(
    session: AsyncSession, class_session_id: uuid.UUID, user_id: uuid.UUID, *, lock: bool = False
) -> RowMapping | None:
    """The Student's extension in the Class session, or None; with `lock` its row is locked until
    the transaction ends."""
    query = select(student_deadline_extensions).where(
        student_deadline_extensions.c.class_session_id == class_session_id,
        student_deadline_extensions.c.user_id == user_id,
    )
    if lock:
        query = query.with_for_update()
    return (await session.execute(query)).mappings().one_or_none()


async def extensions_of_user(
    session: AsyncSession, user_id: uuid.UUID, class_session_ids: Collection[uuid.UUID]
) -> dict[uuid.UUID, RowMapping]:
    """The Student's extensions in these Class sessions, by session id, in one read."""
    if not class_session_ids:
        return {}
    result = await session.execute(
        select(student_deadline_extensions).where(
            student_deadline_extensions.c.user_id == user_id,
            student_deadline_extensions.c.class_session_id.in_(list(class_session_ids)),
        )
    )
    return {row["class_session_id"]: row for row in result.mappings()}


async def extensions_of_session(
    session: AsyncSession, class_session_id: uuid.UUID
) -> dict[uuid.UUID, RowMapping]:
    """Every extension in the Class session, by Student."""
    result = await session.execute(
        select(student_deadline_extensions).where(
            student_deadline_extensions.c.class_session_id == class_session_id
        )
    )
    return {row["user_id"]: row for row in result.mappings()}


async def save_extension(session: AsyncSession, **values: Any) -> None:
    """Insert or replace the Student's extension: one row per Class session and Student."""
    statement = pg_insert(student_deadline_extensions).values(**values)
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=[
                student_deadline_extensions.c.class_session_id,
                student_deadline_extensions.c.user_id,
            ],
            set_={
                "test_deadline": statement.excluded.test_deadline,
                "debrief_deadline": statement.excluded.debrief_deadline,
                "updated_by": statement.excluded.updated_by,
                "updated_at": statement.excluded.updated_at,
            },
        )
    )


# Story 13.9: the day the Class session's Student data is deleted, and its one reminder.


async def extension_test_deadlines(
    session: AsyncSession, class_session_id: uuid.UUID
) -> list[datetime]:
    """Every Student's own Test deadline in the Class session (Story 11.13)."""
    result = await session.execute(
        select(student_deadline_extensions.c.test_deadline).where(
            student_deadline_extensions.c.class_session_id == class_session_id
        )
    )
    return list(result.scalars())


async def set_deletion_date(
    session: AsyncSession, class_session_id: uuid.UUID, deletion_date: date | None
) -> None:
    """Store the date; a date that moved clears the reminder mark, so the Students are told the
    new date in its window."""
    await session.execute(
        update(class_sessions)
        .where(class_sessions.c.id == class_session_id)
        .values(
            deletion_date=deletion_date,
            deletion_reminded_at=case(
                (
                    class_sessions.c.deletion_date.is_distinct_from(deletion_date),
                    None,
                ),
                else_=class_sessions.c.deletion_reminded_at,
            ),
        )
    )


async def due_deletion_reminders(
    session: AsyncSession, today: date, ahead: timedelta
) -> list[uuid.UUID]:
    """The Class sessions whose deletion date lies after `today` and at most `ahead` away, whose
    Students have not been reminded: by id, the earliest date first."""
    result = await session.execute(
        select(class_sessions.c.id)
        .where(
            class_sessions.c.deletion_date.is_not(None),
            class_sessions.c.deletion_reminded_at.is_(None),
            class_sessions.c.deletion_date > today,
            class_sessions.c.deletion_date <= today + ahead,
        )
        .order_by(class_sessions.c.deletion_date, class_sessions.c.id)
    )
    return list(result.scalars())


async def mark_deletion_reminded(
    session: AsyncSession, class_session_id: uuid.UUID, now: datetime
) -> None:
    await session.execute(
        update(class_sessions)
        .where(class_sessions.c.id == class_session_id)
        .values(deletion_reminded_at=now)
    )


async def due_own_deadlines(
    session: AsyncSession, now: datetime, until: datetime
) -> list[RowMapping]:
    """Each Student's own Debrief or Test deadline in `(now, until]` with no reminder of theirs at
    that time (Story 11.13): `class_session_id`, `class_id`, `user_id`, `deadline` (the column
    name) and `at`. The own deadline is the later of the extension's and the Class session's, and
    only where the Class session has that deadline. Oldest session first."""
    parts = []
    for order, name in enumerate(EXTENDED_DEADLINES):
        own = func.greatest(student_deadline_extensions.c[name], class_sessions.c[name])
        reminded = exists().where(
            deadline_reminders.c.class_session_id == class_sessions.c.id,
            deadline_reminders.c.deadline == name,
            deadline_reminders.c.deadline_at == own,
            deadline_reminders.c.user_id == student_deadline_extensions.c.user_id,
        )
        parts.append(
            select(
                class_sessions.c.id.label("class_session_id"),
                class_sessions.c.class_id,
                student_deadline_extensions.c.user_id,
                literal(name, Text).label("deadline"),
                own.label("at"),
                literal(order, Integer).label("place"),
            )
            .join(
                student_deadline_extensions,
                student_deadline_extensions.c.class_session_id == class_sessions.c.id,
            )
            .where(class_sessions.c[name].is_not(None), own > now, own <= until, ~reminded)
        )
    query = union_all(*parts).subquery()
    result = await session.execute(
        select(
            query.c.class_session_id,
            query.c.class_id,
            query.c.user_id,
            query.c.deadline,
            query.c.at,
        ).order_by(query.c.class_session_id, query.c.user_id, query.c.place)
    )
    return list(result.mappings())


_with_class_share = select(
    student_adjustments, class_sessions.c.required_share_percent.label("class_share")
).join(class_sessions, class_sessions.c.id == student_adjustments.c.class_session_id)
"""A Tilrettelegging row with its Class session's required share, so a read can tell a share
above the class's own (the class lowered it since) from a real adjustment (Story 8.9)."""


async def adjustment_row(
    session: AsyncSession, class_session_id: uuid.UUID, user_id: uuid.UUID
) -> RowMapping | None:
    """The Student's Tilrettelegging in the Class session (Story 8.9), or None."""
    result = await session.execute(
        _with_class_share.where(
            student_adjustments.c.class_session_id == class_session_id,
            student_adjustments.c.user_id == user_id,
        )
    )
    return result.mappings().one_or_none()


async def adjustments_of_user(
    session: AsyncSession, user_id: uuid.UUID, class_session_ids: list[uuid.UUID]
) -> list[RowMapping]:
    """The Student's Tilrettelegging in each of these Class sessions, in one read (Hjem)."""
    if not class_session_ids:
        return []
    result = await session.execute(
        _with_class_share.where(
            student_adjustments.c.user_id == user_id,
            student_adjustments.c.class_session_id.in_(class_session_ids),
        )
    )
    return list(result.mappings())


async def delete_adjustment(
    session: AsyncSession, class_session_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    """«Som klassen» and the class share: no Tilrettelegging is kept (Story 8.9)."""
    await session.execute(
        delete(student_adjustments).where(
            student_adjustments.c.class_session_id == class_session_id,
            student_adjustments.c.user_id == user_id,
        )
    )


async def adjustment_rows(
    session: AsyncSession, class_session_id: uuid.UUID, user_ids: list[uuid.UUID]
) -> list[RowMapping]:
    """The Tilrettelegging of these Students in the Class session, in one read (Story 8.9)."""
    if not user_ids:
        return []
    result = await session.execute(
        select(student_adjustments).where(
            student_adjustments.c.class_session_id == class_session_id,
            student_adjustments.c.user_id.in_(user_ids),
        )
    )
    return list(result.mappings())


async def save_adjustment(session: AsyncSession, **values: Any) -> None:
    """Insert or replace the Student's Tilrettelegging (Story 8.9): one row per Class session and
    Student."""
    statement = pg_insert(student_adjustments).values(**values)
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=[student_adjustments.c.class_session_id, student_adjustments.c.user_id],
            set_={
                "time_factor": statement.excluded.time_factor,
                "share_percent": statement.excluded.share_percent,
                "updated_by": statement.excluded.updated_by,
                "updated_at": statement.excluded.updated_at,
            },
        )
    )


async def delete_adjustments_of(session: AsyncSession, user_id: uuid.UUID) -> None:
    """Drop the Student's Tilrettelegging in every Class session (Story 15.2, FR-76)."""
    await session.execute(
        delete(student_adjustments).where(student_adjustments.c.user_id == user_id)
    )


async def delete_extensions_of(session: AsyncSession, user_id: uuid.UUID) -> None:
    """Drop the Student's own Test and Debrief deadlines in every Class session (Story 15.2 after
    Story 11.13)."""
    await session.execute(
        delete(student_deadline_extensions).where(student_deadline_extensions.c.user_id == user_id)
    )
