"""Sharing a Class (Story 4.9, FR-5, FR-10, AD-8, AD-9, AD-12, AD-15): co-owner Lecturers with the
owner's rights, Assistant lecturers invited by e-mail for one Class, what each staff role may do
on every Class route, removal and the last-owner rule. The api's clock is fixed (2026-11-19 09:00
UTC); the database clock is never read, and nothing is ordered by a timestamp."""

import re
import uuid

import pytest
import structlog.testing

from app.modules.identity import service as identity
from app.modules.identity.schemas import AccountRole
from tests.classes.test_classes import LECTURER, OTHER, PASSWORD, as_user, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_student_registration import emitted, second_class
from tests.identity.helpers import CSRF, client, login
from tests.messaging.helpers import drain, mails, rows

__all__ = ["clock", "emitted", "klass"]

LINK = re.compile(r"/invitasjon#([A-Za-z0-9_-]+)")
ASSISTANT = "assistent@x.no"
NEW_PASSWORD = "mitt-forste-passord"


@pytest.fixture(autouse=True)
def _empty_mail(mail_db):
    """The mail tables and the mock outbox empty, before `klass` makes its Users."""


def put_staff(class_id: str, user_id: uuid.UUID, role: str) -> None:
    execute(
        "INSERT INTO class_staff (class_id, user_id, role, added_at) VALUES (%s, %s, %s, %s)",
        class_id,
        user_id,
        role,
        NOW,
    )


def staff_rows(class_id: str) -> set[tuple]:
    return {
        (str(user_id), role)
        for user_id, role in rows(
            "SELECT user_id, role FROM class_staff WHERE class_id = %s", class_id
        )
    }


def audit_actions() -> list[str]:
    return sorted(
        a for (a,) in rows("SELECT action FROM audit_events WHERE action LIKE 'class_staff%%'")
    )


async def call(email: str, method: str, path: str, **kw):
    async with client() as c:
        await as_user(c, email)
        return await c.request(method, path, headers={**CSRF, **kw.pop("headers", {})}, **kw)


async def staff(class_id: str, email: str = LECTURER) -> dict:
    response = await call(email, "GET", f"/api/classes/{class_id}/staff")
    assert response.status_code == 200
    return response.json()


async def invite(class_id: str, address: str = ASSISTANT, email: str = LECTURER):
    return await call(
        email, "POST", f"/api/classes/{class_id}/staff/assistants", json={"email": address}
    )


async def add_lecturer(class_id: str, address: str, email: str = LECTURER):
    return await call(
        email, "POST", f"/api/classes/{class_id}/staff/lecturers", json={"email": address}
    )


async def link_of(address: str) -> str:
    await drain(NOW)
    found = [m for m in mails() if m.to == address]
    return LINK.search(found[-1].text).group(1)


# What each staff role may do (AD-12): every Class route, once per role.

ROLES = ["owner", "co_owner", "assistant", "lecturer_assistant", "outsider", "student"]
READERS = {"owner", "co_owner", "assistant", "lecturer_assistant"}
MANAGERS = {"owner", "co_owner"}
EMAIL = {
    "owner": LECTURER,
    "co_owner": "medeier@x.no",
    "assistant": "assistent@x.no",
    "lecturer_assistant": "laerer-assistent@x.no",
    "outsider": OTHER,
    "student": "student@x.no",
}


def class_routes(class_id: str) -> list[tuple[str, str, str, dict]]:
    """(kind, method, path, request keywords) of every route on one Class. Ids that name nothing
    keep an allowed call harmless."""
    base = f"/api/classes/{class_id}"
    nobody = str(uuid.uuid4())
    return [
        ("read", "GET", base, {}),
        ("read", "GET", f"{base}/registrations", {}),
        ("read", "GET", f"{base}/invitations", {}),
        (
            "manage",
            "POST",
            f"{base}/roster-upload",
            {"content": b"", "headers": {"X-File-Name": "a.csv"}},
        ),
        ("manage", "POST", f"{base}/roster-paste", {"json": {"text": "a@x.no"}}),
        ("manage", "GET", f"{base}/roster-upload", {}),
        ("manage", "PUT", f"{base}/roster-upload/column", {"json": {"column": 0}}),
        ("manage", "DELETE", f"{base}/roster-upload", {}),
        (
            "manage",
            "POST",
            f"{base}/invitations",
            {"json": {"upload_id": nobody, "valid_days": 14}},
        ),
        ("manage", "POST", f"{base}/reminders", {"json": {"valid_days": 14}}),
        ("manage", "POST", f"{base}/roster/entries", {"json": {"email": "x@"}}),
        ("manage", "POST", f"{base}/roster/manual", {"json": {"email": "x@", "name": "X"}}),
        ("manage", "DELETE", f"{base}/roster/entries/{nobody}", {}),
        ("manage", "GET", f"{base}/staff", {}),
        ("manage", "POST", f"{base}/staff/lecturers", {"json": {"email": "x@"}}),
        ("manage", "POST", f"{base}/staff/assistants", {"json": {"email": "x@"}}),
        ("manage", "DELETE", f"{base}/staff/{nobody}", {}),
        ("manage", "DELETE", f"{base}/staff/invitations/{nobody}", {}),
    ]


