"""The live event stream (Story 6.4, AD-8): the hub's one LISTEN connection, the per-User
stream's scope, coalescing, heartbeat, lifetime and deactivation, and `GET /api/events` end to
end. Timings are shortened for the tests; every wait awaits an event, none sleeps."""

import asyncio
import json
import uuid
from contextlib import asynccontextmanager

import pytest
from sqlalchemy import text

from app.platform import events as platform_events
from app.platform.db import get_sessionmaker
from app.platform.events import stream
from app.platform.events.hub import ENDED, Event, Hub, parse
from tests.classes.test_classes import LECTURER, PASSWORD
from tests.classes.test_roster_upload import clock, klass
from tests.conftest import TEST_DATABASE_URL
from tests.games.helpers import execute
from tests.identity.helpers import app, client, login
from tests.messaging.helpers import rows
from tests.sessions.test_lock import _empty
from tests.sessions.test_open_games import confirmed, games_of

__all__ = ["_empty", "clock", "klass"]

ME = str(uuid.uuid7())
GAME, OTHER_GAME = str(uuid.uuid7()), str(uuid.uuid7())
SESSION = str(uuid.uuid7())
SCOPE = stream.Scope(games=frozenset({GAME}), sessions=frozenset({SESSION}))
STUDENT_SCOPE = stream.Scope(games=frozenset({GAME}), sessions=frozenset())


class FakeHub:
    def __init__(self) -> None:
        self.queue: asyncio.Queue = asyncio.Queue()

    @asynccontextmanager
    async def subscribe(self):
        yield self.queue

    def put(self, topic: str, id: str, version: int | None = None) -> None:
        self.queue.put_nowait(Event(topic, id, version))


async def active() -> bool:
    return True


def opened(source, scope=SCOPE, still_active=active, **timings):
    async def resolve():
        return scope

    timings = {"heartbeat": 30.0, "coalesce": 30.0, "lifetime": 60.0, **timings}
    return stream.events(ME, source, resolve, still_active, **timings)


async def next_of(gen):
    return await asyncio.wait_for(anext(gen), 2)


def data(event) -> dict:
    return event.data


async def test_ready_comes_first_then_only_what_the_scope_allows():
    source = FakeHub()
    gen = opened(source, STUDENT_SCOPE)
    ready = await next_of(gen)
    assert ready.event == "ready" and ready.retry == stream.RETRY_MS
    source.put("session", SESSION)  # a Student never gets `session:` (AD-8)
    source.put("game", OTHER_GAME, 4)  # not their game
    source.put("user", str(uuid.uuid7()))  # another User
    source.put("debrief", str(uuid.uuid7()))  # no Debrief scope yet
    source.put("game", GAME, 5)
    assert data(await next_of(gen)) == {"topic": "game", "id": GAME, "version": 5}
    source.put("user", ME)
    assert data(await next_of(gen)) == {"topic": "user", "id": ME, "version": None}
    await gen.aclose()


async def test_staff_get_their_class_session():
    source = FakeHub()
    gen = opened(source)
    await next_of(gen)
    source.put("session", SESSION)
    assert data(await next_of(gen)) == {"topic": "session", "id": SESSION, "version": None}
    await gen.aclose()


async def test_a_heartbeat_comes_when_nothing_else_does():
    gen = opened(FakeHub(), heartbeat=0.05)
    await next_of(gen)
    beat = await next_of(gen)
    assert beat.event == "heartbeat" and beat.data is None
    assert (await next_of(gen)).event == "heartbeat"
    await gen.aclose()


