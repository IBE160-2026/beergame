"""Deadline reminders of a Class session (Story 5.14, FR-18, FR-17, FR-72, AD-9, AD-14, AD-19):
24 hours before each Play, Debrief and Test deadline the sweep's `sessions.send_deadline_reminder`
enqueues one digest notice per registered Student, once per deadline time, and the digest mail
names the deadline in Europe/Oslo. The clocks are passed in (api fixed at 2026-11-19 09:00 UTC);
the database clock is never read."""

import json
import uuid
from datetime import timedelta
from typing import get_args

import pytest

from app.modules.messaging import delivery
from app.modules.ops import sweep
from app.modules.sessions import service
from app.modules.sessions.schemas import DeadlineName
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_student_registration import emitted
from tests.messaging.helpers import mails, rows
from tests.sessions.test_dates import (
    DEBRIEF,
    PLAN,
    PLAY,
    START,
    TEST,
    at,
    new_session,
    save,
    student_of,
)
from tests.sessions.test_lab_hours import sweep_at, two_students
from tests.sessions.test_obligatory import save as save_body

__all__ = ["clock", "emitted", "klass"]

MINUTE = timedelta(minutes=1)
HOUR = timedelta(hours=1)
DAY = timedelta(days=1)
AHEAD = service.REMINDER_AHEAD


@pytest.fixture(autouse=True)
def _empty(ai_db, mail_db, games_db):
    """No model config (Rule-based sessions), no games (the sweep also locks the session), and
    no notices, deliveries or mails."""


async def dated(class_id: str, **body) -> str:
    session_id = await new_session(class_id)
    assert (await save(session_id, PLAN)).status_code == 200
    if body:
        assert (await save_body(session_id, **body)).status_code == 200
    # Locked at the Start date first, which allocates and tells the Students: those notices and
    # their jobs are another story's, so they are cleared here.
    await sweep.run(START)
    execute("TRUNCATE notices, mail_deliveries, procrastinate_jobs CASCADE")
    return session_id


def notices() -> list[tuple]:
    """`(kind, dedupe_key, user_id, ref)` of every notice, oldest first."""
    return rows("SELECT kind, dedupe_key, user_id::text, ref::text FROM notices ORDER BY id")


def reminders() -> list[tuple]:
    return rows(
        "SELECT id::text, class_session_id::text, deadline, deadline_at FROM deadline_reminders "
        "ORDER BY created_at, deadline_at"
    )


def key(session_id: str, kind: str, when, user: str) -> str:
    return f"deadline_reminder:{session_id}:{kind}:{when.isoformat()}:{user}"


async def test_each_student_is_reminded_once_24_hours_before_the_play_deadline(klass, emitted):
    students = await two_students(klass)
    session_id = await dated(klass)
    emitted.clear()
    assert (await sweep.run(PLAY - AHEAD - MINUTE))["sessions.send_deadline_reminder"] == 0
    assert notices() == [] and reminders() == []
    done = await sweep.run(PLAY - AHEAD)
    assert done["sessions.send_deadline_reminder"] == 1
    [(reminder_id, reminded_session, deadline, deadline_at)] = reminders()
    assert (reminded_session, deadline, deadline_at) == (session_id, "play_deadline", PLAY)
    assert notices() == [
        ("deadline_reminder", key(session_id, "play", PLAY, s), s, reminder_id) for s in students
    ]
    assert emitted == [("user", s) for s in students]
    assert {topic for topic, _ in emitted} <= COMMAND_TOPICS["sessions.send_deadline_reminder"]
    # Ids only: the claim jobs carry the notice id and nothing else.
    for (args,) in rows("SELECT args::text FROM procrastinate_jobs"):
        assert list(json.loads(args)) == ["notice_id"]
    # Running the sweep again enqueues nothing more.
    assert (await sweep.run(PLAY - AHEAD + MINUTE))["sessions.send_deadline_reminder"] == 0
    assert (
        await service.send_deadline_reminder(
            uuid.UUID(session_id), "play_deadline", now=PLAY - HOUR
        )
        is False
    )
    assert len(notices()) == 2 and len(reminders()) == 1


