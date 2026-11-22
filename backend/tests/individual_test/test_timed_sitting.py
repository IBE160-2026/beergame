"""One timed sitting for the Individual test (Story 11.12, FR-51, FR-17, FR-66, AD-9).

«Lagre Klasseøkt» stores a Class session's time limit through `tests.service` (in range, before
the Start date); `open_attempt` sets `sitting_ends_at` from it and the Student's time factor and
never changes `effective_deadline`; a save or hand-in after the sitting is refused with
`sitting_ended`; the sweep's `tests.end_sitting` hands the attempt in and starts nothing else, and
`close_attempt` still runs at the Test deadline. The api's clock is fixed and moved by hand; the
database clock is never read."""

import uuid
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.modules.ops import sweep
from app.modules.sessions import service as sessions
from app.modules.tests import commands, rules
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_staff import EMAIL, call, shared
from tests.classes.test_student_registration import emitted
from tests.individual_test.test_answer import first, put
from tests.individual_test.test_open import code, locked_session, path, replayed
from tests.individual_test.test_submit import scores, submit_path
from tests.messaging.helpers import rows
from tests.sessions.test_ai_assessment_switch import planned, save
from tests.sessions.test_dates import START, TEST, at, new_session, refusal
from tests.sessions.test_lock import _empty
from tests.sessions.test_rerun import copy, flag
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "emitted", "klass", "shared"]

MINUTE = timedelta(minutes=1)
HOUR = timedelta(hours=1)


@pytest.fixture(autouse=True)
def _empty_ai(ai_db):
    """No model config: the sessions are Rule-based."""


def limit_of(session_id: str) -> list[tuple]:
    return rows("SELECT minutes FROM test_sittings WHERE class_session_id = %s", session_id)


def attempt(session_id: str, user_id) -> tuple:
    [found] = rows(
        "SELECT id, status, submitted_at, closed_at, sitting_ends_at, effective_deadline "
        "FROM test_attempts WHERE class_session_id = %s AND user_id = %s",
        session_id,
        user_id,
    )
    return found


async def timed(klass: str, minutes: int | None = 60) -> tuple[str, list]:
    """A locked session with a time limit (stored as «Lagre Klasseøkt» would have, before the
    Start date) whose first Student has completed the Replay: (session, seated)."""
    session_id, seated = await locked_session(klass, 1)
    if minutes is not None:
        execute(
            "INSERT INTO test_sittings (class_session_id, minutes, updated_at) VALUES (%s, %s, %s)",
            session_id,
            minutes,
            NOW,
        )
    await replayed(seated[0], session_id)
    return session_id, seated


async def open_test(session_id: str) -> dict:
    response = await call(email(0), "POST", path(session_id))
    assert response.status_code == 201
    return response.json()


def factor(monkeypatch, value: str) -> None:
    """Story 8.9's `sessions.get_adjustment`, which lives on another branch until the merge."""

    async def get_adjustment(s, class_session_id, user_id):
        return SimpleNamespace(time_factor=Decimal(value))

    monkeypatch.setattr(sessions, "get_adjustment", get_adjustment, raising=False)


# The setting on the Klasseøkt.


async def test_the_owner_sets_and_clears_the_time_limit_with_the_save(klass, emitted):
    session_id = await planned(klass)
    read = (await call(EMAIL["owner"], "GET", f"/api/class-sessions/{session_id}")).json()
    assert read["test_sitting"] == {
        "minutes": None,
        "min_minutes": 15,
        "max_minutes": 240,
        "can_change": True,
    }
    emitted.clear()
    response = await save(session_id, test_sitting={"minutes": 90})
    assert response.status_code == 200
    assert response.json()["test_sitting"]["minutes"] == 90
    assert limit_of(session_id) == [(90,)]
    assert emitted == [("session", session_id)]
    # Left out, kept; the same again, unchanged; null switches it off.
    assert (await save(session_id)).json()["test_sitting"]["minutes"] == 90
    assert (await save(session_id, test_sitting={"minutes": 90})).status_code == 200
    assert (await save(session_id, test_sitting={"minutes": None})).json()["test_sitting"][
        "minutes"
    ] is None
    assert limit_of(session_id) == []


@pytest.mark.parametrize("minutes", [14, 241, 0, -5])
async def test_a_limit_out_of_range_is_refused_and_nothing_is_stored(klass, minutes):
    session_id = await planned(klass)
    response = await save(session_id, test_sitting={"minutes": minutes})
    assert refusal(response) == (
        422,
        "invalid_session_values",
        {"test_sitting_minutes": "out_of_range"},
    )
    assert limit_of(session_id) == []


