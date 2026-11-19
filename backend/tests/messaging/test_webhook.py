"""The mail provider's webhook (Story 4.6, AD-11, AD-14, NFR-10): the Svix signature, storing a
delivery or bounce on its mail, idempotency on the event id, unknown mails, and the local bounce
stand-in. The api's clock is fixed; the database clock is never read."""

import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest
import structlog.testing
from fastapi.routing import APIRoute, iter_route_contexts

from app.main import create_app
from app.modules.messaging import service, signature
from app.platform import auth
from app.platform.config import LOCAL_RESEND_WEBHOOK_SECRET
from tests.conftest import enter_production
from tests.identity.helpers import CSRF, client
from tests.messaging.helpers import drain, enqueue, rows, user

NOW = datetime(2026, 11, 19, 9, 0, tzinfo=UTC)
PATH = "/api/webhooks/resend"
ADDRESS = "kari@example.no"


@pytest.fixture(autouse=True)
def _clock(monkeypatch):
    monkeypatch.setattr(auth, "utcnow", lambda: NOW)


@pytest.fixture
async def sent(identity_db, mail_db) -> str:
    """One mail sent through the mock: its provider message id."""
    user_id = await user(ADDRESS)
    await enqueue(user_id, "test_immediate")
    await drain(NOW)
    [(provider_id,)] = rows("SELECT provider_message_id FROM mail_deliveries")
    return provider_id


def event(kind: str, provider_id: str, bounce: str | None = None) -> bytes:
    data: dict = {"email_id": provider_id, "to": [ADDRESS]}
    if bounce is not None:
        data["bounce"] = {"type": bounce, "subType": "General", "message": "550 no such user"}
    return json.dumps({"type": kind, "created_at": NOW.isoformat(), "data": data}).encode()


def signed(
    body: bytes,
    event_id: str | None = None,
    *,
    at: datetime = NOW,
    secret: str = LOCAL_RESEND_WEBHOOK_SECRET,
) -> dict[str, str]:
    event_id = event_id or f"msg_{uuid.uuid4().hex}"
    stamp = int(at.timestamp())
    return {
        "svix-id": event_id,
        "svix-timestamp": str(stamp),
        "svix-signature": signature.sign(secret, event_id, stamp, body),
        "content-type": "application/json",
    }


async def post(body: bytes, headers: dict[str, str]):
    async with client() as c:
        return await c.post(PATH, content=body, headers=headers)


def stored() -> list[tuple]:
    return rows("SELECT delivery_state, bounce_class, last_event_id FROM mail_deliveries")


async def test_a_signed_hard_bounce_is_stored_on_its_mail_without_the_csrf_header(sent):
    body = event("email.bounced", sent, "Permanent")
    response = await post(body, signed(body, "msg_1"))
    assert response.status_code == 200
    assert response.json() == {"outcome": "stored"}
    assert stored() == [("bounced", "hard", "msg_1")]


@pytest.mark.parametrize("bounce", ["Transient", "Undetermined", None])
async def test_every_other_bounce_is_soft(sent, bounce):
    body = event("email.bounced", sent, bounce)
    assert (await post(body, signed(body, "msg_1"))).status_code == 200
    assert stored() == [("bounced", "soft", "msg_1")]


@pytest.mark.parametrize(
    ("kind", "state"), [("email.delivered", "delivered"), ("email.delivery_delayed", "delayed")]
)
async def test_a_delivery_or_a_delay_is_stored(sent, kind, state):
    body = event(kind, sent)
    assert (await post(body, signed(body, "msg_1"))).status_code == 200
    assert stored() == [(state, None, "msg_1")]


def _tampered(body: bytes, headers: dict[str, str]) -> tuple[bytes, dict[str, str]]:
    return body.replace(b"bounced", b"delivered"), headers


def _wrong_secret(body: bytes, _: dict[str, str]) -> tuple[bytes, dict[str, str]]:
    return body, signed(body, "msg_1", secret="whsec_b3RoZXIta2V5")


def _no_signature(body: bytes, headers: dict[str, str]) -> tuple[bytes, dict[str, str]]:
    return body, {k: v for k, v in headers.items() if k != "svix-signature"}


