"""Retention (Story 15.3, FR-77, FR-65, FR-6, AD-9, AD-14, AD-27).

The sweep's due action `ops.retention`: each Class session whose deletion date (Story 13.9, stored
by `sessions`, the one rule) has come has its Student data deleted through the one shared routine
of `identity.erase_user`, one Student per transaction:

1. the registered per-Class-session aggregate writers run first (`reports.service.write_aggregate`,
   Story 14.3, registers through `identity.register_session_aggregate_writer`); if one fails,
   nothing of the Class session is deleted and the next sweep tries again;
2. each User on the Class's Roster (removed ones too) who was not erased before: a User with no
   other Class session still to run is erased whole (anonymised, as `identity.delete_user` does);
   a User who keeps the account (an account role, a Class staff place, another Class session
   whose data is not deleted, or a Class with no Class session yet) has the same parts run
   scoped to this Class session, and keeps the later data;
3. the Class session is marked (`data_deleted_at`) with one audit row (system actor, ids and
   counts), and once every Class session of the Class is marked, the Roster addresses of people
   who never registered and the Student Invitations not accepted are deleted.

An archived Class that never had a Class session keeps those addresses until its archive time
plus its Institution's retention period (`archived_classes`). A Control test's Class belongs to
the operator-owned Institution, so its deletion date follows that Institution's period.

Every part is idempotent: a sweep interrupted half-way runs again from the start, finds the
erased Users erased and the deleted rows gone, and deletes nothing twice. Logs hold ids and counts
only.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

import structlog

from app.modules.classes import service as classes
from app.modules.identity import service as identity
from app.modules.sessions import service as sessions
from app.platform import audit, retention
from app.platform.db import get_sessionmaker

log = structlog.get_logger(__name__)

SESSION_DATA_DELETED = "class_session.data_deleted"
"""The audit action of retention deleting a Class session's Student data (FR-3): the system
actor, the Class session's id and counts, never a name."""


@dataclass(frozen=True)
class RetentionRun:
    """What one run did for a Class session: `outcome` is `deleted`, `not_due` (gone, already
    marked, or its date not come) or `aggregate_failed` (nothing deleted)."""

    outcome: str
    students: int = 0
    anonymised: int = 0
    kept: int = 0


async def due_sessions(now: datetime) -> Sequence[uuid.UUID]:
    """The Class sessions whose deletion date has come and whose data is not deleted yet."""
    return await sessions.due_retention(now)


async def _keeps_account(user_id: uuid.UUID, class_session_id: uuid.UUID) -> bool:
    """Whether the User keeps the account when this Class session's data goes: they hold an
    account role or a Class staff place, or another Class session of a Class they are (or were)
    on the Roster of has data not yet deleted, or they are on the Roster of a Class that is not
    archived and has no Class session yet."""
    async with get_sessionmaker()() as s:
        if await identity.holds_account_role(s, user_id):
            return True
        if await classes.is_staff_anywhere(s, user_id):
            return True
        entries = await identity.roster_classes_of_user(s, user_id)
        class_ids = sorted({class_id for class_id, _ in entries}, key=str)
        targets = await sessions.retention_targets_of_classes(s, class_ids)
        if any(t.id != class_session_id and t.data_deleted_at is None for t in targets):
            return True
        with_sessions = {t.class_id for t in targets}
        current = [class_id for class_id, removed in entries if not removed]
        waiting = [class_id for class_id in current if class_id not in with_sessions]
        if waiting:
            facts = await classes.class_facts(s, waiting)
            if any(not fact.archived for fact in facts.values()):
                return True
    return False