async def test_each_heartbeat_runs_the_presence_hooks():
    """Story 9.12: `beat` runs before each heartbeat; `events.heartbeat` runs every registered
    hook with the User's id, and one that fails neither stops the others nor raises."""
    beats: list[int] = []

    async def beat() -> None:
        beats.append(1)

    gen = opened(FakeHub(), heartbeat=0.05, beat=beat)
    await next_of(gen)
    assert (await next_of(gen)).event == "heartbeat" and beats == [1]
    assert (await next_of(gen)).event == "heartbeat" and beats == [1, 1]
    await gen.aclose()

    seen: list[uuid.UUID] = []

    async def failing(user_id: uuid.UUID) -> None:
        raise RuntimeError("down")

    async def hook(user_id: uuid.UUID) -> None:
        seen.append(user_id)

    async def stalled(user_id: uuid.UUID) -> None:
        await asyncio.sleep(5)

    me = uuid.UUID(ME)
    saved = platform_events.HEARTBEAT_HOOK_TIMEOUT_S
    try:
        platform_events.HEARTBEAT_HOOK_TIMEOUT_S = 0.01
        platform_events.on_heartbeat(failing)
        platform_events.on_heartbeat(stalled)
        platform_events.on_heartbeat(hook)
        platform_events.on_heartbeat(hook)
        await asyncio.wait_for(platform_events.heartbeat(me), 1)
    finally:
        platform_events.HEARTBEAT_HOOK_TIMEOUT_S = saved
        for each in (failing, stalled, hook):
            platform_events._heartbeat_hooks.remove(each)
    assert seen == [me]


async def test_session_events_are_coalesced_per_id():
    loop = asyncio.get_running_loop()
    source = FakeHub()
    other = str(uuid.uuid7())
    gen = opened(source, stream.Scope(frozenset({GAME}), frozenset({SESSION, other})), coalesce=0.2)
    await next_of(gen)
    for _ in range(3):
        source.put("session", SESSION)
    source.put("session", other)
    first = await next_of(gen)
    sent_at = loop.time()
    assert data(first)["id"] == SESSION
    # Another session has a window of its own; the two later SESSION events collapse into one.
    assert data(await next_of(gen))["id"] == other
    second = await next_of(gen)
    assert data(second)["id"] == SESSION
    assert loop.time() - sent_at >= 0.2 - 0.01
    source.put("game", GAME, 1)
    assert data(await next_of(gen))["topic"] == "game"  # nothing else was waiting
    await gen.aclose()


async def test_the_stream_ends_after_its_lifetime():
    gen = opened(FakeHub(), lifetime=0.05)
    await next_of(gen)
    with pytest.raises(StopAsyncIteration):
        await next_of(gen)


def test_the_lifetime_is_drawn_between_ten_and_thirteen_minutes():
    assert stream.LIFETIME_S == (600.0, 780.0)
    assert stream.HEARTBEAT_S == 15.0 and stream.COALESCE_S == 2.0


async def test_the_stream_ends_when_the_hub_loses_its_connection():
    source = FakeHub()
    gen = opened(source)
    await next_of(gen)
    source.queue.put_nowait(ENDED)
    with pytest.raises(StopAsyncIteration):
        await next_of(gen)


async def test_a_deactivated_user_s_stream_ends_on_their_user_event():
    source = FakeHub()

    async def gone() -> bool:
        return False

    gen = opened(source, still_active=gone)
    await next_of(gen)
    source.put("game", GAME, 1)
    assert data(await next_of(gen))["id"] == GAME
    source.put("user", ME)
    with pytest.raises(StopAsyncIteration):
        await next_of(gen)


async def test_the_scope_is_resolved_again_on_the_users_own_event():
    source = FakeHub()
    scopes = [STUDENT_SCOPE, stream.Scope(frozenset({GAME, OTHER_GAME}), frozenset())]
    calls = []

    async def resolve():
        calls.append(1)
        return scopes[min(len(calls), 2) - 1]

    gen = stream.events(ME, source, resolve, active, heartbeat=30, coalesce=30, lifetime=60)
    await next_of(gen)
    source.put("game", OTHER_GAME, 1)  # not theirs yet: dropped
    source.put("user", ME)  # seated meanwhile
    assert data(await next_of(gen))["topic"] == "user"
    source.put("game", OTHER_GAME, 2)
    assert data(await next_of(gen)) == {"topic": "game", "id": OTHER_GAME, "version": 2}
    assert len(calls) == 2
    await gen.aclose()


