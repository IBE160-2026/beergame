"""Login, the session and logout through the api (Story 3.2, FR-4, AD-11, AD-19)."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.modules.identity import service
from app.modules.identity.models import users
from app.modules.identity.schemas import AccountRole
from app.platform import auth, ratelimit
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker
from tests.identity.helpers import CSRF, client, login

PASSWORD = "et langt nok passord"


@pytest.fixture
async def admin(identity_db):
    return await service.create_user(
        email="Kari.Admin@Example.com", name="Kari", password=PASSWORD, roles=[AccountRole.admin]
    )


@pytest.fixture
def frozen(monkeypatch):
    """The login clock, fixed and movable, so the rate-limit window never depends on a real
    clock (the database clock is never read)."""
    clock = {"now": datetime(2026, 11, 18, 12, 1, tzinfo=UTC)}
    monkeypatch.setattr(auth, "utcnow", lambda: clock["now"])
    return clock


async def test_the_right_login_sets_the_session_cookie_and_returns_the_user(admin):
    async with client() as c:
        response = await login(c, "  kari.admin@EXAMPLE.com ", PASSWORD)
        assert response.status_code == 200
        user = response.json()["user"]
        assert user == {
            "id": str(admin),
            "name": "Kari",
            "email": "kari.admin@example.com",
            "roles": ["admin"],
        }
        cookie = response.headers["set-cookie"]
        assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=lax" in cookie
        me = await c.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json() == {"user": user}


@pytest.mark.parametrize(
    "email,password",
    [("kari.admin@example.com", "feil passord"), ("ingen@example.com", PASSWORD)],
    ids=["wrong-password", "unknown-email"],
)
async def test_a_wrong_login_answers_invalid_credentials_without_saying_which(
    admin, email, password
):
    async with client() as c:
        response = await login(c, email, password)
        assert (await c.get("/api/auth/me")).status_code == 401
    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "invalid_credentials",
            "message": "Wrong e-mail or password.",
            "fields": {},
        }
    }
    assert "set-cookie" not in response.headers


async def test_a_deactivated_user_is_named_only_after_the_right_password(admin):
    async with get_sessionmaker().begin() as s:
        await s.execute(update(users).where(users.c.id == admin).values(is_active=False))
    async with client() as c:
        wrong = await login(c, "kari.admin@example.com", "feil passord")
        right = await login(c, "kari.admin@example.com", PASSWORD)
    assert wrong.json()["error"]["code"] == "invalid_credentials"
    assert right.status_code == 403
    assert right.json()["error"]["code"] == "account_deactivated"
    assert "set-cookie" not in right.headers


async def test_a_cookie_stops_working_when_the_user_is_deactivated(admin):
    async with client() as c:
        await login(c, "kari.admin@example.com", PASSWORD)
        async with get_sessionmaker().begin() as s:
            await s.execute(update(users).where(users.c.id == admin).values(is_active=False))
        response = await c.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def _with_cookie(token: str) -> dict[str, str]:
    return {"Cookie": f"{auth.COOKIE_NAME}={token}"}


async def test_a_cookie_of_a_user_who_is_gone_or_tampered_is_refused(admin):
    token = auth.issue_token(admin)
    gone = auth.issue_token(service.uuid.uuid7())
    async with client() as c:
        assert (await c.get("/api/auth/me", headers=_with_cookie(token))).status_code == 200
        tampered = await c.get("/api/auth/me", headers=_with_cookie(token[:-3] + "abc"))
        assert tampered.status_code == 401
        assert (await c.get("/api/auth/me", headers=_with_cookie(gone))).status_code == 401


async def test_an_expired_cookie_is_refused(admin, frozen):
    token = auth.issue_token(admin)
    async with client() as c:
        assert (await c.get("/api/auth/me", headers=_with_cookie(token))).status_code == 200
        frozen["now"] += timedelta(hours=get_settings().session_max_age_hours)
        assert (await c.get("/api/auth/me", headers=_with_cookie(token))).status_code == 401


async def test_logout_clears_the_cookie(admin):
    async with client() as c:
        await login(c, "kari.admin@example.com", PASSWORD)
        assert (await c.get("/api/auth/me")).status_code == 200
        response = await c.post("/api/auth/logout", headers=CSRF)
        assert response.status_code == 204
        assert "Max-Age=0" in response.headers["set-cookie"]
        assert (await c.get("/api/auth/me")).status_code == 401


async def test_a_body_that_fails_validation_answers_in_the_envelope_without_its_values(
    identity_db,
):
    async with client() as c:
        response = await c.post(
            "/api/auth/login", json={"email": "a@b.no", "password": 12345678}, headers=CSRF
        )
        missing = await c.post("/api/auth/login", json={}, headers=CSRF)
    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "invalid_request"
    assert set(body["fields"]) == {"password"}
    assert "12345678" not in response.text
    assert set(missing.json()["error"]["fields"]) == {"email", "password"}


async def test_the_account_limit_refuses_even_the_right_password_until_the_window_ends(
    admin, frozen
):
    limit = get_settings().login_rate_limit_per_account
    async with client() as c:
        for _ in range(limit):
            assert (await login(c, "kari.admin@example.com", "feil")).status_code == 401
        refused = await login(c, "kari.admin@example.com", PASSWORD)
        assert refused.status_code == 429
        assert refused.json()["error"]["code"] == "rate_limited"
        window = timedelta(minutes=get_settings().login_rate_limit_window_minutes)
        start = ratelimit.window_start(frozen["now"], window)
        assert int(refused.headers["Retry-After"]) == int(
            (start + window - frozen["now"]).total_seconds()
        )
        frozen["now"] = start + window
        assert (await login(c, "kari.admin@example.com", PASSWORD)).status_code == 200


async def test_a_success_resets_the_account_count(admin, frozen):
    limit = get_settings().login_rate_limit_per_account
    async with client() as c:
        for _ in range(limit - 1):
            await login(c, "kari.admin@example.com", "feil")
        assert (await login(c, "kari.admin@example.com", PASSWORD)).status_code == 200
        for _ in range(limit - 1):
            assert (await login(c, "kari.admin@example.com", "feil")).status_code == 401
        assert (await login(c, "kari.admin@example.com", PASSWORD)).status_code == 200


async def test_the_ip_limit_counts_failures_across_accounts(admin, frozen, monkeypatch):
    monkeypatch.setenv("LOGIN_RATE_LIMIT_PER_IP", "3")
    get_settings.cache_clear()
    async with client(ip="198.51.100.9") as c:
        for n in range(3):
            assert (await login(c, f"ukjent{n}@example.com", "feil")).status_code == 401
        refused = await login(c, "kari.admin@example.com", PASSWORD)
    assert refused.status_code == 429
    async with client(ip="198.51.100.10") as other:
        assert (await login(other, "kari.admin@example.com", PASSWORD)).status_code == 200


async def test_the_ip_is_read_from_the_last_forwarded_entry(admin, frozen, monkeypatch):
    monkeypatch.setenv("LOGIN_RATE_LIMIT_PER_IP", "1")
    get_settings.cache_clear()
    async with client() as c:
        headers = {**CSRF, "X-Forwarded-For": "10.0.0.1, 192.0.2.44"}
        body = {"email": "ukjent@example.com", "password": "feil"}
        await c.post("/api/auth/login", json=body, headers=headers)
        same = await c.post(
            "/api/auth/login",
            json={"email": "kari.admin@example.com", "password": PASSWORD},
            headers={**CSRF, "X-Forwarded-For": "192.0.2.44"},
        )
        other = await c.post(
            "/api/auth/login",
            json={"email": "kari.admin@example.com", "password": PASSWORD},
            headers={**CSRF, "X-Forwarded-For": "192.0.2.45"},
        )
    assert same.status_code == 429
    assert other.status_code == 200


async def test_no_email_or_ip_is_stored_in_the_rate_limit_table(admin, frozen):
    async with client(ip="198.51.100.77") as c:
        await login(c, "kari.admin@example.com", "feil")
    async with get_sessionmaker().begin() as s:
        rows = (await s.execute(select(ratelimit.rate_limit_counters))).mappings().all()
    assert len(rows) == 2
    text = repr(rows)
    assert "kari" not in text and "198.51.100.77" not in text


async def test_parallel_wrong_guesses_cannot_pass_the_account_limit(admin, frozen):
    """Each attempt is counted before its password is checked, so a burst of parallel guesses
    gets exactly the limit's number of password checks."""
    limit = get_settings().login_rate_limit_per_account
    outcomes = await asyncio.gather(
        *(
            service.authenticate(
                "kari.admin@example.com", "feil", ip=f"10.0.0.{n}", now=frozen["now"]
            )
            for n in range(limit + 6)
        )
    )
    codes = sorted(outcome.code for outcome in outcomes)
    assert codes.count("invalid_credentials") == limit
    assert codes.count("rate_limited") == 6


