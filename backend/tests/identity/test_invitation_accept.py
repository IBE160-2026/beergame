"""Accepting an Invitation, asking for a new one, and the first Admin (Story 3.8, FR-1, FR-2,
FR-4, AD-11, AD-15, AD-17). Every clock is fixed and moved by the test; the database clock is
never read."""

import asyncio
import json
from datetime import UTC, datetime, timedelta

import pytest
from structlog.testing import capture_logs

from app.modules.identity import service
from app.modules.identity.schemas import AccountRole
from app.platform import auth
from app.platform.config import get_settings
from tests.identity.helpers import CSRF, client, login
from tests.messaging.helpers import drain, mails, rows

ADMIN = "kari.admin@example.com"
INVITED = "ny.faglaerer@example.com"
PASSWORD = "admin-passordet"
NEW_PASSWORD = "mitt-nye-passord"


@pytest.fixture
def clock(monkeypatch):
    now = {"now": datetime(2026, 11, 18, 12, 1, tzinfo=UTC)}
    monkeypatch.setattr(auth, "utcnow", lambda: now["now"])
    return now


@pytest.fixture
async def admin(identity_db, mail_db):
    return await service.create_user(
        email=ADMIN, name="Kari", password=PASSWORD, roles=[AccountRole.admin]
    )


async def invitation(admin, clock, email: str = INVITED, role: str = "lecturer") -> tuple:
    """A sent Invitation's id and the token its mail carries."""
    sent = await service.send_invitation(admin, email, AccountRole(role), now=clock["now"])
    return sent.id, auth.link_token(service.INVITATION, sent.id)


async def check(c, token: str):
    return await c.post("/api/auth/invitation/check", json={"token": token}, headers=CSRF)


async def accept(c, token: str, name: str = "  Ny   Faglærer ", password: str = NEW_PASSWORD):
    body = {"token": token, "name": name, "password": password}
    return await c.post("/api/auth/invitation/accept", json=body, headers=CSRF)


async def accept_login(c, token: str, password: str):
    body = {"token": token, "password": password}
    return await c.post("/api/auth/invitation/accept-login", json=body, headers=CSRF)


async def renewal(c, token: str):
    return await c.post("/api/auth/invitation/renewal", json={"token": token}, headers=CSRF)


def users_with(email: str = INVITED) -> list[tuple]:
    return rows("SELECT id, name FROM users WHERE lower(email) = lower(%s)", email)


def accepted_at(invitation_id) -> object:
    return rows("SELECT accepted_at FROM invitations WHERE id = %s", invitation_id)[0][0]


async def test_a_usable_link_shows_the_address_the_role_and_the_days_left(admin, clock):
    _, token = await invitation(admin, clock)
    clock["now"] += timedelta(days=3, hours=1)
    async with client() as c:
        response = await check(c, token)
    assert response.status_code == 200
    assert response.json() == {
        "email": INVITED,
        "role": "lecturer",
        "valid_days": 11,
        "has_account": False,
    }


@pytest.mark.parametrize("state", ["unknown", "accepted", "voided", "expired", "deactivated"])
async def test_a_link_that_no_longer_works_is_one_answer(admin, clock, state):
    invitation_id, token = await invitation(admin, clock)
    if state == "unknown":
        token = "x" * 43
    elif state == "accepted":
        rows("UPDATE invitations SET accepted_at = %s RETURNING id", clock["now"])
    elif state == "voided":
        await invitation(admin, clock)  # sending again voids the first
    elif state == "expired":
        clock["now"] += timedelta(days=14)
    else:
        await service.create_user(email=INVITED, name="Ola", password=PASSWORD, is_active=False)
    async with client() as c:
        checked = await check(c, token)
        accepted = await accept(c, token)
    for response in (checked, accepted):
        assert response.status_code == 410
        assert response.json()["error"]["code"] == "invitation_link_invalid"
    assert len(users_with()) == (1 if state == "deactivated" else 0)