async def test_a_staff_scope_follows_a_session_created_after_it_connected():
    """Follow-up review of Story 6.4 (deferred there): a co-owner's stream reads its scope again
    on the first event of an id outside it, once per id; a Student's stream never does."""
    source = FakeHub()
    new_session = str(uuid.uuid7())
    before = stream.Scope(frozenset({GAME}), frozenset({SESSION}), staff=True)
    after = stream.Scope(frozenset({GAME}), frozenset({SESSION, new_session}), staff=True)
    calls = []

    async def resolve():
        calls.append(1)
        return before if len(calls) == 1 else after

    gen = stream.events(ME, source, resolve, active, heartbeat=30, coalesce=30, lifetime=60)
    await next_of(gen)
    source.put("session", new_session)  # created by the other owner after connect
    assert data(await next_of(gen)) == {"topic": "session", "id": new_session, "version": None}
    for _ in range(3):
        source.put("game", OTHER_GAME, 1)  # another Class's game: read once, then dropped
    source.put("game", GAME, 5)
    assert data(await next_of(gen))["id"] == GAME
    assert len(calls) == 3
    await gen.aclose()

    calls.clear()
    gen = stream.events(ME, source, _const(STUDENT_SCOPE, calls), active, heartbeat=30, lifetime=60)
    await next_of(gen)
    source.put("game", OTHER_GAME, 1)
    source.put("user", ME)
    assert data(await next_of(gen))["topic"] == "user"
    assert len(calls) == 2  # on connect and on their own event only
    await gen.aclose()


def _const(scope, calls):
    async def resolve():
        calls.append(1)
        return scope

    return resolve


@pytest.mark.parametrize(
    "payload",
    [
        "not json",
        "[]",
        '{"topic": "seat", "id": "x", "version": null}',
        '{"topic": "game", "id": "", "version": 1}',
        '{"topic": "user", "id": "u", "version": 3}',
        '{"topic": "game", "id": "g", "version": true}',
    ],
)
def test_a_payload_ad8_does_not_allow_is_refused(payload):
    assert parse(payload) is None


def test_a_payload_is_parsed_into_topic_id_and_version():
    assert parse('{"topic":"game","id":"g","version":3}') == Event("game", "g", 3)
    assert parse('{"topic":"user","id":"u","version":null}') == Event("user", "u", None)


async def test_the_hub_hands_committed_events_to_every_subscriber(test_database):
    hub = Hub()
    try:
        async with hub.subscribe() as one, hub.subscribe() as two:
            async with get_sessionmaker().begin() as s:
                # A bad payload on the channel is skipped, the next one still arrives.
                await s.execute(text("SELECT pg_notify('events', 'nonsense')"))
                await platform_events.emit(s, "game", "g1", 7)
            for queue in (one, two):
                assert await asyncio.wait_for(queue.get(), 2) == Event("game", "g1", 7)
            await hub.close()
            assert await asyncio.wait_for(one.get(), 2) is ENDED
    finally:
        await hub.close()


async def test_a_subscriber_too_far_behind_is_ended_and_the_others_go_on(
    test_database, monkeypatch
):
    """Follow-up review of Story 6.4: a stalled stream's queue never grows past `QUEUE_MAX`."""
    from app.platform.events import hub as hub_module

    monkeypatch.setattr(hub_module, "QUEUE_MAX", 2)
    hub = Hub()
    try:
        async with hub.subscribe() as slow:
            async with hub.subscribe() as quick:
                for version in range(3):
                    async with get_sessionmaker().begin() as s:
                        await platform_events.emit(s, "game", "g1", version)
                    assert (await asyncio.wait_for(quick.get(), 2)).version == version
                assert slow.get_nowait() is ENDED  # what it held is dropped for the end
                assert slow.empty()
    finally:
        await hub.close()


async def test_the_hub_refuses_to_start_without_a_database(unreachable_database):
    hub = Hub(lambda: unreachable_database.replace("+psycopg", ""))
    with pytest.raises(ConnectionError):
        async with hub.subscribe():
            pass


