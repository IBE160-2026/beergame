"""Registering a Student by hand and changing single addresses (Story 4.8, FR-5, FR-7, FR-8, FR-9,
AD-8, AD-9, AD-12, AD-14): manual registration of a new and an existing User, the set-password
mail, adding one address, removing one and putting it back. The api's clock is fixed
(2026-11-19 09:00 UTC); the database clock is never read, and nothing is ordered by a
timestamp."""

import re
import uuid

import pytest
import structlog.testing

from app.modules.classes import service as classes
from tests.classes.test_classes import OTHER, PASSWORD, as_user, make
from tests.classes.test_invitation_counts import accept, sent_class
from tests.classes.test_roster_send import paste, send, staged_id
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_student_registration import emitted, second_class
from tests.identity.helpers import CSRF, client, login
from tests.messaging.helpers import drain, mails, rows

__all__ = ["clock", "emitted", "klass"]

LINK = re.compile(r"http://127\.0\.0\.1:8080/nytt-passord#([A-Za-z0-9_-]+)")
NEW_PASSWORD = "mitt-forste-passord"


@pytest.fixture(autouse=True)
def _empty_mail(mail_db):
    """The mail tables and the mock outbox empty, before `klass` makes its Users."""


async def manual(class_id: str, user: str | None = None, **body):
    async with client() as c:
        await as_user(c, *([user] if user else []))
        return await c.post(f"/api/classes/{class_id}/roster/manual", json=body, headers=CSRF)


async def add(class_id: str, email: str, user: str | None = None):
    async with client() as c:
        await as_user(c, *([user] if user else []))
        return await c.post(
            f"/api/classes/{class_id}/roster/entries", json={"email": email}, headers=CSRF
        )


async def remove(class_id: str, entry_id: str, user: str | None = None):
    async with client() as c:
        await as_user(c, *([user] if user else []))
        return await c.delete(f"/api/classes/{class_id}/roster/entries/{entry_id}", headers=CSRF)


async def statuses(class_id: str) -> dict[str, dict]:
    async with client() as c:
        await as_user(c)
        response = await c.get(f"/api/classes/{class_id}/registrations")
    return {item["email"]: item for item in response.json()["items"]}


def entry(address: str) -> tuple:
    [found] = rows(
        "SELECT id, registration, user_id, removed_at FROM roster_entries WHERE email = %s", address
    )
    return found


def open_invitations(address: str) -> int:
    return rows(
        "SELECT count(*) FROM invitations WHERE email = %s AND accepted_at IS NULL "
        "AND voided_at IS NULL",
        address,
    )[0][0]


async def enrolled(class_id: str, email: str, password: str = PASSWORD) -> int:
    async with client() as c:
        assert (await login(c, email, password)).status_code == 200
        return (await c.get(f"/api/classes/enrolled/{class_id}")).status_code


async def test_a_new_address_is_registered_with_a_user_without_password_and_a_link(klass, emitted):
    response = await manual(klass, email=" Ny@X.no ", name="  Kari   Nordmann ")
    assert response.status_code == 201
    body = response.json()
    assert (body["email"], body["status"], body["remindable"]) == (
        "ny@x.no",
        "registered_manually",
        False,
    )
    [(user_id, name, password_hash)] = rows(
        "SELECT id, name, password_hash FROM users WHERE email = 'ny@x.no'"
    )
    assert (name, password_hash) == ("Kari Nordmann", None)
    assert rows("SELECT role FROM user_roles WHERE user_id = %s", user_id) == []
    assert entry("ny@x.no")[1:] == ("registered_manually", user_id, None)
    assert await classes.registered_students(uuid.UUID(klass)) == [user_id]
    assert ("user", str(user_id)) in emitted
    # No password yet: the account cannot log in, whatever is typed.
    async with client() as c:
        assert (await login(c, "ny@x.no", "")).status_code in (401, 422)
        assert (await login(c, "ny@x.no", PASSWORD)).status_code == 401

    await drain(NOW)
    [mail] = mails()
    assert (mail.to, mail.subject) == ("ny@x.no", "Du er registrert i ØL-spillet")
    assert "Klassen class-of-1994" in mail.text
    assert "til og med 3. desember 2026" in mail.text
    token = LINK.search(mail.text).group(1)
    async with client() as c:
        set_it = await c.post(
            "/api/auth/password-reset/confirm",
            json={"token": token, "password": NEW_PASSWORD},
            headers=CSRF,
        )
        assert set_it.status_code == 200
        again = await c.post(
            "/api/auth/password-reset/confirm",
            json={"token": token, "password": "et-annet-passord"},
            headers=CSRF,
        )
        assert again.status_code == 410
    assert await enrolled(klass, "ny@x.no", NEW_PASSWORD) == 200


