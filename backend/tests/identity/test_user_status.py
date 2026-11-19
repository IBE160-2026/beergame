"""Deactivating and reactivating Users through the api, and the session version that ends their
sessions (Story 3.10, FR-3, AD-8, AD-11, AD-15). The api's clock is fixed; the database clock is
never read."""

import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import psycopg
import pytest
from structlog.testing import capture_logs

from app.modules.identity import repo, service
from app.modules.identity.schemas import AccountRole
from app.platform import auth, events
from app.platform.config import get_settings
from app.platform.events.registry import COMMAND_TOPICS
from tests.conftest import libpq_dsn
from tests.identity.helpers import CSRF, client, login
from tests.messaging.helpers import rows

PASSWORD = "hemmelig-passord"
ADMIN = "kari.admin@example.com"
BARD = "bard@example.com"


@pytest.fixture
def clock(monkeypatch):
    now = datetime(2026, 11, 18, 12, 1, tzinfo=UTC)
    monkeypatch.setattr(auth, "utcnow", lambda: now)
    return now


async def make(email: str, name: str, roles=(), is_active: bool = True) -> uuid.UUID:
    return await service.create_user(
        email=email, name=name, password=PASSWORD, roles=list(roles), is_active=is_active
    )


@pytest.fixture
async def admin(identity_db):
    return await make(ADMIN, "Kari Admin", [AccountRole.admin])


async def as_user(c, email: str = ADMIN):
    assert (await login(c, email, PASSWORD)).status_code == 200


async def deactivate(c, user_id):
    return await c.post(f"/api/admin/users/{user_id}/deactivate", headers=CSRF)


async def reactivate(c, user_id):
    return await c.post(f"/api/admin/users/{user_id}/reactivate", headers=CSRF)


def audit_rows() -> list[tuple]:
    return rows(
        "SELECT actor_user_id, action, target_ids, change, occurred_at FROM audit_events "
        "ORDER BY occurred_at, id"
    )


def account(user_id) -> tuple:
    [row] = rows(
        "SELECT name, email, password_hash, is_active, session_version FROM users WHERE id = %s",
        user_id,
    )
    return row


def roles_in_db(user_id) -> list[str]:
    return [
        r for (r,) in rows("SELECT role FROM user_roles WHERE user_id = %s ORDER BY role", user_id)
    ]


async def open_reset_token(c, user_id, email: str, now: datetime) -> str:
    response = await c.post("/api/auth/password-reset", json={"email": email}, headers=CSRF)
    assert response.status_code == 202
    [(reset_id,)] = rows("SELECT id FROM password_resets WHERE user_id = %s", user_id)
    return auth.link_token(service.PASSWORD_RESET, reset_id)


async def test_deactivating_ends_access_at_once_and_keeps_every_datum(admin, clock, identity_db):
    bard = await make(BARD, "Bård Hansen", [AccountRole.lecturer])
    before = account(bard)
    async with client() as admin_c, client() as bard_c, client("198.51.100.9") as other:
        await as_user(admin_c)
        await as_user(bard_c, BARD)
        assert (await bard_c.get("/api/auth/me")).status_code == 200
        reset_token = await open_reset_token(other, bard, BARD, clock)
        sent = await admin_c.post(
            "/api/admin/invitations", json={"email": BARD, "role": "admin"}, headers=CSRF
        )
        invitation_token = auth.link_token(service.INVITATION, uuid.UUID(sent.json()["id"]))
        with psycopg.connect(libpq_dsn(identity_db), autocommit=True) as listen:
            listen.execute(f"LISTEN {events.CHANNEL}")
            response = await deactivate(admin_c, bard)
            received = [json.loads(n.payload) for n in listen.notifies(timeout=2, stop_after=1)]
        me = await bard_c.get("/api/auth/me")
        relogin = await login(other, BARD, PASSWORD)
        reset = await other.post(
            "/api/auth/password-reset/check", json={"token": reset_token}, headers=CSRF
        )
        invitation = await other.post(
            "/api/auth/invitation/check", json={"token": invitation_token}, headers=CSRF
        )
        again = await deactivate(admin_c, bard)
        listed_invitations = (await admin_c.get("/api/admin/invitations")).json()["items"]

    assert response.status_code == 200
    assert response.json() == {
        "id": str(bard),
        "name": "Bård Hansen",
        "email": BARD,
        "roles": ["lecturer"],
        "is_active": False,
    }
    assert received == [{"topic": "user", "id": str(bard), "version": None}]
    assert {item["topic"] for item in received} == COMMAND_TOPICS["identity.deactivate_user"]
    # The live cookie is rejected at once; the right password names the deactivation.
    assert me.status_code == 401
    assert me.json()["error"]["code"] == "session_expired"
    assert relogin.status_code == 403
    assert relogin.json()["error"]["code"] == "account_deactivated"
    assert reset.status_code == 410
    assert invitation.status_code == 410
    # Nothing of the User is deleted or changed but the status and the session version.
    name, email, password_hash, is_active, version = account(bard)
    assert (name, email, password_hash) == before[:3]
    assert (is_active, version) == (False, before[4] + 1)
    assert roles_in_db(bard) == ["lecturer"]
    # The open reset link and Invitation are voided, so a reactivation does not bring them back,
    # and the Invitation list shows the Invitation as expired at the deactivation.
    assert rows("SELECT voided_at FROM password_resets WHERE user_id = %s", bard) == [(clock,)]
    assert rows("SELECT voided_at FROM invitations WHERE email = %s", BARD) == [(clock,)]
    [listed] = listed_invitations
    assert (listed["status"], listed["expires_at"]) == ("expired", clock.isoformat()[:-6] + "Z")
    # Deactivating again writes nothing.
    assert again.status_code == 200
    assert [row[1] for row in audit_rows()] == ["invitation.sent", "user.deactivated"]
    assert audit_rows()[-1] == (admin, "user.deactivated", {"user_id": str(bard)}, {}, clock)