def user_id(address: str) -> uuid.UUID:
    [(found,)] = rows("SELECT id FROM users WHERE email = %s", address)
    return found


async def test_the_scope_names_own_games_and_the_staffs_sessions_and_games(klass):
    session_id, seated = await confirmed(klass, 2)
    [game] = games_of(session_id)
    student = await stream.resolve_scope(seated[0])
    assert student == stream.Scope(frozenset({game[0]}), frozenset())
    lecturer = await stream.resolve_scope(user_id(LECTURER))
    assert lecturer == stream.Scope(frozenset({game[0]}), frozenset({session_id}))
    assert lecturer.staff and not student.staff
    assert await stream.resolve_scope(uuid.uuid7()) == stream.Scope(frozenset(), frozenset())


def append_occupant(seat_of: uuid.UUID, kind: str | None, user: uuid.UUID | None) -> None:
    """Append a newer occupancy row to the Seat `seat_of` holds now: `kind` None frees it."""
    [(seat,)] = rows(
        "SELECT DISTINCT ON (o.seat_id) o.seat_id FROM seat_occupancy o WHERE o.user_id = %s "
        "ORDER BY o.seat_id, o.id DESC",
        seat_of,
    )
    execute(
        TEST_DATABASE_URL,
        "INSERT INTO seat_occupancy (id, seat_id, from_week, occupant_kind, reason, user_id) "
        "VALUES (%s, %s, 1, %s, %s, %s)",
        (uuid.uuid7(), seat, kind, "moved" if kind is None else "initial", user),
    )


async def test_a_game_the_student_no_longer_holds_a_seat_in_leaves_the_scope(klass):
    """Follow-up review of Story 6.4 (FR-5): the stream forwards `game:<id>` of a Game where the
    Student holds a Seat now, never of one they left (a move, Student choice)."""
    session_id, seated = await confirmed(klass, 2)
    [game] = games_of(session_id)
    append_occupant(seated[0], None, None)  # the Seat is freed: the Student moved away
    assert await stream.resolve_scope(seated[0]) == stream.Scope(frozenset(), frozenset())
    assert await stream.resolve_scope(seated[1]) == stream.Scope(frozenset({game[0]}), frozenset())


async def test_the_stream_refuses_a_visitor_who_is_not_logged_in(test_database):
    async with client() as c:
        response = await c.get("/api/events")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


class AsgiStream:
    """`GET /api/events` driven over raw ASGI, read chunk by chunk (httpx's ASGI transport
    waits for the whole body, and this one never ends by itself)."""

    def __init__(self, cookie: str) -> None:
        self.sent: asyncio.Queue = asyncio.Queue()
        self.gone = asyncio.Event()
        self.asked = False
        self.buffer = ""
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "https",
            "path": "/api/events",
            "raw_path": b"/api/events",
            "query_string": b"",
            "root_path": "",
            "headers": [(b"host", b"t"), (b"cookie", cookie.encode())],
            "client": ("203.0.113.7", 50000),
            "server": ("t", 443),
        }
        self.task = asyncio.create_task(app()(scope, self.receive, self.sent.put))

    async def receive(self):
        if not self.asked:
            self.asked = True
            return {"type": "http.request", "body": b"", "more_body": False}
        await self.gone.wait()
        return {"type": "http.disconnect"}

    async def start(self) -> dict:
        return await asyncio.wait_for(self.sent.get(), 5)

    async def event(self) -> dict[str, str]:
        """The next SSE event's fields, skipping comment pings."""
        while True:
            while "\n\n" not in self.buffer:
                message = await asyncio.wait_for(self.sent.get(), 5)
                self.buffer += message.get("body", b"").decode()
            block, self.buffer = self.buffer.split("\n\n", 1)
            fields = dict(line.split(": ", 1) for line in block.split("\n") if ": " in line)
            if set(fields) - {""}:
                return fields

    async def close(self) -> None:
        self.gone.set()
        try:
            await asyncio.wait_for(self.task, 5)
        except TimeoutError:
            self.task.cancel()


