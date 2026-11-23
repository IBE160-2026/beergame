"""The Debrief quiz (Story 9.9, FR-46, FR-47, FR-18, AD-16, AD-23).

Step 5 is open only once the Student has finished the Debrief (`progress` `debrief`, else 403
`debrief_required`). Each attempt is scored by the answer key on the server and stored once in
`quiz_attempts`; a wrong answer gets its explanation, ending with the sentence about the
Student's own Game rendered from the facts set of their Seat; retries are unlimited until the
Test deadline, and the attempt with every answer right records `quiz_passed` in the same
transaction. One Class game played two Uker, then marked finished, serves the test."""

import json
import random
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import psycopg
import pytest

from app.analysis import quiz as rules
from app.modules.content import service as content
from app.modules.debrief import service as debrief_service
from app.modules.games import service as games
from app.modules.ops import sweep
from app.modules.progress import service as progress
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import clock, klass
from tests.classes.test_staff import call
from tests.classes.test_student_registration import emitted
from tests.debrief.test_debrief import LOCKED, finish, home, open_, refused
from tests.games.helpers import play_week
from tests.messaging.helpers import rows
from tests.sessions.test_lock import _empty
from tests.sessions.test_open_games import confirmed
from tests.sessions.test_start_game import start, task_done
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "emitted", "klass"]


def attempts() -> list[tuple]:
    return rows("SELECT number, quiz_version, answers, passed FROM quiz_attempts ORDER BY number")


def unprocessable(response, reason: str) -> None:
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["fields"] == {"answers": reason}


def conflict(response, code: str) -> None:
    assert response.status_code == 409
    assert response.json()["error"]["code"] == code


def body(answers: list[tuple[str, str]]) -> dict:
    return {"answers": [{"question_id": q, "choice_id": c} for q, c in answers]}


