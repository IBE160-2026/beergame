"""Password reset by e-mail through the api and the mail pipeline (Story 3.6, FR-4, AD-9, AD-11,
AD-14, UX-DR61). Every clock is fixed and moved by the test; the database clock is never read."""

import asyncio
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

OLD = "det gamle passordet"
NEW = "et helt nytt passord"
EMAIL = "kari.faglaerer@example.com"
LINK = re.compile(r"http://127\.0\.0\.1:8080/nytt-passord#([A-Za-z0-9_-]+)")


@pytest.fixture
def clock(monkeypatch):
    """The api's clock, fixed and movable."""
    now = {"now": datetime(2026, 11, 18, 12, 1, tzinfo=UTC)}
    monkeypatch.setattr(auth, "utcnow", lambda: now["now"])
    return now


@pytest.fixture
async def lecturer(identity_db, mail_db):
    return await service.create_user(
        email=EMAIL, name="Kari", password=OLD, roles=[AccountRole.lecturer]
    )


async def ask(c, email: str = EMAIL):
    return await c.post("/api/auth/password-reset", json={"email": email}, headers=CSRF)


async def check(c, token: str):
    return await c.post("/api/auth/password-reset/check", json={"token": token}, headers=CSRF)


async def confirm(c, token: str, password: str = NEW):
    body = {"token": token, "password": password}
    return await c.post("/api/auth/password-reset/confirm", json=body, headers=CSRF)


async def mailed_token(now: datetime) -> str:
    """Run the mail jobs at `now` and return the token from the newest mail's link."""
    await drain(now)
    return LINK.search(mails()[-1].text).group(1)


async def test_an_active_user_gets_one_mail_with_a_link_that_works_once(lecturer, clock):
    async with client() as c:
        response = await ask(c, "  Kari.Faglaerer@EXAMPLE.com ")
        assert response.status_code == 202
        assert response.content == b""
        [(token_hash, expires_at)] = rows("SELECT token_hash, expires_at FROM password_resets")
        assert expires_at == clock["now"] + timedelta(minutes=60)

        token = await mailed_token(clock["now"])
        [mail] = mails()
        assert mail.to == EMAIL
        assert mail.sender == get_settings().email_from
        assert mail.subject == "Nytt passord til ØL-spillet"
        assert mail.text.startswith("ØL-spillet")
        assert "Lenken virker i én time" in mail.text
        assert "http://127.0.0.1:8080/nytt-passord#" + token in mail.html
        assert auth.token_hash(token) == token_hash
        assert deliveries() == [("immediate", 1, True, None, 1)]

        assert (await check(c, token)).json() == {"email": EMAIL}
        done = await confirm(c, token)
        assert done.status_code == 200
        assert done.json() == {"email": EMAIL}
        assert (await login(c, EMAIL, NEW)).status_code == 200
        assert (await login(c, EMAIL, OLD)).status_code == 401

        # Single use: the link is spent.
        for again in (await check(c, token), await confirm(c, token, "et tredje passord")):
            assert again.status_code == 410
            assert again.json()["error"]["code"] == "reset_link_invalid"
    assert rows("SELECT used_at FROM password_resets") == [(clock["now"],)]


async def test_using_one_link_voids_the_users_other_open_links(lecturer, clock):
    async with client() as c:
        await ask(c)
        first = await mailed_token(clock["now"])
        clock["now"] += timedelta(minutes=1)
        await ask(c)
        second = await mailed_token(clock["now"])
        assert first != second
        assert (await confirm(c, second)).status_code == 200
        assert (await check(c, first)).status_code == 410
        assert (await confirm(c, first, "et tredje passord")).status_code == 410
        assert (await login(c, EMAIL, NEW)).status_code == 200
    assert sorted(
        rows("SELECT used_at IS NOT NULL, voided_at IS NOT NULL FROM password_resets")
    ) == [(False, True), (True, False)]


@pytest.mark.parametrize("who", ["deactivated", "nobody"])
async def test_a_deactivated_user_or_an_unknown_address_gets_the_same_answer_and_no_mail(
    identity_db, mail_db, clock, who
):
    if who == "deactivated":
        await service.create_user(email=EMAIL, name="Kari", password=OLD, is_active=False)
    async with client() as c:
        response = await ask(c)
    assert response.status_code == 202
    assert response.content == b""
    await drain(clock["now"])
    assert rows("SELECT count(*) FROM password_resets") == [(0,)]
    assert rows("SELECT count(*) FROM notices") == [(0,)]
    assert mails() == []


