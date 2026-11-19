"""Registration status and reminders (Story 4.7, FR-9, NFR-10, AD-9, AD-14): each address's status
read at request time, the totals, `registered_students`, and the reminder command for all or one
address. The api's clock is fixed and moved by monkeypatching `auth.utcnow`; the database clock
is never read, and nothing is ordered by a timestamp."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
import structlog.testing

from app.modules.classes import service as classes
from app.modules.identity import service as identity
from app.platform import auth
from tests.classes.test_classes import OTHER, as_user
from tests.classes.test_invitation_counts import accept, bounce, execute, sent_class
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.identity.helpers import CSRF, client
from tests.messaging.helpers import rows

__all__ = ["clock", "klass"]

EXPIRES = datetime(2026, 12, 3, 23, 0, tzinfo=UTC)
"""Oslo midnight after the 14th day from 2026-11-19: the first sending's expiry."""


@pytest.fixture(autouse=True)
def _empty_mail(mail_db):
    """The mail tables and the mock outbox empty, before `klass` makes its Users."""


def at(monkeypatch, when: datetime) -> None:
    monkeypatch.setattr(auth, "utcnow", lambda: when)


async def statuses(class_id: str, user: str | None = None):
    async with client() as c:
        if user is None:
            await as_user(c)
        else:
            await as_user(c, user)
        return await c.get(f"/api/classes/{class_id}/registrations")


async def remind(class_id: str, valid_days: object = 14, entry: str | None = None):
    body: dict[str, object] = {"valid_days": valid_days}
    if entry is not None:
        body["roster_entry_id"] = entry
    async with client() as c:
        await as_user(c)
        return await c.post(f"/api/classes/{class_id}/reminders", json=body, headers=CSRF)


def by_email(response) -> dict[str, dict]:
    return {item["email"]: item for item in response.json()["items"]}


def open_invitations(address: str) -> int:
    return rows(
        "SELECT count(*) FROM invitations WHERE email = %s AND accepted_at IS NULL "
        "AND voided_at IS NULL",
        address,
    )[0][0]


def invitation_count(address: str) -> int:
    return rows("SELECT count(*) FROM invitations WHERE email = %s", address)[0][0]


async def test_each_status_and_the_totals(klass):
    await sent_class(klass, ["inv@x.no", "reg@x.no", "man@x.no", "exp@x.no", "hb@x.no", "sb@x.no"])
    accept("reg@x.no")
    execute(
        "UPDATE roster_entries SET registration = 'registered_manually' WHERE email = 'man@x.no'"
    )
    execute("UPDATE invitations SET expires_at = %s WHERE email = 'exp@x.no'", NOW)
    await bounce("hb@x.no", "hard")
    await bounce("sb@x.no", "soft")
    response = await statuses(klass)
    assert response.status_code == 200
    body = response.json()
    assert body["totals"] == {"registered": 1, "registered_manually": 1, "unregistered": 4}
    assert body["reminder_count"] == 4
    found = by_email(response)
    assert [i["email"] for i in body["items"]] == sorted(found)
    simple = {
        e: (i["status"], i["last_valid_day"], i["bounce_class"], i["remindable"])
        for e, i in found.items()
    }
    assert simple == {
        "inv@x.no": ("invited", "2026-12-03", None, True),
        "reg@x.no": ("registered", None, None, False),
        "man@x.no": ("registered_manually", None, None, False),
        "exp@x.no": ("unregistered", None, None, True),
        "hb@x.no": ("bounced", None, "hard", False),
        "sb@x.no": ("bounced", None, "soft", True),
    }


async def test_the_expiry_boundary_is_read_on_the_api_clock(klass, monkeypatch):
    await sent_class(klass, ["a@x.no"])
    at(monkeypatch, EXPIRES - timedelta(microseconds=1))
    assert by_email(await statuses(klass))["a@x.no"]["status"] == "invited"
    at(monkeypatch, EXPIRES)
    body = (await statuses(klass)).json()
    assert body["items"][0]["status"] == "unregistered"
    assert body["totals"]["unregistered"] == 1


