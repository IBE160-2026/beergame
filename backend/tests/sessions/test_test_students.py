"""Test students who consent before they take part (Story 12.8, FR-82, AD-13, AD-27): a User made
from a Control test's Roster carries `is_test_student`; a Control test Roster takes only such
Users and an ordinary Roster none of them, so a test student is a Student of Control test Classes
only; a test student consents or declines on Hjem, each decision a row with the time and the text
version; a Control test's allocation and every automatic seating leave out a test student without
consent. The api's clock is fixed and moved by hand; the database clock is never read."""

import re
import uuid
from pathlib import Path

import pytest

from app.ai import budget
from app.modules.identity import service as identity
from app.modules.sessions import service as sessions
from app.platform import auth
from app.platform.db import get_sessionmaker
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_staff import call
from tests.classes.test_student_registration import accept, accept_login, check, emitted
from tests.identity.helpers import client
from tests.messaging.helpers import rows
from tests.sessions.test_allocation import open_, path, redraw
from tests.sessions.test_allocation_confirm import committed, confirm
from tests.sessions.test_control_test import ADMIN, ASSISTANT, STUDENT, control, people
from tests.sessions.test_dates import PLAN, START, iso, refusal
from tests.sessions.test_lock import MINUTE
from tests.sessions.test_student_choice import flag, take

__all__ = ["clock", "control", "emitted", "klass", "people"]

CONSENT = "/api/me/test-student-consent"
VERSION = identity.CONSENT_TEXT_VERSION


@pytest.fixture(autouse=True)
def _empty(ai_db, mail_db, games_db):
    """No model config, notices or games but what a test adds."""


def class_path(class_id: str, tail: str) -> str:
    return f"/api/classes/{class_id}{tail}"


async def invite(class_id: str, *addresses: str, email: str = ADMIN) -> dict[str, str]:
    """Paste and send Student Invitations as the Class's owner: address → link token."""
    pasted = await call(
        email, "POST", class_path(class_id, "/roster-paste"), json={"text": " ".join(addresses)}
    )
    assert pasted.status_code == 201, pasted.text
    sent = await call(
        email,
        "POST",
        class_path(class_id, "/invitations"),
        json={"upload_id": pasted.json()["id"], "valid_days": 14},
    )
    assert sent.status_code == 201, sent.text
    found = rows(
        "SELECT email, id FROM invitations WHERE kind = 'student' AND class_id = %s", class_id
    )
    return {e: auth.link_token(identity.INVITATION, i) for e, i in found if e in addresses}


async def enrol(class_id: str, email: str, consent: str | None = None) -> uuid.UUID:
    """A registered test student of the Control test Class, with a decision when `consent`."""
    user_id = await make(email, roles=())
    execute("UPDATE users SET is_test_student = true WHERE id = %s", user_id)
    execute(
        "INSERT INTO roster_entries (id, class_id, email, user_id, registration, added_at) "
        "VALUES (gen_random_uuid(), %s, %s, %s, 'registered', %s)",
        class_id,
        email,
        user_id,
        NOW,
    )
    if consent is not None:
        await identity.decide_consent(user_id, consent, VERSION, now=NOW)
    return user_id


def marked(email: str) -> list[tuple]:
    return rows("SELECT is_test_student FROM users WHERE email = %s", email)


def decisions(user_id: uuid.UUID) -> list[tuple]:
    return rows(
        "SELECT decision, text_version, decided_at FROM test_student_consents "
        "WHERE user_id = %s ORDER BY decided_at, id",
        user_id,
    )


async def registrations(class_id: str, email: str = ADMIN) -> dict[str, dict]:
    response = await call(email, "GET", class_path(class_id, "/registrations"))
    assert response.status_code == 200, response.text
    return {item["email"]: item for item in response.json()["items"]}


# The mark and the Roster rule.


async def test_an_invited_address_registers_as_a_test_student_listed_as_one(control):
    class_id = control["class_id"]
    links = await invite(class_id, "ny@x.no")
    async with client() as c:
        checked = await check(c, links["ny@x.no"])
        assert checked.status_code == 200
        accepted = await accept(c, links["ny@x.no"])
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["user"]["is_test_student"] is True
        me = await c.get("/api/auth/me")
        assert me.json()["user"]["is_test_student"] is True
    assert marked("ny@x.no") == [(True,)]
    row = (await registrations(class_id))["ny@x.no"]
    assert (row["status"], row["test_student"], row["consent"]) == ("registered", True, "pending")
    # An ordinary Student is no test student.
    assert (await call(STUDENT, "GET", "/api/auth/me")).json()["user"]["is_test_student"] is False


