"""Invitations to the Lecturer or Admin role through the api and the mail pipeline (Story 3.7,
FR-1, FR-3, FR-5, AD-9, AD-11, AD-14, AD-15). Every clock is fixed and moved by the test; the
database clock is never read."""

import asyncio
import json
import re
from datetime import UTC, datetime, timedelta

import pytest
from structlog.testing import capture_logs

from app.modules.identity import service
from app.modules.identity.schemas import AccountRole
from app.platform import auth
from app.platform.config import get_settings
from tests.identity.helpers import CSRF, client, login
from tests.messaging.helpers import deliveries, drain, mails, rows

PASSWORD = "admin-passordet"
ADMIN = "kari.admin@example.com"
INVITED = "ny.faglaerer@example.com"
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


async def invite(c, email: str = INVITED, role: str = "lecturer"):
    return await c.post("/api/admin/invitations", json={"email": email, "role": role}, headers=CSRF)


async def as_admin(c):
    assert (await login(c, ADMIN, PASSWORD)).status_code == 200


def open_invitations(email: str = INVITED) -> list[tuple]:
    return rows(
        "SELECT id, role FROM invitations "
        "WHERE email = %s AND accepted_at IS NULL AND voided_at IS NULL ORDER BY id",
        email,
    )


async def test_the_admin_sends_one_invitation_with_one_mail_and_one_audit_row(admin, clock):
    async with client() as c:
        await as_admin(c)
        response = await invite(c, "  Ny.Faglaerer@Example.com ")
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == INVITED
    assert body["role"] == "lecturer"
    assert body["valid_days"] == 14
    assert datetime.fromisoformat(body["expires_at"]) == clock["now"] + timedelta(days=14)

    [(invitation_id, email, role, token_hash, expires_at, invited_by)] = rows(
        "SELECT id, email, role, token_hash, expires_at, invited_by FROM invitations"
    )
    assert (str(invitation_id), email, role) == (body["id"], INVITED, "lecturer")
    assert expires_at == clock["now"] + timedelta(days=14)
    assert invited_by == admin
    # Addressed by reference: the notice holds the Invitation's id, never the address.
    assert rows("SELECT user_id, kind, ref FROM notices") == [(None, "invitation", invitation_id)]

    [(actor, action, target, change, occurred_at)] = rows(
        "SELECT actor_user_id, action, target_ids, change, occurred_at FROM audit_events"
    )
    assert (actor, action) == (admin, "invitation.sent")
    assert target == {"invitation_id": str(invitation_id)}
    assert change == {"role": "lecturer"}
    assert occurred_at == clock["now"]

    await drain(clock["now"])
    [mail] = mails()
    assert mail.to == INVITED
    assert mail.sender == get_settings().email_from
    assert mail.subject == "Invitasjon til ØL-spillet"
    assert mail.text.startswith("ØL-spillet")
    assert "som Faglærer" in mail.text
    assert "gyldig i 14 dager" in mail.text
    token = LINK.search(mail.text).group(1)
    assert auth.token_hash(token) == token_hash
    assert f"/invitasjon#{token}" in mail.html
    assert deliveries() == [("immediate", 1, True, None, 1)]


async def test_an_admin_invitation_and_the_validity_follow_the_setting(admin, clock, monkeypatch):
    monkeypatch.setenv("ROLE_INVITATION_VALID_DAYS", "3")
    get_settings.cache_clear()
    async with client() as c:
        await as_admin(c)
        response = await invite(c, role="admin")
    assert response.status_code == 201
    assert response.json()["valid_days"] == 3
    assert rows("SELECT expires_at FROM invitations") == [(clock["now"] + timedelta(days=3),)]
    await drain(clock["now"])
    [mail] = mails()
    assert "som Admin" in mail.text
    assert "gyldig i 3 dager" in mail.text


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "   ",
        "kari",
        "kari@",
        "@example.com",
        "a@@example.com",
        "a b@c.no",
        "kari@b",
        "a\x00@c.no",
    ],
)
async def test_a_malformed_address_is_refused_and_nothing_is_sent(admin, clock, bad):
    async with client() as c:
        await as_admin(c)
        response = await invite(c, bad)
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "invalid_request"
    assert error["fields"] == {"email": "invalid_email"}
    assert rows("SELECT count(*) FROM invitations") == [(0,)]
    assert rows("SELECT count(*) FROM notices") == [(0,)]
    assert rows("SELECT count(*) FROM audit_events") == [(0,)]


