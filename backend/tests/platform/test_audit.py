"""`platform/audit` (Story 3.7, AD-15, AD-14): one row per action, ids and codes only, and no
update or delete."""

import uuid
from datetime import UTC, datetime

import psycopg
import pytest

from app.platform import audit
from app.platform.db import get_sessionmaker
from tests.conftest import TEST_DATABASE_URL, libpq_dsn
from tests.messaging.helpers import rows

AT = datetime(2026, 11, 18, 12, 1, tzinfo=UTC)


async def test_a_row_holds_the_actor_the_action_the_ids_and_the_change(identity_db):
    actor, target = uuid.uuid7(), uuid.uuid7()
    async with get_sessionmaker().begin() as s:
        await audit.record(
            s, actor, "invitation.sent", {"invitation_id": target}, {"role": "admin"}, AT
        )
        await audit.record(s, None, "invitation.sent", {"invitation_id": target}, {}, AT)
    async with get_sessionmaker().begin() as s:
        found = await audit.events_for_target(s, "invitation_id", target)
    assert [(e.actor_user_id, e.action, e.target_ids, e.change) for e in found] == [
        (actor, "invitation.sent", {"invitation_id": str(target)}, {"role": "admin"}),
        (None, "invitation.sent", {"invitation_id": str(target)}, {}),
    ]
    assert {e.occurred_at for e in found} == {AT}


@pytest.mark.parametrize(
    ("target", "change"),
    [({"invitation_id": "kari@example.no"}, {}), ({}, {"emails": ["kari@example.no"]})],
)
async def test_an_email_address_is_refused(identity_db, target, change):
    async with get_sessionmaker().begin() as s:
        with pytest.raises(ValueError, match="e-mail"):
            await audit.record(s, None, "invitation.sent", target, change, AT)
    assert rows("SELECT count(*) FROM audit_events") == [(0,)]


@pytest.mark.parametrize(
    "sql", ["UPDATE audit_events SET action = 'x'", "DELETE FROM audit_events"]
)
async def test_rows_are_never_changed_or_removed(identity_db, sql):
    async with get_sessionmaker().begin() as s:
        await audit.record(s, None, "invitation.sent", {}, {}, AT)
    with psycopg.connect(libpq_dsn(TEST_DATABASE_URL)) as conn:
        with pytest.raises(psycopg.errors.RestrictViolation):
            conn.execute(sql)
    assert rows("SELECT action FROM audit_events") == [("invitation.sent",)]