@pytest.fixture
async def shared(klass) -> str:
    """The Class with one of each staff role, and a Student and an outsider Lecturer."""
    put_staff(klass, await make(EMAIL["co_owner"]), "owner")
    put_staff(klass, await make(EMAIL["assistant"], roles=()), "assistant")
    put_staff(klass, await make(EMAIL["lecturer_assistant"]), "assistant")
    await make(EMAIL["student"], roles=())
    return klass


@pytest.mark.parametrize("role", ROLES)
async def test_each_staff_role_reaches_exactly_its_class_routes(shared, role):
    allowed = {"read": READERS, "manage": MANAGERS}
    async with client() as c:
        await as_user(c, EMAIL[role])
        for kind, method, path, kw in class_routes(shared):
            headers = {**CSRF, **kw.pop("headers", {})}
            response = await c.request(method, path, headers=headers, **kw)
            refused = response.status_code == 403
            assert refused is (role not in allowed[kind]), (role, method, path, response.text)
        listed = (await c.get("/api/classes")).json()["items"] if role != "student" else []
        creates = await c.post("/api/classes", json={}, headers=CSRF)
        institutions = await c.get("/api/classes/institutions")
        home = (await c.get("/api/auth/me")).json()["user"]["roles"]
    assert [item["id"] for item in listed] == ([shared] if role in READERS else [])
    lecturer = role not in {"assistant", "student"}
    assert (creates.status_code == 403, institutions.status_code == 403) == (
        not lecturer,
        not lecturer,
    )
    assert ("assistant" in home) is (role in {"assistant", "lecturer_assistant"})


async def test_an_assistant_reads_the_class_but_is_told_it_cannot_manage_it(shared):
    owner = (await call(LECTURER, "GET", f"/api/classes/{shared}")).json()
    assistant = (await call(EMAIL["assistant"], "GET", f"/api/classes/{shared}")).json()
    assert (owner["staff_role"], owner["can_manage"]) == ("owner", True)
    assert (assistant["staff_role"], assistant["can_manage"]) == ("assistant", False)


# «Legg til Faglærer».


async def test_a_lecturer_added_becomes_co_owner_with_the_owners_rights(klass, emitted):
    other = rows("SELECT id FROM users WHERE email = %s", OTHER)[0][0]
    response = await add_lecturer(klass, " Kari@Example.com ")
    assert response.status_code == 201
    assert response.json() == {"user_id": str(other), "name": "Kari", "email": OTHER}
    assert (str(other), "owner") in staff_rows(klass)
    assert ("user", str(other)) in emitted
    assert audit_actions() == ["class_staff.added"]
    [(targets,)] = rows("SELECT target_ids FROM audit_events WHERE action = 'class_staff.added'")
    assert targets == {"class_id": klass, "user_id": str(other)}
    # The co-owner manages the Class as its creator does, and can share it further.
    assert (await call(OTHER, "GET", f"/api/classes/{klass}/staff")).status_code == 200
    assert (await invite(klass, email=OTHER)).status_code == 201
    listed = await staff(klass)
    assert [p["email"] for p in listed["lecturers"]] == [LECTURER, OTHER]


@pytest.mark.parametrize("case", ["no_account", "no_role", "deactivated", "admin_only"])
async def test_an_address_that_is_no_lecturer_gets_one_reason(klass, case):
    if case == "no_role":
        await make("ingen@x.no", roles=())
    if case == "admin_only":
        # The Admin role grants the Class actions on a Control test Class only (Story 12.7): it
        # never makes a User a Lecturer.
        await make("ingen@x.no", roles=(AccountRole.admin,))
    if case == "deactivated":
        user_id = await make("ingen@x.no")
        execute("UPDATE users SET is_active = false WHERE id = %s", user_id)
    response = await add_lecturer(klass, "ingen@x.no")
    assert response.status_code == 422
    assert response.json()["error"]["fields"] == {"email": "not_lecturer"}
    assert len(staff_rows(klass)) == 1