async def test_each_deadline_gets_its_own_reminder(klass):
    student = str(await student_of(klass))
    session_id = await dated(klass)
    for when in (PLAY, DEBRIEF, TEST):
        await sweep.run(when - AHEAD + HOUR)
    assert [n[1] for n in notices()] == [
        key(session_id, "play", PLAY, student),
        key(session_id, "debrief", DEBRIEF, student),
        key(session_id, "test", TEST, student),
    ]
    # A sweep that finds two deadlines in its window reminds of both, in deadline order.
    execute("DELETE FROM deadline_reminders")
    execute("DELETE FROM notices")
    found = await service.due_deadline_reminders(TEST - AHEAD)
    assert found == [(uuid.UUID(session_id), "test_deadline")]
    execute(
        "UPDATE class_sessions SET debrief_deadline = %s WHERE id = %s", TEST - HOUR, session_id
    )
    found = await service.due_deadline_reminders(TEST - AHEAD)
    assert found == [
        (uuid.UUID(session_id), "debrief_deadline"),
        (uuid.UUID(session_id), "test_deadline"),
    ]


async def test_a_moved_deadline_is_reminded_again_and_only_the_new_time_is_mailed(
    klass, monkeypatch
):
    student = str(await student_of(klass))
    session_id = await dated(klass)
    first = PLAY - AHEAD  # 2026-12-07 10:00 in Oslo
    assert await service.send_deadline_reminder(uuid.UUID(session_id), "play_deadline", now=first)
    # The Lecturer moves the Play deadline two hours earlier, before the digest went.
    moved = PLAY - 2 * HOUR
    at(monkeypatch, first + MINUTE)
    assert (await save(session_id, {**PLAN, "play_deadline": moved})).status_code == 200
    assert await service.due_deadline_reminders(first + 2 * MINUTE) == [
        (uuid.UUID(session_id), "play_deadline")
    ]
    assert await service.send_deadline_reminder(
        uuid.UUID(session_id), "play_deadline", now=first + 2 * MINUTE
    )
    await sweep_at(first + 3 * MINUTE)
    assert [n[1] for n in notices()] == [
        key(session_id, "play", PLAY, student),
        key(session_id, "play", moved, student),
    ]
    [mail] = mails()
    assert "Spillfristen i Klassen class-of-1994 er tirsdag 8. desember kl. 08:00." in mail.text
    assert "kl. 10:00" not in mail.text


async def test_the_digest_names_the_deadline_in_oslo_and_says_when_it_is_obligatory(klass):
    await student_of(klass)
    session_id = await dated(klass, obligatory=True)
    await sweep.run(DEBRIEF - AHEAD)  # 2026-12-10 09:00 UTC, 10:00 in Oslo
    await sweep_at(DEBRIEF - AHEAD + MINUTE)
    [mail] = mails()
    assert mail.to == "student@x.no"
    assert mail.subject == "Nytt fra ØL-spillet"
    assert (
        "Debrieffristen i Klassen class-of-1994 er fredag 11. desember kl. 10:00. "
        "Øvelsen er obligatorisk." in mail.text
    )
    for banned in ("Beer Game", "bullwhip", "uker", "Uke"):
        assert banned not in mail.text and banned not in mail.html
    assert "Debrieffristen" in mail.html
    # Not obligatory: no such line.
    execute("UPDATE class_sessions SET obligatory = false WHERE id = %s", session_id)
    await sweep.run(TEST - AHEAD)
    await sweep_at(TEST - AHEAD + MINUTE)
    second = mails()[1].text
    assert "Testfristen i Klassen class-of-1994 er fredag 18. desember kl. 10:00." in second
    assert "obligatorisk" not in second


