"""The per-endpoint rate limiter and the gateway's clock (AD-6 item 4, NFR-3).

Each endpoint (base URL and key variable) gets one limiter in this process. It spaces the
starts of requests `60 / rpm` seconds apart, `rpm` being the smallest `rate_limit_rpm` of the
configs that used it, and an HTTP 429 pauses the endpoint for every caller. A wait that would
end after the caller's deadline is not taken.

The gateway reads "now" and sleeps only through `clock`, so tests swap in a `SkippingClock`
whose sleeps advance virtual time at once: no test waits for real.
"""

import asyncio
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


class Clock:
    """Real time: wall-clock now, a monotonic reading and `asyncio.sleep`."""

    def now(self) -> datetime:
        return datetime.now(UTC)

    def monotonic(self) -> float:
        return time.monotonic()

    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(max(seconds, 0))


class SkippingClock(Clock):
    """Real time plus skipped seconds: a sleep returns at once and moves both readings forward
    to the moment it would have ended (never back), so waits are checked without waiting
    (tests). `sleeps` records each requested wait."""

    def __init__(self) -> None:
        self.skipped = 0.0
        self.sleeps: list[float] = []

    def now(self) -> datetime:
        return super().now() + timedelta(seconds=self.skipped)

    def monotonic(self) -> float:
        return super().monotonic() + self.skipped

    async def sleep(self, seconds: float) -> None:
        seconds = max(seconds, 0)
        self.sleeps.append(seconds)
        until = self.monotonic() + seconds
        await asyncio.sleep(0)
        self.skipped += max(until - self.monotonic(), 0)


clock: Clock = Clock()
"""The clock the gateway and the limiter read; replaced by `use_clock` in tests."""


@contextmanager
def use_clock(replacement: Clock) -> Iterator[Clock]:
    global clock
    before, clock = clock, replacement
    try:
        yield replacement
    finally:
        clock = before


@dataclass
class _Endpoint:
    rpm: int
    next_start: float = 0.0
    """Monotonic time before which no further request may start."""
    rate_limited: int = 0
    """HTTP 429 answers seen."""
    longest_wait_s: float = 0.0


class Limiter:
    """One spacing schedule per endpoint key."""

    def __init__(self) -> None:
        self._endpoints: dict[tuple[str, str], _Endpoint] = {}

    def _endpoint(self, key: tuple[str, str], rpm: int) -> _Endpoint:
        found = self._endpoints.get(key)
        if found is None:
            found = self._endpoints[key] = _Endpoint(rpm)
        found.rpm = min(found.rpm, rpm)
        return found

    async def acquire(self, key: tuple[str, str], rpm: int, left_s: float | None) -> bool:
        """Wait for the endpoint's next start slot and take it. False, with nothing taken and
        no wait, when the slot comes more than `left_s` seconds from now."""
        endpoint = self._endpoint(key, rpm)
        now = clock.monotonic()
        start = max(now, endpoint.next_start)
        wait = start - now
        if left_s is not None and wait > left_s:
            return False
        endpoint.next_start = start + 60 / endpoint.rpm
        endpoint.longest_wait_s = max(endpoint.longest_wait_s, wait)
        if wait > 0:
            await clock.sleep(wait)
        return True

    def back_off(self, key: tuple[str, str], rpm: int, seconds: float) -> None:
        """The endpoint answered 429: no request starts for `seconds`."""
        endpoint = self._endpoint(key, rpm)
        endpoint.rate_limited += 1
        endpoint.next_start = max(endpoint.next_start, clock.monotonic() + seconds)

    def stats(self, key: tuple[str, str]) -> tuple[int, float]:
        """429 answers seen and the longest wait for a slot, for the endpoint probe."""
        endpoint = self._endpoints.get(key)
        return (0, 0.0) if endpoint is None else (endpoint.rate_limited, endpoint.longest_wait_s)

    def reset(self) -> None:
        self._endpoints.clear()


limiter = Limiter()
"""This process's limiter."""