async def test_a_request_for_a_new_invitation_shows_and_a_reminder_answers_it(klass, monkeypatch):
    await sent_class(klass, ["a@x.no"])
    [(invitation_id,)] = rows("SELECT id FROM invitations")
    token = auth.link_token(identity.INVITATION, invitation_id)
    at(monkeypatch, EXPIRES)
    async with client() as c:
        asked = await c.post("/api/auth/invitation/renewal", json={"token": token}, headers=CSRF)
    assert asked.status_code == 202
    assert by_email(await statuses(klass))["a@x.no"]["status"] == "renewal_requested"
    assert (await remind(klass)).json()["sent"] == 1
    item = by_email(await statuses(klass))["a@x.no"]
    # Sent at Oslo midnight on 4 December: valid through the 14th day after it.
    assert (item["status"], item["last_valid_day"]) == ("invited", "2026-12-18")


async def test_a_renewal_request_outranks_a_bounce(klass, monkeypatch):
    await sent_class(klass, ["a@x.no"])
    await bounce("a@x.no", "hard")
    [(invitation_id,)] = rows("SELECT id FROM invitations")
    at(monkeypatch, EXPIRES)
    async with client() as c:
        await c.post(
            "/api/auth/invitation/renewal",
            json={"token": auth.link_token(identity.INVITATION, invitation_id)},
            headers=CSRF,
        )
    item = by_email(await statuses(klass))["a@x.no"]
    # Asked for anew, but the address bounced hard: no reminder goes to it.
    assert (item["status"], item["bounce_class"], item["remindable"]) == (
        "renewal_requested",
        None,
        False,
    )


async def test_unregistered_after_expiry_is_no_registered_student(klass, monkeypatch):
    await sent_class(klass, ["a@x.no", "b@x.no", "c@x.no", "m@x.no"])
    for address in ["b@x.no", "m@x.no"]:
        execute(
            "INSERT INTO users (id, email, name, password_hash) VALUES (%s, %s, 'B', 'x')",
            uuid.uuid7(),
            address,
        )
    execute(
        "UPDATE roster_entries SET registration = 'registered', "
        "user_id = (SELECT id FROM users WHERE email = 'b@x.no') WHERE email = 'b@x.no'"
    )
    execute(
        "UPDATE roster_entries SET registration = 'registered_manually', "
        "user_id = (SELECT id FROM users WHERE email = 'm@x.no') WHERE email = 'm@x.no'"
    )
    execute(
        "UPDATE roster_entries SET registration = 'registered', removed_at = %s, "
        "user_id = (SELECT id FROM users WHERE email = 'b@x.no') WHERE email = 'c@x.no'",
        NOW,
    )
    at(monkeypatch, EXPIRES + timedelta(days=1))
    students = await classes.registered_students(uuid.UUID(klass))
    expected = rows("SELECT id FROM users WHERE email IN ('b@x.no', 'm@x.no')")
    assert sorted(students) == sorted(i for (i,) in expected)
    assert by_email(await statuses(klass))["a@x.no"]["status"] == "unregistered"
    assert "c@x.no" not in by_email(await statuses(klass))


async def test_a_reminder_to_all_voids_old_links_skips_registered_and_names_hard_bounces(klass):
    waiting = ["inv@x.no", "inv2@x.no", "exp@x.no", "sb@x.no"]
    await sent_class(klass, [*waiting, "hb@x.no", "reg@x.no"])
    execute("UPDATE invitations SET expires_at = %s WHERE email = 'exp@x.no'", NOW)
    await bounce("sb@x.no", "soft")
    await bounce("hb@x.no", "hard")
    accept("reg@x.no")
    old = {email: inv for email, inv in rows("SELECT email, id FROM invitations")}
    response = await remind(klass, 7)
    assert response.status_code == 201
    assert response.json() == {
        "sent": 4,
        "valid_days": 7,
        "last_valid_day": "2026-11-26",
        "expires_at": "2026-11-26T23:00:00Z",
        "left_out": ["hb@x.no"],
    }
    for address in waiting:
        assert invitation_count(address) == 2 and open_invitations(address) == 1
    voided = rows("SELECT id FROM invitations WHERE voided_at IS NOT NULL")
    assert {v for (v,) in voided} == {old[a] for a in waiting}
    assert invitation_count("hb@x.no") == 1 and invitation_count("reg@x.no") == 1
    # The old link no longer works; a new one is mailed as an `invitation` notice.
    async with client() as c:
        checked = await c.post(
            "/api/auth/invitation/check",
            json={"token": auth.link_token(identity.INVITATION, old["inv@x.no"])},
            headers=CSRF,
        )
    assert checked.status_code == 410
    notices = rows("SELECT kind FROM notices")
    assert sorted(notices) == [("invitation",)] * 10