def _no_id(body: bytes, headers: dict[str, str]) -> tuple[bytes, dict[str, str]]:
    return body, {k: v for k, v in headers.items() if k != "svix-id"}


def _other_id(body: bytes, headers: dict[str, str]) -> tuple[bytes, dict[str, str]]:
    return body, {**headers, "svix-id": "msg_2"}


def _stale(body: bytes, _: dict[str, str]) -> tuple[bytes, dict[str, str]]:
    return body, signed(body, "msg_1", at=NOW - timedelta(minutes=6))


def _ahead(body: bytes, _: dict[str, str]) -> tuple[bytes, dict[str, str]]:
    return body, signed(body, "msg_1", at=NOW + timedelta(minutes=6))


def _garbled(body: bytes, headers: dict[str, str]) -> tuple[bytes, dict[str, str]]:
    return body, {**headers, "svix-signature": "v1,AAAA v2,zzz"}


def _bad_stamp(body: bytes, headers: dict[str, str]) -> tuple[bytes, dict[str, str]]:
    return body, {**headers, "svix-timestamp": "soon"}


def _unsigned(body: bytes, _: dict[str, str]) -> tuple[bytes, dict[str, str]]:
    return body, {"content-type": "application/json"}


@pytest.mark.parametrize(
    "spoil",
    [
        _tampered,
        _wrong_secret,
        _no_signature,
        _no_id,
        _other_id,
        _stale,
        _ahead,
        _garbled,
        _bad_stamp,
        _unsigned,
    ],
)
async def test_an_unsigned_wrongly_signed_or_stale_request_is_refused_and_nothing_stored(
    sent, spoil
):
    body = event("email.bounced", sent, "Permanent")
    response = await post(*spoil(body, signed(body, "msg_1")))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "webhook_signature_invalid"
    assert stored() == [(None, None, None)]


async def test_a_signature_among_several_is_enough(sent):
    body = event("email.bounced", sent, "Permanent")
    headers = signed(body, "msg_1")
    headers["svix-signature"] = "v1,b2xkLXNpZ25hdHVyZQ== " + headers["svix-signature"]
    assert (await post(body, headers)).status_code == 200


async def test_the_same_event_twice_changes_nothing(sent):
    body = event("email.bounced", sent, "Transient")
    first = await post(body, signed(body, "msg_1"))
    again = await post(body, signed(body, "msg_1"))
    assert first.json() == {"outcome": "stored"}
    assert again.status_code == 200
    assert again.json() == {"outcome": "repeated"}
    assert stored() == [("bounced", "soft", "msg_1")]


async def test_a_late_delivery_or_soft_bounce_never_undoes_a_hard_bounce(sent):
    hard = event("email.bounced", sent, "Permanent")
    await post(hard, signed(hard, "msg_1"))
    for event_id, later in [
        ("msg_2", event("email.delivered", sent)),
        ("msg_3", event("email.delivery_delayed", sent)),
        ("msg_4", event("email.bounced", sent, "Transient")),
    ]:
        answer = await post(later, signed(later, event_id))
        assert answer.json() == {"outcome": "unchanged"}
    assert stored() == [("bounced", "hard", "msg_1")]


async def test_a_delivery_after_a_soft_bounce_wins_and_a_late_soft_bounce_does_not(sent):
    soft = event("email.bounced", sent, "Transient")
    delivered = event("email.delivered", sent)
    await post(soft, signed(soft, "msg_1"))
    await post(delivered, signed(delivered, "msg_2"))
    assert stored() == [("delivered", None, "msg_2")]
    late = await post(soft, signed(soft, "msg_3"))
    assert late.json() == {"outcome": "unchanged"}
    assert stored() == [("delivered", None, "msg_2")]


async def test_an_older_event_replayed_after_a_newer_one_changes_nothing(sent):
    delivered = event("email.delivered", sent)
    hard = event("email.bounced", sent, "Permanent")
    await post(delivered, signed(delivered, "msg_1"))
    await post(hard, signed(hard, "msg_2"))
    again = await post(delivered, signed(delivered, "msg_1"))
    assert again.status_code == 200
    assert again.json() == {"outcome": "unchanged"}
    assert stored() == [("bounced", "hard", "msg_2")]


