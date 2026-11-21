"""Messages from staff to Students (Story 7.9, FR-40, FR-72, AD-9, AD-12, AD-14, NFR-7): the
Meldingsskjema's form read and «Send Melding» store one Message with one recipient row and one
`message` notice per registered Student in one transaction, emit `session:<id>`, send a mail per
Student through Story 3.5's pipeline and never send twice for one key."""

import uuid

import pytest

from app.engine import GameSettings
from app.modules.games import commands
from app.modules.games import service as games_service
from app.modules.identity.schemas import AccountRole
from app.modules.messaging import delivery
from app.modules.messaging import service as messaging
from app.platform.db import get_sessionmaker
from tests.classes.test_classes import LECTURER, OTHER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_staff import ASSISTANT, call, put_staff
from tests.messaging.helpers import drain, mails, rows
from tests.sessions.test_allocation import students
from tests.sessions.test_dates import new_session, student_of
from tests.sessions.test_game_end import _empty, clock, emitted, klass, short_game
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "emitted", "klass"]


def form_path(session_id: str) -> str:
    return f"/api/class-sessions/{session_id}/messages/form"


async def form(who: str, session_id: str, **params):
    return await call(who, "GET", form_path(session_id), params=params)


async def send(who: str, session_id: str, text: str = "Husk ordren!", key=None, **ids):
    body = {"key": str(key or uuid.uuid4()), "text": text, **ids}
    return await call(who, "POST", f"/api/class-sessions/{session_id}/messages", json=body)


def stored(session_id: str) -> list[tuple]:
    return rows(
        "SELECT m.recipient_kind, m.recipient_game_id::text, m.recipient_user_id::text, m.text, "
        "array_agg(r.user_id::text ORDER BY r.user_id) FROM messages m "
        "JOIN message_recipients r ON r.message_id = m.id WHERE m.class_session_id = %s "
        "GROUP BY m.id ORDER BY m.id",
        session_id,
    )


def message_notices() -> list[tuple]:
    return rows("SELECT user_id::text, dedupe_key FROM notices WHERE kind = 'message' ORDER BY 1")


async def test_a_message_to_the_whole_class_session_reaches_every_registered_student_once(
    klass, emitted
):
    seated = await students(klass, 3)
    session_id = await new_session(klass)
    shown = await form(LECTURER, session_id)
    assert shown.status_code == 200
    body = shown.json()
    assert (body["kind"], body["students"], body["sent_before"], body["max_length"]) == (
        "class_session",
        3,
        0,
        2000,
    )
    assert body["game_number"] is None and body["student_name"] is None and body["class_name"]
    key = uuid.uuid4()
    emitted.clear()
    first = await send(LECTURER, session_id, "  Hei alle!\r\nHusk fristen.\n\n", key=key)
    assert first.status_code == 201
    answer = first.json()
    assert (answer["students"], answer["sent_before"]) == (3, 1)
    everyone = sorted(str(s) for s in seated)
    [(kind, game, user, text, recipients)] = stored(session_id)
    assert (kind, game, user, text) == ("class_session", None, None, "Hei alle!\nHusk fristen.")
    assert sorted(recipients) == everyone
    message_id = answer["message_id"]
    assert message_notices() == [(s, f"message:{message_id}:{s}") for s in everyone]
    assert ("session", session_id) in emitted
    assert {("user", s) for s in everyone} <= set(emitted)
    # A repeat of the same request (a double press, a retry) answers the same and sends nothing.
    again = await send(LECTURER, session_id, "Hei alle!\nHusk fristen.", key=key)
    assert (again.status_code, again.json()) == (201, answer)
    assert len(stored(session_id)) == 1 and len(message_notices()) == 3
    # The mail pipeline sends one mail per Student, at once, with the text and a link to Hjem.
    await drain()
    sent = [m for m in mails() if "Hei alle!" in m.text]
    assert len(sent) == 3
    assert all("Hei alle!\nHusk fristen." in m.text and "/hjem" in m.text for m in sent)
    assert all(m.subject.startswith("Melding fra Klassen") for m in sent)
    # The form now counts the earlier Message.
    assert (await form(LECTURER, session_id)).json()["sent_before"] == 1