async def test_parallel_right_logins_to_one_account_from_one_address_all_succeed(admin, frozen):
    """Story 3.3 found a deadlock: the success transaction took the account row before the IP
    row, against the order of the count. Many tabs or tests log in as one User at once. (More
    parallel attempts than the account limit are refused by design: each is counted first.)"""
    limit = get_settings().login_rate_limit_per_account
    outcomes = await asyncio.gather(
        *(
            service.authenticate(
                "kari.admin@example.com", PASSWORD, ip="10.0.0.1", now=frozen["now"]
            )
            for _ in range(limit)
        )
    )
    assert [type(outcome).__name__ for outcome in outcomes] == ["LoginOk"] * limit


async def test_a_deactivated_users_right_password_does_not_reset_the_count(admin, frozen):
    limit = get_settings().login_rate_limit_per_account
    async with get_sessionmaker().begin() as s:
        await s.execute(update(users).where(users.c.id == admin).values(is_active=False))
    async with client() as c:
        for _ in range(limit - 1):
            await login(c, "kari.admin@example.com", "feil")
        assert (await login(c, "kari.admin@example.com", PASSWORD)).status_code == 403
        assert (await login(c, "kari.admin@example.com", PASSWORD)).status_code == 429


async def test_two_emails_that_differ_only_in_case_are_one_account(admin):
    with pytest.raises(IntegrityError):
        await service.create_user(email="KARI.ADMIN@example.com", name="Kari 2", password="x" * 12)
    with pytest.raises(IntegrityError):  # the CHECK refuses an un-normalised e-mail outright
        async with get_sessionmaker().begin() as s:
            await s.execute(
                users.insert().values(
                    id=service.uuid.uuid7(),
                    email="Kari.Admin@Example.com",
                    name="Kari 3",
                    password_hash="x",
                )
            )