async def retain(class_session_id: object, now: datetime) -> RetentionRun:
    """Delete the Class session's Student data (the module doc). Returns what it did."""
    assert isinstance(class_session_id, uuid.UUID)
    today = now.astimezone(retention.OSLO).date()
    async with get_sessionmaker()() as s:
        target = await sessions.retention_target(s, class_session_id)
    if (
        target is None
        or target.data_deleted_at is not None
        or target.deletion_date is None
        or target.deletion_date > today
    ):
        return RetentionRun("not_due")
    try:
        written = await identity.write_session_aggregates(class_session_id)
    except Exception as exc:  # the type only: an exception's text may hold personal data
        log.error(
            "retention_aggregate_failed",
            class_session_id=str(class_session_id),
            exc_type=type(exc).__name__,
        )
        return RetentionRun("aggregate_failed")
    if written == 0:
        # Story 14.3 registers `reports.service.write_aggregate`; until then no aggregate exists to
        # write, and retention keeps the Institution's date rather than the data (FR-77).
        log.warning("retention_without_aggregate_writer", class_session_id=str(class_session_id))
    async with get_sessionmaker()() as s:
        students = await identity.roster_user_ids(s, target.class_id)
    anonymised = kept = 0
    for user_id in students:
        async with get_sessionmaker()() as s:
            if await identity.is_erased(s, user_id):
                continue
        if await _keeps_account(user_id, class_session_id):
            await identity.erase_user(user_id, now=now, class_session_id=class_session_id)
            kept += 1
        else:
            await identity.erase_user(user_id, now=now)
            anonymised += 1
    async with get_sessionmaker().begin() as s:
        locked = await sessions.retention_target(s, class_session_id, lock=True)
        if (
            locked is None
            or locked.data_deleted_at is not None
            or locked.deletion_date is None
            or locked.deletion_date > today
        ):
            # A deadline saved during the run moved the date: the session is not marked, and the
            # sweep comes back on the new date.
            return RetentionRun("not_due")
        await sessions.mark_data_deleted(s, class_session_id, now)
        await audit.record(
            s,
            None,
            SESSION_DATA_DELETED,
            {"class_session_id": class_session_id},
            {"students": len(students), "anonymised": anonymised, "kept": kept},
            now,
        )
        purged = await _purge_class_if_done(s, target.class_id)
    log.info(
        "retention_ran",
        class_session_id=str(class_session_id),
        class_id=str(target.class_id),
        students=len(students),
        anonymised=anonymised,
        kept=kept,
        roster_entries_deleted=purged[0],
        invitations_deleted=purged[1],
    )
    return RetentionRun("deleted", len(students), anonymised, kept)


async def _purge_class_if_done(s, class_id: uuid.UUID) -> tuple[int, int]:
    """Once every Class session of the Class is marked deleted, its Roster addresses of people who
    never registered and its Student Invitations not accepted go (FR-77, FR-6)."""
    targets = await sessions.retention_targets_of_classes(s, [class_id])
    if not targets or any(t.data_deleted_at is None for t in targets):
        return (0, 0)
    return await classes.purge_unregistered_roster(s, class_id)


async def archived_classes(now: datetime) -> Sequence[uuid.UUID]:
    """Archived Classes that never had a Class session, whose archive day (Oslo) plus their
    Institution's retention period has come: their Roster addresses of people who never registered
    are kept until then (Story 4.10)."""
    today = now.astimezone(retention.OSLO).date()
    found = []
    async with get_sessionmaker()() as s:
        archived = await classes.archived_classes_before(s, now)
        with_sessions = {
            t.class_id
            for t in await sessions.retention_targets_of_classes(s, [c.id for c in archived])
        }
        for each in archived:
            if each.id in with_sessions:
                continue
            months = await identity.retention_months_of(each.institution_id, s)
            due = retention.add_months(each.archived_at.astimezone(retention.OSLO).date(), months)
            if due <= today and await classes.has_unregistered_roster(s, each.id):
                found.append(each.id)
    return found


async def purge_archived_class(class_id: object, now: datetime) -> tuple[int, int]:
    """Delete the archived Class's Roster addresses of people who never registered and its Student
    Invitations not accepted, in one transaction (idempotent)."""
    assert isinstance(class_id, uuid.UUID)
    async with get_sessionmaker().begin() as s:
        purged = await classes.purge_unregistered_roster(s, class_id)
    log.info(
        "retention_archived_class_purged",
        class_id=str(class_id),
        roster_entries_deleted=purged[0],
        invitations_deleted=purged[1],
    )
    return purged