async def test_an_existing_user_is_reused_unchanged_and_mailed_without_a_link(klass):
    user_id = await make("stud@x.no", roles=())
    before = rows("SELECT name, password_hash FROM users WHERE id = %s", user_id)
    response = await manual(klass, email="stud@x.no", name="Et annet navn")
    assert response.status_code == 201
    assert rows("SELECT name, password_hash FROM users WHERE id = %s", user_id) == before
    assert rows("SELECT count(*) FROM users WHERE email = 'stud@x.no'") == [(1,)]
    assert rows("SELECT count(*) FROM password_resets") == [(0,)]
    await drain(NOW)
    [mail] = mails()
    assert LINK.search(mail.text) is None
    assert "Logg inn som vanlig" in mail.text
    assert await enrolled(klass, "stud@x.no") == 200


async def test_an_invited_address_registered_by_hand_has_its_link_voided(klass):
    await sent_class(klass, ["inv@x.no"])
    assert open_invitations("inv@x.no") == 1
    assert (await manual(klass, email="inv@x.no", name="Ida")).status_code == 201
    assert open_invitations("inv@x.no") == 0
    assert entry("inv@x.no")[1] == "registered_manually"
    assert (await statuses(klass))["inv@x.no"]["status"] == "registered_manually"


async def test_a_registered_address_is_refused_beside_the_field(klass):
    await sent_class(klass, ["reg@x.no"])
    accept("reg@x.no")
    response = await manual(klass, email="reg@x.no", name="Rita")
    assert response.status_code == 422
    assert response.json()["error"]["fields"] == {"email": "already_registered"}
    assert entry("reg@x.no")[1] == "registered"


@pytest.mark.parametrize(
    ("body", "fields"),
    [
        ({"email": "x@", "name": "A"}, {"email": "missing_domain"}),
        ({"email": "a@x.no", "name": "   "}, {"name": "name_empty"}),
        ({"email": "a@x.no", "name": "n" * 201}, {"name": "name_too_long"}),
    ],
)
async def test_a_refused_address_or_name_stores_nothing(klass, body, fields):
    response = await manual(klass, **body)
    assert response.status_code == 422
    assert response.json()["error"]["fields"] == fields
    assert rows("SELECT count(*) FROM roster_entries") == [(0,)]


async def test_a_wrong_address_is_corrected_and_its_row_removed(klass):
    await sent_class(klass, ["feil@x.no"])
    [old_id, *_] = entry("feil@x.no")
    response = await manual(klass, email="rett@x.no", name="Rett", roster_entry_id=str(old_id))
    assert response.status_code == 201
    assert entry("feil@x.no")[3] is not None  # removed
    assert open_invitations("feil@x.no") == 0
    assert set(await statuses(klass)) == {"rett@x.no"}


async def test_a_registered_row_is_never_removed_by_a_correction(klass):
    await sent_class(klass, ["reg@x.no"])
    accept("reg@x.no")
    [reg_id, *_] = entry("reg@x.no")
    assert (
        await manual(klass, email="ny@x.no", name="Ny", roster_entry_id=str(reg_id))
    ).status_code == 201
    assert entry("reg@x.no")[3] is None


async def test_registering_from_an_invalid_row_deletes_that_staged_row(klass):
    async with client() as c:
        await as_user(c)
        upload_id = await staged_id(c, klass, "ok@x.no feil@x")
    response = await manual(
        klass,
        email="feil@x.no",
        name="Feil",
        upload_row={"upload_id": upload_id, "row_number": 2},
    )
    assert response.status_code == 201
    async with client() as c:
        await as_user(c)
        staged = (await c.get(f"/api/classes/{klass}/roster-upload")).json()["upload"]
    assert (staged["row_count"], staged["valid_count"], staged["invalid_rows"]) == (1, 1, [])


async def test_a_gone_staging_is_ignored(klass):
    response = await manual(
        klass,
        email="a@x.no",
        name="A",
        upload_row={"upload_id": str(uuid.uuid7()), "row_number": 1},
    )
    assert response.status_code == 201


async def test_one_address_is_added_not_yet_invited_and_a_reminder_invites_it(klass):
    response = await add(klass, "  Late@X.no")
    assert response.status_code == 201
    assert (response.json()["status"], response.json()["remindable"]) == ("not_invited", True)
    assert rows("SELECT count(*) FROM invitations") == [(0,)]
    async with client() as c:
        await as_user(c)
        totals = (await c.get(f"/api/classes/{klass}/registrations")).json()
        assert (totals["totals"]["unregistered"], totals["reminder_count"]) == (1, 1)
        sent = await c.post(f"/api/classes/{klass}/reminders", json={}, headers=CSRF)
    assert sent.json()["sent"] == 1
    assert (await statuses(klass))["late@x.no"]["status"] == "invited"