async def test_reactivating_restores_login_with_the_same_password_and_roles(
    admin, clock, identity_db
):
    bard = await make(BARD, "Bård", [AccountRole.lecturer, AccountRole.admin])
    async with client() as admin_c, client() as old_c, client() as new_c:
        await as_user(admin_c)
        await as_user(old_c, BARD)
        assert (await deactivate(admin_c, bard)).status_code == 200
        with psycopg.connect(libpq_dsn(identity_db), autocommit=True) as listen:
            listen.execute(f"LISTEN {events.CHANNEL}")
            response = await reactivate(admin_c, bard)
            received = [json.loads(n.payload) for n in listen.notifies(timeout=2, stop_after=1)]
        relogin = await login(new_c, BARD, PASSWORD)
        me = await new_c.get("/api/auth/me")
        stale = await old_c.get("/api/auth/me")
        again = await reactivate(admin_c, bard)
    assert response.status_code == 200
    assert response.json()["is_active"] is True
    assert received == [{"topic": "user", "id": str(bard), "version": None}]
    assert {item["topic"] for item in received} == COMMAND_TOPICS["identity.reactivate_user"]
    assert relogin.status_code == 200
    assert me.json()["user"]["roles"] == ["admin", "lecturer"]
    # A session from before the deactivation stays ended.
    assert stale.status_code == 401
    assert again.status_code == 200
    assert audit_rows()[-2:] == [
        (admin, "user.deactivated", {"user_id": str(bard)}, {}, clock),
        (admin, "user.reactivated", {"user_id": str(bard)}, {}, clock),
    ]
    assert len(audit_rows()) == 2


async def test_an_admin_cannot_deactivate_themselves_even_beside_another_admin(admin):
    await make(BARD, "Bård", [AccountRole.admin])
    async with client() as c:
        await as_user(c)
        response = await deactivate(c, admin)
        assert (await c.get("/api/auth/me")).status_code == 200
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "last_admin"
    assert account(admin)[3] is True
    assert audit_rows() == []


async def test_an_admin_may_deactivate_another_active_admin(admin, clock):
    bard = await make(BARD, "Bård", [AccountRole.admin])
    async with client() as c:
        await as_user(c)
        response = await deactivate(c, bard)
    assert response.status_code == 200
    assert response.json()["roles"] == ["admin"]
    assert account(bard)[3] is False


async def test_a_deactivation_and_a_revoke_at_once_leave_one_active_admin(admin, monkeypatch):
    """Kari deactivates Bård while Bård revokes Kari's Admin role. Each transaction is held after
    its last-Admin count until the other has counted too (or a short wait ends). Without the
    shared `role:admin` lock both counts see one other active Admin and both go through, leaving
    none; with it the second count waits for the first commit and is refused."""
    bard = await make(BARD, "Bård", [AccountRole.admin])
    counted: list[uuid.UUID] = []
    both_counted = asyncio.Event()
    real_count = repo.count_active_holders

    async def held_count(session, role, *, excluding):
        found = await real_count(session, role, excluding=excluding)
        counted.append(excluding)
        if len(counted) == 2:
            both_counted.set()
        try:
            await asyncio.wait_for(both_counted.wait(), timeout=0.3)
        except TimeoutError:
            pass
        return found

    monkeypatch.setattr(repo, "count_active_holders", held_count)
    async with client() as kari_c, client() as bard_c:
        await as_user(kari_c)
        await as_user(bard_c, BARD)
        answers = await asyncio.gather(
            deactivate(kari_c, bard),
            bard_c.delete(f"/api/admin/users/{admin}/roles/admin", headers=CSRF),
        )
    assert sorted(a.status_code for a in answers) == [200, 409]
    assert [a.json()["error"]["code"] for a in answers if a.status_code == 409] == ["last_admin"]
    active_admins = rows(
        "SELECT count(*) FROM user_roles r JOIN users u ON u.id = r.user_id "
        "WHERE r.role = 'admin' AND u.is_active"
    )
    assert active_admins == [(1,)]
    assert len(audit_rows()) == 1


