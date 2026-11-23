"""The Class session's deletion date and its one reminder (Story 13.9, FR-77, FR-57, AD-9).

`class_sessions.deletion_date` is the latest effective Test deadline (the Class session's, or the
latest Student extension of Story 11.13) on the Europe/Oslo calendar plus `RETENTION_MONTHS`,
stored by `sessions.service` in the transaction of every Test deadline save and every extension.
Hjem states it; `DELETION_REMINDER_DAYS` before it the sweep's `sessions.send_deletion_reminder`
enqueues one digest notice per Student. The api's clock is fixed (2026-11-19 09:00 UTC) and moved
by hand; the database clock is never read."""

import json
import uuid
from datetime import UTC, date, datetime, timedelta

import pytest

from app.modules.messaging import delivery
from app.modules.ops import sweep
from app.modules.sessions import service
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_student_registration import emitted
from tests.individual_test.test_extension import extend
from tests.messaging.helpers import drain, mails, rows
from tests.sessions.test_dates import PLAN, STUDENT, TEST, at, new_session, save, student_of
from tests.sessions.test_lab_hours import two_students
from tests.sessions.test_student_home import home

__all__ = ["clock", "emitted", "klass"]

DAY = timedelta(days=1)
DELETION = date(2027, 6, 18)
"""`TEST` (2026-12-18 09:00 UTC, 10:00 in Oslo) plus six months."""
WINDOW_OPENS = datetime(2027, 6, 4, 8, tzinfo=UTC)
"""10:00 in Oslo on the day 14 days before `DELETION`, inside the digest hours."""


@pytest.fixture(autouse=True)
def _empty(ai_db, mail_db, games_db):
    """No model config, no games, no notices, deliveries or mails."""


@pytest.fixture
def reminder_only(monkeypatch):
    """The sweep runs only the digest claim and this story's action: half a year on, every other
    due action (the lock, the playout, …) is another story's work."""
    monkeypatch.setattr(
        sweep,
        "DUE_ACTIONS",
        tuple(
            a
            for a in sweep.DUE_ACTIONS
            if a.name in {"messaging.mail", "sessions.send_deletion_reminder"}
        ),
    )


def stored(session_id: str) -> date | None:
    [(found,)] = rows("SELECT deletion_date FROM class_sessions WHERE id = %s", session_id)
    return found


def notices() -> list[tuple]:
    return rows("SELECT kind, dedupe_key, user_id::text, ref::text FROM notices ORDER BY id")


async def planned(klass: str) -> str:
    session_id = await new_session(klass)
    assert stored(session_id) is None
    assert (await save(session_id, PLAN)).status_code == 200
    return session_id


async def test_saving_the_test_deadline_stores_the_date_hjem_states(klass):
    await student_of(klass)
    session_id = await planned(klass)
    assert stored(session_id) == DELETION
    assert (await home(STUDENT))["deletion_date"] == "2027-06-18"


async def test_a_session_without_a_test_deadline_has_no_date(klass):
    await student_of(klass)
    session_id = await new_session(klass)
    assert (await save(session_id, {**PLAN, "test_deadline": None})).status_code == 200
    assert stored(session_id) is None
    assert (await home(STUDENT))["deletion_date"] is None


async def test_moving_the_test_deadline_moves_the_date_both_ways(klass, monkeypatch):
    session_id = await planned(klass)
    # Later, past a month's end: 31 January in Oslo plus six months is the last of July.
    later = datetime(2027, 1, 31, 12, tzinfo=UTC)
    assert (await save(session_id, {**PLAN, "test_deadline": later})).status_code == 200
    assert stored(session_id) == date(2027, 7, 31)
    # Earlier, across midnight in Oslo: 23:30 UTC on 20 December is 21 December there.
    earlier = datetime(2026, 12, 20, 23, 30, tzinfo=UTC)
    assert (await save(session_id, {**PLAN, "test_deadline": earlier})).status_code == 200
    assert stored(session_id) == date(2027, 6, 21)
    # Cleared, then set again.
    assert (await save(session_id, {**PLAN, "test_deadline": None})).status_code == 200
    assert stored(session_id) is None
    assert (await save(session_id, PLAN)).status_code == 200
    assert stored(session_id) == DELETION


async def test_an_extension_moves_the_date_and_a_class_deadline_moved_earlier_keeps_it(klass):
    first, _ = await two_students(klass)
    session_id = await planned(klass)
    own = TEST + 20 * DAY  # 2027-01-07 in Oslo
    assert (await extend(session_id, first, own)).status_code == 200
    assert stored(session_id) == date(2027, 7, 7)
    # Both Students' Hjem read the Class session's date: the latest one keeps everyone's data.
    assert (await home(STUDENT))["deletion_date"] == "2027-07-07"
    assert (await home("student2@x.no"))["deletion_date"] == "2027-07-07"
    # The Lecturer moves the Class session's Test deadline earlier: the extension still holds,
    # so no Student's data can fall due before their own period has run.
    assert (await save(session_id, {**PLAN, "test_deadline": TEST - DAY})).status_code == 200
    assert stored(session_id) == date(2027, 7, 7)
    # Moved past the extension, the Class session's own date decides.
    assert (await save(session_id, {**PLAN, "test_deadline": own + DAY})).status_code == 200
    assert stored(session_id) == date(2027, 7, 8)


