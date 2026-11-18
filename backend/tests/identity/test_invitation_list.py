"""The Admin's Invitation list and resending an Invitation through the api and the mail pipeline
(Story 3.10, FR-1, FR-3, AD-11, AD-15). Every clock is fixed and moved by the test; the database
clock is never read."""

import re
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.modules.identity import service
from app.modules.identity.schemas import AccountRole
from app.platform import auth
from tests.identity.helpers import CSRF, client, login
from tests.messaging.helpers import drain, mails, rows

PASSWORD = "admin-passordet"
ADMIN = "kari.admin@example.com"
LINK = re.compile(r"http://127\.0\.0\.1:8080/invitasjon#([A-Za-z0-9_-]+)")


@pytest.fixture
def clock(monkeypatch):
    """The api's clock, fixed and movable."""
    now = {"now": datetime(2026, 11, 18, 12, 1, tzinfo=UTC)}
    monkeypatch.setattr(auth, "utcnow", lambda: now["now"])
    return now


@pytest.fixture
async def admin(identity_db, mail_db):
    return await service.create_user(
        email=ADMIN, name="Kari", password=PASSWORD, roles=[AccountRole.admin]
    )


async def as_admin(c):
    assert (await login(c, ADMIN, PASSWORD)).status_code == 200


async def invite(c, email: str, role: str = "lecturer") -> str:
    response = await c.post(
        "/api/admin/invitations", json={"email": email, "role": role}, headers=CSRF
    )
    assert response.status_code == 201
    return response.json()["id"]


def token_of(invitation_id: str) -> str:
    return auth.link_token(service.INVITATION, uuid.UUID(invitation_id))


async def accept(invitation_id: str) -> None:
    """Take the Invitation as a new account, in a client of its own (it logs that account in)."""
    body = {"token": token_of(invitation_id), "name": "Tatt", "password": "et-godt-passord"}
    async with client("198.51.100.20") as other:
        response = await other.post("/api/auth/invitation/accept", json=body, headers=CSRF)
    assert response.status_code == 200


async def later(c, clock, days: int) -> None:
    """Move the clock on, and log in again: a session lasts a week."""
    clock["now"] += timedelta(days=days)
    await as_admin(c)


async def check(c, invitation_id: str):
    body = {"token": token_of(invitation_id)}
    return await c.post("/api/auth/invitation/check", json=body, headers=CSRF)


async def resend(c, invitation_id):
    return await c.post(f"/api/admin/invitations/{invitation_id}/resend", headers=CSRF)


async def listed(c, **params) -> dict:
    response = await c.get("/api/admin/invitations", params=params)
    assert response.status_code == 200
    return response.json()


async def test_the_list_shows_the_newest_invitation_per_address_and_role(admin, clock):
    async with client() as c:
        await as_admin(c)
        old = await invite(c, "gammel@example.com")
        await later(c, clock, 15)  # «gammel» has expired
        taken = await invite(c, "tatt@example.com", "admin")
        await accept(taken)
        first = await invite(c, "ny@example.com")
        second = await invite(c, "ny@example.com")  # voids the first
        asked = await c.post(
            "/api/auth/invitation/renewal", json={"token": token_of(first)}, headers=CSRF
        )
        assert asked.status_code == 202
        other_role = await invite(c, "ny@example.com", "admin")
        page = await listed(c)
    expires = clock["now"] + timedelta(days=14)
    assert page == {
        "items": [
            {
                "id": other_role,
                "email": "ny@example.com",
                "role": "admin",
                "status": "open",
                "expires_at": expires.isoformat().replace("+00:00", "Z"),
                "renewal_requested": False,
            },
            {
                "id": second,
                "email": "ny@example.com",
                "role": "lecturer",
                "status": "open",
                "expires_at": expires.isoformat().replace("+00:00", "Z"),
                "renewal_requested": True,
            },
            {
                "id": taken,
                "email": "tatt@example.com",
                "role": "admin",
                "status": "accepted",
                "expires_at": expires.isoformat().replace("+00:00", "Z"),
                "renewal_requested": False,
            },
            {
                "id": old,
                "email": "gammel@example.com",
                "role": "lecturer",
                "status": "expired",
                "expires_at": (expires - timedelta(days=15)).isoformat().replace("+00:00", "Z"),
                "renewal_requested": False,
            },
        ],
        "next_cursor": None,
    }


async def test_the_list_pages_by_cursor_and_refuses_a_foreign_cursor(admin, clock):
    async with client() as c:
        await as_admin(c)
        ids = [await invite(c, f"p{n}@example.com") for n in range(3)]
        one = await listed(c, limit=2)
        two = await listed(c, limit=2, cursor=one["next_cursor"])
        unknown = service._encode_cursor(uuid.uuid7())
        bad = [
            await c.get("/api/admin/invitations", params={"cursor": cursor})
            for cursor in ("!!", unknown)
        ]
        limits = [await c.get("/api/admin/invitations", params={"limit": n}) for n in (0, 101)]
    assert [item["id"] for item in one["items"] + two["items"]] == ids[::-1]
    assert two["next_cursor"] is None
    assert [r.status_code for r in bad] == [422, 422]
    assert {r.json()["error"]["code"] for r in bad} == {"invalid_request"}
    assert [r.status_code for r in limits] == [422, 422]