async def test_requests_are_limited_per_account(lecturer, clock):
    async with client() as c:
        # Case and spaces do not make another account.
        for variant in (EMAIL, EMAIL.upper(), f"  {EMAIL} ", EMAIL.title(), EMAIL):
            assert (await ask(c, variant)).status_code == 202
        refused = await ask(c, EMAIL.upper())
        # Any address counts, known or not, so the limit reveals nothing either.
        for _ in range(5):
            assert (await ask(c, "ingen@example.com")).status_code == 202
        unknown = await ask(c, "ingen@example.com")
    for response in (refused, unknown):
        assert response.status_code == 429
        assert response.json()["error"]["code"] == "rate_limited"
        assert int(response.headers["Retry-After"]) > 0
    assert rows("SELECT count(*) FROM password_resets") == [(5,)]


async def test_requests_are_limited_per_ip_address(lecturer, clock, monkeypatch):
    monkeypatch.setenv("PASSWORD_RESET_RATE_LIMIT_PER_IP", "2")
    get_settings.cache_clear()
    async with client("198.51.100.4") as c:
        assert (await ask(c, "a@example.com")).status_code == 202
        assert (await ask(c, "b@example.com")).status_code == 202
        assert (await ask(c, "c@example.com")).status_code == 429
    async with client("198.51.100.5") as other:
        assert (await ask(other)).status_code == 202


async def test_an_expired_link_works_no_more_and_its_late_mail_is_skipped(lecturer, clock):
    async with client() as c:
        await ask(c)
        start = clock["now"]
        token = auth.link_token(
            service.PASSWORD_RESET, rows("SELECT id FROM password_resets")[0][0]
        )
        clock["now"] = start + timedelta(minutes=60)
        assert (await check(c, token)).status_code == 410
        assert (await confirm(c, token)).status_code == 410
    # The claim job ran late, after the hour: no dead link is mailed.
    await drain(start + timedelta(minutes=61))
    assert mails() == []
    assert deliveries() == [("immediate", 1, False, "stale", 0)]


async def test_a_user_deactivated_after_the_request_can_not_use_the_link(lecturer, clock):
    async with client() as c:
        await ask(c)
        token = await mailed_token(clock["now"])
        await ask(c)
        rows("UPDATE users SET is_active = false RETURNING id")
        await drain(clock["now"])
        assert (await check(c, token)).status_code == 410
        assert (await confirm(c, token)).status_code == 410
    assert len(mails()) == 1
    assert deliveries()[-1] == ("immediate", 1, False, "no_recipient", 0)


async def test_a_short_password_is_refused_and_the_link_still_works(lecturer, clock):
    async with client() as c:
        await ask(c)
        token = await mailed_token(clock["now"])
        short = await confirm(c, token, "1234567")
        assert short.status_code == 422
        assert short.json()["error"]["fields"] == {"password": "string_too_short"}
        assert (await check(c, token)).status_code == 200


async def test_a_reset_clears_the_failed_login_count(lecturer, clock):
    async with client() as c:
        for _ in range(5):
            await login(c, EMAIL, "feil passord")
        assert (await login(c, EMAIL, OLD)).status_code == 429
        await ask(c)
        assert (await confirm(c, await mailed_token(clock["now"]))).status_code == 200
        assert (await login(c, EMAIL, NEW)).status_code == 200


async def test_no_name_email_or_token_reaches_a_log_line_or_a_job_argument(lecturer, clock):
    with capture_logs() as logs:
        async with client() as c:
            await ask(c)
            jobs = rows("SELECT args::text FROM procrastinate_jobs")
            token = await mailed_token(clock["now"])
            await confirm(c, token)
    jobs += rows("SELECT args::text FROM procrastinate_jobs")
    seen = repr(logs) + repr(jobs) + repr(rows("SELECT * FROM notices"))
    seen += repr(rows("SELECT * FROM mail_deliveries"))
    assert logs and jobs
    for secret in (EMAIL, "Kari", token, "nytt-passord"):
        assert secret not in seen


async def test_parallel_confirmations_let_exactly_one_through(lecturer, clock):
    """One link, or two open links of one User, confirmed at once: one password is set."""
    async with client() as c:
        await ask(c)
        first = await mailed_token(clock["now"])
        await ask(c)
        second = await mailed_token(clock["now"])
    tokens = [first, first, second, second]
    passwords = [f"parallelt passord {n}" for n in range(len(tokens))]
    outcomes = await asyncio.gather(
        *(
            service.confirm_password_reset(token, password, now=clock["now"])
            for token, password in zip(tokens, passwords, strict=True)
        )
    )
    assert [o for o in outcomes if o is not None] == [EMAIL]
    winner = passwords[[o is not None for o in outcomes].index(True)]
    async with client() as c:
        assert (await login(c, EMAIL, winner)).status_code == 200


async def test_a_late_mail_states_the_time_left(lecturer, clock):
    async with client() as c:
        await ask(c)
    await drain(clock["now"] + timedelta(minutes=59, seconds=30))
    assert "Lenken virker i ett minutt" in mails()[0].text