async def test_a_reminder_to_one_address_sends_only_to_it(klass):
    await sent_class(klass, ["a@x.no", "b@x.no"])
    entry = by_email(await statuses(klass))["a@x.no"]["id"]
    response = await remind(klass, 30, entry)
    assert response.status_code == 201
    assert (response.json()["sent"], response.json()["left_out"]) == (1, [])
    assert invitation_count("a@x.no") == 2 and invitation_count("b@x.no") == 1


@pytest.mark.parametrize("to", ["all", "one"])
async def test_a_reminder_to_only_a_hard_bounce_is_left_out_and_named(klass, to):
    await sent_class(klass, ["a@x.no"])
    await bounce("a@x.no", "hard")
    entry = by_email(await statuses(klass))["a@x.no"]["id"] if to == "one" else None
    response = await remind(klass, 14, entry)
    assert response.status_code == 201
    assert (response.json()["sent"], response.json()["left_out"]) == (0, ["a@x.no"])
    assert invitation_count("a@x.no") == 1


@pytest.mark.parametrize("target", ["registered", "unknown"])
async def test_a_reminder_with_nothing_to_send_is_refused(klass, target):
    """The other address is still invited, so only the named entry can cause the refusal."""
    await sent_class(klass, ["a@x.no", "b@x.no"])
    accept("a@x.no")
    entry = by_email(await statuses(klass))["a@x.no"]["id"] if target == "registered" else None
    response = await remind(klass, 14, entry or str(uuid.uuid4()))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "nothing_to_send"
    assert invitation_count("a@x.no") == 1 and invitation_count("b@x.no") == 1


async def test_a_reminder_to_all_when_everyone_registered_is_refused(klass):
    await sent_class(klass, ["a@x.no"])
    accept("a@x.no")
    response = await remind(klass)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "nothing_to_send"


async def test_an_entry_of_another_class_gets_no_reminder(klass):
    await sent_class(klass, ["a@x.no"])
    entry = by_email(await statuses(klass))["a@x.no"]["id"]
    async with client() as c:
        await as_user(c)
        other = await c.post(
            "/api/classes",
            json={
                "name": "class-of-1995",
                "institution_id": str(rows("SELECT id FROM institutions")[0][0]),
            },
            headers=CSRF,
        )
    response = await remind(other.json()["id"], 14, entry)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "nothing_to_send"
    assert invitation_count("a@x.no") == 1


@pytest.mark.parametrize("days", [0, 61, "14", True])
async def test_a_validity_outside_the_range_is_refused(klass, days):
    await sent_class(klass, ["a@x.no"])
    response = await remind(klass, days)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert invitation_count("a@x.no") == 1


async def test_an_acceptance_before_the_reminder_commits_gets_nothing(klass, monkeypatch):
    """An entry that becomes registered after the statuses were read is read again after the
    void, and gets no new Invitation."""
    await sent_class(klass, ["a@x.no"])
    real = identity.class_roster

    async def then_accept(class_id, *, now):
        found = await real(class_id, now=now)
        accept("a@x.no")
        return found

    monkeypatch.setattr(identity, "class_roster", then_accept)
    response = await remind(klass)
    assert response.status_code == 422
    assert invitation_count("a@x.no") == 1


@pytest.mark.parametrize("target", ["other", "unknown", "malformed"])
async def test_a_class_the_user_may_not_manage_is_forbidden_alike(klass, target):
    await sent_class(klass, ["a@x.no"])
    class_id = {"other": klass, "unknown": str(uuid.uuid4()), "malformed": "ikke-en-id"}[target]
    user = OTHER if target == "other" else "bard@example.com"
    read = await statuses(class_id, user)
    async with client() as c:
        await as_user(c, user)
        sent = await c.post(
            f"/api/classes/{class_id}/reminders", json={"valid_days": 14}, headers=CSRF
        )
    assert (read.status_code, sent.status_code) == (403, 403)
    assert invitation_count("a@x.no") == 1


async def test_anonymous_is_refused(klass):
    async with client() as c:
        read = await c.get(f"/api/classes/{klass}/registrations")
        sent = await c.post(f"/api/classes/{klass}/reminders", json={}, headers=CSRF)
    assert (read.status_code, sent.status_code) == (401, 401)


async def test_statuses_and_reminders_log_no_address(klass):
    await sent_class(klass, ["a@x.no", "b@x.no"])
    await bounce("b@x.no", "hard")
    with structlog.testing.capture_logs() as logs:
        await statuses(klass)
        await remind(klass)
    assert "a@x.no" not in repr(logs) and "b@x.no" not in repr(logs)