async def test_a_manual_registration_on_a_control_test_makes_a_test_student(control):
    class_id = control["class_id"]
    response = await call(
        ADMIN,
        "POST",
        class_path(class_id, "/roster/manual"),
        json={"email": "hand@x.no", "name": "Per Hand"},
    )
    assert response.status_code in (200, 201), response.text
    assert marked("hand@x.no") == [(True,)]


async def test_a_control_test_roster_refuses_a_user_who_is_no_test_student(people, control):
    class_id = control["class_id"]
    pasted = await call(
        ADMIN,
        "POST",
        class_path(class_id, "/roster-paste"),
        json={"text": f"{STUDENT} {LECTURER} ny@x.no"},
    )
    body = pasted.json()
    assert body["valid_count"] == 1
    assert [(r["value"], r["reason"]) for r in body["invalid_rows"]] == [
        (STUDENT, "not_test_student"),
        (LECTURER, "not_test_student"),
    ]
    sent = await call(
        ADMIN,
        "POST",
        class_path(class_id, "/invitations"),
        json={"upload_id": body["id"], "valid_days": 14},
    )
    assert sent.json()["sent"] == 1
    on_roster = {
        e for (e,) in rows("SELECT email FROM roster_entries WHERE class_id = %s", class_id)
    }
    assert on_roster == {"ny@x.no"}
    for tail, extra in (("/roster/entries", {}), ("/roster/manual", {"name": "Ola"})):
        refused = await call(
            ADMIN, "POST", class_path(class_id, tail), json={"email": STUDENT, **extra}
        )
        assert refusal(refused) == (422, "invalid_request", {"email": "not_test_student"}), tail
    assert marked(STUDENT) == [(False,)]


async def test_an_ordinary_roster_refuses_a_test_student(people, control):
    await enrol(control["class_id"], "test@x.no")
    ordinary = people["class"]
    pasted = await call(
        LECTURER, "POST", class_path(ordinary, "/roster-paste"), json={"text": "test@x.no"}
    )
    assert [(r["value"], r["reason"]) for r in pasted.json()["invalid_rows"]] == [
        ("test@x.no", "address_unavailable")
    ]
    assert pasted.json()["valid_count"] == 0
    for tail, extra in (("/roster/entries", {}), ("/roster/manual", {"name": "Ola"})):
        refused = await call(
            LECTURER, "POST", class_path(ordinary, tail), json={"email": "test@x.no", **extra}
        )
        assert refusal(refused) == (422, "invalid_request", {"email": "address_unavailable"}), tail


async def test_a_link_whose_address_became_a_user_of_the_other_kind_is_unusable(people, control):
    control_class, ordinary = control["class_id"], people["class"]
    to_control = await invite(control_class, "a@x.no")
    to_ordinary = await invite(ordinary, "b@x.no", email=LECTURER)
    # Each address becomes a User of the other kind before its link is used.
    made_ordinary = await call(
        LECTURER,
        "POST",
        class_path(ordinary, "/roster/manual"),
        json={"email": "a@x.no", "name": "A"},
    )
    made_test = await call(
        ADMIN,
        "POST",
        class_path(control_class, "/roster/manual"),
        json={"email": "b@x.no", "name": "B"},
    )
    assert made_ordinary.status_code in (200, 201) and made_test.status_code in (200, 201)
    assert marked("a@x.no") == [(False,)] and marked("b@x.no") == [(True,)]
    async with client() as c:
        for token in (to_control["a@x.no"], to_ordinary["b@x.no"]):
            assert (await check(c, token)).status_code != 200
            refused = await accept_login(c, token, "whatever-password")
            assert refused.json()["error"]["code"] == "invitation_link_invalid"


# Consent on Hjem.