async def test_accepting_creates_the_account_with_its_role_and_logs_in(admin, clock):
    invitation_id, token = await invitation(admin, clock)
    async with client() as c:
        with capture_logs() as logs:
            response = await accept(c, token)
        assert response.status_code == 200
        user = response.json()["user"]
        assert (user["email"], user["name"]) == (INVITED, "Ny Faglærer")
        assert user["roles"] == ["lecturer"]
        me = await c.get("/api/auth/me")
        assert me.status_code == 200
        assert me.json()["user"]["id"] == user["id"]
        again = await accept(c, token)
    assert again.status_code == 410
    [(user_id, name)] = users_with()
    assert (str(user_id), name) == (user["id"], "Ny Faglærer")
    assert rows("SELECT role FROM user_roles WHERE user_id = %s", user_id) == [("lecturer",)]
    assert accepted_at(invitation_id) == clock["now"]
    [(actor, target, change)] = rows(
        "SELECT actor_user_id, target_ids, change FROM audit_events "
        "WHERE action = 'invitation.accepted'"
    )
    assert actor == user_id
    assert target == {"invitation_id": str(invitation_id), "user_id": str(user_id)}
    assert change == {"role": "lecturer", "account": "created"}
    # No address, name or token in a log line.
    text = json.dumps(logs, default=str)
    assert INVITED not in text and "Faglærer" not in text and token not in text


async def test_an_admin_invitation_makes_an_admin(admin, clock):
    _, token = await invitation(admin, clock, role="admin")
    async with client() as c:
        response = await accept(c, token)
    assert response.json()["user"]["roles"] == ["admin"]


async def test_an_account_made_meanwhile_is_not_made_twice(admin, clock):
    invitation_id, token = await invitation(admin, clock)
    async with client() as c:
        assert (await check(c, token)).json()["has_account"] is False
        await service.create_user(email=INVITED, name="Ola", password=PASSWORD)
        assert (await check(c, token)).json()["has_account"] is True
        response = await accept(c, token)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "account_exists"
    assert len(users_with()) == 1
    assert accepted_at(invitation_id) is None


async def test_an_existing_account_logs_in_and_gains_the_role(admin, clock):
    user_id = await service.create_user(
        email=INVITED, name="Ola", password=PASSWORD, roles=[AccountRole.lecturer]
    )
    invitation_id, token = await invitation(admin, clock, role="admin")
    async with client() as c:
        wrong = await accept_login(c, token, "feil-passord")
        assert wrong.status_code == 401
        assert wrong.json()["error"]["code"] == "invalid_credentials"
        assert accepted_at(invitation_id) is None
        response = await accept_login(c, token, PASSWORD)
        assert response.status_code == 200
        assert response.json()["user"]["roles"] == ["admin", "lecturer"]
        assert (await c.get("/api/auth/me")).status_code == 200
    assert users_with() == [(user_id, "Ola")]
    assert accepted_at(invitation_id) == clock["now"]
    [(change,)] = rows("SELECT change FROM audit_events WHERE action = 'invitation.accepted'")
    assert change == {"role": "admin", "account": "existing", "role_added": True}


async def test_the_existing_account_route_refuses_an_address_with_no_account(admin, clock):
    _, token = await invitation(admin, clock)
    async with client() as c:
        response = await accept_login(c, token, PASSWORD)
    assert response.status_code == 410
    assert users_with() == []


async def test_parallel_acceptances_make_one_account(admin, clock):
    _, token = await invitation(admin, clock)
    async with client() as c:
        responses = await asyncio.gather(accept(c, token), accept(c, token))
    assert sorted(r.status_code for r in responses) == [200, 410]
    assert len(users_with()) == 1


@pytest.mark.parametrize(
    ("name", "password", "field"),
    [
        ("   ", NEW_PASSWORD, "name"),
        ("Ola", "kort123", "password"),
        ("Ola\x00", NEW_PASSWORD, "name"),
    ],
)
async def test_a_bad_name_or_password_is_refused(admin, clock, name, password, field):
    invitation_id, token = await invitation(admin, clock)
    async with client() as c:
        response = await accept(c, token, name=name, password=password)
    assert response.status_code == 422
    assert field in response.json()["error"]["fields"]
    assert users_with() == []
    assert accepted_at(invitation_id) is None


async def test_acceptance_attempts_are_rate_limited_per_link(admin, clock, monkeypatch):
    monkeypatch.setenv("INVITATION_ACCEPT_RATE_LIMIT_PER_INVITATION", "2")
    get_settings.cache_clear()
    _, token = await invitation(admin, clock)
    async with client() as c:
        first = await accept_login(c, token, "x")
        second = await accept_login(c, token, "x")
        third = await accept(c, token)
    assert (first.status_code, second.status_code) == (410, 410)
    assert third.status_code == 429
    assert third.json()["error"]["code"] == "rate_limited"
    assert int(third.headers["Retry-After"]) > 0
    assert users_with() == []