async def test_resending_voids_the_old_link_mails_a_new_one_and_clears_the_request(admin, clock):
    async with client() as c:
        await as_admin(c)
        old = await invite(c, "sen@example.com")
        await later(c, clock, 15)
        await c.post("/api/auth/invitation/renewal", json={"token": token_of(old)}, headers=CSRF)
        assert (await listed(c))["items"][0]["renewal_requested"] is True
        await drain(clock["now"])
        mails_before = len(mails())
        response = await resend(c, old)
        await drain(clock["now"])
        new = response.json()["id"]
        old_check = await check(c, old)
        new_check = await check(c, new)
        page = await listed(c)
    assert response.status_code == 201
    assert response.json()["email"] == "sen@example.com"
    assert response.json()["valid_days"] == 14
    assert datetime.fromisoformat(response.json()["expires_at"]) == clock["now"] + timedelta(
        days=14
    )
    assert new != old
    assert old_check.status_code == 410
    assert new_check.status_code == 200
    [mail] = mails()[mails_before:]
    assert mail.to == "sen@example.com"
    assert LINK.search(mail.text).group(1) == token_of(new)
    assert page["items"][0]["id"] == new
    assert page["items"][0]["status"] == "open"
    assert page["items"][0]["renewal_requested"] is False
    assert rows("SELECT count(*) FROM invitations WHERE renewal_requested_at IS NOT NULL") == [(0,)]
    [(actor, action, target, change)] = rows(
        "SELECT actor_user_id, action, target_ids, change FROM audit_events "
        "WHERE action = 'invitation.resent'"
    )
    assert (actor, action, target) == (admin, "invitation.resent", {"invitation_id": new})
    # The expired Invitation was never voided; the resend voids it too.
    assert change == {
        "role": "lecturer",
        "resent_invitation_id": old,
        "voided_invitation_ids": [old],
    }


async def test_resending_an_open_invitation_voids_it(admin, clock):
    async with client() as c:
        await as_admin(c)
        old = await invite(c, "aapen@example.com")
        response = await resend(c, old)
        old_check = await check(c, old)
    assert response.status_code == 201
    assert old_check.status_code == 410
    [(change,)] = rows("SELECT change FROM audit_events WHERE action = 'invitation.resent'")
    assert change["voided_invitation_ids"] == [old]


async def test_a_resend_is_refused_for_accepted_replaced_unknown_and_deactivated(admin, clock):
    await service.create_user(
        email="borte@example.com", name="Borte", password="et-passord", is_active=False
    )
    async with client() as c:
        await as_admin(c)
        taken = await invite(c, "tatt@example.com")
        await accept(taken)
        replaced = await invite(c, "to@example.com")
        await invite(c, "to@example.com")
        gone = await invite(c, "borte@example.com", "admin")
        audit_before = rows("SELECT count(*) FROM audit_events")
        answers = {
            "accepted": await resend(c, taken),
            "replaced": await resend(c, replaced),
            "unknown": await resend(c, uuid.uuid7()),
            "deactivated": await resend(c, gone),
        }
    assert {k: (r.status_code, r.json()["error"]["code"]) for k, r in answers.items()} == {
        "accepted": (409, "invitation_accepted"),
        "replaced": (409, "invitation_superseded"),
        "unknown": (404, "not_found"),
        "deactivated": (409, "account_deactivated"),
    }
    assert rows("SELECT count(*) FROM audit_events") == audit_before


async def test_only_an_admin_reaches_the_list_and_the_resend(admin, clock):
    await service.create_user(
        email="lektor@example.com", name="Lektor", password=PASSWORD, roles=[AccountRole.lecturer]
    )
    async with client() as c:
        await as_admin(c)
        sent = await invite(c, "x@example.com")
    async with client() as anon:
        assert (await anon.get("/api/admin/invitations")).status_code == 401
        assert (await resend(anon, sent)).status_code == 401
    async with client() as c:
        assert (await login(c, "lektor@example.com", PASSWORD)).status_code == 200
        assert (await c.get("/api/admin/invitations")).status_code == 403
        assert (await resend(c, sent)).status_code == 403
    assert rows("SELECT count(*) FROM invitations") == [(1,)]


async def test_a_new_invitation_from_the_form_also_answers_the_request(admin, clock):
    async with client() as c:
        await as_admin(c)
        old = await invite(c, "skjema@example.com")
        await later(c, clock, 15)
        await c.post("/api/auth/invitation/renewal", json={"token": token_of(old)}, headers=CSRF)
        await invite(c, "skjema@example.com")
        page = await listed(c)
    assert page["items"][0]["renewal_requested"] is False
