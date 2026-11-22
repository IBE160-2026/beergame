"""Review and submit the Individual test (Story 11.10, FR-51, FR-18, FR-54, FR-5, AD-8, AD-9,
AD-16, AD-23).

`POST /api/me/class-sessions/{id}/test/submit` hands the attempt in once through
`tests.commands.submit`: under the attempt row lock the status becomes `submitted` with the time,
each saved choice, table and number answer gets its computed score from `tests.scoring` with the
question set version, and `test_submitted` is recorded through `progress.record_step`. A repeat,
a save after it or a submit past the deadline is refused; a submitted Student gets no Test
deadline reminder. The api's clock is fixed and moved by hand; the database clock is never read."""

import asyncio
import uuid
from datetime import timedelta
from types import SimpleNamespace

from app.modules.content import service as content
from app.modules.identity.schemas import AccountRole
from app.modules.progress import service as progress
from app.modules.sessions import service as sessions
from app.modules.tests import commands, scoring
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_staff import call
from tests.classes.test_student_registration import emitted
from tests.individual_test.test_answer import Z, first, opened, put
from tests.individual_test.test_open import code, path, replayed
from tests.messaging.helpers import rows
from tests.sessions.test_dates import TEST, at
from tests.sessions.test_lock import _empty
from tests.sessions.test_student_choice import email
from tests.sessions.test_student_home import home

__all__ = ["_empty", "clock", "emitted", "klass"]


def submit_path(session_id: str) -> str:
    return f"{path(session_id)}/submit"


def scores(session_id: str) -> dict[str, tuple]:
    found = rows(
        "SELECT a.item_id, a.score, a.scored_version FROM test_answers a "
        "JOIN test_attempts t ON t.id = a.attempt_id WHERE t.class_session_id = %s",
        session_id,
    )
    return {item_id: (score, version) for item_id, score, version in found}


def status(session_id: str) -> list[tuple]:
    return rows(
        "SELECT status, submitted_at FROM test_attempts WHERE class_session_id = %s", session_id
    )


async def test_submit_scores_the_saved_answers_and_records_the_step_once(klass, emitted):
    session_id, seated, test = await opened(klass)
    choice = first(test, "choice")
    long = first(test, "long")
    answers = {
        choice["id"]: choice["options"][0],
        "tabell-annen-bransje": [8, None, 9, None, None],
        "tall-annen-bransje": 16,
        "startoppgave-posisjon": -13,
        long["id"]: "Et langsvar.",
    }
    for item_id, value in answers.items():
        assert (await put(session_id, item_id, value, 1)).status_code == 200

    emitted.clear()
    done = await call(email(0), "POST", submit_path(session_id))
    assert done.status_code == 200
    body = done.json()
    assert (body["state"], body["submitted_at"]) == ("submitted", Z)
    # The items and saved answers stay readable, with no score, key or weight (FR-54).
    back = {item["id"]: item["answer"] for item in body["items"]}
    assert all(back[i]["value"] == v for i, v in answers.items())
    assert "score" not in str(body) and "credit" not in str(body) and "weight" not in str(body)
    assert status(session_id) == [("submitted", NOW)]

    # Each computed score equals `score_answer` on the stored value, with the set's version.
    [(version,)] = rows(
        "SELECT question_set_version FROM test_attempts WHERE class_session_id = %s", session_id
    )
    question_set = await content.get(content.Kind.QUESTION_SET, version)
    by_id = {item.id: item for item in question_set.items}
    _, task = await content.starting_task(None)
    stored = scores(session_id)
    for item_id, value in answers.items():
        expected = scoring.score_answer(by_id[item_id], value, task)
        score, scored_version = stored[item_id]
        if expected is None:  # a long answer: the Scoring guide's (Epic 12)
            assert (item_id, score, scored_version) == (long["id"], None, None)
            continue
        assert scored_version == version
        assert score["answered"] is expected.answered
        assert score["credit"] == expected.credit
        assert [c["code"] for c in score["criteria"]] == [c.code for c in expected.criteria]
    assert stored["tall-annen-bransje"][0]["criteria"]  # an Interactive item keeps its criteria
    # No row is made for an item never answered.
    assert set(stored) == set(answers)

    # The step, once, and exactly the registered topics (AD-8, AD-16).
    assert await progress.has_step(seated[0], uuid.UUID(session_id), progress.Step.TEST_SUBMITTED)
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["tests.submit"]
    assert sorted(emitted) == [("session", session_id), ("user", str(seated[0]))]
    test_step = next(s for s in (await home(email(0)))["steps"] if s["step"] == "test")
    assert test_step["state"] == "done"

    # Read again on any device: the submitted state with the answers.
    again = (await call(email(0), "GET", path(session_id))).json()
    assert again == body

    # A second submit changes nothing and emits nothing; the API refuses it.
    emitted.clear()
    repeat = await call(email(0), "POST", submit_path(session_id))
    assert code(repeat) == (409, "attempt_submitted")
    student = SimpleNamespace(id=seated[0], roles=())
    later = NOW + timedelta(minutes=5)
    unchanged = await commands.submit(student, uuid.UUID(session_id), later)
    assert unchanged is not None and unchanged.submitted is False
    assert unchanged.attempt["submitted_at"] == NOW
    assert emitted == [] and status(session_id) == [("submitted", NOW)]
    assert scores(session_id) == stored


