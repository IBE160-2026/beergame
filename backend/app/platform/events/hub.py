"""The one `LISTEN` connection per `backend` process (AD-8, Story 6.4).

The hub listens on `CHANNEL` and hands every event to each subscriber's queue in memory; each
`GET /api/events` stream is one subscriber. It starts on the first subscriber. If the connection
fails, every subscriber is ended (its stream closes, the browser reconnects and reads its pages
again), so a lost event is never missed silently; the next subscriber opens a new connection.
"""

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass

import psycopg
import structlog
from sqlalchemy.engine import make_url

from app.platform.config import get_settings
from app.platform.events import CHANNEL, TOPICS

log = structlog.get_logger("app.platform.events")


@dataclass(frozen=True)
class Event:
    """One change event as the stream forwards it: `{topic, id, version}`, never data."""

    topic: str
    id: str
    version: int | None

    def as_data(self) -> dict:
        return {"topic": self.topic, "id": self.id, "version": self.version}


ENDED = None
"""What a subscriber's queue receives when the hub lost its connection or closed."""


def parse(payload: str) -> Event | None:
    """The event in a NOTIFY payload, or None when it is not one AD-8 allows."""
    try:
        data = json.loads(payload)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    topic, id, version = data.get("topic"), data.get("id"), data.get("version")
    if topic not in TOPICS or not isinstance(id, str) or not id:
        return None
    if version is not None and (type(version) is not int or topic != "game"):
        return None
    return Event(topic, id, version)


KEEPALIVES = {
    "keepalives": 1,
    "keepalives_idle": 60,
    "keepalives_interval": 10,
    "keepalives_count": 6,
}


def _dsn() -> str:
    url = make_url(get_settings().database_url).set(drivername="postgresql")
    return url.render_as_string(hide_password=False)


QUEUE_MAX = 1000
"""Events a subscriber may fall behind by. A stream that falls further behind (a stalled tab, a
half-open connection) is ended instead, so its queue cannot grow with every event of the
process; the browser reconnects and reads its pages again on `ready`."""
CONNECT_TIMEOUT_S = 10
"""How long the LISTEN connection may take to connect, so a database that does not answer fails
the stream's start instead of leaving it hanging without `ready`."""


def _end(queue: asyncio.Queue[Event | None]) -> None:
    """Hand `queue` the end, dropping what it still holds if it is full."""
    try:
        queue.put_nowait(ENDED)
    except asyncio.QueueFull:
        while not queue.empty():
            queue.get_nowait()
        queue.put_nowait(ENDED)


class Hub:
    """Fans the events of one LISTEN connection out to its subscribers."""

    def __init__(self, connect: Callable[[], str] = _dsn) -> None:
        self._dsn = connect
        self._queues: set[asyncio.Queue[Event | None]] = set()
        self._task: asyncio.Task | None = None
        self._ready: asyncio.Event | None = None

    @asynccontextmanager
    async def subscribe(self) -> AsyncIterator[asyncio.Queue[Event | None]]:
        """A queue of every event from now on, until the block ends. Returns once the LISTEN
        runs, so nothing committed after this is missed; raises if it cannot be started."""
        queue: asyncio.Queue[Event | None] = asyncio.Queue(QUEUE_MAX)
        self._queues.add(queue)
        try:
            await self._start()
            yield queue
        finally:
            self._queues.discard(queue)

    async def _start(self) -> None:
        if self._task is None or self._task.done():
            self._ready = asyncio.Event()
            self._task = asyncio.create_task(self._listen(self._ready))
        ready, task = self._ready, self._task
        assert ready is not None
        waiter = asyncio.create_task(ready.wait())
        try:
            await asyncio.wait({waiter, task}, return_when=asyncio.FIRST_COMPLETED)
        finally:
            waiter.cancel()
        if not ready.is_set():
            raise ConnectionError("the event listener could not start")

    async def _listen(self, ready: asyncio.Event) -> None:
        try:
            # TCP keepalives: a connection lost without a reset (a network drop, a failover) fails
            # within about two minutes instead of waiting silently for notifications.
            async with await psycopg.AsyncConnection.connect(
                self._dsn(), autocommit=True, connect_timeout=CONNECT_TIMEOUT_S, **KEEPALIVES
            ) as conn:
                await conn.execute(f"LISTEN {CHANNEL}")
                ready.set()
                async for notify in conn.notifies():
                    event = parse(notify.payload)
                    if event is None:
                        log.warning("event_payload_refused", error_code="bad_event_payload")
                        continue
                    for queue in list(self._queues):
                        try:
                            queue.put_nowait(event)
                        except asyncio.QueueFull:
                            # Too far behind: the stream ends and the browser reconnects.
                            self._queues.discard(queue)
                            _end(queue)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.error(
                "event_listener_lost", error_code="listener_lost", exc_type=type(exc).__name__
            )
        finally:
            self._end_all()

    def _end_all(self) -> None:
        for queue in list(self._queues):
            _end(queue)

    async def close(self) -> None:
        """Stop listening (app shutdown); every subscriber is ended."""
        task, self._task = self._task, None
        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError, Exception):
                await task
        self._end_all()


hub = Hub()
"""The process's hub."""
