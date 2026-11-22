"""The AI assessment (Epic 12). Other modules import only this file.

Story 12.1 (FR-61, AD-9, AD-12): the «KI-vurdering» switch of a Class session. It is on unless a
Lecturer switched it off; «Lagre Klasseøkt» stores it here (`set_switch`) inside the save's
transaction, and `sessions.lock_test` pins it at the original Test deadline (`pin_switch`), once
and idempotently, in the same step that pins what else hangs on that deadline. Once pinned it
never changes (a trigger refuses it too). `assessment_due` is the one question the assessment of
Story 12.2 asks before it assesses anything or calls an LLM: only a pinned switch that is on says
yes, so nothing is assessed before the Test deadline and nothing at all when it is off.

This module imports no feature module: `sessions` calls it, never the other way round."""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assessment.models import assessment_switches
from app.platform.db import get_sessionmaker

__all__ = [
    "DEFAULT_SWITCH",
    "Switch",
    "SwitchPinned",
    "assessment_due",
    "copy_switch",
    "pin_switch",
    "set_switch",
    "switch_of",
]


@dataclass(frozen=True)
class Switch:
    """The «KI-vurdering» switch of a Class session: on or off, and when the Test-deadline lock
    pinned it (None while it can still change)."""

    enabled: bool
    pinned_at: datetime | None

    @property
    def pinned(self) -> bool:
        return self.pinned_at is not None


DEFAULT_SWITCH = Switch(enabled=True, pinned_at=None)
"""A Class session with no row: on, not pinned (FR-61: on by default)."""


class SwitchPinned(Exception):
    """The switch was pinned at the Test deadline and no longer changes."""


async def switch_of(session: AsyncSession, class_session_id: uuid.UUID) -> Switch:
    """The Class session's switch as stored, or `DEFAULT_SWITCH` when nothing is stored."""
    row = (
        await session.execute(
            select(assessment_switches.c.enabled, assessment_switches.c.pinned_at).where(
                assessment_switches.c.class_session_id == class_session_id
            )
        )
    ).first()
    return DEFAULT_SWITCH if row is None else Switch(enabled=row.enabled, pinned_at=row.pinned_at)


async def set_switch(
    session: AsyncSession, class_session_id: uuid.UUID, enabled: bool, *, now: datetime
) -> None:
    """Store the switch in the caller's transaction (the caller holds the Class session's row
    lock). Raises `SwitchPinned` when it is pinned; an unchanged value stores nothing."""
    current = await switch_of(session, class_session_id)
    if current.enabled == enabled:
        return
    if current.pinned:
        raise SwitchPinned
    statement = insert(assessment_switches).values(
        class_session_id=class_session_id, enabled=enabled, updated_at=now
    )
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=[assessment_switches.c.class_session_id],
            set_={"enabled": statement.excluded.enabled, "updated_at": now},
            where=assessment_switches.c.pinned_at.is_(None),
        )
    )


async def pin_switch(session: AsyncSession, class_session_id: uuid.UUID, *, at: datetime) -> bool:
    """Pin the switch as it stands (on when nothing is stored) as of `at`, in the caller's
    transaction: `sessions.lock_test` at the original Test deadline. True when this call pinned
    it; a second call changes nothing and answers False."""
    statement = insert(assessment_switches).values(
        class_session_id=class_session_id, enabled=True, pinned_at=at, updated_at=at
    )
    pinned = await session.execute(
        statement.on_conflict_do_update(
            index_elements=[assessment_switches.c.class_session_id],
            set_={"pinned_at": at, "updated_at": at},
            where=assessment_switches.c.pinned_at.is_(None),
        ).returning(assessment_switches.c.class_session_id)
    )
    return pinned.first() is not None


async def copy_switch(
    session: AsyncSession, source_id: uuid.UUID, target_id: uuid.UUID, *, now: datetime
) -> None:
    """«Lag kopi» (Story 5.18, FR-66): the new Class session takes the source's value, not its
    pin. Nothing is stored when the source's is on, the default."""
    source = await switch_of(session, source_id)
    if not source.enabled:
        await set_switch(session, target_id, False, now=now)


async def assessment_due(
    class_session_id: uuid.UUID, *, session: AsyncSession | None = None
) -> bool:
    """Whether the Class session's Individual tests are to be assessed by the AI: only once the
    Test-deadline lock has pinned the switch, and only when it is on (FR-61, AD-9). Story 12.2's
    assessment asks this before it creates an assessment or makes any LLM call."""
    if session is not None:
        switch = await switch_of(session, class_session_id)
    else:
        async with get_sessionmaker()() as s:
            switch = await switch_of(s, class_session_id)
    return switch.pinned and switch.enabled
