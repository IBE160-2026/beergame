"""`platform/ratelimit` on its own (AD-11), with the caller's clock passed in."""

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from starlette.requests import Request

from app.platform import ratelimit
from app.platform.db import get_sessionmaker

WINDOW = timedelta(minutes=15)
T0 = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)


def test_the_window_start_is_aligned_and_holds_now():
    assert ratelimit.window_start(T0 + timedelta(minutes=14, seconds=59), WINDOW) == T0
    assert ratelimit.window_start(T0 + timedelta(minutes=15), WINDOW) == T0 + WINDOW


async def _count(bucket: str, key: str) -> int:
    async with get_sessionmaker().begin() as s:
        rows = (
            await s.execute(
                select(ratelimit.rate_limit_counters.c.count).where(
                    ratelimit.rate_limit_counters.c.bucket == bucket,
                    ratelimit.rate_limit_counters.c.key_hash == ratelimit.key_hash(key),
                )
            )
        ).scalars()
        return sum(rows)


async def test_hit_give_back_reset_and_purge(identity_db):
    async with get_sessionmaker().begin() as s:
        assert await ratelimit.hit(s, "b", "k", window=WINDOW, now=T0) == 1
        assert await ratelimit.hit(s, "b", "k", window=WINDOW, now=T0) == 2
        assert await ratelimit.hit(s, "b", "other", window=WINDOW, now=T0) == 1
        assert await ratelimit.hit(s, "c", "k", window=WINDOW, now=T0) == 1
        await ratelimit.give_back(s, "b", "k", window=WINDOW, now=T0)
    assert await _count("b", "k") == 1
    async with get_sessionmaker().begin() as s:
        # The next window starts from zero, and a hit there deletes the past window's row.
        later = T0 + WINDOW
        assert await ratelimit.hit(s, "b", "k", window=WINDOW, now=later) == 1
        await ratelimit.hit(s, "b", "gone", window=WINDOW, now=T0)
        assert await ratelimit.purge_before(s, later) == 3  # gone, b/other and c/k
        await ratelimit.give_back(s, "b", "k", window=WINDOW, now=later)
        await ratelimit.give_back(s, "b", "k", window=WINDOW, now=later)  # never below zero
    assert await _count("b", "k") == 0
    async with get_sessionmaker().begin() as s:
        await ratelimit.hit(s, "b", "k", window=WINDOW, now=later)
        await ratelimit.reset(s, "b", "k")
    assert await _count("b", "k") == 0


def test_seconds_left_counts_to_the_end_of_the_window():
    assert ratelimit.seconds_left(T0 + timedelta(minutes=10), WINDOW) == 300
    assert ratelimit.seconds_left(T0 + WINDOW - timedelta(milliseconds=1), WINDOW) == 1


async def test_parallel_hits_each_get_their_own_count(identity_db):
    """The count is taken in one atomic upsert, so parallel callers never share a count."""

    async def one() -> int:
        async with get_sessionmaker().begin() as s:
            return await ratelimit.hit(s, "b", "k", window=WINDOW, now=T0)

    counts = await asyncio.gather(*(one() for _ in range(8)))
    assert sorted(counts) == list(range(1, 9))


def _request(headers: dict[str, str], peer: str | None = "192.0.2.1") -> Request:
    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": (peer, 1234) if peer else None,
    }
    return Request(scope)


def test_client_ip_prefers_the_last_forwarded_entry():
    assert ratelimit.client_ip(_request({"X-Forwarded-For": "1.1.1.1, 2.2.2.2"})) == "2.2.2.2"
    assert ratelimit.client_ip(_request({"X-Forwarded-For": " 3.3.3.3 "})) == "3.3.3.3"
    assert ratelimit.client_ip(_request({})) == "192.0.2.1"
    assert ratelimit.client_ip(_request({"X-Forwarded-For": " , "})) == "192.0.2.1"
    assert ratelimit.client_ip(_request({}, peer=None)) == "unknown"