async def test_a_class_game_reaches_each_seats_student_also_where_an_ai_took_over(klass):
    session_id, game_id, seated = await short_game(klass)
    replaced = next(
        s for s in (await games_service.get_game(game_id)).seats if str(s.user_id) == str(seated[1])
    )
    await commands.switch_to_rule_based(game_id, replaced.role, "takeover_inactivity")
    shown = (await form(LECTURER, session_id, game_id=game_id)).json()
    assert (shown["kind"], shown["game_number"], shown["students"]) == ("class_game", 1, 2)
    response = await send(LECTURER, session_id, "Spill videre!", game_id=game_id)
    assert response.status_code == 201 and response.json()["students"] == 2
    [(kind, game, _, _, recipients)] = stored(session_id)
    assert (kind, game) == ("class_game", game_id)
    assert sorted(recipients) == sorted(str(s) for s in seated)
    # One Student, written from the game: titled with both; counted per Student.
    student = str(seated[0])
    one = (await form(LECTURER, session_id, game_id=game_id, student_id=student)).json()
    assert (one["kind"], one["game_number"], one["students"], one["sent_before"]) == (
        "student",
        1,
        1,
        0,
    )
    assert one["student_name"]
    response = await send(LECTURER, session_id, game_id=game_id, student_id=student)
    assert response.json()["students"] == 1 and response.json()["sent_before"] == 1
    assert stored(session_id)[1][2:] == (student, "Husk ordren!", [student])
    # Spillinnsikt names the Student of each Student Seat for its «Melding» link.
    insight = (await call(LECTURER, "GET", f"/api/games/{game_id}/insight")).json()
    ids = {seat["role"]: seat["user_id"] for seat in insight["seats"]}
    assert ids[replaced.role] is None
    assert sorted(i for i in ids.values() if i) == [student]


def test_each_seat_gives_its_student_now_or_the_last_before_an_ai_player():
    seat = [uuid.uuid4() for _ in range(5)]
    a, b, c, d = (uuid.uuid4() for _ in range(4))
    history = [
        {"seat_id": seat[0], "occupant_kind": "student", "user_id": a},
        {"seat_id": seat[1], "occupant_kind": "student", "user_id": b},
        {"seat_id": seat[1], "occupant_kind": "rule_based", "user_id": None},  # a Takeover
        {"seat_id": seat[2], "occupant_kind": "student", "user_id": c},
        {"seat_id": seat[2], "occupant_kind": None, "user_id": None},  # c moved away
        {"seat_id": seat[2], "occupant_kind": "rule_based", "user_id": None},
        {"seat_id": seat[3], "occupant_kind": "llm", "user_id": None},
        {"seat_id": seat[3], "occupant_kind": "student", "user_id": d},  # a late registrant
        {"seat_id": seat[4], "occupant_kind": "rule_based", "user_id": None},  # never a Student
    ]
    assert games_service.assigned_students(history) == (a, b, d)


