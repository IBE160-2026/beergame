"""Debrief quiz exclusions and the staff's view of quiz attempts (Story 9.10, FR-46, FR-47,
AD-12, AD-15, AD-23).

The Class's owners take questions out of a Class session's Debrief quiz as Class session rows
(never an edit of the content record), audited, until the Test deadline and never the last one;
Assistant lecturers read the quiz with its answer keys. A Student's next attempt asks only the
rest; nobody is passed by an exclusion, and a Student whose last attempt got wrong only questions
now taken out is told (a `quiz_changed` notice; Hjem's Quiz step says so). The staff's Debrief
summary names the Student and lists their attempts. One Class game played two Uker, then marked
finished, serves the test."""

import uuid
from datetime import UTC, datetime
from unittest.mock import patch

from app.modules.content import service as content
from app.modules.debrief import commands, rules
from app.modules.identity.schemas import AccountRole
from app.modules.messaging import delivery
from app.modules.ops import sweep
from app.modules.progress import service as progress
from app.modules.sessions import service as sessions
from app.platform.db import get_sessionmaker
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_classes import LECTURER, OTHER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import clock, klass
from tests.classes.test_staff import call, put_staff
from tests.classes.test_student_registration import emitted
from tests.debrief.test_debrief import LOCKED, finish, home, open_, refused
from tests.debrief.test_quiz import body, conflict
from tests.games.helpers import play_week
from tests.messaging.helpers import rows
from tests.sessions.test_lock import _empty
from tests.sessions.test_open_games import confirmed
from tests.sessions.test_start_game import start, task_done
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "emitted", "klass"]

ASSISTANT = "assistent-910@x.no"
ADMIN = "admin-910@x.no"


def exclusions() -> list[tuple]:
    return rows("SELECT question_id, quiz_version FROM quiz_exclusions ORDER BY question_id")


def audits() -> list[tuple]:
    return rows(
        "SELECT target_ids, change FROM audit_events "
        "WHERE action = 'debrief_quiz.exclusions_changed' ORDER BY occurred_at, id"
    )


def notices() -> list[tuple]:
    return rows(
        "SELECT user_id, ref::text FROM notices WHERE kind = 'quiz_changed' ORDER BY created_at"
    )


async def exclude(session_id: str, ids: list[str], who: str = LECTURER):
    return await call(
        who,
        "PUT",
        f"/api/class-sessions/{session_id}/debrief-quiz/exclusions",
        json={"excluded": ids},
    )


async def mail_context(user_id, class_session_id):
    async with get_sessionmaker()() as s:
        return await sessions.quiz_changed_mail_context(
            s, user_id, class_session_id, datetime.now(UTC)
        )


def quiz_step(item: dict) -> dict:
    return next(s for s in item["steps"] if s["step"] == "quiz")


