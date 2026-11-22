"""Extend one Student's Test deadline (Story 11.13, FR-18, AD-8, AD-9, AD-12, AD-15).

`PUT /api/class-sessions/{id}/students/{user_id}/deadline` («Lagre frist» on the Studentside) runs
`tests.commands.extend_deadline`: the Student's own Test deadline, later than the Class session's,
and their Debrief deadline moved by the same amount, stored through `sessions.service` with an
audit row, and the open attempt's `effective_deadline` moved in the same transaction (its timed
sitting keeps its end). `effective_test_deadline` and `effective_debrief_deadline` then answer the
Student's own date wherever a Student is judged (Hjem, the test, the Replay, the Debrief), the
sweep closes their attempt only at it, and the reminders follow their own date. The api's clock
is fixed and moved by hand; the database clock is never read."""

import uuid
from datetime import timedelta

import pytest

from app.modules.games import service as games_service
from app.modules.ops import sweep
from app.modules.sessions import service as sessions
from app.modules.tests import commands
from app.platform.db import get_sessionmaker
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_classes import make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_staff import ASSISTANT, EMAIL, call, put_staff
from tests.classes.test_student_registration import emitted
from tests.individual_test.test_open import code, locked_session, path, replayed
from tests.individual_test.test_submit import submit_path
from tests.individual_test.test_timed_sitting import attempt, open_test, timed
from tests.messaging.helpers import rows
from tests.sessions.test_dates import DEBRIEF, OUTSIDER, TEST, at
from tests.sessions.test_lock import _empty
from tests.sessions.test_student_choice import email
from tests.sessions.test_student_home import home

__all__ = ["_empty", "clock", "emitted", "klass"]

MINUTE = timedelta(minutes=1)
HOUR = timedelta(hours=1)
DAY = timedelta(days=1)
OWN = TEST + 3 * DAY
OWN_DEBRIEF = DEBRIEF + 3 * DAY


@pytest.fixture(autouse=True)
def _empty_ai(ai_db):
    """No model config: the sessions are Rule-based."""


@pytest.fixture(autouse=True)
def _no_playout(monkeypatch):
    """The sweeps after the Play deadline would play the Class games out (Story 8.14), seconds of
    work per test that no deadline here depends on."""
    monkeypatch.setattr(
        sweep,
        "DUE_ACTIONS",
        tuple(action for action in sweep.DUE_ACTIONS if action.name != "sessions.playout"),
    )


def deadline_path(session_id: str, user_id) -> str:
    return f"/api/class-sessions/{session_id}/students/{user_id}/deadline"


async def extend(session_id: str, user_id, when, who: str = EMAIL["owner"]):
    return await call(
        who, "PUT", deadline_path(session_id, user_id), json={"test_deadline": when.isoformat()}
    )


def stored(session_id: str) -> list[tuple]:
    return rows(
        "SELECT user_id, test_deadline, debrief_deadline FROM student_deadline_extensions "
        "WHERE class_session_id = %s",
        session_id,
    )


def iso(when) -> str:
    return when.isoformat().replace("+00:00", "Z")


# The save.


async def test_an_extension_moves_both_deadlines_and_the_open_attempt_not_its_sitting(
    klass, emitted
):
    session_id, seated = await timed(klass, 60)
    await open_test(session_id)
    ends = attempt(session_id, seated[0])[4]
    emitted.clear()
    response = await extend(session_id, seated[0], OWN)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "class_debrief_deadline": iso(DEBRIEF),
        "class_test_deadline": iso(TEST),
        "debrief_deadline": iso(OWN_DEBRIEF),
        "test_deadline": iso(OWN),
        "extended": True,
        "submitted": False,
    }
    assert stored(session_id) == [(seated[0], OWN, OWN_DEBRIEF)]
    # The open attempt takes the date in the same transaction; its sitting keeps its end.
    _, status, _, _, sitting_ends, deadline = attempt(session_id, seated[0])
    assert (status, sitting_ends, deadline) == ("open", ends, OWN)
    assert set(emitted) == {("user", str(seated[0])), ("session", session_id)}
    assert COMMAND_TOPICS["tests.extend_deadline"] == {"session", "user"}
    # Audited by ids and times; no name, no reason.
    [(target, change)] = rows(
        "SELECT target_ids, change FROM audit_events WHERE action = 'deadline_extension.saved'"
    )
    assert target == {"class_session_id": session_id, "user_id": str(seated[0])}
    assert change == {
        "test_deadline": OWN.isoformat(),
        "debrief_deadline": OWN_DEBRIEF.isoformat(),
        "was": None,
    }
    # The Studentside reads the block too.
    page = await call(
        EMAIL["owner"], "GET", f"/api/class-sessions/{session_id}/students/{seated[0]}"
    )
    assert page.json()["deadlines"]["test_deadline"] == iso(OWN)
    # A second save replaces it and the audit names the one before.
    assert (await extend(session_id, seated[0], OWN + DAY)).status_code == 200
    assert stored(session_id) == [(seated[0], OWN + DAY, OWN_DEBRIEF + DAY)]
    assert attempt(session_id, seated[0])[5] == OWN + DAY
    [(again,)] = rows(
        "SELECT change FROM audit_events WHERE action = 'deadline_extension.saved' "
        "ORDER BY id DESC LIMIT 1"
    )
    assert again["was"] == {
        "test_deadline": OWN.isoformat(),
        "debrief_deadline": OWN_DEBRIEF.isoformat(),
    }