async def test_a_test_student_declines_then_consents_and_cannot_take_it_back(control, emitted):
    student = await enrol(control["class_id"], "test@x.no")
    first = await call("test@x.no", "GET", CONSENT)
    assert first.json() == {"decision": None, "text_version": VERSION, "decided_at": None}
    stale = await call("test@x.no", "PUT", CONSENT, json={"decision": "given", "text_version": "0"})
    assert refusal(stale) == (409, "consent_text_changed", {"text_version": "consent_text_changed"})
    emitted.clear()
    declined = await call(
        "test@x.no", "PUT", CONSENT, json={"decision": "declined", "text_version": VERSION}
    )
    assert declined.status_code == 200 and declined.json()["decision"] == "declined"
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["identity.decide_consent"]
    assert emitted == [("user", str(student))]
    # The decision held again writes nothing.
    again = await call(
        "test@x.no", "PUT", CONSENT, json={"decision": "declined", "text_version": VERSION}
    )
    assert again.status_code == 200
    assert decisions(student) == [("declined", VERSION, NOW)]
    assert (await registrations(control["class_id"]))["test@x.no"]["consent"] == "declined"
    given = await call(
        "test@x.no", "PUT", CONSENT, json={"decision": "given", "text_version": VERSION}
    )
    assert given.json()["decision"] == "given"
    assert [d for d, *_ in decisions(student)] == ["declined", "given"]
    assert (await registrations(control["class_id"]))["test@x.no"]["consent"] == "given"
    back = await call(
        "test@x.no", "PUT", CONSENT, json={"decision": "declined", "text_version": VERSION}
    )
    assert refusal(back) == (409, "consent_given", {"decision": "consent_given"})
    # A decision on an older text is no decision on the current one.
    execute("UPDATE test_student_consents SET text_version = 'gammel' WHERE user_id = %s", student)
    assert (await call("test@x.no", "GET", CONSENT)).json()["decision"] is None


async def test_only_a_test_student_reads_or_gives_consent(people):
    for email in (STUDENT, LECTURER, ADMIN):
        assert (await call(email, "GET", CONSENT)).status_code == 403
        put = await call(email, "PUT", CONSENT, json={"decision": "given", "text_version": VERSION})
        assert put.status_code == 403
    assert rows("SELECT count(*) FROM test_student_consents") == [(0,)]


# Allocation and seating.


async def dated(session_id: str) -> None:
    saved = await call(
        ADMIN,
        "PUT",
        f"/api/class-sessions/{session_id}",
        json={"ai_mode": "rule_based", "dates": iso(PLAN)},
    )
    assert saved.status_code == 200, saved.text


async def test_the_allocation_waits_until_every_test_student_has_consented(control):
    session_id, class_id = control["id"], control["class_id"]
    await dated(session_id)
    first = await enrol(class_id, "t1@x.no", "given")
    second = await enrol(class_id, "t2@x.no", "declined")
    third = await enrol(class_id, "t3@x.no")
    read = (await call(ADMIN, "GET", path(session_id))).json()
    assert (read["registered_count"], read["consent_missing"]) == (3, 2)
    refused = await open_(session_id, ADMIN)
    assert refusal(refused) == (
        409,
        "consent_missing",
        {"allocation": "consent_missing", "missing": "2"},
    )
    assert (await call(ADMIN, "GET", path(session_id))).json()["draft"] is None
    for user_id in (second, third):
        await identity.decide_consent(user_id, "given", VERSION, now=NOW)
    drawn = await open_(session_id, ADMIN)
    assert drawn.status_code == 200, drawn.text
    assert drawn.json()["consent_missing"] == 0
    draft = drawn.json()["draft"]
    # A fourth test student registers without consent: the confirm waits for them too.
    fourth = await enrol(class_id, "t4@x.no")
    waiting = await confirm(session_id, draft, ADMIN)
    assert refusal(waiting) == (
        409,
        "consent_missing",
        {"allocation": "consent_missing", "missing": "1"},
    )
    assert refusal(await redraw(session_id, ADMIN))[1] == "consent_missing"
    assert committed(session_id) == []
    await identity.decide_consent(fourth, "given", VERSION, now=NOW)
    confirmed = await confirm(session_id, draft, ADMIN)
    assert confirmed.status_code == 200, confirmed.text
    # The Control test plays ordinary Class games on its own budget row (AD-6, AD-27).
    assert {
        p for (p,) in rows("SELECT purpose FROM games WHERE class_session_id = %s", session_id)
    } == {"class"}
    assert await budget.get(budget.BudgetScope.class_session(session_id)) is not None
    seated = {u for *_, u in committed(session_id)}
    assert seated == {str(first), str(second), str(third)}