async def test_a_limit_that_is_no_whole_number_is_refused(klass):
    session_id = await planned(klass)
    for wrong in (90.5, "90", True):
        response = await save(session_id, test_sitting={"minutes": wrong})
        assert response.status_code == 422
    assert limit_of(session_id) == []


async def test_the_limit_is_read_only_from_the_start_date(klass, monkeypatch):
    session_id = await planned(klass)
    assert (await save(session_id, test_sitting={"minutes": 60})).status_code == 200
    at(monkeypatch, START + MINUTE)
    response = await save(session_id, test_sitting={"minutes": 90})
    assert refusal(response) == (409, "session_locked", {"test_sitting": "locked"})
    assert limit_of(session_id) == [(60,)]
    # Unchanged it is no change; the read says it can no longer change.
    assert (await save(session_id, test_sitting={"minutes": 60})).status_code == 200
    read = (await call(EMAIL["owner"], "GET", f"/api/class-sessions/{session_id}")).json()
    assert read["test_sitting"]["can_change"] is False


async def test_an_assistant_lecturer_reads_it_but_cannot_change_it(klass, shared):
    session_id = await planned(klass)
    assert (await save(session_id, test_sitting={"minutes": 60})).status_code == 200
    read = await call(EMAIL["assistant"], "GET", f"/api/class-sessions/{session_id}")
    assert read.json()["test_sitting"]["minutes"] == 60
    assert read.json()["test_sitting"]["can_change"] is False
    response = await save(session_id, EMAIL["assistant"], test_sitting={"minutes": 90})
    assert response.status_code == 403
    assert limit_of(session_id) == [(60,)]


async def test_a_copy_takes_the_time_limit(klass, monkeypatch):
    flag(monkeypatch, True)
    source = await planned(klass)
    assert (await save(source, test_sitting={"minutes": 75})).status_code == 200
    copied = await copy(klass, source)
    assert copied.status_code == 201
    assert copied.json()["test_sitting"]["minutes"] == 75
    assert limit_of(copied.json()["id"]) == [(75,)]
    plain = (await copy(klass, await new_session(klass))).json()
    assert plain["test_sitting"]["minutes"] is None and limit_of(plain["id"]) == []


# The Student's timed sitting.


async def test_the_statement_names_the_limit_and_the_sitting_ends_after_it(klass):
    session_id, seated = await timed(klass, 60)
    statement = (await call(email(0), "GET", path(session_id))).json()
    assert statement["state"] == "statement"
    assert statement["time_limit_minutes"] == 60
    assert statement["sitting_ends_at"] is None
    test = await open_test(session_id)
    _, status, _, _, ends, deadline = attempt(session_id, seated[0])
    # Opened at NOW: the sitting ends an hour later, and the Test deadline is untouched.
    assert (status, ends, deadline) == ("open", NOW + HOUR, TEST)
    assert test["time_limit_minutes"] == 60
    assert test["sitting_ends_at"] == test["answering_ends_at"]
    assert test["answering_ends_at"].startswith((NOW + HOUR).isoformat()[:19])
    assert test["server_now"].startswith(NOW.isoformat()[:19])
    assert test["sitting_ended"] is False


async def test_a_time_factor_extends_the_sitting(klass, monkeypatch):
    factor(monkeypatch, "1.5")
    session_id, seated = await timed(klass, 45)
    assert (await call(email(0), "GET", path(session_id))).json()["time_limit_minutes"] == 68
    test = await open_test(session_id)
    assert attempt(session_id, seated[0])[4] == NOW + timedelta(minutes=67, seconds=30)
    assert test["time_limit_minutes"] == 68
    assert attempt(session_id, seated[0])[5] == TEST


async def test_a_factor_of_one_or_none_leaves_the_limit(klass, monkeypatch):
    factor(monkeypatch, "1")
    session_id, seated = await timed(klass, 30)
    await open_test(session_id)
    assert attempt(session_id, seated[0])[4] == NOW + 30 * MINUTE


async def test_without_the_option_nothing_is_timed(klass):
    session_id, seated = await timed(klass, None)
    statement = (await call(email(0), "GET", path(session_id))).json()
    assert statement["time_limit_minutes"] is None
    test = await open_test(session_id)
    assert attempt(session_id, seated[0])[4] is None
    assert (test["time_limit_minutes"], test["sitting_ends_at"]) == (None, None)
    assert test["answering_ends_at"].startswith(TEST.isoformat()[:19])
    assert await commands.due_sitting_ends(TEST - MINUTE) == []


