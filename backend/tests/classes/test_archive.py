"""Archiving a Class (Story 4.10, FR-2, FR-6, AD-8, AD-12, AD-15): the archive transaction, what an
archived Class allows on every Class route for every role, its old Invitation links, what its
Students see, the Lecturer-revoke blocker and `is_writable`. The api's clock is fixed (2026-11-19
09:00 UTC); the database clock is never read, and nothing is ordered by a timestamp."""

import asyncio
import uuid
from datetime import timedelta

import pytest
import structlog.testing

from app.modules.classes import repo as classes_repo
from app.modules.classes import service as classes
from app.modules.identity import repo as identity_repo
from app.modules.identity import service as identity
from app.modules.identity.schemas import AccountRole
from app.platform import auth
from tests.classes.test_classes import LECTURER, OTHER, PASSWORD, as_user, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_send import staged_id, staging_count
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_staff import (
    ASSISTANT,
    EMAIL,
    MANAGERS,
    READERS,
    ROLES,
    call,
    class_routes,
    invite,
    put_staff,
    shared,
)
from tests.classes.test_student_registration import (
    accept,
    check,
    emitted,
    second_class,
)
from tests.classes.test_student_registration import invite as invite_students
from tests.identity.helpers import CSRF, client
from tests.messaging.helpers import rows

__all__ = ["clock", "emitted", "klass", "shared"]


@pytest.fixture(autouse=True)
def _empty_mail(mail_db):
    """The mail tables and the mock outbox empty, before `klass` makes its Users."""


async def archive(class_id: str, email: str = LECTURER):
    return await call(email, "POST", f"/api/classes/{class_id}/archive")


def voided(address: str) -> list[bool]:
    return [
        v is not None
        for (v,) in rows("SELECT voided_at FROM invitations WHERE email = %s", address)
    ]


# The archive itself.


async def test_archiving_closes_the_class_in_one_transaction_and_tells_its_staff(klass, emitted):
    assistant = await make(ASSISTANT, roles=())
    put_staff(klass, assistant, "assistant")
    await invite_students(klass, "ola@x.no", "kari@x.no")
    # Kari's link has expired already: it stays as it is and still counts as expired.
    execute(
        "UPDATE invitations SET expires_at = %s WHERE email = 'kari@x.no'", NOW - timedelta(hours=1)
    )
    assert (await invite(klass, "ny-assistent@x.no")).status_code == 201
    async with client() as c:
        await as_user(c)
        await staged_id(c, klass, "per@x.no")
    emitted.clear()

    response = await archive(klass)

    assert response.status_code == 200
    body = response.json()
    assert (body["id"], body["archived"], body["can_manage"]) == (klass, True, True)
    assert rows("SELECT archived_at FROM classes WHERE id = %s", klass) == [(NOW,)]
    assert (voided("ola@x.no"), voided("kari@x.no"), voided("ny-assistent@x.no")) == (
        [True],
        [False],
        [True],
    )
    assert staging_count() == 0
    [(targets, change)] = rows(
        "SELECT target_ids, change FROM audit_events WHERE action = 'class.archived'"
    )
    assert (targets, change) == ({"class_id": klass}, {"voided_invitations": 2})
    owner = rows("SELECT id FROM users WHERE email = %s", LECTURER)[0][0]
    assert sorted(emitted) == sorted([("user", str(owner)), ("user", str(assistant))])
    # The counts keep the expired Invitation; the status list has no live link left.
    summary = (await call(LECTURER, "GET", f"/api/classes/{klass}/invitations")).json()
    assert summary["expired"] == 2  # Kari's expired link and Ola's stopped one (Issue #93)
    statuses = (await call(LECTURER, "GET", f"/api/classes/{klass}/registrations")).json()
    assert {i["status"] for i in statuses["items"]} == {"unregistered"}
    # A second archive is a change like any other.
    again = await archive(klass)
    assert (again.status_code, again.json()["error"]["code"]) == (409, "class_archived")