async def test_a_save_after_the_hand_in_is_refused(klass):
    session_id, _, test = await opened(klass)
    choice = first(test, "choice")
    assert (await put(session_id, choice["id"], choice["options"][0], 1)).status_code == 200
    assert (await call(email(0), "POST", submit_path(session_id))).status_code == 200
    late = await put(session_id, choice["id"], choice["options"][1], 2)
    assert code(late) == (409, "attempt_submitted")
    [(score, _)] = scores(session_id).values()
    assert score is not None
    assert rows("SELECT value, revision FROM test_answers") == [(choice["options"][0], 1)]


async def test_two_submits_at_once_hand_in_once(klass, emitted):
    session_id, _, test = await opened(klass)
    choice = first(test, "choice")
    assert (await put(session_id, choice["id"], choice["options"][0], 1)).status_code == 200
    emitted.clear()
    a, b = await asyncio.gather(
        call(email(0), "POST", submit_path(session_id)),
        call(email(0), "POST", submit_path(session_id)),
    )
    assert sorted([a.status_code, b.status_code]) == [200, 409]
    assert len(status(session_id)) == 1 and status(session_id)[0][0] == "submitted"
    assert len([e for e in emitted if e[0] == "user"]) == 1


async def test_past_the_deadline_the_attempt_stays_open(klass, monkeypatch):
    session_id, _, _ = await opened(klass)
    at(monkeypatch, TEST)
    refused = await call(email(0), "POST", submit_path(session_id))
    assert code(refused) == (409, "test_deadline_passed")
    assert status(session_id) == [("open", None)]
    assert rows("SELECT count(*) FROM progress_steps WHERE step = 'test_submitted'") == [(0,)]


async def test_no_one_else_submits_and_an_unopened_test_is_not_submitted(klass):
    session_id, seated, _ = await opened(klass, 2)
    await replayed(seated[1], session_id)  # their own session, the test not opened
    await make("admin@x.no", roles=(AccountRole.admin,))
    for who, target in (
        (email(1), session_id),
        (LECTURER, session_id),
        ("admin@x.no", session_id),
        (email(0), str(uuid.uuid7())),
        (email(0), "not-an-id"),
    ):
        refused = await call(who, "POST", submit_path(target))
        assert code(refused) == (403, "forbidden")
    assert status(session_id) == [("open", None)]


async def test_a_submitted_student_gets_no_test_deadline_reminder(klass):
    session_id, seated, _ = await opened(klass, 2)
    assert (await call(email(0), "POST", submit_path(session_id))).status_code == 200
    sid = uuid.UUID(session_id)
    assert await sessions.reminder_recipients(sid, "test_deadline") == [seated[1]]
    # The other deadlines still remind both.
    both = sorted(seated)
    assert await sessions.reminder_recipients(sid, "play_deadline") == both
    assert await sessions.reminder_recipients(sid, "debrief_deadline") == both


async def test_scores_use_the_pinned_starting_task_not_a_later_version(klass):
    session_id, _, _ = await opened(klass)
    _, task = await content.starting_task(None)
    position = next(t for t in task.items if t.id == "position")
    rows_by_key = {row.key: row.value for row in position.rows}
    right = sum(term.sign * rows_by_key[term.row] for term in position.terms)
    assert (await put(session_id, "startoppgave-posisjon", right, 1)).status_code == 200
    # A later Starting task version moves the answer; the session pinned version 1 at its lock.
    body = task.model_dump(mode="json")
    later = next(item for item in body["items"] if item["id"] == "position")
    later["rows"][0]["value"] += 7
    published = await content.publish("starting_task", body)
    try:
        assert (await call(email(0), "POST", submit_path(session_id))).status_code == 200
        score, _ = scores(session_id)["startoppgave-posisjon"]
        assert score["credit"] == 1.0
    finally:
        execute(
            "DELETE FROM content_records WHERE kind = 'starting_task' AND version = %s", published
        )