async def test_exclusions_change_the_next_attempt_and_staff_see_attempts(klass, emitted):
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
    [(mine, my_name)] = rows("SELECT id, name FROM users WHERE email = %s", me)
    assert (await call(me, "POST", f"{path}/explanation", json={"text": "Min."})).status_code == 201
    for step in (progress.Step.CLASS_GAME, progress.Step.DEBRIEF):
        await progress.record_step(mine, sid, step, datetime.now(UTC))
    _, quiz = await content.debrief_quiz(None)
    ids = [q.id for q in quiz.questions]
    right = dict((q.id, q.answer) for q in quiz.questions)
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")
    await make(ADMIN, roles=(AccountRole.admin,))
    quiz_path = f"/api/class-sessions/{session_id}/debrief-quiz"

    # The staff read the pinned quiz with its answer keys; only an owner may take questions out.
    owner = (await call(LECTURER, "GET", quiz_path)).json()
    assert (owner["version"], owner["pinned"], owner["can_exclude"], owner["open"]) == (
        1,
        True,
        True,
        True,
    )
    assert [(q["id"], q["answer"], q["excluded"]) for q in owner["questions"]] == [
        (q.id, q.answer, False) for q in quiz.questions
    ]
    helper = await call(ASSISTANT, "GET", quiz_path)
    assert helper.status_code == 200 and helper.json() == {**owner, "can_exclude": False}
    for who in (me, ADMIN, OTHER):
        refused(await call(who, "GET", quiz_path), "forbidden")
        refused(await exclude(session_id, [ids[0]], who), "forbidden")
    refused(await exclude(session_id, [ids[0]], ASSISTANT), "forbidden")
    for bad in ("nope", str(uuid.uuid4())):
        refused(await call(LECTURER, "GET", f"/api/class-sessions/{bad}/debrief-quiz"), "forbidden")
        refused(await exclude(bad, [ids[0]]), "forbidden")

    # The Student's last attempt got only the first question wrong.
    wrong = [(ids[0], next(c.id for c in quiz.questions[0].choices if c.id != right[ids[0]]))]
    first = [*wrong, *((q, right[q]) for q in ids[1:])]
    sent = await call(me, "POST", f"{path}/quiz/attempts", json=body(first))
    assert sent.status_code == 201 and not sent.json()["passed"]

    # Refused changes store nothing.
    unknown = await exclude(session_id, ["ukjent"])
    assert unknown.status_code == 422
    assert unknown.json()["error"]["fields"] == {"excluded": "unknown_question"}
    conflict(await exclude(session_id, ids), "last_question")
    late = sessions.lock_for_quiz_exclusions

    async def past(s, class_session_id):
        pins, _ = await late(s, class_session_id)
        return pins, datetime(2000, 1, 1, tzinfo=UTC)

    with patch("app.modules.debrief.commands.sessions.lock_for_quiz_exclusions", past):
        conflict(await exclude(session_id, [ids[0]]), "test_deadline_passed")
    assert (exclusions(), audits(), notices()) == ([], [], [])

    # Taking the first question out: a Class session row, one audit row, the staff's `session`
    # and the Student's notice; not passed, and Hjem says the quiz has changed.
    emitted.clear()
    saved = await exclude(session_id, [ids[0]])
    assert saved.status_code == 200
    assert [q["excluded"] for q in saved.json()["questions"]] == [True, False, False]
    assert exclusions() == [(ids[0], 1)]
    assert audits() == [
        (
            {"class_session_id": session_id},
            {"excluded": [ids[0]], "lifted": [], "quiz_version": 1},
        )
    ]
    assert notices() == [(mine, session_id)]
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["debrief.set_quiz_exclusions"]
    assert ("session", session_id) in emitted and ("user", str(mine)) in emitted
    assert not await progress.has_step(mine, sid, progress.Step.QUIZ_PASSED)
    item = await home(me)
    assert quiz_step(item) == {
        "step": "quiz",
        "state": "current",
        "held": False,
        "quiz_changed": True,
        "group_open": False,
        "closed": False,
        "counts": None,
        "after_makeup": False,
        "corrected": False,
    }
    # The same set again changes nothing and tells nobody again.
    assert (await exclude(session_id, [ids[0]])).status_code == 200
    assert (len(audits()), len(notices())) == (1, 1)
    # The digest names the change while it still holds for the Student.
    assert await mail_context(mine, sid) is not None
    # A lift ends «quizen er endret» and the Student's pages read again; taken out once more,
    # they are told again.
    emitted.clear()
    assert (await exclude(session_id, [])).status_code == 200
    assert ("user", str(mine)) in emitted
    assert quiz_step(await home(me))["quiz_changed"] is False
    assert await mail_context(mine, sid) is None
    assert (await exclude(session_id, [ids[0]])).status_code == 200
    assert (len(audits()), len(notices())) == (3, 2)

    # The next attempt asks only the rest; a stale form's answer to the excluded question is left
    # out, and every remaining answer right passes.
    shown = (await call(me, "GET", f"{path}/quiz")).json()
    assert sorted(q["id"] for q in shown["questions"]) == sorted(ids[1:])
    stale = [(ids[0], wrong[0][1]), *((q["id"], right[q["id"]]) for q in shown["questions"])]
    passed = await call(me, "POST", f"{path}/quiz/attempts", json=body(stale))
    assert passed.status_code == 201
    assert (passed.json()["passed"], passed.json()["asked"]) == (True, len(ids) - 1)
    [(stored,)] = rows("SELECT answers FROM quiz_attempts WHERE number = 2")
    assert ids[0] not in [a["question_id"] for a in stored]
    assert quiz_step(await home(me))["state"] == "done"

    # Lifting it later: the Student stays passed, and nobody is told.
    lifted = await exclude(session_id, [])
    assert [q["excluded"] for q in lifted.json()["questions"]] == [False, False, False]
    assert exclusions() == [] and len(notices()) == 2
    assert await mail_context(mine, sid) is None
    assert audits()[-1][1] == {"excluded": [], "lifted": [ids[0]], "quiz_version": 1}
    assert await progress.has_step(mine, sid, progress.Step.QUIZ_PASSED)
    assert (await call(me, "GET", f"{path}/quiz")).json()["questions"] == []

    # The staff's Debrief summary names the Student and lists every attempt with its time.
    attempts = rows(
        "SELECT number, submitted_at, passed FROM quiz_attempts WHERE user_id = %s ORDER BY number",
        mine,
    )
    summary_path = f"/api/class-sessions/{session_id}/students/{mine}/debrief-summary"
    for who in (LECTURER, ASSISTANT):
        read = (await call(who, "GET", summary_path)).json()
        assert read["name"] == my_name and my_name
        assert read["quiz"]["passed_at"] == read["quiz"]["attempts"][-1]["submitted_at"]
        assert [(a["number"], a["passed"]) for a in read["quiz"]["attempts"]] == [
            (n, p) for n, _, p in attempts
        ]
        assert [datetime.fromisoformat(a["submitted_at"]) for a in read["quiz"]["attempts"]] == [
            at for _, at, _ in attempts
        ]
    # A Student with no attempt yet; a Student no longer on the Roster has no name.
    mate = (await call(LECTURER, "GET", summary_path.replace(str(mine), str(seated[1])))).json()
    assert mate["quiz"] == {"attempts": [], "passed_at": None}
    assert await sessions.student_name(sid, uuid.uuid4()) is None

    # An archived Class takes no change.
    execute("UPDATE classes SET archived_at = now() WHERE id = %s", uuid.UUID(klass))
    conflict(await exclude(session_id, [ids[0]]), "class_archived")
    assert (await call(LECTURER, "GET", quiz_path)).json()["can_exclude"] is False
    assert exclusions() == []


def test_stegene_says_the_quiz_changed_only_on_the_current_quiz_step():
    done = {progress.Step.CLASS_GAME, progress.Step.DEBRIEF}
    steps = sessions.stegene(True, done, quiz_changed=True)
    assert [(s.step, s.state, s.quiz_changed) for s in steps[1:4]] == [
        ("debrief", "done", False),
        ("quiz", "current", True),
        ("replay", "locked", False),
    ]
    assert not any(s.quiz_changed for s in sessions.stegene(True, done))


def test_the_quiz_changed_notice_is_a_digest_kind_and_the_rule_is_registered():
    assert delivery.QUIZ_CHANGED_KIND == commands.QUIZ_CHANGED_NOTICE
    assert delivery.KINDS[commands.QUIZ_CHANGED_NOTICE].mode == delivery.DIGEST
    assert sessions._quiz_changed == [rules.quiz_changed]


async def test_an_attempt_never_asks_nothing():
    from app.modules.debrief import service

    _, quiz = await content.debrief_quiz(None)
    ids = [q.id for q in quiz.questions]
    assert service._asked(quiz, {ids[0]}) == ids[1:]
    # Rows taken out of another version that cover every question here: all are asked.
    assert service._asked(quiz, set(ids)) == ids