async def test_an_unknown_role_is_refused(admin, clock):
    async with client() as c:
        await as_admin(c)
        response = await invite(c, role="student")
    assert response.status_code == 422
    assert rows("SELECT count(*) FROM invitations") == [(0,)]


async def test_sending_again_voids_the_earlier_link_and_leaves_one_open(admin, clock):
    async with client() as c:
        await as_admin(c)
        first = (await invite(c)).json()
        clock["now"] += timedelta(minutes=5)
        second = (await invite(c)).json()
    assert first["id"] != second["id"]
    assert [str(i) for i, _ in open_invitations()] == [second["id"]]
    assert rows("SELECT voided_at FROM invitations WHERE id = %s", first["id"]) == [(clock["now"],)]
    [(_, change)] = rows(
        "SELECT target_ids, change FROM audit_events WHERE target_ids->>'invitation_id' = %s",
        second["id"],
    )
    assert change == {"role": "lecturer", "voided_invitation_ids": [first["id"]]}

    # The first mail had not left yet: it is skipped, and only the second link is mailed.
    await drain(clock["now"])
    [mail] = mails()
    token = LINK.search(mail.text).group(1)
    [(token_hash,)] = rows("SELECT token_hash FROM invitations WHERE id = %s", second["id"])
    assert auth.token_hash(token) == token_hash
    assert sorted(d[3] or "sent" for d in deliveries()) == ["no_recipient", "sent"]


async def test_an_invitation_for_another_role_stays_open_beside_it(admin, clock):
    async with client() as c:
        await as_admin(c)
        await invite(c, role="lecturer")
        await invite(c, role="admin")
    assert sorted(role for _, role in open_invitations()) == ["admin", "lecturer"]


async def test_parallel_sends_leave_exactly_one_open_invitation(admin, clock):
    async with client() as c:
        await as_admin(c)
        responses = await asyncio.gather(*(invite(c) for _ in range(4)))
    assert [r.status_code for r in responses] == [201] * 4
    assert len(open_invitations()) == 1
    assert rows("SELECT count(*) FROM invitations") == [(4,)]
    assert rows("SELECT count(*) FROM audit_events") == [(4,)]


@pytest.mark.parametrize("who", ["lecturer", "no role", "nobody"])
async def test_only_an_admin_may_invite(identity_db, mail_db, clock, who):
    if who != "nobody":
        roles = [AccountRole.lecturer] if who == "lecturer" else []
        await service.create_user(email=ADMIN, name="Kari", password=PASSWORD, roles=roles)
    async with client() as c:
        if who != "nobody":
            await as_admin(c)
        response = await invite(c, role="admin")
    if who == "nobody":
        assert response.status_code == 401
    else:
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"
    await drain(clock["now"])
    for table in ("invitations", "notices", "audit_events"):
        assert rows(f"SELECT count(*) FROM {table}") == [(0,)], table
    assert mails() == []


async def test_an_invitation_that_expires_before_its_mail_leaves_is_not_mailed(admin, clock):
    async with client() as c:
        await as_admin(c)
        await invite(c)
    await drain(clock["now"] + timedelta(days=14))
    assert mails() == []
    assert deliveries() == [("immediate", 1, False, "no_recipient", 0)]


async def test_a_late_mail_states_the_days_left(admin, clock):
    async with client() as c:
        await as_admin(c)
        await invite(c)
    await drain(clock["now"] + timedelta(days=13, hours=1))
    [mail] = mails()
    assert "gyldig i én dag" in mail.text


async def test_no_address_or_token_lands_in_a_log_line_a_job_or_an_audit_row(admin, clock):
    with capture_logs() as logs:
        async with client() as c:
            await as_admin(c)
            await invite(c)
            jobs = rows("SELECT args::text FROM procrastinate_jobs")
            await drain(clock["now"])
    token = LINK.search(mails()[0].text).group(1)
    stored = json.dumps(rows("SELECT target_ids, change FROM audit_events"), default=str)
    for text in (json.dumps(logs, default=str), json.dumps(jobs, default=str), stored):
        assert INVITED not in text
        assert ADMIN not in text
        assert token not in text
