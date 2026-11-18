"""The local dev mailbox (Story 3.6): the newest mail to a User, rendered again, so Playwright
can follow a link from the `[email:mock]` mail. It does not exist in production."""

from datetime import UTC, datetime

from fastapi.routing import APIRoute, iter_route_contexts

from app.main import create_app
from app.modules.identity import service as identity
from app.platform import auth
from tests.identity.helpers import CSRF, client
from tests.messaging.helpers import drain, mails

NOW = datetime(2026, 11, 18, 12, 1, tzinfo=UTC)


async def test_it_returns_the_newest_mail_sent_to_the_address(identity_db, mail_db, monkeypatch):
    monkeypatch.setattr(auth, "utcnow", lambda: NOW)
    await identity.create_user(email="kari@example.com", name="Kari", password="et passord")
    async with client() as c:
        empty = await c.get("/api/dev/mailbox/latest", params={"to": "kari@example.com"})
        await c.post("/api/auth/password-reset", json={"email": "kari@example.com"}, headers=CSRF)
        await drain(NOW)
        found = await c.get("/api/dev/mailbox/latest", params={"to": "KARI@example.com"})
        nobody = await c.get("/api/dev/mailbox/latest", params={"to": "ingen@example.com"})
    assert empty.status_code == 404
    assert nobody.status_code == 404
    assert nobody.json()["error"]["code"] == "not_found"
    assert found.status_code == 200
    [sent] = mails()
    body = found.json()
    assert (body["subject"], body["text"], body["html"]) == (sent.subject, sent.text, sent.html)
    assert datetime.fromisoformat(body["sent_at"]) == NOW


def test_it_is_not_routed_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db.example/olspillet")
    paths = {
        ctx.path
        for ctx in iter_route_contexts(create_app().routes)
        if isinstance(ctx.route, APIRoute)
    }
    assert "/api/auth/password-reset" in paths
    assert not any(path.startswith("/api/dev") for path in paths)


def test_it_is_not_in_the_openapi_schema():
    assert not any(path.startswith("/api/dev") for path in create_app().openapi()["paths"])


async def test_it_finds_an_invitation_mail_by_its_address(identity_db, mail_db, monkeypatch):
    from app.modules.identity.schemas import AccountRole

    monkeypatch.setattr(auth, "utcnow", lambda: NOW)
    admin = await identity.create_user(
        email="admin@example.com", name="Admin", password="et passord", roles=[AccountRole.admin]
    )
    await identity.send_invitation(admin, "ny@example.com", AccountRole.lecturer, now=NOW)
    await drain(NOW)
    async with client() as c:
        found = await c.get("/api/dev/mailbox/latest", params={"to": "Ny@example.com"})
    assert found.status_code == 200
    [sent] = mails()
    assert found.json()["text"] == sent.text
