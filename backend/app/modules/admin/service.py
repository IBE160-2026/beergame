"""Reading the audit log for the Admin (Story 3.12, FR-3, AD-14, AD-15). The rows hold ids only;
names come from the modules that own them, through the labelers registered with
`platform/audit`, at the moment the page is read."""

import base64
import binascii
import uuid
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.modules.admin.schemas import (
    AuditActor,
    AuditActorsOut,
    AuditEventOut,
    AuditListOut,
    AuditTarget,
)
from app.platform import audit
from app.platform.db import get_sessionmaker

OSLO = ZoneInfo("Europe/Oslo")
USER_KEY = "user_id"
"""The target key whose labels also name the actors."""


class InvalidCursor(ValueError):
    """The cursor is not one this list gave out."""


def encode_cursor(event: audit.AuditEvent) -> str:
    raw = f"{event.occurred_at.isoformat()}|{event.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
        at, _, event_id = raw.partition("|")
        occurred_at = datetime.fromisoformat(at)
        if occurred_at.tzinfo is None:
            raise ValueError("a cursor time carries a time zone")
        return occurred_at, uuid.UUID(event_id)
    except (binascii.Error, UnicodeDecodeError, ValueError) as error:
        raise InvalidCursor from error


def day_start(day: date) -> datetime:
    """Midnight in Oslo at the start of `day`, as an aware time."""
    return datetime.combine(day, time(0), OSLO)


def _uuid(value: object) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


async def audit_page(
    *,
    cursor: str | None,
    limit: int,
    actor: uuid.UUID | None = None,
    system: bool = False,
    action: str | None = None,
    since: date | None = None,
    until: date | None = None,
) -> AuditListOut:
    """One page of the log, newest first. `since` and `until` are inclusive Oslo days; `system`
    keeps only the rows with no actor. Raises `InvalidCursor`."""
    after = decode_cursor(cursor) if cursor else None
    async with get_sessionmaker().begin() as s:
        rows = await audit.page(
            s,
            limit=limit + 1,
            after=after,
            actor=audit.SYSTEM if system else actor,
            action=action,
            # The first and last dates a date input allows have no day before or after them:
            # they bound nothing, and computing their midnight would overflow.
            since=day_start(since) if since and since > date.min else None,
            until=day_start(until + timedelta(days=1)) if until and until < date.max else None,
        )
    page = rows[:limit]

    # One labeler call per key for the whole page, not one per row.
    wanted: dict[str, list[uuid.UUID]] = {}
    for event in page:
        for key, value in event.target_ids.items():
            if (found := _uuid(value)) is not None:
                wanted.setdefault(key, []).append(found)
        if event.actor_user_id is not None:
            wanted.setdefault(USER_KEY, []).append(event.actor_user_id)
    names = {key: await audit.labels(key, ids) for key, ids in wanted.items()}
    users = names.get(USER_KEY, {})

    def target(key: str, value: object) -> AuditTarget:
        found = _uuid(value)
        label = names.get(key, {}).get(found) if found is not None else None
        return AuditTarget(key=key, id=str(value), label=label)

    return AuditListOut(
        items=[
            AuditEventOut(
                id=event.id,
                occurred_at=event.occurred_at,
                action=event.action,
                actor_id=event.actor_user_id,
                actor_name=users.get(event.actor_user_id) if event.actor_user_id else None,
                targets=[target(key, value) for key, value in event.target_ids.items()],
                change=dict(event.change),
            )
            for event in page
        ],
        next_cursor=encode_cursor(page[-1]) if len(rows) > limit else None,
    )


async def audit_actors() -> AuditActorsOut:
    """Every actor of the log for the filter: the system first, then the Users by name."""
    async with get_sessionmaker().begin() as s:
        found = await audit.actors(s)
    ids = [actor for actor in found if actor is not None]
    users = await audit.labels(USER_KEY, ids)
    people = sorted(
        (AuditActor(id=actor, name=users.get(actor)) for actor in ids),
        key=lambda a: ((a.name or "").casefold(), str(a.id)),
    )
    system = [AuditActor(id=None, name=None)] if None in found else []
    return AuditActorsOut(items=system + people)