@pytest.mark.parametrize(
    ("address", "reason"),
    [("x@", "missing_domain"), ("", "empty"), ("a@@x.no", "two_at"), ("ax.no", "missing_at")],
)
async def test_an_address_is_checked_as_an_upload_is(klass, address, reason):
    response = await add(klass, address)
    assert response.status_code == 422
    assert response.json()["error"]["fields"] == {"email": reason}


async def test_an_address_on_the_roster_is_refused_as_a_duplicate(klass):
    assert (await add(klass, "a@x.no")).status_code == 201
    response = await add(klass, "A@x.no ")
    assert response.status_code == 422
    assert response.json()["error"]["fields"] == {"email": "on_roster"}


async def test_removing_a_student_ends_access_and_keeps_the_account(klass, emitted):
    user_id = await make("stud@x.no", roles=())
    assert (await manual(klass, email="stud@x.no", name="S")).status_code == 201
    [entry_id, *_] = entry("stud@x.no")
    assert await enrolled(klass, "stud@x.no") == 200
    response = await remove(klass, str(entry_id))
    assert response.status_code == 204
    assert entry("stud@x.no")[3] is not None
    assert await classes.registered_students(uuid.UUID(klass)) == []
    assert await enrolled(klass, "stud@x.no") == 403
    assert rows("SELECT is_active FROM users WHERE id = %s", user_id) == [(True,)]
    assert ("user", str(user_id)) in emitted
    assert "stud@x.no" not in await statuses(klass)
    # Gone already: the same answer as an unknown entry.
    assert (await remove(klass, str(entry_id))).status_code == 404
    assert (await remove(klass, str(uuid.uuid7()))).status_code == 404
    assert (await remove(klass, "ikke-en-id")).status_code == 404


async def test_removing_an_invited_address_voids_its_link(klass):
    await sent_class(klass, ["inv@x.no"])
    [entry_id, *_] = entry("inv@x.no")
    assert (await remove(klass, str(entry_id))).status_code == 204
    assert open_invitations("inv@x.no") == 0


async def test_a_removed_student_added_again_has_access_without_a_new_registration(klass):
    await make("stud@x.no", roles=())
    await manual(klass, email="stud@x.no", name="S")
    [entry_id, *_] = entry("stud@x.no")
    await remove(klass, str(entry_id))
    await drain(NOW)
    assert mails() == []  # removed before its mail left: no «Du er registrert»
    response = await add(klass, "stud@x.no")
    assert response.status_code == 201
    assert (response.json()["id"], response.json()["status"]) == (
        str(entry_id),
        "registered_manually",
    )
    assert await enrolled(klass, "stud@x.no") == 200
    await drain(NOW)
    assert mails() == []


async def test_a_removed_address_sent_again_is_back_and_invited_once(klass):
    await sent_class(klass, ["a@x.no"])
    [entry_id, *_] = entry("a@x.no")
    await remove(klass, str(entry_id))
    async with client() as c:
        await as_user(c)
        sent = await send(c, klass, await staged_id(c, klass, "a@x.no"))
    assert sent.json()["sent"] == 1
    assert entry("a@x.no")[3] is None
    assert open_invitations("a@x.no") == 1


async def test_another_lecturer_an_unknown_class_and_a_malformed_id_are_refused(klass):
    await sent_class(klass, ["a@x.no"])
    [entry_id, *_] = entry("a@x.no")
    async with client() as owner, client() as other:
        await as_user(owner)
        await as_user(other, OTHER)
        for c, class_id in ((other, klass), (owner, str(uuid.uuid7())), (owner, "ikke-en")):
            base = f"/api/classes/{class_id}/roster"
            for response in (
                await c.post(f"{base}/entries", json={"email": "b@x.no"}, headers=CSRF),
                await c.post(f"{base}/manual", json={"email": "b@x.no", "name": "B"}, headers=CSRF),
                await c.delete(f"{base}/entries/{entry_id}", headers=CSRF),
            ):
                assert response.status_code == 403
                assert response.json()["error"]["code"] == "forbidden"
    assert entry("a@x.no")[3] is None
    assert rows("SELECT count(*) FROM roster_entries") == [(1,)]


async def test_no_address_or_name_reaches_the_logs(klass):
    with structlog.testing.capture_logs() as logs:
        await manual(klass, email="hemmelig@x.no", name="Hemmelig Navn")
        await add(klass, "skjult@x.no")
        await add(klass, "skjult@x.no")
        [entry_id, *_] = entry("skjult@x.no")
        await remove(klass, str(entry_id))
    text = repr(logs)
    for secret in ("hemmelig", "Hemmelig Navn", "skjult"):
        assert secret not in text


