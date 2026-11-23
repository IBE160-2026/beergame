"""Reading Messages (Story 7.10, FR-40, FR-73, AD-12, AD-14, NFR-7): a Student reads the Messages
written to them on Hjem, through `authz.messages_addressed_to` only, and the staff of the Class
read «Meldinger», every Message a Class session was sent, with recipient, sender, time and reach.
No route lets a Student write. Sending is `test_messages.py`."""

import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy import event

from app.main import create_app
from app.modules.games import commands
from app.platform.db import get_engine
from tests.classes.test_classes import LECTURER, OTHER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_staff import ASSISTANT, call, put_staff
from tests.messaging.helpers import rows
from tests.messaging.test_messages import send
from tests.sessions.test_allocation import students
from tests.sessions.test_dates import NOW, new_session
from tests.sessions.test_game_end import _empty, clock, emitted, klass
from tests.sessions.test_student_choice import email
from tests.test_authz_rules import api_routes

__all__ = ["_empty", "clock", "emitted", "klass"]

BACKEND = Path(__file__).parents[2]


async def mine(who: str):
    return await call(who, "GET", "/api/me/messages")


async def sent(who: str, session_id: str):
    return await call(who, "GET", f"/api/class-sessions/{session_id}/messages")


async def other_class_with(student: uuid.UUID, address: str) -> str:
    """A Class of the other Lecturer in which `student` is a registered Student too."""
    place = rows("SELECT id::text FROM institutions LIMIT 1")[0][0]
    created = await call(
        OTHER, "POST", "/api/classes", json={"name": "class-of-1995", "institution_id": place}
    )
    assert created.status_code == 201
    class_id = created.json()["id"]
    execute(
        "INSERT INTO roster_entries (id, class_id, email, user_id, registration, added_at) "
        "VALUES (gen_random_uuid(), %s, %s, %s, 'registered', %s)",
        class_id,
        address,
        student,
        NOW,
    )
    return class_id


async def test_a_student_reads_only_their_own_messages_newest_first_as_written(klass):
    first, second = await students(klass, 2)
    session_id = await new_session(klass)
    text = "<b>Hei</b> & velkommen\nhttps://example.com/<script>"
    assert (await send(LECTURER, session_id, text)).status_code == 201
    to_second = await send(LECTURER, session_id, "Bare til deg", student_id=str(second))
    assert to_second.status_code == 201
    # The first Student reads the Message to all, as written; never the one to the second.
    [item] = (await mine(email(0))).json()["items"]
    assert (item["text"], item["sender_name"], item["class_name"]) == (
        text,
        "Bard",
        "class-of-1994",
    )
    assert item["class_id"] == klass and item["sent_at"]
    # The second reads both, newest first.
    items = (await mine(email(1))).json()["items"]
    assert [m["text"] for m in items] == ["Bare til deg", text]
    assert items[0]["id"] == to_second.json()["message_id"]
    # Staff and Users with no Message read an empty list; nobody can write here.
    assert (await mine(LECTURER)).json() == {"items": []}
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        assert (await call(email(0), method, "/api/me/messages", json={})).status_code == 405
    # A Student removed from the Roster no longer reads that Class's Messages.
    execute("UPDATE roster_entries SET removed_at = %s WHERE user_id = %s", NOW, first)
    assert (await mine(email(0))).json() == {"items": []}


async def test_a_student_in_two_classes_reads_each_message_with_its_class(klass):
    [student] = await students(klass, 1)
    other = await other_class_with(student, email(0))
    assert (await send(LECTURER, await new_session(klass), "Fra den første")).status_code == 201
    other_session = (await call(OTHER, "POST", f"/api/classes/{other}/class-sessions")).json()
    assert (await send(OTHER, other_session["id"], "Fra den andre")).status_code == 201
    items = (await mine(email(0))).json()["items"]
    assert [(m["text"], m["class_name"], m["sender_name"]) for m in items] == [
        ("Fra den andre", "class-of-1995", "Kari"),
        ("Fra den første", "class-of-1994", "Bard"),
    ]
    # An archived Class's Messages are closed to its Students, like the rest of it (Story 4.10).
    execute("UPDATE classes SET archived_at = now() WHERE id = %s", other)
    assert [m["text"] for m in (await mine(email(0))).json()["items"]] == ["Fra den første"]


