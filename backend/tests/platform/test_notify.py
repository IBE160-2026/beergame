"""Story 3.5: `platform/notify.enqueue` writes one notice with ids only, emits `user:<id>` and
defers the claim job in the caller's transaction (AD-9, AD-8, AD-14)."""

import json
import uuid
from datetime import UTC, datetime, timedelta

import psycopg
import pytest

from app.platform import events, notify
from app.platform.db import get_sessionmaker
from app.platform.events.registry import COMMAND_TOPICS
from tests.conftest import libpq_dsn
from tests.messaging.helpers import enqueue, rows, user


def claim_jobs() -> list[tuple]:
    return rows(
        "SELECT queue_name, task_name, args FROM procrastinate_jobs "
        "WHERE task_name = %s ORDER BY id",
        notify.CLAIM_TASK,
    )


async def test_enqueue_writes_one_notice_emits_the_user_and_defers_its_claim(mail_db):
    user_id = await user()
    with psycopg.connect(libpq_dsn(mail_db), autocommit=True) as listen:
        listen.execute(f"LISTEN {events.CHANNEL}")
        assert await enqueue(user_id, "test_immediate", "k1")
        received = [json.loads(n.payload) for n in listen.notifies(timeout=2, stop_after=1)]
    assert received == [{"topic": "user", "id": str(user_id), "version": None}]
    assert {item["topic"] for item in received} == COMMAND_TOPICS["notify.enqueue"]
    [(notice_id, uid, kind, key, ref)] = rows(
        "SELECT id, user_id, kind, dedupe_key, ref FROM notices"
    )
    assert (uid, kind, key, ref) == (user_id, "test_immediate", "k1", None)
    assert claim_jobs() == [("mail", notify.CLAIM_TASK, {"notice_id": str(notice_id)})]


async def test_a_rolled_back_enqueue_leaves_no_notice_no_job_and_no_event(mail_db):
    user_id = await user()
    with psycopg.connect(libpq_dsn(mail_db), autocommit=True) as listen:
        listen.execute(f"LISTEN {events.CHANNEL}")
        async with get_sessionmaker()() as session:
            await notify.enqueue(session, user_id, "test_immediate", "k1")
            await session.rollback()
        assert list(listen.notifies(timeout=0.2)) == []
    assert rows("SELECT id FROM notices") == []
    assert claim_jobs() == []


async def test_the_same_dedupe_key_gives_one_notice(mail_db):
    user_id = await user()
    assert await enqueue(user_id, "test_immediate", "same")
    assert not await enqueue(user_id, "test_digest", "same")
    assert len(rows("SELECT id FROM notices")) == 1
    assert len(claim_jobs()) == 1


async def test_a_notice_by_reference_emits_nothing_and_holds_no_address(mail_db):
    ref = uuid.uuid7()
    with psycopg.connect(libpq_dsn(mail_db), autocommit=True) as listen:
        listen.execute(f"LISTEN {events.CHANNEL}")
        assert await enqueue(None, "test_immediate", "by-ref", ref=ref)
        assert list(listen.notifies(timeout=0.2)) == []
    assert rows("SELECT user_id, ref FROM notices") == [(None, ref)]
    assert len(claim_jobs()) == 1


@pytest.mark.parametrize(
    ("user_id", "kind", "key", "not_before", "message"),
    [
        (None, "k", "d", None, "by user_id or by ref"),
        (uuid.uuid7(), "", "d", None, "kind and a dedupe_key"),
        (uuid.uuid7(), "k", "", None, "kind and a dedupe_key"),
        (uuid.uuid7(), "k", "d", datetime(2027, 1, 1), "time zone"),
    ],
)
async def test_enqueue_refuses_a_notice_without_recipient_kind_key_or_zone(
    user_id, kind, key, not_before, message
):
    with pytest.raises(ValueError, match=message):
        await notify.enqueue(None, user_id, kind, key, None, not_before)  # type: ignore[arg-type]


async def test_claim_due_takes_due_unclaimed_notices_once(mail_db):
    user_id = await user()
    now = datetime(2027, 1, 12, 9, tzinfo=UTC)
    await enqueue(user_id, "test_digest", "due")
    await enqueue(user_id, "test_digest", "later", not_before=now + timedelta(hours=1))
    await enqueue(user_id, "test_immediate", "other-kind")
    async with get_sessionmaker().begin() as session:
        assert [n.kind for n in await notify.due(session, now, ["test_digest"])] == ["test_digest"]
        first = await notify.claim_due(session, now, kinds=["test_digest"], user_id=user_id)
        again = await notify.claim_due(session, now, kinds=["test_digest"], user_id=user_id)
        assert await notify.claim_due(session, now, kinds=[]) == []
        assert await notify.due(session, now, []) == []
    assert [n.kind for n in first] == ["test_digest"]
    assert again == []
    async with get_sessionmaker().begin() as session:
        later = await notify.claim_due(session, now + timedelta(hours=1), kinds=["test_digest"])
        assert [n.id for n in await notify.get(session, [first[0].id])] == [first[0].id]
        assert await notify.get(session, []) == []
    assert len(later) == 1
