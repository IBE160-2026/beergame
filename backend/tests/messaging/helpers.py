"""Shared pieces of the mail pipeline tests (Story 3.5)."""

import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from app.modules.identity import service as identity
from app.modules.messaging import service
from app.platform import jobs, notify
from app.platform.db import get_sessionmaker
from app.platform.email import senders
from tests.conftest import TEST_DATABASE_URL, kept_connection

OSLO = ZoneInfo("Europe/Oslo")


def oslo(day: int, hour: int, minute: int = 0) -> datetime:
    """A controlled clock in January 2027 (winter time, UTC+1)."""
    return datetime(2027, 1, day, hour, minute, tzinfo=OSLO)


async def user(email: str = "kari@example.no", name: str = "Kari Nordmann", **kw) -> uuid.UUID:
    return await identity.create_user(email=email, name=name, password="hemmelig-passord", **kw)


async def enqueue(
    user_id: uuid.UUID | None,
    kind: str,
    key: str | None = None,
    *,
    ref: uuid.UUID | None = None,
    not_before: datetime | None = None,
) -> bool:
    async with get_sessionmaker().begin() as session:
        return await notify.enqueue(
            session, user_id, kind, key or f"test:{uuid.uuid7()}", ref, not_before
        )


async def drain(now: datetime | None = None) -> None:
    """Run every waiting `mail` job (claims and sends), and the jobs they defer; with `now`, the
    jobs run on that clock instead of this process's."""
    if now is None:
        await jobs.run_until_idle([jobs.MAIL])
        return
    real = service.utcnow
    service.utcnow = lambda: now
    try:
        await jobs.run_until_idle([jobs.MAIL])
    finally:
        service.utcnow = real


def mails() -> list:
    return [mail for _, mail in senders.MOCK.sent]


def rows(sql: str, *params) -> list[tuple]:
    return kept_connection(TEST_DATABASE_URL).execute(sql, params).fetchall()


def deliveries() -> list[tuple]:
    """`(mode, notice count, sent, skipped_reason, attempts)` per delivery, oldest first."""
    return rows(
        "SELECT mode, cardinality(notice_ids), sent_at IS NOT NULL, skipped_reason, attempts "
        "FROM mail_deliveries ORDER BY id"
    )