async def test_a_bounce_after_a_delivery_is_stored(sent):
    delivered = event("email.delivered", sent)
    bounced = event("email.bounced", sent, "Permanent")
    await post(delivered, signed(delivered, "msg_1"))
    await post(bounced, signed(bounced, "msg_2"))
    assert stored() == [("bounced", "hard", "msg_2")]


async def test_a_soft_bounce_turns_hard_when_a_hard_one_follows(sent):
    soft = event("email.bounced", sent, "Transient")
    hard = event("email.bounced", sent, "Permanent")
    await post(soft, signed(soft, "msg_1"))
    await post(hard, signed(hard, "msg_2"))
    assert stored() == [("bounced", "hard", "msg_2")]


async def test_an_event_for_an_unknown_mail_is_acknowledged_and_logged_without_an_address(sent):
    body = event("email.bounced", "re_unknown", "Permanent")
    with structlog.testing.capture_logs() as logs:
        response = await post(body, signed(body, "msg_1"))
    assert response.status_code == 200
    assert response.json() == {"outcome": "ignored"}
    assert stored() == [(None, None, None)]
    [line] = [entry for entry in logs if entry["event"] == "webhook_event_ignored"]
    assert line["event_type"] == "email.bounced"
    assert ADDRESS not in repr(logs)


async def test_another_event_type_is_acknowledged_and_ignored(sent):
    body = event("email.opened", sent)
    with structlog.testing.capture_logs() as logs:
        response = await post(body, signed(body, "msg_1"))
    assert response.json() == {"outcome": "ignored"}
    assert stored() == [(None, None, None)]
    assert ADDRESS not in repr(logs)


@pytest.mark.parametrize(
    "body",
    [b"not json", b"[]", b'{"type": "email.bounced"}', b'{"type": "email.bounced", "data": {}}'],
)
async def test_a_signed_body_that_is_no_event_is_refused(sent, body):
    response = await post(body, signed(body, "msg_1"))
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"
    assert stored() == [(None, None, None)]


async def test_a_body_over_the_limit_is_refused_unread(sent):
    body = b"x" * (256 * 1024 + 1)
    response = await post(body, signed(body, "msg_1"))
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"


async def test_a_streamed_body_over_the_limit_is_refused_without_a_declared_length(sent):
    async def chunks():
        for _ in range(65):
            yield b"x" * 4096

    async with client() as c:
        response = await c.post(PATH, content=chunks(), headers=signed(b"", "msg_1"))
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"
    assert stored() == [(None, None, None)]


async def test_an_ignored_event_type_needs_no_readable_data(sent):
    body = b'{"type": "contact.created", "data": "x"}'
    response = await post(body, signed(body, "msg_1"))
    assert response.status_code == 200
    assert response.json() == {"outcome": "ignored"}


async def test_the_local_bounce_signs_an_event_through_the_same_handler(sent):
    async with client() as c:
        response = await c.post(
            "/api/dev/mailbox/bounce",
            json={"to": "Kari@Example.no", "bounce_class": "soft"},
            headers=CSRF,
        )
        nobody = await c.post(
            "/api/dev/mailbox/bounce",
            json={"to": "ingen@example.no", "bounce_class": "hard"},
            headers=CSRF,
        )
    assert response.status_code == 200
    [(delivery_id,)] = rows("SELECT id FROM mail_deliveries")
    assert response.json() == {"delivery_id": str(delivery_id)}
    [(state, bounce, event_id)] = stored()
    assert (state, bounce) == ("bounced", "soft")
    assert event_id.startswith("msg_local_")
    assert nobody.status_code == 404


def test_the_webhook_is_routed_in_production_and_the_local_bounce_is_not(monkeypatch):
    enter_production(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db.example/olspillet")
    paths = {
        ctx.path
        for ctx in iter_route_contexts(create_app().routes)
        if isinstance(ctx.route, APIRoute)
    }
    assert PATH in paths
    assert "/api/dev/mailbox/bounce" not in paths


async def test_the_bounce_simulation_refuses_in_production(monkeypatch):
    enter_production(monkeypatch)
    with pytest.raises(RuntimeError):
        await service.simulate_bounce(ADDRESS, "hard", NOW)
