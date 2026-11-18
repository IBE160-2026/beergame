"""Notices: the one way a module asks for someone to be told (AD-9, AD-8, AD-14, Story 3.5).

A module calls `enqueue(session, user_id, kind, dedupe_key, ref, not_before)` inside its own
transaction. That writes one `notices` row, unique on `dedupe_key`, holding ids only, and:

- with a `user_id`, emits `user:<id>` (AD-8), so the app can show the notice at once;
- with `user_id=None`, names its recipient by reference: `ref` is the id of the record that holds
  the address (an Invitation id, say). The kind's entry in `messaging`'s delivery table names the
  owning module's resolver; the address is never copied here, and nothing is emitted;
- defers the claim job `CLAIM_TASK` for the notice by its registered name, on the caller's
  connection, so the job commits with the notice or not at all. The claim job (`messaging`)
  sends a due notice of an `immediate` kind at once and leaves every other notice to the sweep.

`messaging` is the only reader: it claims notices with `claim_due` and reads claimed ones with
`get`. This package imports no module; it knows the claim task by name only.

Times are passed in (`now`, `not_before`) from the caller's clock; nothing here compares them
with the database clock. A NULL `not_before` means due at once.
"""

import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Table,
    Text,
    Uuid,
    and_,
    func,
    or_,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform import events, jobs
from app.platform.db import metadata

__all__ = [
    "CLAIM_TASK",
    "Notice",
    "claim_due",
    "due",
    "enqueue",
    "get",
    "notices",
]

CLAIM_TASK = "messaging.claim_notice"
"""The task `enqueue` defers per notice (registered by `modules/messaging/jobs.py`)."""

notices = Table(
    "notices",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
    Column("kind", Text, nullable=False),
    Column("dedupe_key", Text, nullable=False, unique=True),
    Column("ref", Uuid, nullable=True),
    Column("not_before", DateTime(timezone=True), nullable=True),
    Column("claimed_at", DateTime(timezone=True), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("user_id IS NOT NULL OR ref IS NOT NULL", name="ck_notices_recipient"),
    Index("ix_notices_unclaimed", "kind", "not_before", postgresql_where="claimed_at IS NULL"),
)
"""Owned by `platform/notify`. Ids only: no name, address, link or free text (AD-14)."""


@dataclass(frozen=True)
class Notice:
    id: uuid.UUID
    user_id: uuid.UUID | None
    kind: str
    ref: uuid.UUID | None
    not_before: datetime | None


def _notice(row) -> Notice:
    return Notice(
        id=row["id"],
        user_id=row["user_id"],
        kind=row["kind"],
        ref=row["ref"],
        not_before=row["not_before"],
    )


_COLUMNS = (
    notices.c.id,
    notices.c.user_id,
    notices.c.kind,
    notices.c.ref,
    notices.c.not_before,
)


async def enqueue(
    session: AsyncSession,
    user_id: uuid.UUID | None,
    kind: str,
    dedupe_key: str,
    ref: uuid.UUID | None = None,
    not_before: datetime | None = None,
) -> bool:
    """Ask for `user_id` (or the recipient `ref` names) to be told about `kind`, in the caller's
    transaction. Returns False, and changes nothing, when `dedupe_key` was used before."""
    if user_id is None and ref is None:
        raise ValueError("a notice names its recipient by user_id or by ref")
    if not kind or not dedupe_key:
        raise ValueError("a notice has a kind and a dedupe_key")
    if not_before is not None and not_before.tzinfo is None:
        raise ValueError("not_before must carry a time zone")
    notice_id = uuid.uuid7()
    result = await session.execute(
        insert(notices)
        .values(
            id=notice_id,
            user_id=user_id,
            kind=kind,
            dedupe_key=dedupe_key,
            ref=ref,
            not_before=not_before,
        )
        .on_conflict_do_nothing(index_elements=[notices.c.dedupe_key])
        .returning(notices.c.id)
    )
    if result.scalar_one_or_none() is None:
        return False
    if user_id is not None:
        await events.emit(session, "user", str(user_id))
    await jobs.defer(
        session,
        CLAIM_TASK,
        queue=jobs.MAIL,
        queueing_lock=f"notice:{notice_id}",
        notice_id=str(notice_id),
    )
    return True


def _due(now: datetime):
    return and_(
        notices.c.claimed_at.is_(None),
        or_(notices.c.not_before.is_(None), notices.c.not_before <= now),
    )


async def due(session: AsyncSession, now: datetime, kinds: Iterable[str]) -> list[Notice]:
    """The unclaimed notices of `kinds` that are due at `now`, oldest first (read only)."""
    kinds = list(kinds)
    if not kinds:
        return []
    result = await session.execute(
        select(*_COLUMNS).where(_due(now), notices.c.kind.in_(kinds)).order_by(notices.c.id)
    )
    return [_notice(row) for row in result.mappings()]


async def claim_due(
    session: AsyncSession,
    now: datetime,
    *,
    kinds: Iterable[str],
    notice_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
) -> list[Notice]:
    """Claim the unclaimed notices of `kinds` due at `now`, narrowed to one notice or one User,
    and return them. Rows another transaction holds are skipped, so two claimers never get the
    same notice; a claimed notice is never claimed again."""
    kinds = list(kinds)
    if not kinds:
        return []
    picked = select(notices.c.id).where(_due(now), notices.c.kind.in_(kinds))
    if notice_id is not None:
        picked = picked.where(notices.c.id == notice_id)
    if user_id is not None:
        picked = picked.where(notices.c.user_id == user_id)
    picked = picked.with_for_update(skip_locked=True)
    result = await session.execute(
        update(notices)
        .where(notices.c.id.in_(picked.scalar_subquery()))
        .values(claimed_at=now)
        .returning(*_COLUMNS)
    )
    return sorted((_notice(row) for row in result.mappings()), key=lambda n: n.id)


async def get(session: AsyncSession, ids: Sequence[uuid.UUID]) -> list[Notice]:
    """The notices with `ids`, in id order (claimed ones included)."""
    if not ids:
        return []
    result = await session.execute(
        select(*_COLUMNS).where(notices.c.id.in_(list(ids))).order_by(notices.c.id)
    )
    return [_notice(row) for row in result.mappings()]