async def test_saves_and_the_hand_in_are_refused_once_the_sitting_ended(klass, monkeypatch):
    session_id, seated = await timed(klass, 60)
    test = await open_test(session_id)
    choice = first(test, "choice")
    at(monkeypatch, NOW + HOUR - MINUTE)
    assert (await put(session_id, choice["id"], choice["options"][0], 1)).status_code == 200
    at(monkeypatch, NOW + HOUR)
    assert code(await put(session_id, choice["id"], choice["options"][1], 2)) == (
        409,
        "sitting_ended",
    )
    assert code(await call(email(0), "POST", submit_path(session_id))) == (409, "sitting_ended")
    assert attempt(session_id, seated[0])[1] == "open"


async def test_the_sweep_hands_in_the_ended_sitting_and_starts_nothing_else(
    klass, monkeypatch, emitted
):
    session_id, seated = await timed(klass, 60)
    test = await open_test(session_id)
    choice = first(test, "choice")
    assert (await put(session_id, choice["id"], choice["options"][0], 1)).status_code == 200
    assert await commands.due_sitting_ends(NOW + HOUR - MINUTE) == []

    late = NOW + HOUR + 3 * MINUTE
    emitted.clear()
    done = await sweep.run(late)
    assert done["tests.end_sitting"] == 1
    assert done["sessions.lock_test"] == 0 and done["tests.close_attempt"] == 0
    attempt_id, status, submitted_at, closed_at, ends, deadline = attempt(session_id, seated[0])
    # Handed in as of the sitting's end, scored, the step recorded; not closed.
    assert (status, submitted_at, closed_at, deadline) == ("auto_submitted", ends, None, TEST)
    assert scores(session_id)[choice["id"]][0] is not None
    [(at_step,)] = rows(
        "SELECT at FROM progress_steps WHERE user_id = %s AND step = 'test_submitted'", seated[0]
    )
    assert at_step == ends
    assert {("session", session_id), ("user", str(seated[0]))} <= set(emitted)
    assert COMMAND_TOPICS["tests.end_sitting"] == {"session", "user"}
    # Nothing that hangs on the Test deadline ran: no lock, no pinned Scoring guide.
    assert rows("SELECT test_locked_at FROM class_sessions WHERE id = %s", session_id) == [(None,)]

    # The Student reads it handed in at the sitting's end; a save now is `attempt_submitted`.
    at(monkeypatch, late)
    body = (await call(email(0), "GET", path(session_id))).json()
    assert (body["state"], body["sitting_ended"]) == ("auto_submitted", True)
    assert code(await put(session_id, choice["id"], choice["options"][1], 2)) == (
        409,
        "attempt_submitted",
    )

    # A repeat changes nothing.
    assert (await sweep.run(late + MINUTE))["tests.end_sitting"] == 0
    assert await commands.end_sitting(attempt_id, late + MINUTE) is False

    # At the Test deadline the lock runs, then `close_attempt` only marks it closed.
    stored = scores(session_id)
    done = await sweep.run(TEST + MINUTE)
    assert done["sessions.lock_test"] == 1 and done["tests.close_attempt"] == 1
    assert attempt(session_id, seated[0])[1:4] == ("auto_submitted", ends, TEST + MINUTE)
    assert scores(session_id) == stored


async def test_a_sitting_that_would_end_after_the_deadline_ends_with_it(klass, monkeypatch):
    session_id, seated = await timed(klass, 60)
    at(monkeypatch, TEST - 30 * MINUTE)
    test = await open_test(session_id)
    attempt_id, _, _, _, ends, deadline = attempt(session_id, seated[0])
    assert (ends, deadline) == (TEST + 30 * MINUTE, TEST)
    assert test["answering_ends_at"].startswith(TEST.isoformat()[:19])
    # At the deadline a save is `test_deadline_passed`, the sitting is not the sweep's to end,
    # and `close_attempt` hands it in as of the deadline.
    at(monkeypatch, TEST)
    choice = first(test, "choice")
    assert code(await put(session_id, choice["id"], choice["options"][0], 1)) == (
        409,
        "test_deadline_passed",
    )
    assert await commands.due_sitting_ends(TEST + HOUR) == []
    assert await commands.end_sitting(attempt_id, TEST + HOUR) is False
    done = await sweep.run(TEST + MINUTE)
    assert done["tests.end_sitting"] == 0 and done["tests.close_attempt"] == 1
    assert attempt(session_id, seated[0])[1:4] == ("auto_submitted", TEST, TEST + MINUTE)
    at(monkeypatch, TEST + MINUTE)
    assert (await call(email(0), "GET", path(session_id))).json()["sitting_ended"] is False