async def test_a_student_who_has_not_opened_the_test_opens_it_after_the_class_deadline(klass):
    session_id, seated = await timed(klass, None)
    assert (await extend(session_id, seated[0], OWN)).status_code == 200
    assert rows("SELECT 1 FROM test_attempts WHERE class_session_id = %s", session_id) == []
    at_after = TEST + HOUR
    with pytest.MonkeyPatch.context() as patch:
        at(patch, at_after)
        statement = (await call(email(0), "GET", path(session_id))).json()
        assert (statement["state"], statement["test_deadline"]) == ("statement", iso(OWN))
        opened = await call(email(0), "POST", path(session_id))
        assert opened.status_code == 201
    assert attempt(session_id, seated[0])[5] == OWN


@pytest.mark.parametrize(
    ("when", "reason"),
    [(TEST, "not_later"), (TEST - DAY, "not_later")],
)
async def test_a_date_not_later_than_the_class_deadline_is_refused(klass, when, reason):
    session_id, seated = await timed(klass, None)
    response = await extend(session_id, seated[0], when)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_extension"
    assert response.json()["error"]["fields"] == {"test_deadline": reason}
    assert stored(session_id) == []


async def test_a_date_that_has_passed_is_refused(klass, monkeypatch):
    session_id, seated = await timed(klass, None)
    at(monkeypatch, TEST + DAY)
    response = await extend(session_id, seated[0], TEST + HOUR)
    assert response.json()["error"]["fields"] == {"test_deadline": "passed"}
    assert stored(session_id) == []


async def test_a_session_with_no_test_deadline_has_nothing_to_extend(klass):
    session_id, seated = await timed(klass, None)
    execute("UPDATE class_sessions SET test_deadline = NULL WHERE id = %s", session_id)
    response = await extend(session_id, seated[0], OWN)
    assert response.json()["error"]["fields"] == {"test_deadline": "no_test_deadline"}
    assert stored(session_id) == []


async def test_a_handed_in_test_cannot_be_extended(klass):
    session_id, seated = await timed(klass, None)
    await open_test(session_id)
    assert (await call(email(0), "POST", submit_path(session_id))).status_code == 200
    assert code(await extend(session_id, seated[0], OWN)) == (409, "attempt_submitted")
    assert stored(session_id) == []
    page = await call(
        EMAIL["owner"], "GET", f"/api/class-sessions/{session_id}/students/{seated[0]}"
    )
    assert page.json()["deadlines"]["submitted"] is True


async def test_only_a_lecturer_of_the_class_may_extend(klass):
    session_id, seated = await timed(klass, None)
    assistant = await make(ASSISTANT, roles=())
    put_staff(klass, assistant, "assistant")
    await make(OUTSIDER, roles=())
    for who in (ASSISTANT, OUTSIDER, email(0)):
        assert (await extend(session_id, seated[0], OWN, who)).status_code == 403
    # A User who is no Student of the Class, and ids that are none, are refused alike.
    assert (await extend(session_id, uuid.uuid4(), OWN)).status_code == 403
    assert (await extend(session_id, "nope", OWN)).status_code == 403
    assert (await extend(str(uuid.uuid4()), seated[0], OWN)).status_code == 403
    assert stored(session_id) == []


async def test_an_archived_class_takes_no_extension(klass):
    session_id, seated = await timed(klass, None)
    execute("UPDATE classes SET archived_at = now() WHERE id = %s", klass)
    assert code(await extend(session_id, seated[0], OWN)) == (409, "class_archived")
    assert stored(session_id) == []


# The deadlines that follow.