async def test_the_stream_sends_ready_then_a_committed_event_of_the_users_own(klass, monkeypatch):
    monkeypatch.setattr(stream, "hub", Hub())
    async with client() as c:
        assert (await login(c, LECTURER, PASSWORD)).status_code == 200
        cookie = "; ".join(f"{k}={v}" for k, v in c.cookies.items())
    me = str(user_id(LECTURER))
    live = AsgiStream(cookie)
    try:
        start = await live.start()
        assert start["status"] == 200
        headers = dict(start["headers"])
        assert headers[b"content-type"].startswith(b"text/event-stream")
        assert (await live.event())["event"] == "ready"
        async with get_sessionmaker().begin() as s:
            await platform_events.emit(s, "user", str(uuid.uuid7()))  # another User's
            await platform_events.emit(s, "user", me)
        fields = await live.event()
        assert "event" not in fields
        assert json.loads(fields["data"]) == {"topic": "user", "id": me, "version": None}
    finally:
        await live.close()
        await stream.hub.close()


async def test_the_real_stream_runs_the_presence_hooks_on_its_heartbeat(klass, monkeypatch):
    """Story 9.12: `GET /api/events` passes each heartbeat to `events.heartbeat` with the stream's
    User, and the app registers `debrief.commands.touch` at startup."""
    from app.modules.debrief import commands as debrief_commands

    monkeypatch.setattr(stream, "hub", Hub())
    monkeypatch.setattr(stream, "HEARTBEAT_S", 0.1)
    seen: list[uuid.UUID] = []

    async def hook(user_id: uuid.UUID) -> None:
        seen.append(user_id)

    async with client() as c:
        assert (await login(c, LECTURER, PASSWORD)).status_code == 200
        cookie = "; ".join(f"{k}={v}" for k, v in c.cookies.items())
    assert debrief_commands.touch in platform_events._heartbeat_hooks
    platform_events.on_heartbeat(hook)
    live = AsgiStream(cookie)
    try:
        assert (await live.start())["status"] == 200
        assert (await live.event())["event"] == "ready"
        assert (await live.event())["event"] == "heartbeat"
        assert seen == [user_id(LECTURER)]
    finally:
        platform_events._heartbeat_hooks.remove(hook)
        await live.close()
        await stream.hub.close()


async def test_the_hub_ends_its_subscribers_when_the_connection_is_lost(test_database):
    hub = Hub()
    try:
        async with hub.subscribe() as queue:
            async with get_sessionmaker().begin() as s:
                await s.execute(
                    text(
                        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                        "WHERE datname = current_database() AND query = 'LISTEN events'"
                    )
                )
            assert await asyncio.wait_for(queue.get(), 5) is ENDED
        # The next subscriber opens a new connection, which delivers again.
        async with hub.subscribe() as queue:
            async with get_sessionmaker().begin() as s:
                await platform_events.emit(s, "user", "u2")
            assert await asyncio.wait_for(queue.get(), 2) == Event("user", "u2", None)
    finally:
        await hub.close()


async def test_a_deactivated_users_stream_ends_without_their_event(klass, monkeypatch):
    monkeypatch.setattr(stream, "hub", Hub())
    async with client() as c:
        assert (await login(c, LECTURER, PASSWORD)).status_code == 200
        cookie = "; ".join(f"{k}={v}" for k, v in c.cookies.items())
    me = str(user_id(LECTURER))
    live = AsgiStream(cookie)
    try:
        assert (await live.start())["status"] == 200
        assert (await live.event())["event"] == "ready"
        async with get_sessionmaker().begin() as s:
            await s.execute(text("UPDATE users SET is_active = false WHERE id = :id"), {"id": me})
            await platform_events.emit(s, "user", me)
        # The body ends, and no event is sent first.
        while True:
            message = await asyncio.wait_for(live.sent.get(), 5)
            assert b"data: {" not in message.get("body", b"")
            if not message.get("more_body", False):
                break
    finally:
        await live.close()
        await stream.hub.close()
