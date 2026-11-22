"""Saved answers handed in at the Test deadline (Story 11.11, FR-51, FR-18, FR-17, AD-9, AD-16).

The sweep first runs `sessions.lock_test`, then `tests.close_attempt` for each attempt whose
`effective_deadline` has passed: an open one becomes `auto_submitted` with its saved answers
scored as at a hand-in and `test_submitted` recorded; one handed in already is only marked
closed. A save after the deadline is refused, a Student who never opened the test gets no attempt,
and `tests.service.parts_with_content` tells Completion which parts hold content. The api's clock
is fixed and moved by hand; the database clock is never read."""

import uuid
from datetime import timedelta

import psycopg
import pytest

from app.modules.ops import sweep
from app.modules.progress import service as progress
from app.modules.sessions import service as sessions
from app.modules.tests import commands
from app.modules.tests import service as tests_service
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_staff import call
from tests.classes.test_student_registration import emitted
from tests.individual_test.test_answer import first, opened, put
from tests.individual_test.test_open import code, path, replayed
from tests.individual_test.test_submit import scores, submit_path
from tests.messaging.helpers import rows
from tests.sessions.test_dates import TEST, at
from tests.sessions.test_lock import _empty
from tests.sessions.test_student_choice import email
from tests.sessions.test_student_home import home

__all__ = ["_empty", "clock", "emitted", "klass"]

MINUTE = timedelta(minutes=1)


def attempt(session_id: str, user_id) -> tuple:
    [found] = rows(
        "SELECT id, status, submitted_at, closed_at FROM test_attempts "
        "WHERE class_session_id = %s AND user_id = %s",
        session_id,
        user_id,
    )
    return found


def step_of(body: dict) -> dict:
    return next(s for s in body["steps"] if s["step"] == "test")


async def test_the_sweep_locks_first_then_hands_in_the_saved_answers_once(klass, monkeypatch):
    session_id, seated, test = await opened(klass)
    choice = first(test, "choice")
    answers = {choice["id"]: choice["options"][0], "tall-annen-bransje": 16}
    for item_id, value in answers.items():
        assert (await put(session_id, item_id, value, 1)).status_code == 200
    long = first(test, "long")
    assert (await put(session_id, long["id"], "Et langsvar.", 1)).status_code == 200
    assert rows("SELECT test_locked_at FROM class_sessions WHERE id = %s", session_id) == [(None,)]

    # One sweep, late after the deadline: the lock runs first, then the close in the same run.
    late = TEST + 3 * MINUTE
    done = await sweep.run(late)
    assert done["sessions.lock_test"] == 1 and done["tests.close_attempt"] == 1
    attempt_id, status, submitted_at, closed_at = attempt(session_id, seated[0])
    assert (status, submitted_at, closed_at) == ("auto_submitted", TEST, late)
    # The Scoring guide was pinned by the lock before the close (Story 11.2).
    [(pinned_at,)] = rows(
        "SELECT pinned_at FROM test_scoring_guides WHERE class_session_id = %s", session_id
    )
    assert pinned_at == TEST
    # Scored as at a hand-in: choice and number answers carry scores, the long answer none.
    stored = scores(session_id)
    assert set(stored) == {*answers, long["id"]}
    assert all(stored[item][0] is not None and stored[item][1] for item in answers)
    assert stored[long["id"]] == (None, None)
    [(at_step,)] = rows(
        "SELECT at FROM progress_steps WHERE user_id = %s AND step = 'test_submitted'", seated[0]
    )
    assert at_step == TEST
    assert await progress.has_step(seated[0], uuid.UUID(session_id), progress.Step.TEST_SUBMITTED)

    # The Student reads it handed in automatically, with the answers; Hjem marks the step done.
    at(monkeypatch, late)
    body = (await call(email(0), "GET", path(session_id))).json()
    assert body["state"] == "auto_submitted"
    saved = {item["id"]: item["answer"]["value"] for item in body["items"] if item["answer"]}
    assert saved == {**answers, long["id"]: "Et langsvar."}
    assert step_of(await home(email(0)))["state"] == "done"

    # A repeat sweep changes nothing.
    again = await sweep.run(late + MINUTE)
    assert again["sessions.lock_test"] == 0 and again["tests.close_attempt"] == 0
    assert attempt(session_id, seated[0]) == (attempt_id, status, submitted_at, closed_at)
    assert scores(session_id) == stored
    assert await commands.close_attempt(attempt_id, late + 2 * MINUTE) is False