async def test_an_owner_again_or_a_malformed_address_is_refused(klass):
    assert (await add_lecturer(klass, LECTURER)).json()["error"]["fields"] == {
        "email": "already_staff"
    }
    assert (await add_lecturer(klass, "x@")).json()["error"]["fields"] == {
        "email": "missing_domain"
    }


async def test_an_assistant_who_is_a_lecturer_is_promoted(klass, emitted):
    user_id = await make("laerer@x.no")
    put_staff(klass, user_id, "assistant")
    response = await add_lecturer(klass, "laerer@x.no")
    assert response.status_code == 201
    assert (str(user_id), "owner") in staff_rows(klass)
    assert ("user", str(user_id)) in emitted
    [(change,)] = rows("SELECT change FROM audit_events WHERE action = 'class_staff.added'")
    assert change == {"role": "owner", "previous_role": "assistant"}


async def test_a_lecturer_added_has_their_open_assistant_invitation_voided(klass):
    await make("laerer@x.no")
    assert (await invite(klass, "laerer@x.no")).status_code == 201
    token = await link_of("laerer@x.no")
    assert (await add_lecturer(klass, "laerer@x.no")).status_code == 201
    async with client() as c:
        check = await c.post("/api/auth/invitation/check", json={"token": token}, headers=CSRF)
    assert check.status_code == 410


async def test_an_assistant_logging_in_gets_the_assistant_role(klass):
    """The login answer carries the session role, so «Logg inn» sends them to the Lærerhjem."""
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")
    async with client() as c:
        response = await login(c, ASSISTANT, PASSWORD)
    assert response.json()["user"]["roles"] == ["assistant"]


async def test_a_co_owned_class_blocks_the_revoke_of_the_lecturer_role(klass):
    """Story 3.9's blocker counts owned Classes; a co-owner is an owner."""
    assert (await add_lecturer(klass, OTHER)).status_code == 201
    other = rows("SELECT id FROM users WHERE email = %s", OTHER)[0][0]
    refused = await identity.revoke_role(other, other, AccountRole.lecturer, now=NOW)
    assert (refused.code, refused.classes) == ("role_revoke_blocked", 1)


# «Inviter Assistent» and its acceptance.


async def test_an_assistant_invitation_is_listed_mailed_and_accepted_into_one_class(klass, emitted):
    other_class = await second_class()
    response = await invite(klass, " Assistent@X.no ")
    assert response.status_code == 201
    body = response.json()
    assert (body["email"], body["status"], body["last_valid_day"], body["user_id"]) == (
        ASSISTANT,
        "invited",
        "2026-12-03",
        None,
    )
    assert (await staff(klass))["assistants"] == [body]
    [(kind, role, entry)] = rows(
        "SELECT kind, role, roster_entry_id FROM invitations WHERE class_id = %s", klass
    )
    assert (kind, role, entry) == ("assistant", None, None)
    token = await link_of(ASSISTANT)
    [mail] = mails()
    assert (mail.subject, "Assistent i Klassen class-of-1994" in mail.text) == (
        "Invitasjon til ØL-spillet",
        True,
    )
    assert "til og med 3. desember 2026" in mail.text

    async with client() as c:
        checked = await c.post("/api/auth/invitation/check", json={"token": token}, headers=CSRF)
        assert checked.status_code == 200
        assert {k: checked.json()[k] for k in ("kind", "role", "class_name", "invited_by")} == {
            "kind": "assistant",
            "role": None,
            "class_name": "class-of-1994",
            "invited_by": "Bard",
        }
        accepted = await c.post(
            "/api/auth/invitation/accept",
            json={"token": token, "name": "Ada Assistent", "password": NEW_PASSWORD},
            headers=CSRF,
        )
        assert accepted.status_code == 200
        assert accepted.json()["user"]["roles"] == ["assistant"]
        user_id = accepted.json()["user"]["id"]
        assert rows("SELECT role FROM user_roles WHERE user_id = %s", user_id) == []
        assert (user_id, "assistant") in staff_rows(klass)
        assert ("user", user_id) in emitted
        # The Lærerhjem holds this Class only; the other Class is refused as one that is not.
        assert [i["id"] for i in (await c.get("/api/classes")).json()["items"]] == [klass]
        assert (await c.get(f"/api/classes/{klass}/registrations")).status_code == 200
        assert (await c.get(f"/api/classes/{other_class}")).status_code == 403
        assert (await c.get(f"/api/classes/{other_class}/registrations")).status_code == 403
        again = await c.post("/api/auth/invitation/check", json={"token": token}, headers=CSRF)
        assert again.status_code == 410
    listed = (await staff(klass))["assistants"]
    assert [(a["email"], a["status"], a["name"]) for a in listed] == [
        (ASSISTANT, "active", "Ada Assistent")
    ]
    assert audit_actions() == ["class_staff.invited", "class_staff.joined"]


