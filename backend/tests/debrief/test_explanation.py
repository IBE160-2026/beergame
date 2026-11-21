"""The Explanation before the reveal (Story 9.3, FR-5, FR-14, FR-41, AD-12, AD-14, AD-16, AD-21).

Step 1 reads the Student's own Netto lager from the Decision log; «Send Forklaring» stores the
Explanation once, as typed, and records the `explanation` step in the same transaction; every
step after step 1 answers 403 `explanation_required` until then. The Class's owners and
Assistant lecturers read a Student's Explanation; another Student and an Admin without a staff
role do not. One Class game played a few Uker, then marked finished, serves each test."""

import json
import uuid

import psycopg
import pytest

from app.modules.games import service as games
from app.modules.identity.schemas import AccountRole
from app.modules.ops import sweep
from app.modules.progress import service as progress
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_classes import LECTURER, OTHER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import clock, klass
from tests.classes.test_staff import call, put_staff
from tests.classes.test_student_registration import emitted
from tests.debrief.test_debrief import LOCKED, finish, home, open_, refused
from tests.games.helpers import play_week
from tests.messaging.helpers import rows
from tests.sessions.test_lock import _empty
from tests.sessions.test_open_games import confirmed
from tests.sessions.test_start_game import start, task_done
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "emitted", "klass"]

ASSISTANT = "assistent-93@x.no"
ADMIN = "admin-93@x.no"
TEXT = "  Restordren vokste, så jeg bestilte mye.\nDet som var på vei, regnet jeg lite med.  "


def base(debrief_id: str) -> str:
    return f"/api/debriefs/{debrief_id}"


def user_id(address: str) -> uuid.UUID:
    [(found,)] = rows("SELECT id FROM users WHERE email = %s", address)
    return found


def explanations() -> list[tuple]:
    return rows("SELECT user_id, text, length FROM debrief_explanations ORDER BY user_id")


async def played(klass: str) -> tuple[str, str, dict, dict[str, str]]:
    """A Class session with two Class games (five Students); the first Student's game played
    a few Uker and finished, its Debrief opened. Returns the session id, game id and Debrief."""
    session_id, seated = await confirmed(klass, 5)
    await sweep.run(LOCKED)
    game_id = (await home(email(0)))["game"]["id"]
    await task_done(seated[0], session_id)
    assert (await start(email(0), game_id)).status_code == 200
    for _ in range(2):
        await play_week(game_id)
    finish(game_id)
    opened = await open_(email(0), session_id)
    assert opened.status_code == 200
    game_of = {email(i): (await home(email(i)))["game"]["id"] for i in range(5)}
    return session_id, game_id, opened.json(), game_of


def holds_no_reveal(body: object, own_role: str) -> None:
    """No demand, incoming order or other Role anywhere in an answer (FR-14, FR-41)."""
    text = json.dumps(body)
    for word in ("demand", "incoming", "customer", "orders", "backlog"):
        assert word not in text, (word, text)
    others = {"retailer", "wholesaler", "distributor", "factory"} - {own_role}
    assert not any(role in text for role in others), text