async def test_the_lock_and_the_late_seating_leave_out_a_test_student_without_consent(control):
    session_id, class_id = control["id"], control["class_id"]
    await dated(session_id)
    given = await enrol(class_id, "t1@x.no", "given")
    waiting = await enrol(class_id, "t2@x.no", "declined")
    assert await sessions.lock_due(uuid.UUID(session_id), START + MINUTE) is True
    assert {u for *_, u in committed(session_id)} - {None} == {str(given)}
    later = START + 2 * MINUTE
    assert await sessions.late_registrants(later) == []
    assert await sessions.seat_late_registrant(uuid.UUID(session_id), waiting, now=later) is False
    # Once they consent, the next sweep seats them in a game that has not started.
    await identity.decide_consent(waiting, "given", VERSION, now=later)
    assert await sessions.late_registrants(later) == [(uuid.UUID(session_id), waiting)]


# Kept out of every ordinary list (AD-13), and the reads Epic 13 registers.


async def test_no_ordinary_lecturer_assistant_or_student_meets_a_test_student(people, control):
    test_id = await enrol(control["class_id"], "test@x.no", "given")
    ordinary = people["class"]
    course = (await call(LECTURER, "POST", class_path(ordinary, "/class-sessions"))).json()["id"]
    reads = {
        LECTURER: [
            class_path(ordinary, "/registrations"),
            f"/api/class-sessions/{course}/allocation",
            f"/api/class-sessions/{course}/overview",
            "/api/classes",
            "/api/lecturer-home/class-sessions",
        ],
        ASSISTANT: [f"/api/class-sessions/{course}/overview", "/api/classes"],
        STUDENT: ["/api/classes/enrolled", "/api/me/class-sessions"],
    }
    for email, paths in reads.items():
        for read_path in paths:
            response = await call(email, "GET", read_path)
            assert response.status_code == 200, (email, read_path, response.text)
            assert str(test_id) not in response.text and "test@x.no" not in response.text
    async with get_sessionmaker().begin() as s:
        found = await identity.test_students(s, [test_id, await make("o@x.no", roles=())])
        assert found == {test_id}
        assert await identity.is_test_student(s, test_id) is True
        assert await identity.consented_users(s, [test_id]) == {test_id}


async def test_with_student_choice_a_test_student_without_consent_takes_and_is_drawn_no_seat(
    control, monkeypatch
):
    flag(monkeypatch, True)
    session_id, class_id = control["id"], control["class_id"]
    given = await enrol(class_id, "t1@x.no", "given")
    waiting = await enrol(class_id, "t2@x.no")
    saved = await call(
        ADMIN,
        "PUT",
        f"/api/class-sessions/{session_id}",
        json={"ai_mode": "rule_based", "dates": iso(PLAN), "allocation_method": "student_choice"},
    )
    assert saved.status_code == 200, saved.text
    refused = await take(session_id, "t2@x.no", 1, "retailer")
    assert refusal(refused) == (409, "consent_missing", {"seat": "consent_missing", "missing": "1"})
    assert (await take(session_id, "t1@x.no", 1, "factory")).status_code == 200
    assert {u for *_, u in committed(session_id)} - {None} == {str(given)}
    # The lock draws a Seat for no one who has not consented.
    assert await sessions.lock_due(uuid.UUID(session_id), START + MINUTE) is True
    assert {u for *_, u in committed(session_id)} - {None} == {str(given)}
    assert str(waiting) not in {u for *_, u in committed(session_id)}


NB = Path(__file__).resolve().parents[3] / "frontend" / "src" / "copy" / "nb.ts"


@pytest.mark.skipif(not NB.exists(), reason="the web app's copy is not in this checkout")
def test_the_web_app_shows_the_consent_text_of_the_current_version():
    """`nb.homes.consent.version` names the text Hjem shows; a PUT of another version is refused,
    so the two must agree or no one can consent."""
    block = NB.read_text(encoding="utf-8").split("consent: {", 1)[1]
    found = re.search(r'version: "([^"]+)"', block)
    assert found is not None and found.group(1) == VERSION
