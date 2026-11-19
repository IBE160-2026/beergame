"""What became of a Class's Invitations (Story 4.6, FR-8, NFR-10, AD-10, AD-14): the four counts
the api computes and the bounced Roster addresses with their bounce class. Bounces arrive as
signed provider events through the local stand-in (`POST /api/dev/mailbox/bounce`). The api's
clock is fixed; the database clock is never read, and nothing is ordered by a timestamp."""

import uuid
from datetime import timedelta

import pytest
import structlog.testing

from app.platform import auth
from tests.classes.test_classes import OTHER, as_user
from tests.classes.test_roster_send import send, staged_id
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.identity.helpers import CSRF, client
from tests.messaging.helpers import drain, rows

__all__ = ["clock", "klass"]

ADDRESSES = ["a@x.no", "b@x.no", "c@x.no", "d@x.no"]


@pytest.fixture(autouse=True)
def _empty_mail(mail_db):
    """The mail tables and the mock outbox empty, before `klass` makes its Users."""


def path(class_id: str) -> str:
    return f"/api/classes/{class_id}/invitations"


async def summary(class_id: str):
    async with client() as c:
        await as_user(c)
        return await c.get(path(class_id))


async def bounce(address: str, bounce_class: str) -> None:
    async with client() as c:
        response = await c.post(
            "/api/dev/mailbox/bounce",
            json={"to": address, "bounce_class": bounce_class},
            headers=CSRF,
        )
    assert response.status_code == 200


def execute(sql: str, *params) -> None:
    import psycopg

    from tests.conftest import TEST_DATABASE_URL, libpq_dsn

    with psycopg.connect(libpq_dsn(TEST_DATABASE_URL), autocommit=True) as conn:
        conn.execute(sql, params)


def accept(address: str) -> None:
    """Story 4.5's acceptance, as its rows end: Invitation accepted, entry registered."""
    execute("UPDATE invitations SET accepted_at = %s WHERE email = %s", NOW, address)
    execute("UPDATE roster_entries SET registration = 'registered' WHERE email = %s", address)


async def sent_class(klass: str, addresses=ADDRESSES) -> None:
    async with client() as c:
        await as_user(c)
        response = await send(c, klass, await staged_id(c, klass, " ".join(addresses)))
    assert response.status_code == 201
    await drain(NOW)


async def test_before_any_sending_every_count_is_zero(klass):
    response = await summary(klass)
    assert response.status_code == 200
    assert response.json() == {"sent": 0, "bounced": 0, "accepted": 0, "expired": 0, "bounces": []}


async def test_invitations_not_yet_handed_to_the_provider_are_not_counted_as_sent(klass):
    async with client() as c:
        await as_user(c)
        await send(c, klass, await staged_id(c, klass, "a@x.no b@x.no"))
    assert (await summary(klass)).json()["sent"] == 0
    await drain(NOW)
    assert (await summary(klass)).json()["sent"] == 2


async def test_each_count_and_the_bounced_addresses_with_their_class(klass):
    await sent_class(klass)
    await bounce("a@x.no", "hard")
    await bounce("B@x.no", "soft")
    accept("c@x.no")
    # d's last valid day is past: set from the api's clock, never the database's.
    execute("UPDATE invitations SET expires_at = %s WHERE email = %s", NOW, "d@x.no")
    response = await summary(klass)
    assert response.status_code == 200
    assert response.json() == {
        "sent": 4,
        "bounced": 2,
        "accepted": 1,
        "expired": 1,
        "bounces": [
            {"email": "a@x.no", "registration": "bounced", "bounce_class": "hard"},
            {"email": "b@x.no", "registration": "bounced", "bounce_class": "soft"},
        ],
    }


async def test_a_bounce_posted_to_the_webhook_shows_in_the_counts(klass):
    """The provider's own path, end to end: a signed `email.bounced` over HTTP for an Invitation
    mail, then the Lecturer's counts and list."""
    from tests.messaging.test_webhook import event, signed

    await sent_class(klass, ["a@x.no"])
    [(provider_id,)] = rows("SELECT provider_message_id FROM mail_deliveries")
    body = event("email.bounced", provider_id, "Permanent")
    async with client() as c:
        posted = await c.post("/api/webhooks/resend", content=body, headers=signed(body))
    assert posted.json() == {"outcome": "stored"}
    found = (await summary(klass)).json()
    assert (found["sent"], found["bounced"]) == (1, 1)
    assert found["bounces"] == [
        {"email": "a@x.no", "registration": "bounced", "bounce_class": "hard"}
    ]


def provider_id_of(invitation_id) -> str:
    [(provider_id,)] = rows(
        "SELECT d.provider_message_id FROM mail_deliveries d JOIN notices n "
        "ON n.id = ANY(d.notice_ids) WHERE n.ref = %s",
        invitation_id,
    )
    return provider_id


async def remind_and_drain(klass: str) -> None:
    async with client() as c:
        await as_user(c)
        response = await c.post(
            f"/api/classes/{klass}/reminders", json={"valid_days": 14}, headers=CSRF
        )
    assert response.status_code == 201
    await drain(NOW)