async def test_a_handed_in_attempt_is_not_the_sweeps_to_end(klass, monkeypatch):
    session_id, seated = await timed(klass, 60)
    await open_test(session_id)
    assert (await call(email(0), "POST", submit_path(session_id))).status_code == 200
    attempt_id = attempt(session_id, seated[0])[0]
    assert await commands.due_sitting_ends(NOW + 2 * HOUR) == []
    assert await commands.end_sitting(attempt_id, NOW + 2 * HOUR) is False
    assert attempt(session_id, seated[0])[1] == "submitted"


async def test_end_sitting_does_nothing_before_the_end(klass):
    session_id, seated = await timed(klass, 60)
    await open_test(session_id)
    attempt_id = attempt(session_id, seated[0])[0]
    assert await commands.end_sitting(attempt_id, NOW + HOUR - MINUTE) is False
    assert await commands.end_sitting(uuid.uuid4(), NOW + HOUR) is False
    assert await commands.due_sitting_ends(NOW + HOUR) == [attempt_id]


async def test_the_sweep_ends_sittings_before_the_test_deadline_actions():
    names = [action.name for action in sweep.DUE_ACTIONS]
    assert names.index("tests.end_sitting") < names.index("sessions.lock_test")
    assert names.index("tests.end_sitting") < names.index("tests.close_attempt")


# The pure rules.


def test_answering_ends_at_the_earlier_of_the_sitting_and_the_deadline():
    def a(ends, deadline):
        return {"sitting_ends_at": ends, "effective_deadline": deadline}

    assert rules.answering_ends_at(a(None, None)) is None
    assert rules.answering_ends_at(a(None, TEST)) == TEST
    assert rules.answering_ends_at(a(NOW, None)) == NOW
    assert rules.answering_ends_at(a(NOW, TEST)) == NOW
    assert rules.answering_ends_at(a(TEST + HOUR, TEST)) == TEST
    assert rules.sitting_ended(a(NOW, TEST), NOW) is True
    assert rules.sitting_ended(a(NOW, TEST), NOW - MINUTE) is False
    assert rules.sitting_ended(a(NOW, None), NOW) is True
    assert rules.sitting_ended(a(TEST, TEST), TEST) is False
    assert rules.sitting_ended(a(None, TEST), TEST) is False
    assert rules.sitting_end(NOW, 90, Decimal("2")) == NOW + 3 * HOUR
    assert rules.limit_minutes(45, Decimal("1.5")) == 68
    assert rules.limit_minutes(60, Decimal("1")) == 60


async def test_a_sitting_with_no_test_deadline_is_handed_in_by_the_sweep(klass):
    session_id, seated = await timed(klass, 60)
    await open_test(session_id)
    execute(
        "UPDATE test_attempts SET effective_deadline = NULL WHERE class_session_id = %s",
        session_id,
    )
    attempt_id = attempt(session_id, seated[0])[0]
    assert await commands.due_sitting_ends(NOW + HOUR) == [attempt_id]
    assert (await sweep.run(NOW + HOUR + MINUTE))["tests.end_sitting"] == 1
    assert attempt(session_id, seated[0])[1:3] == ("auto_submitted", NOW + HOUR)


async def test_a_sitting_the_sweep_missed_is_handed_in_at_its_end_by_the_close(klass, monkeypatch):
    session_id, seated = await timed(klass, 60)
    await open_test(session_id)
    attempt_id = attempt(session_id, seated[0])[0]
    # `end_sitting` never ran (it failed every minute): the close at the deadline hands it in as
    # of the sitting's end, since saves were refused from then on.
    await sessions.lock_test(uuid.UUID(session_id), now=TEST)
    assert await commands.close_attempt(attempt_id, TEST + MINUTE) is True
    assert attempt(session_id, seated[0])[1:4] == ("auto_submitted", NOW + HOUR, TEST + MINUTE)
    [(at_step,)] = rows(
        "SELECT at FROM progress_steps WHERE user_id = %s AND step = 'test_submitted'", seated[0]
    )
    assert at_step == NOW + HOUR
    at(monkeypatch, TEST + MINUTE)
    assert (await call(email(0), "GET", path(session_id))).json()["sitting_ended"] is True