async def test_an_existing_user_accepts_with_their_password_and_stays_one_user(klass):
    user_id = await make(ASSISTANT, roles=())
    assert (await invite(klass)).status_code == 201
    token = await link_of(ASSISTANT)
    async with client() as c:
        accepted = await c.post(
            "/api/auth/invitation/accept-login",
            json={"token": token, "password": PASSWORD},
            headers=CSRF,
        )
    assert accepted.status_code == 200
    assert accepted.json()["user"]["roles"] == ["assistant"]
    assert rows("SELECT count(*) FROM users WHERE email = %s", ASSISTANT) == [(1,)]
    assert (str(user_id), "assistant") in staff_rows(klass)


async def test_inviting_again_voids_the_old_link_and_withdrawing_voids_the_new(klass):
    assert (await invite(klass)).status_code == 201
    first = await link_of(ASSISTANT)
    second = await invite(klass)
    assert second.status_code == 201
    async with client() as c:
        check = await c.post("/api/auth/invitation/check", json={"token": first}, headers=CSRF)
        assert check.status_code == 410
    token = await link_of(ASSISTANT)
    invitation = second.json()["invitation_id"]
    path = f"/api/classes/{klass}/staff/invitations/{invitation}"
    assert (await call(LECTURER, "DELETE", path)).status_code == 204
    assert (await call(LECTURER, "DELETE", path)).status_code == 404
    async with client() as c:
        check = await c.post("/api/auth/invitation/check", json={"token": token}, headers=CSRF)
        assert check.status_code == 410
    assert (await staff(klass))["assistants"] == []


async def test_staff_of_the_class_cannot_be_invited_and_an_expired_invitation_reads_expired(klass):
    assert (await invite(klass, LECTURER)).json()["error"]["fields"] == {"email": "already_staff"}
    assert (await invite(klass, "a@")).json()["error"]["fields"] == {"email": "missing_domain"}
    assert (await invite(klass)).status_code == 201
    execute("UPDATE invitations SET expires_at = %s WHERE email = %s", NOW, ASSISTANT)
    [row] = (await staff(klass))["assistants"]
    assert (row["status"], row["last_valid_day"]) == ("expired", None)


# Removal and the last owner.


async def test_a_removed_assistant_loses_access_at_the_next_request(klass, emitted):
    user_id = await make(ASSISTANT, roles=())
    put_staff(klass, user_id, "assistant")
    async with client() as c:
        await as_user(c, ASSISTANT)
        assert (await c.get(f"/api/classes/{klass}")).status_code == 200
        removed = await call(LECTURER, "DELETE", f"/api/classes/{klass}/staff/{user_id}")
        assert removed.status_code == 204
        assert (await c.get(f"/api/classes/{klass}")).status_code == 403
        assert (await c.get("/api/auth/me")).json()["user"]["roles"] == []
    assert ("user", str(user_id)) in emitted
    assert audit_actions() == ["class_staff.removed"]
    again = await call(LECTURER, "DELETE", f"/api/classes/{klass}/staff/{user_id}")
    assert again.status_code == 404


async def test_the_last_owner_cannot_be_removed_but_one_of_two_can(klass):
    owner = rows("SELECT id FROM users WHERE email = %s", LECTURER)[0][0]
    path = f"/api/classes/{klass}/staff/{owner}"
    refused = await call(LECTURER, "DELETE", path)
    assert (refused.status_code, refused.json()["error"]["code"]) == (422, "last_owner")
    assert (await add_lecturer(klass, OTHER)).status_code == 201
    assert (await call(OTHER, "DELETE", path)).status_code == 204
    assert (await call(LECTURER, "GET", f"/api/classes/{klass}")).status_code == 403
    other = rows("SELECT id FROM users WHERE email = %s", OTHER)[0][0]
    last = await call(OTHER, "DELETE", f"/api/classes/{klass}/staff/{other}")
    assert last.json()["error"]["code"] == "last_owner"
    assert staff_rows(klass) == {(str(other), "owner")}


async def test_staff_commands_log_ids_never_addresses(klass):
    with structlog.testing.capture_logs() as logs:
        await add_lecturer(klass, OTHER)
        await add_lecturer(klass, "ingen@x.no")
        await invite(klass)
    assert logs
    assert not [entry for entry in logs if "@" in repr(entry)]


async def test_another_class_and_a_malformed_id_are_refused_alike(klass):
    async with client() as c:
        assert (await login(c, OTHER, PASSWORD)).status_code == 200
        for path in (f"/api/classes/{klass}/staff", "/api/classes/nope/staff"):
            assert (await c.get(path)).status_code == 403