async def test_only_the_classes_faglaerere_may_archive_it(shared):
    for role in ROLES:
        if role in MANAGERS:
            continue
        response = await archive(shared, EMAIL[role])
        assert (response.status_code, response.json()["error"]["code"]) == (403, "forbidden"), role
    assert rows("SELECT archived_at FROM classes WHERE id = %s", shared) == [(None,)]


async def test_archiving_logs_ids_never_addresses(klass):
    await invite_students(klass, "ola@x.no")
    with structlog.testing.capture_logs() as logs:
        assert (await archive(klass)).status_code == 200
        assert (await invite(klass, "ny@x.no")).status_code == 409
    text = repr(logs)
    assert "ola@x.no" not in text and "ny@x.no" not in text
    assert {"class_archived", "class_change_refused"} <= {e["event"] for e in logs}


# What an archived Class allows (FR-6): every Class route, for every role.

GET_FOR_MANAGERS = {"/roster-upload", "/staff"}


@pytest.fixture
async def archived(shared) -> str:
    """The shared Class with its Student registered by hand, then archived by its owner."""
    registered = await call(
        LECTURER,
        "POST",
        f"/api/classes/{shared}/roster/manual",
        json={"email": EMAIL["student"], "name": "Stine Student"},
    )
    assert registered.status_code == 201
    async with client() as c:
        await as_user(c, EMAIL["student"])
        assert [i["id"] for i in (await c.get("/api/classes/enrolled")).json()["items"]] == [shared]
    assert (await archive(shared)).status_code == 200
    return shared


@pytest.mark.parametrize("role", ROLES)
async def test_an_archived_class_is_read_only_for_every_role_on_every_route(archived, role):
    routes = [*class_routes(archived), ("manage", "POST", f"/api/classes/{archived}/archive", {})]
    async with client() as c:
        await as_user(c, EMAIL[role])
        for kind, method, path, kw in routes:
            headers = {**CSRF, **kw.pop("headers", {})}
            response = await c.request(method, path, headers=headers, **kw)
            readable = kind == "read" or (
                method == "GET"
                and path.removeprefix(f"/api/classes/{archived}") in GET_FOR_MANAGERS
            )
            allowed = READERS if kind == "read" else MANAGERS
            if role not in allowed:
                expected = (403, "forbidden")
            elif readable:
                expected = (200, None)
            else:
                expected = (409, "class_archived")
            code = response.json()["error"]["code"] if response.status_code >= 400 else None
            assert (response.status_code, code) == expected, (role, method, path, response.text)
        listed = (await c.get("/api/classes")).json() if role in READERS else {"items": []}
        enrolled = (await c.get("/api/classes/enrolled")).json()["items"]
        enrolled_one = await c.get(f"/api/classes/enrolled/{archived}")
    assert [(i["id"], i["archived"]) for i in listed["items"]] == (
        [(archived, True)] if role in READERS else []
    )
    # Its Student no longer sees it (nor does anyone else).
    assert enrolled == [] and enrolled_one.status_code == 403
    if role in MANAGERS:  # nothing staged survives the archive
        upload = await call(EMAIL[role], "GET", f"/api/classes/{archived}/roster-upload")
        assert upload.json() == {"upload": None}


NOBODY = "00000000-0000-4000-8000-000000000000"
UNDER_WAY = [
    ("POST", "/invitations", {"upload_id": NOBODY, "valid_days": 14}),
    ("POST", "/reminders", {"valid_days": 14}),
    ("POST", "/roster/entries", {"email": "ny@x.no"}),
    ("POST", "/roster/manual", {"email": "ny@x.no", "name": "Ny Student"}),
    ("DELETE", f"/roster/entries/{NOBODY}", None),
    ("POST", "/staff/lecturers", {"email": OTHER}),
    ("POST", "/staff/assistants", {"email": "ny@x.no"}),
    ("DELETE", f"/staff/{NOBODY}", None),
    ("DELETE", f"/staff/invitations/{NOBODY}", None),
]


