"""Story 3.5: immediate notices leave at once through the claim job; every mail gets one
`mail_deliveries` row and a `mail` job that runs twice sends one mail (AD-9, AD-14). Jobs are
driven with `run_until_idle`, never with a clock."""

import io
import logging
import uuid
from datetime import UTC, datetime, timedelta
from types import MappingProxyType

import pytest

from app.modules.messaging import delivery, service
from app.platform import email, jobs, notify
from app.platform.config import Settings
from app.platform.email import senders
from app.platform.logging import configure_logging
from tests.conftest import enter_production
from tests.messaging.helpers import deliveries, drain, enqueue, mails, oslo, rows, user


async def test_an_immediate_notice_leaves_at_once_even_at_night(mail_db):
    user_id = await user()
    await enqueue(user_id, "test_immediate")
    await drain()
    [mail] = mails()
    assert mail.to == "kari@example.no" and mail.subject == "Testmelding fra ØL-spillet"
    assert deliveries() == [("immediate", 1, True, None, 1)]
    [(provider_id, uid)] = rows("SELECT provider_message_id, user_id FROM mail_deliveries")
    assert provider_id.startswith("mock-") and uid == user_id
    # The claim job does not look at the hour: 23:00 in Oslo claims at once as well.
    await enqueue(user_id, "test_immediate", "night")
    [(notice_id,)] = rows("SELECT id FROM notices WHERE dedupe_key = 'night'")
    assert await service.claim_notice(notice_id, oslo(12, 23)) is not None


async def test_the_claim_job_leaves_a_digest_and_a_later_notice_to_the_sweep(mail_db):
    user_id = await user()
    await enqueue(user_id, "test_digest")
    later = datetime.now(UTC) + timedelta(hours=1)
    await enqueue(user_id, "test_immediate", "later", not_before=later)
    await drain()
    assert mails() == [] and deliveries() == []
    assert rows("SELECT count(*) FROM notices WHERE claimed_at IS NULL") == [(2,)]
    # The sweep after `not_before` sends the immediate one.
    [item] = [i for i in await service.due_items(later) if i.notice_id]
    await service.claim(item, later)
    await drain()
    assert [m.subject for m in mails()] == ["Testmelding fra ØL-spillet"]


async def test_a_mail_job_that_runs_twice_sends_one_mail(mail_db):
    user_id = await user()
    await enqueue(user_id, "test_immediate")
    await drain()
    [(delivery_id,)] = rows("SELECT id FROM mail_deliveries")
    assert await service.send(delivery_id) == "none"
    async with service.get_sessionmaker().begin() as session:
        await service._defer_send(session, delivery_id)
    await drain()
    assert len(mails()) == 1
    assert await service.send(uuid.uuid7()) == "none"  # no such delivery


async def test_a_claimed_notice_is_never_claimed_again(mail_db):
    user_id = await user()
    await enqueue(user_id, "test_immediate")
    [(notice_id,)] = rows("SELECT id FROM notices")
    now = datetime.now(UTC)
    assert await service.claim_notice(notice_id, now) is not None
    assert await service.claim_notice(notice_id, now) is None
    await drain()  # the enqueued claim job finds it claimed
    assert len(mails()) == 1 and len(deliveries()) == 1


@pytest.fixture
def by_reference(monkeypatch):
    """A kind addressed by reference, as Story 3.7's Invitation will be."""
    found: dict[uuid.UUID, email.Recipient] = {}

    async def resolve(session, ref, now):
        return found.get(ref)

    kinds = dict(delivery.KINDS) | {
        "test_by_ref": delivery.Delivery(delivery.IMMEDIATE, "test_immediate", resolve)
    }
    monkeypatch.setattr(delivery, "KINDS", MappingProxyType(kinds))
    return found


async def test_a_notice_by_reference_is_addressed_through_the_owning_resolver(
    mail_db, by_reference
):
    ref, gone = uuid.uuid7(), uuid.uuid7()
    by_reference[ref] = email.Recipient("ny@example.no", None)
    await enqueue(None, "test_by_ref", ref=ref)
    await enqueue(None, "test_by_ref", ref=gone)
    await drain()
    assert [m.to for m in mails()] == ["ny@example.no"]
    assert sorted(d[3] or "sent" for d in deliveries()) == ["no_recipient", "sent"]
    assert rows("SELECT count(*) FROM mail_deliveries WHERE user_id IS NULL") == [(2,)]


async def test_a_failing_resolver_counts_as_a_failed_try(mail_db, monkeypatch):
    async def broken(session, ref, now):
        raise RuntimeError("ny@example.no is unknown")

    kinds = dict(delivery.KINDS) | {
        "test_by_ref": delivery.Delivery(delivery.IMMEDIATE, "test_immediate", broken)
    }
    monkeypatch.setattr(delivery, "KINDS", MappingProxyType(kinds))
    await enqueue(None, "test_by_ref", ref=uuid.uuid7())
    await drain()
    assert mails() == [] and deliveries() == [("immediate", 1, False, None, 1)]