async def test_the_digest_waits_out_the_quiet_hours(klass):
    await student_of(klass)
    await dated(klass)
    late = PLAY - AHEAD + 12 * HOUR  # 22:00 in Oslo
    await sweep_at(late)
    assert len(notices()) == 1 and mails() == []
    await sweep_at(late + 9 * HOUR)  # 07:00 in Oslo
    assert len(mails()) == 1


async def test_a_passed_deadline_unset_deadline_or_archived_class_gets_no_reminder(klass):
    await student_of(klass)
    session_id = await dated(klass)
    assert (
        await service.send_deadline_reminder(uuid.UUID(session_id), "play_deadline", now=PLAY)
        is False
    )
    execute("UPDATE class_sessions SET test_deadline = NULL WHERE id = %s", session_id)
    assert await service.due_deadline_reminders(TEST - HOUR) == []
    assert (
        await service.send_deadline_reminder(
            uuid.UUID(session_id), "test_deadline", now=TEST - HOUR
        )
        is False
    )
    execute("UPDATE classes SET archived_at = %s WHERE id = %s", NOW, klass)
    assert await service.due_deadline_reminders(PLAY - HOUR) == []
    assert (
        await service.send_deadline_reminder(
            uuid.UUID(session_id), "play_deadline", now=PLAY - HOUR
        )
        is False
    )
    assert notices() == [] and reminders() == []


async def test_a_student_who_left_before_the_digest_gets_no_mail(klass):
    await student_of(klass)
    await dated(klass)
    late = PLAY - 2 * HOUR  # 2026-12-08 07:00 UTC, 08:00 in Oslo
    await sweep_at(late - 9 * HOUR)  # 23:00 in Oslo: enqueued, held by the quiet hours
    assert len(notices()) == 1 and mails() == []
    execute("UPDATE roster_entries SET removed_at = %s WHERE class_id = %s", NOW, klass)
    await sweep_at(late)
    assert mails() == []


async def test_an_archived_class_before_the_digest_gets_no_mail(klass):
    await student_of(klass)
    await dated(klass)
    await sweep_at(PLAY - 10 * HOUR)  # 00:00 in Oslo: enqueued, held by the quiet hours
    assert len(notices()) == 1
    execute("UPDATE classes SET archived_at = %s WHERE id = %s", NOW, klass)
    await sweep_at(PLAY - 2 * HOUR)  # 08:00 in Oslo
    assert mails() == []


async def test_a_deadline_that_passed_before_the_digest_is_not_mailed(klass):
    await student_of(klass)
    await dated(klass)
    await sweep_at(PLAY - 10 * HOUR)  # 22:00 in Oslo: held
    await sweep_at(PLAY + MINUTE)  # 11:01 in Oslo the next day: the deadline has passed
    assert len(notices()) == 1 and mails() == []


async def test_reminder_recipients_are_every_registered_student_sorted(klass):
    students = sorted(await two_students(klass))
    session_id = await dated(klass)
    found = await service.reminder_recipients(uuid.UUID(session_id), "test_deadline")
    assert [str(s) for s in found] == students
    assert await service.reminder_recipients(uuid.uuid7(), "play_deadline") == []


def test_the_deadline_names_agree():
    assert service.DEADLINE_NAMES == get_args(DeadlineName) == tuple(service.DATE_NAMES[1:])


def test_the_delivery_table_names_the_reminder_as_digest():
    assert delivery.DEADLINE_REMINDER_KIND == service.DEADLINE_REMINDER_NOTICE
    assert delivery.KINDS[service.DEADLINE_REMINDER_NOTICE].mode == delivery.DIGEST
    assert [a.name for a in sweep.DUE_ACTIONS][-1] == "sessions.send_deadline_reminder"


async def test_a_reminder_item_holds_a_session_id_and_a_deadline_name():
    with pytest.raises(TypeError):
        await service.send_deadline_reminder_due(("x", "play_deadline"), NOW)
    with pytest.raises(TypeError):
        await service.send_deadline_reminder_due((uuid.uuid7(), "start_at"), NOW)