async def test_two_admins_deactivating_each_other_at_once_leave_one_active_admin(
    admin, monkeypatch
):
    """The same hold as above, with both sides deactivating."""
    bard = await make(BARD, "Bård", [AccountRole.admin])
    counted: list[uuid.UUID] = []
    both_counted = asyncio.Event()
    real_count = repo.count_active_holders

    async def held_count(session, role, *, excluding):
        found = await real_count(session, role, excluding=excluding)
        counted.append(excluding)
        if len(counted) == 2:
            both_counted.set()
        try:
            await asyncio.wait_for(both_counted.wait(), timeout=0.3)
        except TimeoutError:
            pass
        return found

    monkeypatch.setattr(repo, "count_active_holders", held_count)
    async with client() as kari_c, client() as bard_c:
        await as_user(kari_c)
        await as_user(bard_c, BARD)
        answers = await asyncio.gather(deactivate(kari_c, bard), deactivate(bard_c, admin))
    assert sorted(a.status_code for a in answers) == [200, 409]
    assert rows("SELECT count(*) FROM users WHERE is_active") == [(1,)]


async def test_an_acceptance_and_a_deactivation_of_the_same_user_at_once_never_deadlock(
    admin, clock, monkeypatch
):
    """Issue #82: Bård accepts an Invitation with his password while Kari deactivates him. Each
    side is held after its first row lock until the other has taken its own (or a short wait
    ends). When the acceptance locked the Invitation before the User, the deactivation (User, then
    the Invitations it voids) closed a cycle and Postgres aborted one of them with a 500. One lock
    order (User, then Invitation) lets them run in turn."""
    bard = await make(BARD, "Bård", [AccountRole.lecturer])
    sent = await service.send_invitation(admin, BARD, AccountRole.admin, now=clock)
    token = auth.link_token(service.INVITATION, sent.id)
    user_locked, invitation_locked = asyncio.Event(), asyncio.Event()
    real_lock_user, real_lock_invitation = repo.lock_user, repo.lock_invitation

    async def hold(mine: asyncio.Event, other: asyncio.Event) -> None:
        mine.set()
        try:
            await asyncio.wait_for(other.wait(), timeout=0.5)
        except TimeoutError:
            pass

    async def held_lock_user(session, user_id):
        found = await real_lock_user(session, user_id)
        await hold(user_locked, invitation_locked)
        return found

    async def held_lock_invitation(session, invitation_id):
        found = await real_lock_invitation(session, invitation_id)
        await hold(invitation_locked, user_locked)
        return found

    async with client() as kari_c, client("198.51.100.9") as bard_c:
        await as_user(kari_c)
        monkeypatch.setattr(repo, "lock_user", held_lock_user)
        monkeypatch.setattr(repo, "lock_invitation", held_lock_invitation)
        answers = await asyncio.gather(
            bard_c.post(
                "/api/auth/invitation/accept-login",
                json={"token": token, "password": PASSWORD},
                headers=CSRF,
            ),
            deactivate(kari_c, bard),
            return_exceptions=True,
        )
    accepted, deactivated = answers
    assert not isinstance(accepted, BaseException), accepted
    assert not isinstance(deactivated, BaseException), deactivated
    assert deactivated.status_code == 200
    assert accepted.status_code in (200, 410)
    assert account(bard)[3] is False
    # Either the acceptance ran first (the role is added) or it saw the deactivation.
    assert ("admin" in roles_in_db(bard)) == (accepted.status_code == 200)


async def test_only_an_admin_may_change_a_status(admin):
    lecturer = await make("lektor@example.com", "Lektor", [AccountRole.lecturer])
    async with client() as anon:
        assert (await deactivate(anon, lecturer)).status_code == 401
    async with client() as c:
        await as_user(c, "lektor@example.com")
        assert (await deactivate(c, admin)).status_code == 403
        assert (await reactivate(c, admin)).status_code == 403
    assert account(admin)[3] is True
    assert audit_rows() == []


async def test_an_unknown_user_is_not_found(admin):
    async with client() as c:
        await as_user(c)
        for response in (
            await deactivate(c, uuid.uuid7()),
            await reactivate(c, uuid.uuid7()),
        ):
            assert response.status_code == 404
            assert response.json()["error"]["code"] == "not_found"
        assert (await deactivate(c, "ikke-en-id")).status_code == 422
    assert audit_rows() == []


async def test_a_cookie_from_before_session_versions_still_works(admin, clock):
    """A token without `sv` (issued before Story 3.10) reads as version 0."""
    claims = {"user_id": str(admin), "iat": clock, "exp": clock + timedelta(hours=1)}
    token = jwt.encode(claims, get_settings().jwt_secret, algorithm=auth.ALGORITHM)
    async with client() as c:
        response = await c.get("/api/auth/me", headers={"Cookie": f"{auth.COOKIE_NAME}={token}"})
    assert response.status_code == 200


async def test_no_name_or_address_lands_in_a_log_line_or_an_audit_row(admin, clock):
    bard = await make(BARD, "Bård Hansen", [AccountRole.lecturer])
    with capture_logs() as logs:
        async with client() as c:
            await as_user(c)
            await deactivate(c, bard)
            await reactivate(c, bard)
    text = json.dumps([*map(str, logs), *map(str, audit_rows())])
    assert "Bård" not in text and BARD not in text