def test_a_digest_kind_cannot_be_addressed_by_reference():
    async def resolve(session, ref, now):
        return None

    with pytest.raises(ValueError, match="digest"):
        delivery.Delivery(delivery.DIGEST, "x", resolve)
    with pytest.raises(ValueError, match="mode"):
        delivery.Delivery("weekly", "x")  # type: ignore[arg-type]


def test_a_kind_by_reference_takes_no_context_resolver():
    async def resolve(session, ref, now):
        return None

    async def context(session, user_id, ref, now):
        return {}

    with pytest.raises(ValueError, match="by reference"):
        delivery.Delivery(delivery.IMMEDIATE, "x", resolve, context=context)


async def test_a_deactivated_user_gets_no_mail(mail_db):
    user_id = await user(is_active=False)
    await enqueue(user_id, "test_immediate")
    await drain()
    assert mails() == []
    assert deliveries() == [("immediate", 1, False, "no_recipient", 0)]


async def test_a_failed_send_is_tried_again_by_the_sweep_then_given_up(mail_db, monkeypatch):
    user_id = await user()

    class Down:
        async def send(self, mail, *, idempotency_key):
            raise email.SendRefused("provider_status_503")

    monkeypatch.setattr(email, "get_sender", lambda: Down())
    await enqueue(user_id, "test_immediate")
    await drain()
    assert deliveries() == [("immediate", 1, False, None, 1)]
    [(claimed_at,)] = rows("SELECT claimed_at FROM mail_deliveries")
    # Not yet: the first retry waits 2 minutes doubled once.
    assert [i for i in await service.due_items(claimed_at + timedelta(minutes=3))] == []
    for attempt in range(1, service.MAX_ATTEMPTS):
        now = claimed_at + service.RETRY_AFTER * 2**attempt
        [item] = await service.due_items(now)
        assert item.delivery_id is not None
        await service.claim(item, now)  # defers the `mail` job again
        assert await service.send(item.delivery_id) == "failed"
    assert deliveries() == [("immediate", 1, False, "send_failed", service.MAX_ATTEMPTS)]
    assert await service.due_items(claimed_at + timedelta(days=1)) == []
    # With the provider back, nothing is sent for a given-up delivery.
    monkeypatch.setattr(email, "get_sender", lambda: senders.MOCK)
    [(delivery_id,)] = rows("SELECT id FROM mail_deliveries")
    assert await service.send(delivery_id) == "none" and mails() == []


async def test_an_unknown_kind_is_skipped_and_never_claimed(mail_db):
    user_id = await user()
    await enqueue(user_id, "no_such_kind")
    await drain()
    now = datetime.now(UTC)
    assert await service.due_items(now) == []
    # A delivery whose notices lost their kind (a kind removed from the table) is skipped.
    await enqueue(user_id, "test_immediate", "k")
    [(notice_id,)] = rows("SELECT id FROM notices WHERE dedupe_key = 'k'")
    delivery_id = await service.claim_notice(notice_id, now)
    rows("UPDATE notices SET kind = 'gone' WHERE id = %s RETURNING id", notice_id)
    assert await service.send(delivery_id) == "skipped"
    assert deliveries() == [("immediate", 1, False, "unknown_kind", 0)]


def test_production_has_no_dummy_kinds():
    production = Settings(app_env="production", database_url="postgresql://x/y")
    assert "test_immediate" not in delivery.table(production)
    assert "test_digest" not in delivery.table(production)
    assert set(delivery.TEST_KINDS) <= set(delivery.table(Settings(app_env="local")))


async def test_in_production_without_a_key_the_mail_fails_and_stays_unsent(mail_db, monkeypatch):
    user_id = await user()
    await enqueue(user_id, "test_immediate")
    [(notice_id,)] = rows("SELECT id FROM notices")
    delivery_id = await service.claim_notice(notice_id, datetime.now(UTC))
    enter_production(monkeypatch)
    monkeypatch.setattr(delivery, "table", lambda settings=None: delivery.TEST_KINDS)
    monkeypatch.setattr(
        email, "get_sender", lambda: senders.get_sender(Settings(app_env="production"))
    )
    assert await service.send(delivery_id) == "failed"
    assert mails() == []
    assert deliveries() == [("immediate", 1, False, None, 1)]


async def test_no_address_or_name_reaches_a_log_line_or_a_job_argument(mail_db):
    stream = io.StringIO()
    configure_logging("debug", stream=stream)
    try:
        user_id = await user()
        await enqueue(user_id, "test_immediate")
        await enqueue(user_id, "test_digest")
        await drain()
        await service.claim(service.DueItem(digest_user_id=user_id), oslo(12, 9))
        await drain(oslo(12, 9))
    finally:
        logging.getLogger().handlers[:] = []
    assert len(mails()) == 2
    out = stream.getvalue()
    assert "[email:mock]" in out
    for secret in ("kari@example.no", "Kari", "Nordmann", "127.0.0.1:8080"):
        assert secret not in out
    for (args,) in rows("SELECT args::text FROM procrastinate_jobs"):
        assert "@" not in args and "Kari" not in args
    assert {task for (task,) in rows("SELECT DISTINCT task_name FROM procrastinate_jobs")} <= {
        notify.CLAIM_TASK,
        service.SEND_MAIL,
    }
    assert jobs.MAIL == "mail"
