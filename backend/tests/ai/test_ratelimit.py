"""Story 2.7: the per-endpoint rate limiter (AD-6 item 4, NFR-3), in virtual time."""

import asyncio

from app.ai import ratelimit
from app.ai.gateway import Failure, Result
from tests.ai.test_adapters import call, endpoint, real_scope, rows, template  # noqa: F401

KEY = ("https://router.example.test/api/v1", "OLSPILLET_TEST_KEY")


async def test_concurrent_calls_start_one_interval_apart(
    ai_db,
    template,  # noqa: F811
    endpoint,  # noqa: F811
    monkeypatch,
):
    granted: list[float] = []
    acquire = ratelimit.limiter.acquire

    async def recorded(*args):
        taken = await acquire(*args)
        granted.append(ratelimit.clock.monotonic())
        return taken

    monkeypatch.setattr(ratelimit.limiter, "acquire", recorded)
    scope = await real_scope(rate_limit_rpm=60)
    results = await asyncio.gather(*(call(scope) for _ in range(3)))
    assert all(isinstance(result, Result) for result in results)
    # The three requests started one minute / 60 apart, in virtual time.
    assert [round(at - granted[0], 1) for at in granted] == [0.0, 1.0, 2.0]
    assert len(endpoint.requests) == 3
    assert len(rows(ai_db)) == 3


async def test_a_slot_after_the_deadline_is_not_waited_for(
    ai_db,
    template,  # noqa: F811
    endpoint,  # noqa: F811
):
    scope = await real_scope(rate_limit_rpm=1)
    assert isinstance(await call(scope), Result)
    slept = len(ratelimit.clock.sleeps)
    result = await call(scope, deadline_s=5.0)  # the next slot is 60 s away
    assert result == Failure("timeout", (), "no request slot before the deadline")
    assert len(ratelimit.clock.sleeps) == slept  # gave up at once, without waiting
    assert len(endpoint.requests) == 1 and len(rows(ai_db)) == 1


async def test_the_smallest_rate_of_an_endpoint_holds_and_back_off_pauses_it():
    limiter = ratelimit.Limiter()
    clock = ratelimit.clock
    assert await limiter.acquire(KEY, 600, None)
    assert await limiter.acquire(KEY, 60, None)  # waits 0.1 s; from now on 60 per minute
    start = clock.monotonic()
    assert await limiter.acquire(KEY, 600, None)
    assert round(clock.monotonic() - start, 1) == 1.0
    limiter.back_off(KEY, 600, 5.0)
    start = clock.monotonic()
    assert await limiter.acquire(KEY, 600, None)
    assert round(clock.monotonic() - start, 1) == 5.0
    assert limiter.stats(KEY)[0] == 1
    assert not await limiter.acquire(KEY, 600, 0.5)  # next slot 1 s away
