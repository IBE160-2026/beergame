"""`GET /api/events`: one native SSE stream per logged-in User (AD-8, AD-12, Story 6.4).

Push invalidates, pull reads. The stream sends:

- `ready` once it is subscribed: from then on nothing committed is missed, so the web app reads
  its pages again on a `ready` after a reconnect;
- the default `message` event with data `{topic, id, version}` for each event the User's scope
  allows, and nothing else of the change;
- `heartbeat` every `HEARTBEAT_S`, so the web app can tell quiet from stale (`EventSource` never
  sees SSE comments, so FastAPI's own pings do not do it).

The scope is resolved on connect and again on each `user:<id>` event for the User; if the User is
then deactivated (or the session is older than the User's session version) the stream ends.
`session:<id>` is sent at most once per `COALESCE_S` per id. The stream holds no database session
between those reads, and ends after a random 600 to 780 s so the browser reconnects before the
host's 15-minute request limit.
"""

import asyncio
import random
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.sse import EventSourceResponse, ServerSentEvent
from sqlalchemy import union

from app.platform import auth, authz
from app.platform.db import get_sessionmaker
from app.platform.events.hub import ENDED, Event, Hub, hub

HEARTBEAT_S = 15.0
COALESCE_S = 2.0
LIFETIME_S = (600.0, 780.0)
RETRY_MS = 2000
"""How long the browser waits before it reconnects, sent with `ready`."""


@dataclass(frozen=True)
class Scope:
    """The topics a User's stream forwards besides their own `user:<id>`."""

    games: frozenset[str]
    sessions: frozenset[str]


async def resolve_scope(user_id: uuid.UUID) -> Scope:
    """The User's `game:` and `session:` topics through `platform/authz`, in one short read."""
    async with get_sessionmaker()() as s:
        games = await s.scalars(
            union(authz.seat_held_by(user_id), authz.class_games_staffed_by(user_id))
        )
        sessions = await s.scalars(authz.class_sessions_staffed_by(user_id))
        return Scope(
            frozenset(str(g) for g in games.all()), frozenset(str(x) for x in sessions.all())
        )


StillActive = Callable[[], Awaitable[bool]]
ResolveScope = Callable[[], Awaitable[Scope]]


def allows(user_id: str, scope: Scope, event: Event) -> bool:
    """Whether the User's stream forwards `event` (AD-8's "Forwarded to" column)."""
    if event.topic == "user":
        return event.id == user_id
    if event.topic == "game":
        return event.id in scope.games
    if event.topic == "session":
        return event.id in scope.sessions
    return False  # `debrief:` gets its scope with the Debrief (Epic 9)


async def events(
    user_id: str,
    source: Hub,
    resolve: ResolveScope,
    still_active: StillActive,
    *,
    heartbeat: float | None = None,
    coalesce: float | None = None,
    lifetime: float | None = None,
) -> AsyncIterator[ServerSentEvent]:
    """The stream's events for `user_id`, read from `source`."""
    heartbeat = HEARTBEAT_S if heartbeat is None else heartbeat
    coalesce = COALESCE_S if coalesce is None else coalesce
    lifetime = random.uniform(*LIFETIME_S) if lifetime is None else lifetime
    loop = asyncio.get_running_loop()
    async with source.subscribe() as queue:
        # Resolved once subscribed: an event that arrives meanwhile is judged by the new scope.
        scope = await resolve()
        start = loop.time()
        end = start + lifetime
        next_beat = start + heartbeat
        last_session: dict[str, float] = {}  # session id -> when it was last sent
        pending: dict[str, Event] = {}  # session id -> the event waiting for its window
        yield ServerSentEvent(event="ready", raw_data="", retry=RETRY_MS)
        while True:
            now = loop.time()
            for sid, event in list(pending.items()):
                if now >= last_session[sid] + coalesce:
                    del pending[sid]
                    last_session[sid] = now
                    yield ServerSentEvent(data=event.as_data())
            if now >= end:
                return
            if now >= next_beat:
                next_beat = now + heartbeat
                yield ServerSentEvent(event="heartbeat", raw_data="")
                continue
            due = min([end, next_beat, *(last_session[s] + coalesce for s in pending)])
            try:
                event = await asyncio.wait_for(queue.get(), max(0.0, due - now))
            except TimeoutError:
                continue
            if event is ENDED:
                return
            if event.topic == "user" and event.id == user_id:
                if not await still_active():
                    return
                scope = await resolve()
                # A Class session the User no longer staffs sends nothing more, not even a
                # coalesced event already waiting for its window.
                pending = {sid: e for sid, e in pending.items() if sid in scope.sessions}
            if not allows(user_id, scope, event):
                continue
            if event.topic == "session":
                now = loop.time()
                sent = last_session.get(event.id)
                if sent is not None and now < sent + coalesce:
                    pending[event.id] = event
                    continue
                last_session[event.id] = now
            yield ServerSentEvent(data=event.as_data())


router = APIRouter(prefix="/api")


@router.get("/events", response_class=EventSourceResponse, operation_id="streamEvents")
async def stream_events(
    request: Request,
    user: Annotated[authz.Principal, Depends(authz.require("events.read"))],
) -> AsyncIterator[ServerSentEvent]:
    """The live event stream (AD-8): `ready`, then `{topic, id, version}` for each change the
    User may see, and `heartbeat` every 15 s. 401 without a valid session."""
    session = auth.read_session(request.cookies.get(auth.COOKIE_NAME))
    version = session.version if session else -1

    async def still_active() -> bool:
        return await authz.load_principal(user.id, version) is not None

    async for item in events(str(user.id), hub, lambda: resolve_scope(user.id), still_active):
        yield item