async def test_the_quiz_is_scored_stored_retried_and_passed(klass, emitted):
    session_id, seated = await confirmed(klass, 2)
    await sweep.run(LOCKED)
    me = email(0)
    game_id = (await home(me))["game"]["id"]
    await task_done(seated[0], session_id)
    assert (await start(me, game_id)).status_code == 200
    for _ in range(2):
        await play_week(game_id)
    finish(game_id)
    debrief = (await open_(me, session_id)).json()
    path = f"/api/debriefs/{debrief['id']}"
    sid = uuid.UUID(session_id)
    [(mine,)] = rows("SELECT id FROM users WHERE email = %s", me)
    _, quiz = await content.debrief_quiz(None)
    right = [(q.id, q.answer) for q in quiz.questions]

    # Before the Debrief is finished (here: with the Explanation sent): refused, in the api, and
    # nothing is stored.
    sent = await call(me, "POST", f"{path}/explanation", json={"text": "Min."})
    assert sent.status_code == 201
    refused(await call(me, "GET", f"{path}/quiz"), "debrief_required")
    refused(await call(me, "POST", f"{path}/quiz/attempts", json=body(right)), "debrief_required")
    assert attempts() == []
    await progress.record_step(mine, sid, progress.Step.DEBRIEF, datetime.now(UTC))

    # The pinned version, marked placeholder, in the content's order, without the answer key.
    opened = await call(me, "GET", f"{path}/quiz")
    assert opened.status_code == 200
    shown = opened.json()
    assert (shown["version"], shown["placeholder"], shown["attempts"]) == (1, True, 0)
    assert (shown["passed_at"], shown["last"]) == (None, None)
    assert [q["id"] for q in shown["questions"]] == [q.id for q in quiz.questions]
    assert "answer" not in json.dumps(shown["questions"])
    assert [c["id"] for c in shown["questions"][0]["choices"]] == ["netto", "posisjon", "sum"]

    # A body that cannot be scored stores nothing.
    for sent, reason in (
        (right[:2], "incomplete"),
        ([*right, right[0]], "incomplete"),
        ([("posisjon", "ukjent"), *right[1:]], "unknown_choice"),
    ):
        unprocessable(await call(me, "POST", f"{path}/quiz/attempts", json=body(sent)), reason)
    assert attempts() == []

    # A wrong answer: stored once, scored on the server, the explanation with it; not passed.
    emitted.clear()
    wrong = [("posisjon", "netto"), *right[1:]]
    first = await call(me, "POST", f"{path}/quiz/attempts", json=body(wrong))
    assert first.status_code == 201
    result = first.json()
    assert (result["number"], result["passed"], result["correct"], result["asked"]) == (
        1,
        False,
        2,
        3,
    )
    missed, *rest = result["results"]
    assert (missed["chosen"], missed["right_choice"], missed["correct"]) == (
        "netto",
        "posisjon",
        False,
    )
    stored = await games.fact_set(game_id, debrief["role"])
    own = rules.render_in_your_game(stored.facts, quiz.questions[0])
    expected = quiz.questions[0].explanation + (f" {own.text}" if own else "")
    assert missed["explanation"] == {"text": expected, "ai_generated": False, "llm_call_id": None}
    assert all(r["correct"] and r["explanation"] is None for r in rest)
    assert attempts() == [
        (
            1,
            1,
            [{"question_id": q, "choice_id": c, "correct": q != "posisjon"} for q, c in wrong],
            False,
        )
    ]
    assert not await progress.has_step(mine, sid, progress.Step.QUIZ_PASSED)
    assert {topic for topic, _ in emitted} == {"debrief"}
    with pytest.raises(psycopg.errors.RestrictViolation):
        execute("UPDATE quiz_attempts SET passed = true")

    # The retry: the next attempt's questions, reshuffled with a seed of the Student and the
    # attempt (the same on a reload), and the last result to read.
    again = (await call(me, "GET", f"{path}/quiz")).json()
    order = [q.id for q in quiz.questions]
    random.Random(f"{mine}:2").shuffle(order)
    assert [q["id"] for q in again["questions"]] == order
    assert again["attempts"] == 1 and again["last"] == result
    assert (await call(me, "GET", f"{path}/quiz")).json() == again

    # After the Test deadline (judged in the database's time): refused, nothing stored.
    past = AsyncMock(return_value=(None, datetime(2000, 1, 1, tzinfo=UTC)))
    with patch("app.modules.debrief.service.sessions.student_deadlines", past):
        conflict(
            await call(me, "POST", f"{path}/quiz/attempts", json=body(right)),
            "test_deadline_passed",
        )
    assert len(attempts()) == 1

    # Every answer right, in the shown order: passed, with the step in the same transaction.
    emitted.clear()
    shown_order = [(q, dict(right)[q]) for q in order]
    passed = await call(me, "POST", f"{path}/quiz/attempts", json=body(shown_order))
    assert passed.status_code == 201
    assert (passed.json()["number"], passed.json()["passed"]) == (2, True)
    assert [r["question_id"] for r in passed.json()["results"]] == order
    assert all(r["explanation"] is None for r in passed.json()["results"])
    [(step_at,)] = rows(
        "SELECT at FROM progress_steps WHERE user_id = %s AND step = 'quiz_passed'", mine
    )
    [(submitted_at,)] = rows("SELECT submitted_at FROM quiz_attempts WHERE number = 2")
    assert step_at == submitted_at
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["debrief.submit_quiz"]
    assert ("debrief", debrief["id"]) in emitted
    steps = {s["step"]: s["state"] for s in (await home(me))["steps"]}
    assert steps["quiz"] == "done"

    # Passed: no further attempt, no questions, the passing result stays the last.
    conflict(await call(me, "POST", f"{path}/quiz/attempts", json=body(right)), "quiz_passed")
    done = (await call(me, "GET", f"{path}/quiz")).json()
    assert (done["attempts"], done["questions"], done["last"]) == (2, [], passed.json())
    assert done["passed_at"] == passed.json()["submitted_at"]
    assert len(attempts()) == 2

    # The Debrief summary carries the number of attempts and when the quiz was passed (read at
    # request time; the summary row itself never changes).
    execute(
        "INSERT INTO debrief_summaries (user_id, class_session_id, game_id, fact_set_id, "
        "moment_ids, reflection, finished_at) VALUES (%s, %s, %s, %s, '[]', '[]', now())",
        mine,
        sid,
        uuid.UUID(game_id),
        uuid.UUID(stored.id),
    )
    summary = (await call(me, "GET", f"{path}/summary")).json()["summary"]
    assert (summary["quiz_attempts"], summary["quiz_passed_at"]) == (2, done["passed_at"])
    # Story 13.10: the Student report counts the same attempts, up to the pass.
    reported = await debrief_service.report_debrief(mine, sid)
    assert (reported.quiz_attempts, reported.quiz_passed) == (2, True)
    assert reported.late == summary["late"]

    # Another Student of the Class who has not finished the Debrief is still refused.
    theirs = (await open_(email(1), session_id)).json()
    refused(await call(email(1), "GET", f"/api/debriefs/{theirs['id']}/quiz"), "debrief_required")