async def test_close_records_the_step_with_the_registered_topics(klass, emitted):
    session_id, seated, _ = await opened(klass)
    await sessions.lock_test(uuid.UUID(session_id), now=TEST)
    [attempt_id] = await commands.due_closes(TEST)
    emitted.clear()
    assert await commands.close_attempt(attempt_id, TEST) is True
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["tests.close_attempt"]
    assert sorted(emitted) == [("session", session_id), ("user", str(seated[0]))]


async def test_nothing_is_closed_before_the_test_deadline_lock(klass):
    session_id, seated, _ = await opened(klass)
    attempt_id = attempt(session_id, seated[0])[0]
    # Past the deadline, but `lock_test` has not run: not found, and a direct call does nothing.
    assert await commands.due_closes(TEST + MINUTE) == []
    assert await commands.close_attempt(attempt_id, TEST + MINUTE) is False
    assert attempt(session_id, seated[0])[1:] == ("open", None, None)


async def test_an_attempt_not_yet_due_is_left_open(klass):
    session_id, seated, _ = await opened(klass)
    await sessions.lock_test(uuid.UUID(session_id), now=TEST - MINUTE)  # the dev route's case
    attempt_id = attempt(session_id, seated[0])[0]
    assert await commands.due_closes(TEST - MINUTE) == []
    assert await commands.close_attempt(attempt_id, TEST - MINUTE) is False
    assert attempt(session_id, seated[0])[1:] == ("open", None, None)
    assert await commands.due_closes(TEST) == [attempt_id]


async def test_a_handed_in_attempt_is_only_marked_closed(klass, emitted):
    session_id, seated, test = await opened(klass)
    choice = first(test, "choice")
    assert (await put(session_id, choice["id"], choice["options"][0], 1)).status_code == 200
    assert (await call(email(0), "POST", submit_path(session_id))).status_code == 200
    stored = scores(session_id)
    await sessions.lock_test(uuid.UUID(session_id), now=TEST)
    attempt_id = attempt(session_id, seated[0])[0]
    emitted.clear()
    assert await commands.close_attempt(attempt_id, TEST + MINUTE) is True
    assert attempt(session_id, seated[0])[1:] == ("submitted", NOW, TEST + MINUTE)
    assert scores(session_id) == stored
    assert emitted == []
    assert rows("SELECT count(*) FROM progress_steps WHERE step = 'test_submitted'") == [(1,)]
    assert await commands.close_attempt(attempt_id, TEST + 2 * MINUTE) is False


async def test_a_save_after_the_deadline_is_refused_and_the_saved_answer_is_handed_in(
    klass, monkeypatch
):
    session_id, seated, test = await opened(klass)
    choice = first(test, "choice")
    before, after = choice["options"][0], choice["options"][1]
    assert (await put(session_id, choice["id"], before, 1)).status_code == 200
    at(monkeypatch, TEST)
    late = await put(session_id, choice["id"], after, 2)
    assert code(late) == (409, "test_deadline_passed")
    await sweep.run(TEST + MINUTE)
    assert attempt(session_id, seated[0])[1] == "auto_submitted"
    assert rows("SELECT value, revision FROM test_answers") == [(before, 1)]
    assert scores(session_id)[choice["id"]][0] is not None