async def test_a_message_is_refused_when_empty_too_long_or_reaching_no_one(klass):
    session_id = await new_session(klass)
    # No registered Student yet: the form says so and a send stores nothing.
    assert (await form(LECTURER, session_id)).json()["students"] == 0
    nobody = await send(LECTURER, session_id)
    assert (nobody.status_code, nobody.json()["error"]["code"]) == (422, "no_recipients")
    assert stored(session_id) == [] and message_notices() == []
    await students(klass, 1)
    for text, code in (("  \n ", "message_empty"), ("x" * 2001, "message_too_long")):
        response = await send(LECTURER, session_id, text)
        assert (response.status_code, response.json()["error"]["code"]) == (422, code)
    assert (await send(LECTURER, session_id, "x" * 2001)).json()["error"]["fields"] == {
        "max_length": 2000
    }
    assert (await send(LECTURER, session_id, "x" * 2000)).status_code == 201
    # A list a calling module passes (Epic 13) keeps only registered Students: none here.
    async with get_sessionmaker().begin() as session:
        with pytest.raises(messaging.MessageRefused) as refused:
            await messaging.send_message(
                session,
                class_session_id=uuid.UUID(session_id),
                class_id=uuid.UUID(klass),
                sender_id=uuid.UUID(
                    rows("SELECT id::text FROM users WHERE email = %s", LECTURER)[0][0]
                ),
                key=uuid.uuid4(),
                recipient=messaging.Recipient(
                    messaging.RecipientKind.LIST, user_ids=(uuid.uuid4(),)
                ),
                text="Til ingen",
            )
    assert refused.value.code == "no_recipients"
    assert len(stored(session_id)) == 1
    # A key is one Message's: reused for another Class session or another text, it sends nothing.
    key = uuid.uuid4()
    assert (await send(LECTURER, session_id, key=key)).status_code == 201
    other_session = await new_session(klass)
    for clash in (
        await send(LECTURER, other_session, key=key),
        await send(LECTURER, session_id, "Noe annet", key=key),
    ):
        assert (clash.status_code, clash.json()["error"]["code"]) == (409, "message_key_conflict")
    # NUL, which a database text cannot hold, is left out rather than failing the send.
    assert (await send(LECTURER, session_id, "Hei\x00 du")).status_code == 201
    assert stored(session_id)[-1][3] == "Hei du"
    assert delivery.MESSAGE_KIND == messaging.MESSAGE_KIND == "message"


async def test_only_the_staff_of_the_class_may_send_and_any_outsider_is_refused_alike(klass):
    session_id, game_id, seated = await short_game(klass, students=1)
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")
    assert (await send(ASSISTANT, session_id, "Fra assistenten")).status_code == 201
    # A registered Student of the Class who holds no Seat in the game.
    stranger = await student_of(klass, "stranger@x.no")
    await make("admin-only@x.no", roles=(AccountRole.admin,))
    test_game = await commands.create(
        "lecturer_test", GameSettings(), class_session_id=uuid.UUID(session_id)
    )
    other_session = await new_session(klass)
    refused = [
        await send(email(0), session_id),  # a Student of the Class
        await send(OTHER, session_id),  # a Lecturer of another Class
        await send("admin-only@x.no", session_id),  # an Admin not attached to the Class
        await send(LECTURER, str(uuid.uuid7())),  # no such Class session
        await send(LECTURER, "not-an-id"),
        await send(LECTURER, other_session, game_id=game_id),  # a game of another session
        await send(LECTURER, session_id, game_id=str(test_game)),  # a test Game (AD-13)
        await send(LECTURER, session_id, student_id=str(uuid.uuid4())),  # not a Student here
        await send(LECTURER, session_id, student_id=str(stranger), game_id=game_id),  # not seated
        await form(email(0), session_id),
        await form(LECTURER, session_id, game_id="not-an-id"),
    ]
    assert {r.status_code for r in refused} == {403}
    assert len({r.content for r in refused}) == 1
    assert [s[0] for s in stored(session_id)] == ["class_session"]


async def test_an_archived_class_takes_no_message(klass):
    await students(klass, 1)
    session_id = await new_session(klass)
    execute("UPDATE classes SET archived_at = now() WHERE id = %s", klass)
    response = await send(LECTURER, session_id)
    assert (response.status_code, response.json()["error"]["code"]) == (409, "class_archived")
    assert stored(session_id) == []


async def test_the_mail_keeps_line_breaks_and_escapes_everything_else(klass):
    [student] = await students(klass, 1)
    session_id = await new_session(klass)
    text = '<b>Hei</b> & "velkommen"\nhttps://example.com/<script>'
    assert (await send(LECTURER, session_id, text)).status_code == 201
    await drain()
    [mail] = [m for m in mails() if "velkommen" in m.text]
    assert text in mail.text
    assert (
        "&lt;b&gt;Hei&lt;/b&gt; &amp; &#34;velkommen&#34;<br>https://example.com/&lt;script&gt;"
        in (mail.html)
    )
    assert "<b>Hei</b>" not in mail.html and "<script>" not in mail.html
    assert mail.to == rows("SELECT email FROM users WHERE id = %s", student)[0][0]