def footprint() -> tuple:
    return tuple(
        rows(f"SELECT count(*) FROM {table}")[0][0]  # noqa: S608 - fixed table names
        for table in ("roster_entries", "invitations", "class_staff", "audit_events", "users")
    )


@pytest.mark.parametrize(
    ("method", "rest", "body"), UNDER_WAY, ids=[f"{m} {r}" for m, r, _ in UNDER_WAY]
)
async def test_a_change_under_way_when_the_class_is_archived_is_refused(
    klass, monkeypatch, method, rest, body
):
    """The second check, inside the change's own transaction: the Class was archived after the
    first check passed. Nothing is written."""
    await invite_students(klass, "ola@x.no")  # something for a reminder to reach
    real = classes.manageable

    async def first_check_passes_then_archived(user, class_id):
        answer = await real(user, class_id)
        execute("UPDATE classes SET archived_at = %s WHERE id = %s", NOW, class_id)
        return answer

    monkeypatch.setattr(classes, "manageable", first_check_passes_then_archived)
    before = footprint()
    kw = {} if body is None else {"json": body}
    response = await call(LECTURER, method, f"/api/classes/{klass}{rest}", **kw)
    assert (response.status_code, response.json()["error"]["code"]) == (409, "class_archived")
    assert footprint() == before


# Old links (Stories 4.5, 4.9): the expired-link state, and no one joins.


async def test_the_links_of_an_archived_class_register_no_one(klass):
    students = await invite_students(klass, "ola@x.no")
    assert (await invite(klass)).status_code == 201
    [(assistant_id,)] = rows("SELECT id FROM invitations WHERE kind = 'assistant'")
    assistant = auth.link_token(identity.INVITATION, assistant_id)
    assert (await archive(klass)).status_code == 200
    async with client() as c:
        answers = [
            await step(c, token)
            for token in (students["ola@x.no"], assistant)
            for step in (check, accept)
        ]
        renewal = await c.post(
            "/api/auth/invitation/renewal", json={"token": students["ola@x.no"]}, headers=CSRF
        )
    assert [a.status_code for a in answers] == [410] * 4
    assert {a.json()["error"]["code"] for a in answers} == {"invitation_link_invalid"}
    # The check tells the link's holder there is no new Invitation to ask for (Issue #93).
    assert [a.json()["error"]["fields"] for a in answers[::2]] == [{"class_archived": True}] * 2
    assert renewal.status_code == 202
    assert rows("SELECT count(*) FROM invitations WHERE renewal_requested_at IS NOT NULL") == [(0,)]
    assert rows("SELECT id FROM users WHERE email IN ('ola@x.no', %s)", ASSISTANT) == []
    assert rows("SELECT registration, user_id FROM roster_entries") == [("invited", None)]
    assert len(rows("SELECT 1 FROM class_staff WHERE class_id = %s", klass)) == 1