async def test_a_used_link_mails_no_link_and_an_expired_one_no_mail(klass):
    from datetime import timedelta

    from app.modules.identity import service as identity
    from app.platform import auth

    await manual(klass, email="ny@x.no", name="Ny")
    await manual(klass, email="sen@x.no", name="Sen")
    reset_of = dict(
        rows("SELECT u.email, r.id FROM password_resets r JOIN users u ON u.id = r.user_id")
    )
    token = auth.link_token(identity.PASSWORD_RESET, reset_of["ny@x.no"])
    async with client() as c:
        # «Nytt passord» is told the account has no password yet (Issue #91).
        checked = await c.post(
            "/api/auth/password-reset/check", json={"token": token}, headers=CSRF
        )
        assert checked.json() == {"email": "ny@x.no", "first_password": True}
        done = await c.post(
            "/api/auth/password-reset/confirm",
            json={"token": token, "password": NEW_PASSWORD},
            headers=CSRF,
        )
    assert done.status_code == 200
    # The mails leave after the links' last valid day: the one whose link was used tells the
    # Student to log in as usual, the other has no working link left and is not sent.
    await drain(NOW + timedelta(days=30))
    [mail] = mails()
    assert mail.to == "ny@x.no"
    assert LINK.search(mail.text) is None
    assert "Logg inn som vanlig" in mail.text


async def test_an_entry_of_another_class_is_not_found_and_that_class_is_untouched(klass):
    other = await second_class()
    await make("stud@x.no", roles=())
    assert (await manual(other, email="stud@x.no", name="S")).status_code == 201
    assert (await manual(klass, email="stud@x.no", name="S")).status_code == 201
    [other_entry] = rows("SELECT id FROM roster_entries WHERE class_id = %s", other)
    assert (await remove(klass, str(other_entry[0]))).status_code == 404
    # A correction that names the other Class's row leaves it alone.
    response = await manual(klass, email="ny@x.no", name="Ny", roster_entry_id=str(other_entry[0]))
    assert response.status_code == 201
    assert rows("SELECT removed_at FROM roster_entries WHERE id = %s", other_entry[0]) == [(None,)]
    # Removed from one Class, the Student keeps the other.
    [own] = rows("SELECT id FROM roster_entries WHERE class_id = %s AND email = 'stud@x.no'", klass)
    assert (await remove(klass, str(own[0]))).status_code == 204
    assert await enrolled(klass, "stud@x.no") == 403
    assert await enrolled(other, "stud@x.no") == 200


async def test_a_removed_registered_student_sent_again_has_access_and_no_invitation(klass, emitted):
    user_id = await make("stud@x.no", roles=())
    await manual(klass, email="stud@x.no", name="S")
    [entry_id, *_] = entry("stud@x.no")
    await remove(klass, str(entry_id))
    async with client() as c:
        await as_user(c)
        staged = await paste(c, klass, "stud@x.no new@x.no")
        sent = await send(c, klass, staged.json()["id"])
    # «Send N» counts what is sent (Issue #91): both rows go on the Roster, one is put back with
    # access and no Invitation, so the button reads «Send 1».
    assert (staged.json()["valid_count"], staged.json()["restored_count"]) == (2, 1)
    assert sent.json()["sent"] == 1  # the new address only
    assert open_invitations("stud@x.no") == 0
    assert entry("stud@x.no")[1:] == ("registered_manually", user_id, None)
    assert await enrolled(klass, "stud@x.no") == 200
    assert emitted.count(("user", str(user_id))) >= 3  # registered, removed, back


async def test_a_not_invited_address_gets_its_first_invitation_alone(klass):
    await add(klass, "late@x.no")
    await add(klass, "other@x.no")
    [entry_id, *_] = entry("late@x.no")
    async with client() as c:
        await as_user(c)
        sent = await c.post(
            f"/api/classes/{klass}/reminders",
            json={"roster_entry_id": str(entry_id)},
            headers=CSRF,
        )
    assert sent.json()["sent"] == 1
    found = await statuses(klass)
    assert (found["late@x.no"]["status"], found["other@x.no"]["status"]) == (
        "invited",
        "not_invited",
    )


async def test_a_request_for_a_new_invitation_goes_with_the_removal(klass, monkeypatch):
    from app.modules.identity import service as identity
    from app.platform import auth
    from tests.classes.test_registrations import EXPIRES, at

    await sent_class(klass, ["a@x.no"])
    [(invitation_id,)] = rows("SELECT id FROM invitations")
    at(monkeypatch, EXPIRES)
    async with client() as c:
        await c.post(
            "/api/auth/invitation/renewal",
            json={"token": auth.link_token(identity.INVITATION, invitation_id)},
            headers=CSRF,
        )
    assert (await statuses(klass))["a@x.no"]["status"] == "renewal_requested"
    [entry_id, *_] = entry("a@x.no")
    await remove(klass, str(entry_id))
    await add(klass, "a@x.no")
    assert (await statuses(klass))["a@x.no"]["status"] == "unregistered"