async def test_acceptance_attempts_are_rate_limited_per_address(admin, clock, monkeypatch):
    monkeypatch.setenv("INVITATION_ACCEPT_RATE_LIMIT_PER_IP", "1")
    get_settings.cache_clear()
    _, token = await invitation(admin, clock)
    async with client() as c:
        await accept_login(c, "y" * 43, "x")
        response = await accept(c, token)
    assert response.status_code == 429


async def test_asking_for_a_new_invitation_answers_the_same_for_any_link(admin, clock):
    expired_id, expired = await invitation(admin, clock, email="gammel@example.com")
    clock["now"] += timedelta(days=15)
    open_id, open_token = await invitation(admin, clock)
    async with client() as c:
        answers = [await renewal(c, t) for t in (expired, "z" * 43, open_token)]
    assert [(r.status_code, r.content) for r in answers] == [(202, b"")] * 3
    marks = dict(rows("SELECT id, renewal_requested_at FROM invitations"))
    assert marks == {expired_id: clock["now"], open_id: None}


async def test_asking_for_a_new_invitation_is_rate_limited(admin, clock, monkeypatch):
    _, token = await invitation(admin, clock)
    async with client() as c:
        answers = [(await renewal(c, token)).status_code for _ in range(4)]
    assert answers == [202, 202, 202, 429]


# The first Admin (AD-17).


async def test_the_bootstrap_invitation_is_made_once_for_an_address_with_no_account(
    admin, clock, monkeypatch
):
    monkeypatch.setenv(
        "BOOTSTRAP_ADMIN_EMAILS",
        " Forste.Admin@Example.com, ikke-en-adresse, , kari.admin@example.com",
    )
    get_settings.cache_clear()
    [invitation_id] = await service.ensure_bootstrap_invitations(clock["now"])
    assert await service.ensure_bootstrap_invitations(clock["now"]) == []
    assert rows("SELECT email, role, invited_by FROM invitations") == [
        ("forste.admin@example.com", "admin", None)
    ]
    [(actor, action, target)] = rows("SELECT actor_user_id, action, target_ids FROM audit_events")
    assert (actor, action) == (None, "invitation.bootstrap")
    assert target == {"invitation_id": str(invitation_id)}
    await drain(clock["now"])
    [mail] = mails()
    assert mail.to == "forste.admin@example.com"
    assert "som Admin" in mail.text

    # Once expired unaccepted, the next start sends a fresh one.
    clock["now"] += timedelta(days=15)
    [renewed] = await service.ensure_bootstrap_invitations(clock["now"])
    assert renewed != invitation_id


async def test_the_api_makes_bootstrap_invitations_only_in_production(monkeypatch):
    from app import main

    calls = []

    async def record(now):
        calls.append(now)

    async def nothing():
        return None

    monkeypatch.setattr(main.identity_service, "ensure_bootstrap_invitations", record)
    monkeypatch.setattr(main.identity_seed, "ensure_demo_users_logged", nothing)
    import app.ai.seed

    monkeypatch.setattr(app.ai.seed, "ensure_zero_config_logged", nothing)
    for env, expected in (("local", 0), ("production", 1)):
        monkeypatch.setenv("APP_ENV", env)
        get_settings.cache_clear()
        async with main.lifespan(main.create_app()):
            pass
        assert len(calls) == expected


async def test_a_listed_user_gains_admin_at_first_login_only(
    identity_db, mail_db, clock, monkeypatch
):
    monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAILS", INVITED)
    get_settings.cache_clear()
    user_id = await service.create_user(
        email=INVITED, name="Ola", password=PASSWORD, roles=[AccountRole.lecturer]
    )
    async with client() as c:
        first = await login(c, INVITED, PASSWORD)
        assert first.json()["user"]["roles"] == ["admin", "lecturer"]
        rows("DELETE FROM user_roles WHERE user_id = %s AND role = 'admin' RETURNING role", user_id)
        second = await login(c, INVITED, PASSWORD)
    assert second.json()["user"]["roles"] == ["lecturer"]
    [(actor, action, change)] = rows("SELECT actor_user_id, action, change FROM audit_events")
    assert (actor, action, change) == (
        None,
        "role.bootstrap_granted",
        {"role": "admin", "role_added": True},
    )
