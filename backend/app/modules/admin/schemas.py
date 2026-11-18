"""The audit page's envelopes (Story 3.12, FR-3, AD-19)."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

AUDIT_PAGE_DEFAULT = 50
AUDIT_PAGE_MAX = 100
ACTION_MAX_LENGTH = 64


class AuditTarget(BaseModel):
    """One id the action touched: its key in the row (`user_id`, `invitation_id`, …) and what the
    owning module calls it now; `label` is null when no module knows it."""

    key: str
    id: str
    label: str | None


class AuditEventOut(BaseModel):
    """One audit row with names resolved at read time. No actor (`actor_id` null) is the system."""

    id: uuid.UUID
    occurred_at: datetime
    action: str
    actor_id: uuid.UUID | None
    actor_name: str | None
    targets: list[AuditTarget]
    change: dict[str, Any]


class AuditListOut(BaseModel):
    """A page of audit rows in the list envelope, newest first; `next_cursor` is null on the last
    page."""

    items: list[AuditEventOut]
    next_cursor: str | None


class AuditActor(BaseModel):
    """An actor of the log for the filter: a User with their name, or the system (both null)."""

    id: uuid.UUID | None
    name: str | None


class AuditActorsOut(BaseModel):
    items: list[AuditActor]