async def test_step_one_the_one_send_the_gate_and_the_readers(klass, emitted):
    session_id, game_id, debrief, game_of = await played(klass)
    me, role = email(0), debrief["role"]
    mate = next(who for who, game in game_of.items() if game == game_id and who != me)
    stranger = next(who for who, game in game_of.items() if game != game_id)
    path = base(debrief["id"])

    # Step 1: the own Seat's Netto lager in every logged Uke, nothing else.
    net = await call(me, "GET", f"{path}/net-inventory")
    assert net.status_code == 200
    logged = [r for r in await games.decision_log(game_id) if r.role == role]
    assert net.json() == {
        "weeks": [
            {"week": r.week, "net_inventory": r.state_seen.net_inventory}
            for r in sorted(logged, key=lambda r: r.week)
        ]
    }
    weeks = [w["week"] for w in net.json()["weeks"]]
    assert len(weeks) >= 2 and weeks == list(range(1, len(weeks) + 1))

    # Without an Explanation: every Debrief data endpoint holds no demand and no other Seat,
    # and every step after step 1 is refused.
    for method, url in (
        ("POST", f"/api/me/class-sessions/{session_id}/debrief"),
        ("GET", path),
        ("GET", f"{path}/net-inventory"),
        ("GET", f"{path}/explanation"),
    ):
        response = await call(me, method, url)
        assert response.status_code == 200, url
        holds_no_reveal(response.json(), role)
    for step in range(2, 6):
        refused(await call(me, "GET", f"{path}/steps/{step}"), "explanation_required")
    assert (await call(me, "GET", f"{path}/explanation")).json() == {"explanation": None}

    # White space only and too long are refused and store nothing.
    for text, reason in (("  \n\t ", "blank"), ("x" * 5001, "too_long")):
        response = await call(me, "POST", f"{path}/explanation", json={"text": text})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"
        assert response.json()["error"]["fields"] == {"text": reason}
    assert explanations() == []

    # Sent once, as typed, with its length and time, and the step recorded with it.
    emitted.clear()
    sent = await call(me, "POST", f"{path}/explanation", json={"text": TEXT})
    assert sent.status_code == 201
    body = sent.json()
    assert (body["text"], body["length"]) == (TEXT, len(TEXT))
    assert set(body) == {"text", "length", "saved_at"}
    assert explanations() == [(user_id(me), TEXT, len(TEXT))]
    assert await progress.has_step(user_id(me), uuid.UUID(session_id), "explanation")
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["debrief.save_explanation"]
    assert ("debrief", debrief["id"]) in emitted

    # A second send is refused and changes nothing; nor can the row be changed in the database.
    again = await call(me, "POST", f"{path}/explanation", json={"text": "Noe annet."})
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "explanation_exists"
    with pytest.raises(psycopg.errors.RestrictViolation):
        execute("UPDATE debrief_explanations SET text = 'endret', length = 6")
    assert explanations() == [(user_id(me), TEXT, len(TEXT))]
    assert (await call(me, "GET", f"{path}/explanation")).json() == {"explanation": body}

    # With it, the steps after step 1 answer.
    for step in range(2, 6):
        response = await call(me, "GET", f"{path}/steps/{step}")
        assert response.status_code == 200
        assert response.json() == {"debrief_id": debrief["id"], "step": step}

    # Another Student of the same game reads only their own (none) and is still gated.
    other = mate
    assert (await call(other, "GET", f"{path}/explanation")).json() == {"explanation": None}
    refused(await call(other, "GET", f"{path}/steps/2"), "explanation_required")

    await readers(session_id, game_id, path, klass, body, mate, stranger)


async def readers(
    session_id: str, game_id: str, path: str, klass: str, sent: dict, mate: str, stranger: str
) -> None:
    """Who reads the first Student's sent Explanation, and who reaches the Debrief's routes.
    Part of the test above, so the played game is set up once."""
    me = email(0)
    staff_path = f"/api/class-sessions/{session_id}/students/{user_id(me)}/explanation"
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")
    await make(ADMIN, roles=(AccountRole.admin,))

    # The staff are told when a Student has sent none.
    none_path = f"/api/class-sessions/{session_id}/students/{user_id(mate)}/explanation"
    missing = await call(ASSISTANT, "GET", none_path)
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "not_found"

    for who in (ASSISTANT, LECTURER):
        read = await call(who, "GET", staff_path)
        assert read.status_code == 200 and read.json() == sent
    # Another Student of the same game, an Admin and a Lecturer of no role in the Class.
    for who in (mate, ADMIN, OTHER):
        refused(await call(who, "GET", staff_path), "forbidden")
    for bad in ("nope", str(uuid.uuid4())):
        refused(
            await call(ASSISTANT, "GET", f"/api/class-sessions/{bad}/students/x/explanation"),
            "forbidden",
        )

    # The Student of the other Class game and the staff reach none of the Debrief's routes.
    for who in (stranger, ASSISTANT):
        for method, url in (
            ("GET", f"{path}/net-inventory"),
            ("GET", f"{path}/explanation"),
            ("POST", f"{path}/explanation"),
            ("GET", f"{path}/steps/2"),
        ):
            kw = {"json": {"text": "x"}} if method == "POST" else {}
            refused(await call(who, method, url, **kw), "forbidden")

    # A game that is not finished refuses them alike, with the envelope only.
    execute("UPDATE games SET lifecycle = 'playing_out' WHERE id = %s", game_id)
    for url in (f"{path}/net-inventory", f"{path}/explanation", f"{path}/steps/2"):
        refused(await call(me, "GET", url), "debrief_not_open")