async def test_the_class_deadline_closes_the_others_and_the_extended_attempt_at_its_own(klass):
    session_id, seated = await locked_session(klass, 2)
    for user_id in seated:
        await replayed(user_id, session_id)
    for n in (0, 1):
        assert (await call(email(n), "POST", path(session_id))).status_code == 201
    assert (await extend(session_id, seated[0], OWN)).status_code == 200

    done = await sweep.run(TEST + MINUTE)
    assert done["sessions.lock_test"] == 1 and done["tests.close_attempt"] == 1
    assert attempt(session_id, seated[1])[1:4] == ("auto_submitted", TEST, TEST + MINUTE)
    assert attempt(session_id, seated[0])[1:4] == ("open", None, None)
    assert (await sweep.run(OWN - MINUTE))["tests.close_attempt"] == 0
    assert (await sweep.run(OWN + MINUTE))["tests.close_attempt"] == 1
    assert attempt(session_id, seated[0])[1:4] == ("auto_submitted", OWN, OWN + MINUTE)


async def test_a_moved_class_deadline_keeps_the_later_own_one(klass):
    session_id, seated = await locked_session(klass, 2)
    for n, user_id in enumerate(seated):
        await replayed(user_id, session_id)
        assert (await call(email(n), "POST", path(session_id))).status_code == 201
    assert (await extend(session_id, seated[0], OWN)).status_code == 200

    async def move(when) -> None:
        async with get_sessionmaker().begin() as s:
            await commands.move_deadline(s, uuid.UUID(session_id), when)

    await move(TEST + DAY)
    assert [attempt(session_id, u)[5] for u in seated] == [OWN, TEST + DAY]
    await move(OWN + DAY)
    assert [attempt(session_id, u)[5] for u in seated] == [OWN + DAY, OWN + DAY]
    await move(None)
    assert [attempt(session_id, u)[5] for u in seated] == [None, None]


async def test_every_gate_reads_the_students_own_date(klass, monkeypatch):
    session_id, seated = await locked_session(klass, 2)
    for user_id in seated:
        await replayed(user_id, session_id)
    assert (await extend(session_id, seated[0], OWN)).status_code == 200
    at(monkeypatch, TEST + HOUR)

    # Hjem: the own dates, the test step and the Replay still open for the extended Student.
    mine = await home(email(0))
    theirs = await home(email(1))
    assert (mine["test_deadline"], mine["debrief_deadline"]) == (iso(OWN), iso(OWN_DEBRIEF))
    assert mine["next_deadline"] == {"kind": "test", "at": iso(OWN)}
    assert (theirs["test_deadline"], theirs["next_deadline"]) == (iso(TEST), None)
    assert mine["replay"]["can_start"] is True and theirs["replay"]["can_start"] is False

    # The Debrief, its quiz and the follow-up read `student_deadlines`; the Replay's close and
    # Orders `games`' registered reader.
    uid = uuid.UUID(session_id)
    assert await sessions.student_deadlines(seated[0], uid) == (OWN_DEBRIEF, OWN)
    assert await sessions.student_deadlines(seated[1], uid) == (DEBRIEF, TEST)
    async with get_sessionmaker()() as s:
        assert await games_service._test_deadline[0](s, seated[0], uid) == OWN
        assert await games_service._test_deadline[0](s, seated[1], uid) == TEST

    # The test: open for one, closed for the other.
    assert (await call(email(0), "POST", path(session_id))).status_code == 201
    assert code(await call(email(1), "POST", path(session_id))) == (409, "test_deadline_passed")


# The reminders.


def own_notices() -> list[tuple]:
    return rows(
        "SELECT dedupe_key, user_id FROM notices WHERE kind = 'deadline_reminder' ORDER BY id"
    )


def key(session_id: str, kind: str, when, user) -> str:
    return f"deadline_reminder:{session_id}:{kind}:{when.isoformat()}:{user}"