@pytest.mark.parametrize("second", ["delivered", "bounced"])
async def test_a_re_sent_invitation_counts_each_mail_and_lists_by_the_newest(klass, second):
    """Story 4.6's deferred case, reachable with Story 4.7's reminders: an address whose first
    Invitation bounced (soft) and was sent again. Both Invitations count as sent; the bounced list
    follows the newest Invitation only."""
    from tests.messaging.test_webhook import event, signed

    await sent_class(klass, ["a@x.no"])
    await bounce("a@x.no", "soft")
    await remind_and_drain(klass)
    newest = rows("SELECT id FROM invitations WHERE voided_at IS NULL AND accepted_at IS NULL")[0][
        0
    ]
    if second == "delivered":
        body = event("email.delivered", provider_id_of(newest))
        async with client() as c:
            posted = await c.post("/api/webhooks/resend", content=body, headers=signed(body))
        assert posted.json() == {"outcome": "stored"}
    else:
        await bounce("a@x.no", "hard")
    found = (await summary(klass)).json()
    if second == "delivered":
        assert (found["sent"], found["bounced"], found["bounces"]) == (2, 1, [])
    else:
        assert (found["sent"], found["bounced"]) == (2, 2)
        assert found["bounces"] == [
            {"email": "a@x.no", "registration": "bounced", "bounce_class": "hard"}
        ]


async def test_expired_is_read_at_request_time_and_leaves_accepted_ones_out(klass, monkeypatch):
    await sent_class(klass)
    accept("c@x.no")
    assert (await summary(klass)).json()["expired"] == 0
    monkeypatch.setattr(auth, "utcnow", lambda: NOW + timedelta(days=15))
    assert (await summary(klass)).json()["expired"] == 3


async def test_a_replaced_invitation_never_counts_as_expired(klass, monkeypatch):
    await sent_class(klass, ["a@x.no"])
    async with client() as c:
        await as_user(c)
        reminded = await c.post(f"/api/classes/{klass}/reminders", json={}, headers=CSRF)
    assert reminded.json()["sent"] == 1
    monkeypatch.setattr(auth, "utcnow", lambda: NOW + timedelta(days=10))
    assert (await summary(klass)).json()["expired"] == 0


async def test_a_stopped_link_of_a_waiting_address_counts_as_expired_as_its_row_reads(klass):
    """Issue #93: an archive voids the open links; each row then reads «Uregistrert, Invitasjonen
    er utløpt», and «Utløpt» counts them. A voided link of an address registered since does not."""
    await sent_class(klass, ["a@x.no", "b@x.no"])
    accept("b@x.no")
    execute("UPDATE invitations SET voided_at = %s WHERE accepted_at IS NULL", NOW)
    async with client() as c:
        await as_user(c)
        statuses = (await c.get(f"/api/classes/{klass}/registrations")).json()["items"]
    assert {i["email"]: i["status"] for i in statuses} == {
        "a@x.no": "unregistered",
        "b@x.no": "registered",
    }
    assert (await summary(klass)).json()["expired"] == 1


async def test_a_registered_or_removed_address_is_counted_but_not_listed_as_bounced(klass):
    await sent_class(klass, ["a@x.no", "b@x.no"])
    await bounce("a@x.no", "hard")
    await bounce("b@x.no", "hard")
    accept("a@x.no")
    execute("UPDATE roster_entries SET removed_at = %s WHERE email = %s", NOW, "b@x.no")
    body = (await summary(klass)).json()
    assert (body["sent"], body["bounced"], body["bounces"]) == (2, 2, [])


async def test_a_manually_registered_address_is_not_listed_as_bounced(klass):
    await sent_class(klass, ["a@x.no"])
    await bounce("a@x.no", "hard")
    execute("UPDATE roster_entries SET registration = 'registered_manually'")
    assert (await summary(klass)).json()["bounces"] == []


async def test_counts_are_per_class(klass):
    await sent_class(klass, ["a@x.no"])
    await bounce("a@x.no", "soft")
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
        empty = await c.get(path(other.json()["id"]))
    assert empty.json()["sent"] == 0 and empty.json()["bounces"] == []


@pytest.mark.parametrize("target", ["other", "unknown", "malformed"])
async def test_a_class_the_user_may_not_manage_is_forbidden_alike(klass, target):
    await sent_class(klass, ["a@x.no"])
    class_id = {"other": klass, "unknown": str(uuid.uuid4()), "malformed": "ikke-en-id"}[target]
    async with client() as c:
        await as_user(c, OTHER if target == "other" else "bard@example.com")
        response = await c.get(path(class_id))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


async def test_anonymous_is_refused(klass):
    async with client() as c:
        response = await c.get(path(klass))
    assert response.status_code == 401


async def test_reading_the_counts_logs_no_address(klass):
    await sent_class(klass, ["a@x.no"])
    with structlog.testing.capture_logs() as logs:
        await bounce("a@x.no", "hard")
        await summary(klass)
    assert "a@x.no" not in repr(logs)
