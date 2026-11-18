"""The audit log of Admin and system actions (FR-3, AD-15, NFR-7, Story 3.7).

A module calls `record(session, actor, action, target, change, at)` inside the transaction of the
action itself, so the row commits with the action or not at all: exactly one row per action.

- `actor` is the acting User's id, or None when the system acts (the bootstrap Invitation of
  Story 3.8).
- `action` is a dotted name such as `invitation.sent`.
- `target` names the ids the action touched (`{"invitation_id": …}`); `change` holds what changed
  (`{"role": "lecturer"}`). Both are ids and codes only: a name or an e-mail address never lands
  here (AD-14). `record` refuses any string holding `@`.
- `at` comes from the caller's clock; nothing here reads the database clock.

There is no update or delete: a trigger refuses both (migration 0018). Rows have no foreign key,
so the history outlives anything it names. Reading the log for the Admin comes with Story 3.12.
This module imports no `app.modules` code.
"""

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, Index, Table, Text, Uuid, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.db import metadata

__all__ = ["AuditEvent", "audit_events", "events_for_target", "record"]

audit_events = Table(
    "audit_events",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("actor_user_id", Uuid, nullable=True),
    Column("action", Text, nullable=False),
    Column("target_ids", JSONB, nullable=False),
    Column("change", JSONB, nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Index("ix_audit_events_occurred_at", "occurred_at"),
)
"""Owned by `platform/audit`. Append-only; ids and codes only."""


@dataclass(frozen=True)
class AuditEvent:
    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    action: str
    target_ids: Mapping[str, Any]
    change: Mapping[str, Any]
    occurred_at: datetime


def _plain(value: Any) -> Any:
    """`value` as JSON, with ids as text; refuses anything that looks like an e-mail address."""
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, str):
        if "@" in value:
            raise ValueError("an audit row holds ids and codes, never an e-mail address")
        return value
    if isinstance(value, Mapping):
        return {str(_plain(k)): _plain(v) for k, v in value.items()}
    if isinstance(value, Sequence):
        return [_plain(v) for v in value]
    if value is None or isinstance(value, bool | int | float):
        return value
    raise TypeError(f"an audit value must be an id, a code or a number, not {type(value)}")


async def record(
    session: AsyncSession,
    actor: uuid.UUID | None,
    action: str,
    target: Mapping[str, Any],
    change: Mapping[str, Any],
    at: datetime,
) -> uuid.UUID:
    """Write one audit row in the caller's transaction; returns its id."""
    if not action:
        raise ValueError("an audit row names its action")
    if at.tzinfo is None:
        raise ValueError("at must carry a time zone")
    event_id = uuid.uuid7()
    await session.execute(
        audit_events.insert().values(
            id=event_id,
            actor_user_id=actor,
            action=action,
            target_ids=_plain(target),
            change=_plain(change),
            occurred_at=at,
        )
    )
    return event_id


async def events_for_target(session: AsyncSession, key: str, value: uuid.UUID) -> list[AuditEvent]:
    """The rows whose `target_ids[key]` is `value`, oldest first."""
    result = await session.execute(
        select(audit_events)
        .where(audit_events.c.target_ids[key].astext == str(value))
        .order_by(audit_events.c.occurred_at, audit_events.c.id)
    )
    return [AuditEvent(**row) for row in result.mappings()]