async def test_a_student_who_never_opened_the_test_gets_no_attempt(klass, monkeypatch):
    session_id, seated, _ = await opened(klass, 2)
    await replayed(seated[1], session_id)  # through the Replay, the test never opened
    at(monkeypatch, TEST + MINUTE)
    await sweep.run(TEST + MINUTE)
    assert rows("SELECT count(*) FROM test_attempts WHERE user_id = %s", seated[1]) == [(0,)]
    closed = (await call(email(1), "GET", path(session_id))).json()
    assert (closed["state"], closed["items"]) == ("closed", [])
    assert code(await call(email(1), "POST", path(session_id))) == (409, "test_deadline_passed")
    # Hjem: the step stays current and not done, marked closed («ikke gjort, Testfristen er ute»).
    step = step_of(await home(email(1)))
    assert (step["state"], step["closed"]) == ("current", True)
    assert not await progress.has_step(
        seated[1], uuid.UUID(session_id), progress.Step.TEST_SUBMITTED
    )


async def test_before_the_deadline_the_test_step_is_not_closed(klass):
    session_id, _, _ = await opened(klass)
    step = step_of(await home(email(0)))
    assert (step["state"], step["closed"]) == ("current", False)


async def test_parts_with_content_name_the_parts_that_hold_an_answer(klass):
    session_id, seated, test = await opened(klass, 2)
    await replayed(seated[1], session_id)
    sid = uuid.UUID(session_id)
    assert await tests_service.parts_with_content(seated[1], sid) is None  # no attempt
    long = first(test, "long")
    choice = first(test, "choice")
    assert (await put(session_id, choice["id"], choice["options"][0], 1)).status_code == 200
    assert (await put(session_id, long["id"], "   ", 1)).status_code == 200  # blank: no content
    assert (await put(session_id, "tabell-annen-bransje", [None] * 5, 1)).status_code == 200
    # A number typed and then cleared is stored as null: no content either.
    assert (await put(session_id, "tall-annen-bransje", 4, 1)).status_code == 200
    assert (await put(session_id, "tall-annen-bransje", None, 2)).status_code == 200
    parts = await tests_service.parts_with_content(seated[0], sid)
    types = {item["type"] for item in test["items"]}
    expected = {tests_service.PARTS[t] for t in types}
    assert set(parts) == expected
    assert parts["choice"] is True
    assert parts["long"] is False and parts["interactive"] is False
    assert (
        await put(session_id, "tabell-annen-bransje", [None, 3, None, None, None], 2)
    ).status_code == 200
    assert (await tests_service.parts_with_content(seated[0], sid))["interactive"] is True


async def test_a_sweep_closes_at_most_its_share_oldest_deadline_first(klass, monkeypatch):
    session_id, seated, _ = await opened(klass, 2)
    await replayed(seated[1], session_id)
    assert (await call(email(1), "POST", path(session_id))).status_code == 201
    execute(
        "UPDATE test_attempts SET effective_deadline = %s WHERE user_id = %s",
        TEST - MINUTE,
        seated[1],
    )
    await sessions.lock_test(uuid.UUID(session_id), now=TEST)
    monkeypatch.setattr(commands, "CLOSES_PER_SWEEP", 1)
    earlier = attempt(session_id, seated[1])[0]
    assert await commands.due_closes(TEST) == [earlier]
    assert (await sweep.run(TEST + MINUTE))["tests.close_attempt"] == 1
    assert attempt(session_id, seated[1])[1] == "auto_submitted"
    assert attempt(session_id, seated[0])[1] == "open"
    assert (await sweep.run(TEST + 2 * MINUTE))["tests.close_attempt"] == 1
    assert attempt(session_id, seated[0])[1] == "auto_submitted"


async def test_the_sweep_closes_attempts_right_after_the_test_deadline_lock():
    names = [action.name for action in sweep.DUE_ACTIONS]
    assert names.index("tests.close_attempt") == names.index("sessions.lock_test") + 1


async def test_a_closed_attempt_is_never_open_in_the_database(klass):
    _, seated, _ = await opened(klass)
    with pytest.raises(psycopg.errors.CheckViolation):
        execute("UPDATE test_attempts SET closed_at = %s WHERE user_id = %s", NOW, seated[0])