async def test_the_staff_list_every_message_of_the_session_with_recipient_and_reach(klass):
    first, second, third = await students(klass, 3)
    session_id = await new_session(klass)
    assert (await send(LECTURER, session_id, "Til alle")).status_code == 201
    assert (await send(LECTURER, session_id, "Til én", student_id=str(first))).status_code == 201
    gone = await send(LECTURER, session_id, "Til en som går", student_id=str(third))
    assert gone.status_code == 201
    execute("UPDATE roster_entries SET removed_at = %s WHERE user_id = %s", NOW, third)
    # A Message to a Class game, stored as `send_message` would (a Game with no Student cannot
    # be sent one): listed with its game number.
    game_id = await commands.create("class", class_session_id=session_id, game_number=2)
    execute(
        "INSERT INTO messages (id, key, class_session_id, sender_id, recipient_kind, "
        "recipient_game_id, text, created_at) SELECT gen_random_uuid(), gen_random_uuid(), %s, "
        "id, 'class_game', %s, 'Til spillet', now() - interval '1 day' FROM users WHERE email = %s",
        session_id,
        game_id,
        LECTURER,
    )
    execute(
        "INSERT INTO message_recipients (message_id, user_id) "
        "SELECT id, %s FROM messages WHERE recipient_game_id = %s",
        second,
        game_id,
    )
    # Another session's Message is not listed.
    assert (await send(LECTURER, await new_session(klass), "Annen økt")).status_code == 201
    answer = await sent(LECTURER, session_id)
    assert answer.status_code == 200
    body = answer.json()
    assert (body["class_id"], body["class_name"], body["class_session_id"]) == (
        klass,
        "class-of-1994",
        session_id,
    )
    assert body["session_number"] == 1
    listed = [
        (m["kind"], m["student_id"], m["student_name"], m["students"], m["text"], m["sender_name"])
        for m in body["items"]
    ]
    assert listed == [
        ("student", str(third), None, 1, "Til en som går", "Bard"),
        ("student", str(first), "S0", 1, "Til én", "Bard"),
        ("class_session", None, None, 3, "Til alle", "Bard"),
        ("class_game", None, None, 1, "Til spillet", "Bard"),
    ]
    assert [(m["game_id"], m["game_number"]) for m in body["items"]] == [(None, None)] * 3 + [
        (game_id, 2)
    ]


async def test_only_the_staff_read_the_list_and_outsiders_are_refused_alike(klass):
    await students(klass, 1)
    session_id = await new_session(klass)
    refused = [
        await sent(email(0), session_id),  # a Student of the Class
        await sent(OTHER, session_id),  # a Lecturer of another Class
        await sent(LECTURER, str(uuid.uuid7())),  # no such Class session
        await sent(LECTURER, "not-an-id"),
    ]
    assert {r.status_code for r in refused} == {403}
    assert len({r.content for r in refused}) == 1
    assert (await sent(LECTURER, session_id)).json()["items"] == []
    # An Assistant lecturer of the Class reads it as the Lecturer does.
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")
    assert (await sent(ASSISTANT, session_id)).json()["items"] == []


async def test_both_reads_take_the_same_queries_for_one_message_or_many(klass):
    first, _ = await students(klass, 2)
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")
    session_id = await new_session(klass)
    engine = get_engine().sync_engine
    statements: list[str] = []

    def record(conn, cursor, statement, *rest) -> None:
        statements.append(statement)

    async def counted(read) -> int:
        statements.clear()
        assert (await read).status_code == 200
        return len(statements)

    assert (await send(LECTURER, session_id, "Én")).status_code == 201
    to_one = await send(LECTURER, session_id, "Til én", student_id=str(first))
    assert to_one.status_code == 201
    event.listen(engine, "before_cursor_execute", record)
    try:
        few = (await counted(mine(email(0))), await counted(sent(LECTURER, session_id)))
        # More Messages, from another sender too: the lookups stay batched.
        assert (await send(ASSISTANT, session_id, "Fra assistenten")).status_code == 201
        again = await send(LECTURER, session_id, "Til én igjen", student_id=str(first))
        assert again.status_code == 201
        many = (await counted(mine(email(0))), await counted(sent(LECTURER, session_id)))
    finally:
        event.remove(engine, "before_cursor_execute", record)
    assert few == many


def test_no_route_lets_a_student_write_a_message():
    """C-5, UX-DR78: the only route that writes a Message is the staff's send (Story 7.9)."""
    writes = sorted(
        (path, method)
        for path, methods, _ in api_routes(create_app())
        if "messages" in path
        for method in methods
        if method not in ("GET", "HEAD")
    )
    assert writes == [("/api/class-sessions/{session_id}/messages", "POST")]


@pytest.mark.parametrize(
    "module",
    ["app.modules.messaging.messages", "app.modules.ops.jobs"],
)
def test_the_messages_module_imports_first_in_a_fresh_interpreter(module):
    """Story 7.9 broke an import cycle here: importing `messaging.messages` before anything else
    must work. Story 13.6: so must the worker's first import (`ops.jobs`), which reaches
    `messages` through `sessions`, `classes` and `messaging.delivery` while `sessions` loads."""
    done = subprocess.run(
        [sys.executable, "-c", f"import {module}"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert done.returncode == 0, done.stderr