@pytest.mark.parametrize("existing", [False, True], ids=["new account", "existing account"])
async def test_an_assistant_accepting_while_the_class_is_archived_never_deadlocks(
    klass, monkeypatch, existing
):
    """Issue #93: the Assistant accepts at the instant the owner archives. Each side is held after
    its first lock until the other has taken its own (or a short wait ends). When the acceptance
    locked its Invitation before the Class row, the archive (Class row, then the Invitations it
    voids) closed a cycle and Postgres aborted one with a 500. Now the acceptance takes the Class
    row first: the two run in turn, and either the Assistant joined before the archive or the link
    was void."""
    if existing:
        await make(ASSISTANT, roles=())
    assert (await invite(klass)).status_code == 201
    [(invitation_id,)] = rows("SELECT id FROM invitations WHERE kind = 'assistant'")
    token = auth.link_token(identity.INVITATION, invitation_id)
    class_locked, invitation_locked = asyncio.Event(), asyncio.Event()
    real_class_state, real_lock_invitation = classes_repo.class_state, identity_repo.lock_invitation

    async def hold(mine: asyncio.Event, other: asyncio.Event) -> None:
        mine.set()
        try:
            await asyncio.wait_for(other.wait(), timeout=0.5)
        except TimeoutError:
            pass

    async def held_class_state(session, class_id, *, exclusive):
        found = await real_class_state(session, class_id, exclusive=exclusive)
        await hold(class_locked, invitation_locked)
        return found

    async def held_lock_invitation(session, invitation_id):
        found = await real_lock_invitation(session, invitation_id)
        await hold(invitation_locked, class_locked)
        return found

    async with client() as owner, client("198.51.100.9") as assistant:
        await as_user(owner)
        monkeypatch.setattr(classes_repo, "class_state", held_class_state)
        monkeypatch.setattr(identity_repo, "lock_invitation", held_lock_invitation)
        if existing:
            path, body = "/api/auth/invitation/accept-login", {"password": PASSWORD}
        else:
            path, body = "/api/auth/invitation/accept", {"name": "Ada", "password": "et-passord-1"}
        answers = await asyncio.gather(
            assistant.post(path, json={"token": token, **body}, headers=CSRF),
            owner.post(f"/api/classes/{klass}/archive", headers=CSRF),
            return_exceptions=True,
        )
    accepted, archived = answers
    assert not isinstance(accepted, BaseException), accepted
    assert not isinstance(archived, BaseException), archived
    assert archived.status_code == 200
    assert accepted.status_code in (200, 410)
    joined = rows(
        "SELECT count(*) FROM class_staff s JOIN users u ON u.id = s.user_id "
        "WHERE s.class_id = %s AND u.email = %s",
        klass,
        ASSISTANT,
    )
    assert joined == [(1 if accepted.status_code == 200 else 0,)]


async def test_an_open_link_to_an_archived_class_is_refused_too(klass):
    """Should a link still be open (archived by other means), «Du er invitert» refuses it."""
    students = await invite_students(klass, "ola@x.no")
    execute("UPDATE classes SET archived_at = %s WHERE id = %s", NOW, klass)
    async with client() as c:
        answers = [await check(c, students["ola@x.no"]), await accept(c, students["ola@x.no"])]
    assert [a.status_code for a in answers] == [410, 410]
    assert rows("SELECT registration FROM roster_entries") == [("invited",)]


# The Lecturer-revoke blocker (Story 3.9) and `is_writable` (Epic 5).


async def test_the_revoke_blocker_counts_active_owned_and_co_owned_classes_only(klass):
    other = rows("SELECT id FROM users WHERE email = %s", OTHER)[0][0]
    own = await second_class("kari sin")
    put_staff(own, other, "owner")
    execute("DELETE FROM class_staff WHERE class_id = %s AND user_id <> %s", own, other)
    assert (await archive(own, OTHER)).status_code == 200
    put_staff(klass, other, "owner")  # co-owner of an active Class
    blocked = await identity.revoke_role(other, other, AccountRole.lecturer, now=NOW)
    assert (blocked.code, blocked.classes) == ("role_revoke_blocked", 1)
    assert (await archive(klass)).status_code == 200
    allowed = await identity.revoke_role(other, other, AccountRole.lecturer, now=NOW)
    assert getattr(allowed, "code", None) != "role_revoke_blocked"
    assert rows("SELECT role FROM user_roles WHERE user_id = %s", other) == []


async def test_is_writable_answers_for_later_epics(klass):
    class_id = uuid.UUID(klass)
    assert await classes.is_writable(class_id) is True
    assert await classes.is_writable(uuid.uuid4()) is False
    assert (await archive(klass)).status_code == 200
    assert await classes.is_writable(class_id) is False