async def test_each_student_is_reminded_once_14_days_before(
    klass, reminder_only, emitted, monkeypatch
):
    students = await two_students(klass)
    session_id = await planned(klass)
    emitted.clear()
    assert "sessions.send_deletion_reminder" in {a.name for a in sweep.DUE_ACTIONS}
    # 22:00 in Oslo the evening before the window: not yet.
    before = datetime(2027, 6, 3, 20, tzinfo=UTC)
    assert (await sweep.run(before))["sessions.send_deletion_reminder"] == 0
    assert notices() == []
    assert await service.due_deletion_reminders(WINDOW_OPENS) == [uuid.UUID(session_id)]
    done = await sweep.run(WINDOW_OPENS)
    assert done["sessions.send_deletion_reminder"] == 1
    assert notices() == [
        ("deletion_reminder", f"deletion_reminder:{session_id}:2027-06-18:{s}", s, session_id)
        for s in students
    ]
    assert {topic for topic, _ in emitted} <= COMMAND_TOPICS["sessions.send_deletion_reminder"]
    for (args,) in rows("SELECT args::text FROM procrastinate_jobs"):
        assert list(json.loads(args)) == ["notice_id"]
    # Again, by the sweep or by hand: nothing more.
    assert (await sweep.run(WINDOW_OPENS + DAY))["sessions.send_deletion_reminder"] == 0
    assert await service.send_deletion_reminder(uuid.UUID(session_id), now=WINDOW_OPENS) is False
    assert len(notices()) == 2
    # The digest tells each Student the Class and the date.
    at(monkeypatch, WINDOW_OPENS)
    await sweep.run(WINDOW_OPENS + timedelta(minutes=1))
    await drain(WINDOW_OPENS + timedelta(minutes=1))
    assert sorted(m.to for m in mails()) == ["student2@x.no", "student@x.no"]
    for mail in mails():
        assert (
            "Dataene dine fra Klassen class-of-1994 slettes 18. juni 2027. "
            "Last ned Studentrapporten fra Hjem før det." in mail.text
        )
    assert delivery.KINDS["deletion_reminder"].mode == delivery.DIGEST


async def test_no_reminder_on_or_after_the_date_or_without_one(klass):
    await student_of(klass)
    session_id = await planned(klass)
    on_the_day = datetime(2027, 6, 18, 8, tzinfo=UTC)
    assert await service.due_deletion_reminders(on_the_day) == []
    assert await service.send_deletion_reminder(uuid.UUID(session_id), now=on_the_day) is False
    bare = await new_session(klass)
    assert uuid.UUID(bare) not in await service.due_deletion_reminders(WINDOW_OPENS)
    assert await service.send_deletion_reminder(uuid.UUID(bare), now=WINDOW_OPENS) is False
    assert notices() == []


async def test_a_student_removed_before_the_digest_gets_no_mail(klass, reminder_only):
    await student_of(klass)
    session_id = await planned(klass)
    assert await service.send_deletion_reminder(uuid.UUID(session_id), now=WINDOW_OPENS)
    execute("UPDATE roster_entries SET removed_at = %s WHERE class_id = %s", NOW, klass)
    await sweep.run(WINDOW_OPENS + timedelta(minutes=1))
    await drain(WINDOW_OPENS + timedelta(minutes=1))
    assert mails() == []


async def test_a_date_moved_after_the_reminder_is_told_again_in_its_window(klass):
    student = str(await student_of(klass))
    session_id = await planned(klass)
    assert await service.send_deletion_reminder(uuid.UUID(session_id), now=WINDOW_OPENS)
    # A later Test deadline (the clock is the api's, before the deadline) moves the date a month.
    assert (await save(session_id, {**PLAN, "test_deadline": TEST + 31 * DAY})).status_code == 200
    assert stored(session_id) == date(2027, 7, 18)
    assert await service.due_deletion_reminders(WINDOW_OPENS + DAY) == []
    later = datetime(2027, 7, 4, 8, tzinfo=UTC)
    assert await service.due_deletion_reminders(later) == [uuid.UUID(session_id)]
    assert await service.send_deletion_reminder(uuid.UUID(session_id), now=later)
    assert [n[1] for n in notices()] == [
        f"deletion_reminder:{session_id}:2027-06-18:{student}",
        f"deletion_reminder:{session_id}:2027-07-18:{student}",
    ]
    # Saving the same date again keeps the mark.
    assert (await save(session_id, {**PLAN, "test_deadline": TEST + 31 * DAY})).status_code == 200
    assert await service.due_deletion_reminders(later) == []
