"""Postgres-backed rate limits in fixed windows (AD-11, Story 3.2).

A caller counts events per `bucket` (for example `login_ip`, `login_account`) and key. Keys are
stored only as SHA-256 of the key text, so no IP address or e-mail lands in this table (AD-14).
The window start comes from the caller's clock, passed in, so a test controls the window without
reading the database clock.

`hit` counts one event and returns the new count in one atomic upsert, so a caller counts first
and refuses when the count passes its limit; `give_back` takes one back, `reset` forgets a key and
`seconds_left` says when the window ends. The owner decides what counts: login counts every
attempt first, gives a successful one back, and resets the account's count on success.

Rows of past windows for a key are deleted when the key is hit again. Rows of keys that are never
hit again stay until a sweep removes them (`purge_before`, for `ops.sweep` in Story 3.5).
"""

import hashlib
from datetime import datetime, timedelta

from sqlalchemy import Column, DateTime, Integer, Table, Text, delete, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.platform.db import metadata

rate_limit_counters = Table(
    "rate_limit_counters",
    metadata,
    Column("bucket", Text, primary_key=True),
    Column("key_hash", Text, primary_key=True),
    Column("window_start", DateTime(timezone=True), primary_key=True),
    Column("count", Integer, nullable=False),
)
"""Owned by `platform/ratelimit`; one row per bucket, hashed key and window."""


def key_hash(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def window_start(now: datetime, window: timedelta) -> datetime:
    """The start of the fixed window that holds `now`, aligned to the Unix epoch."""
    seconds = int(window.total_seconds())
    epoch = int(now.timestamp())
    return datetime.fromtimestamp(epoch - epoch % seconds, now.tzinfo)


def seconds_left(now: datetime, window: timedelta) -> int:
    """Seconds until the window that holds `now` ends (at least 1)."""
    return max(1, int((window_start(now, window) + window - now).total_seconds()))


async def hit(
    session: AsyncSession, bucket: str, key: str, *, window: timedelta, now: datetime
) -> int:
    """Count one event for the key in the current window; returns the new count. One atomic
    upsert, so concurrent callers each see their own count: a caller that counts first and
    refuses when the count passes its limit cannot be outrun by parallel requests."""
    start = window_start(now, window)
    hashed = key_hash(key)
    await session.execute(
        delete(rate_limit_counters).where(
            rate_limit_counters.c.bucket == bucket,
            rate_limit_counters.c.key_hash == hashed,
            rate_limit_counters.c.window_start < start,
        )
    )
    statement = insert(rate_limit_counters).values(
        bucket=bucket, key_hash=hashed, window_start=start, count=1
    )
    statement = statement.on_conflict_do_update(
        index_elements=["bucket", "key_hash", "window_start"],
        set_={"count": rate_limit_counters.c.count + 1},
    ).returning(rate_limit_counters.c.count)
    return (await session.execute(statement)).scalar_one()


async def give_back(
    session: AsyncSession, bucket: str, key: str, *, window: timedelta, now: datetime
) -> None:
    """Take back one counted event in the current window (an attempt that turned out fine)."""
    await session.execute(
        update(rate_limit_counters)
        .where(
            rate_limit_counters.c.bucket == bucket,
            rate_limit_counters.c.key_hash == key_hash(key),
            rate_limit_counters.c.window_start == window_start(now, window),
            rate_limit_counters.c.count > 0,
        )
        .values(count=rate_limit_counters.c.count - 1)
    )


async def reset(session: AsyncSession, bucket: str, key: str) -> None:
    await session.execute(
        delete(rate_limit_counters).where(
            rate_limit_counters.c.bucket == bucket,
            rate_limit_counters.c.key_hash == key_hash(key),
        )
    )


async def purge_before(session: AsyncSession, cutoff: datetime) -> int:
    """Delete every window that started before `cutoff`; returns the number of rows removed."""
    result = await session.execute(
        delete(rate_limit_counters).where(rate_limit_counters.c.window_start < cutoff)
    )
    return result.rowcount or 0


def client_ip(request: Request) -> str:
    """The client address: the last `X-Forwarded-For` entry, which the proxy in front of the api
    (Caddy) writes, else the socket peer. Caddy replaces a header it does not trust, so a client
    cannot choose its own address."""
    forwarded = request.headers.get("x-forwarded-for", "")
    entries = [part.strip() for part in forwarded.split(",") if part.strip()]
    if entries:
        return entries[-1]
    return request.client.host if request.client else "unknown"