async def test_the_extended_student_is_reminded_of_their_own_dates_only(klass):
    session_id, seated = await locked_session(klass, 2)
    assert (await extend(session_id, seated[0], OWN)).status_code == 200
    uid = uuid.UUID(session_id)
    execute("DELETE FROM notices WHERE kind = 'deadline_reminder'")

    # The Class session's Debrief and Test reminders leave the extended Student out.
    for name, when in (("debrief_deadline", DEBRIEF), ("test_deadline", TEST)):
        assert await sessions.send_deadline_reminder(uid, name, now=when - HOUR) is True
    assert own_notices() == [
        (key(session_id, "debrief", DEBRIEF, seated[1]), seated[1]),
        (key(session_id, "test", TEST, seated[1]), seated[1]),
    ]
    execute("DELETE FROM notices WHERE kind = 'deadline_reminder'")

    # Their own: found 24 hours ahead of each own date, once, as the same digest notice.
    assert (
        await sessions.due_own_deadline_reminders(OWN_DEBRIEF - sessions.REMINDER_AHEAD - MINUTE)
        == []
    )
    assert await sessions.due_own_deadline_reminders(OWN_DEBRIEF - HOUR) == [
        (uid, seated[0], "debrief_deadline")
    ]
    assert (await sweep.run(OWN_DEBRIEF - HOUR))["sessions.send_own_deadline_reminder"] == 1
    assert (await sweep.run(OWN_DEBRIEF - HOUR + MINUTE))[
        "sessions.send_own_deadline_reminder"
    ] == 0
    assert (await sweep.run(OWN - HOUR))["sessions.send_own_deadline_reminder"] == 1
    assert own_notices() == [
        (key(session_id, "debrief", OWN_DEBRIEF, seated[0]), seated[0]),
        (key(session_id, "test", OWN, seated[0]), seated[0]),
    ]
    [(own_ref,)] = rows(
        "SELECT id FROM deadline_reminders WHERE user_id = %s AND deadline = 'test_deadline'",
        seated[0],
    )
    [(class_ref,)] = rows(
        "SELECT id FROM deadline_reminders WHERE user_id IS NULL AND deadline = 'test_deadline'"
    )
    async with get_sessionmaker()() as s:
        context = await sessions.deadline_reminder_mail_context(s, seated[0], own_ref, OWN - HOUR)
        assert context is not None and context["deadline"] == "test"
        # The own reminder is no one else's; the Class one no longer the extended Student's.
        assert (
            await sessions.deadline_reminder_mail_context(s, seated[1], own_ref, OWN - HOUR) is None
        )
        assert (
            await sessions.deadline_reminder_mail_context(s, seated[0], class_ref, TEST - HOUR)
            is None
        )
        assert (
            await sessions.deadline_reminder_mail_context(s, seated[1], class_ref, TEST - HOUR)
            is not None
        )


async def test_reminders_follow_a_class_date_moved_to_or_past_the_own_one(klass):
    session_id, seated = await locked_session(klass, 2)
    assert (await extend(session_id, seated[0], OWN)).status_code == 200
    uid = uuid.UUID(session_id)
    execute("DELETE FROM notices WHERE kind = 'deadline_reminder'")
    await sessions.send_deadline_reminder(uid, "test_deadline", now=OWN - HOUR, user_id=seated[0])

    # The Class's date moved to the Student's: the Class is still reminded (the Student's own row
    # does not count as the Class's), the Student not twice.
    execute("UPDATE class_sessions SET test_deadline = %s WHERE id = %s", OWN, session_id)
    assert (uid, "test_deadline") in await sessions.due_deadline_reminders(OWN - HOUR)
    assert await sessions.send_deadline_reminder(uid, "test_deadline", now=OWN - HOUR) is True
    assert await sessions.due_own_deadline_reminders(OWN - HOUR) == []
    assert own_notices() == [
        (key(session_id, "test", OWN, seated[0]), seated[0]),
        (key(session_id, "test", OWN, seated[1]), seated[1]),
    ]

    # Past it: the Student's date is the Class's again, reminded on their own row at that time.
    later = OWN + DAY
    execute("UPDATE class_sessions SET test_deadline = %s WHERE id = %s", later, session_id)
    assert await sessions.due_own_deadline_reminders(later - HOUR) == [
        (uid, seated[0], "test_deadline")
    ]
    assert (await sweep.run(later - HOUR))["sessions.send_own_deadline_reminder"] == 1
    assert own_notices()[-1] == (key(session_id, "test", later, seated[0]), seated[0])
    page = await call(
        EMAIL["owner"], "GET", f"/api/class-sessions/{session_id}/students/{seated[0]}"
    )
    assert page.json()["deadlines"]["test_deadline"] == iso(later)
    assert page.json()["deadlines"]["extended"] is False


async def test_a_handed_in_student_gets_no_own_test_reminder(klass):
    session_id, seated = await timed(klass, None)
    assert (await extend(session_id, seated[0], OWN)).status_code == 200
    await open_test(session_id)
    assert (await call(email(0), "POST", submit_path(session_id))).status_code == 200
    execute("DELETE FROM notices WHERE kind = 'deadline_reminder'")
    assert (
        await sessions.send_deadline_reminder(
            uuid.UUID(session_id), "test_deadline", now=OWN - HOUR, user_id=seated[0]
        )
        is True
    )
    assert own_notices() == []


async def test_an_own_reminder_item_holds_two_ids_and_an_own_deadline():
    with pytest.raises(TypeError):
        await sessions.send_own_deadline_reminder_due((uuid.uuid7(), "x", "test_deadline"), NOW)
    with pytest.raises(TypeError):
        await sessions.send_own_deadline_reminder_due(
            (uuid.uuid7(), uuid.uuid7(), "play_deadline"), NOW
        )
    with pytest.raises(ValueError):
        await sessions.send_deadline_reminder(
            uuid.uuid7(), "play_deadline", now=NOW, user_id=uuid.uuid7()
        )
