"""Story 13.3 at the api (FR-17, FR-3, FR-5, AD-8, AD-12, AD-15, AD-16): «Lagre retting»,
`POST /api/class-sessions/{id}/students/{user_id}/corrections`.

The correction and Hjem run on one short Class game, as in `test_completion_status.py`; the
refusals need no game, only a dated Class session with registered Students."""

import json
import uuid
from typing import get_args

import psycopg
import pytest

from app.analysis.completion import COMPLETION_STEPS
from app.modules.identity.schemas import AccountRole
from app.modules.progress import service as progress
from app.modules.progress.models import CORRECTABLE_STEPS
from app.modules.reports import service as reports
from app.modules.reports.schemas import CompletionStepName
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_staff import ASSISTANT, call, put_staff
from tests.classes.test_student_registration import emitted
from tests.messaging.helpers import rows
from tests.reports.test_completion_status import counts, every_later_step, obligatory
from tests.reports.test_studentside import ADMIN, OTHER_LECTURER, record
from tests.sessions.test_allocation import students
from tests.sessions.test_dates import OUTSIDER
from tests.sessions.test_game_end import _empty, clock, klass, short_game
from tests.sessions.test_lock import dated
from tests.sessions.test_orders import code
from tests.sessions.test_student_choice import email
from tests.sessions.test_student_home import home

__all__ = ["_empty", "clock", "emitted", "klass"]

REASON = "Holdt følge, men gruppen spilte sakte og utspillingen tok de siste ukene."


def corrections_path(session_id: str, student: object) -> str:
    return f"/api/class-sessions/{session_id}/students/{student}/corrections"


async def correct(who: str, session_id: str, student: object, step: str, done: bool, reason: str):
    return await call(
        who,
        "POST",
        corrections_path(session_id, student),
        json={"step": step, "done": done, "reason": reason},
    )


def stored() -> list[tuple]:
    return rows(
        "SELECT user_id, class_session_id, step, done, reason, actor_user_id "
        "FROM completion_corrections ORDER BY at, id"
    )


def audited() -> list[tuple]:
    return rows(
        "SELECT actor_user_id, target_ids, change FROM audit_events "
        "WHERE action = 'completion.corrected' ORDER BY occurred_at, id"
    )


def step_of(body: dict, name: str) -> dict:
    return next(step for step in body["completion"]["steps"] if step["step"] == name)


async def test_a_lecturer_corrects_a_step_and_the_latest_correction_applies(klass, emitted):
    session_id, _, seated = await short_game(klass)
    sid = uuid.UUID(session_id)
    obligatory(session_id)
    me = seated[0]
    await every_later_step(me, session_id)
    # The Debrief is recorded, but with no Explanation it does not count; the Replay counts.
    before = (await record(LECTURER, session_id, me)).json()
    assert before["can_correct"] is True
    assert (step_of(before, "debrief")["done"], step_of(before, "debrief")["correction"]) == (
        False,
        None,
    )
    funnel_before = await reports.funnel(sid)
    steps_before = rows("SELECT step, at FROM progress_steps WHERE user_id = %s ORDER BY step", me)
    seat_weeks_before = rows("SELECT count(*), max(id::text) FROM seat_weeks")
    emitted.clear()

    saved = await correct(LECTURER, session_id, me, "debrief", True, f"  {REASON}  ")
    assert saved.status_code == 200
    assert saved.headers["cache-control"] == "no-store"
    debrief = step_of(saved.json(), "debrief")
    assert (debrief["done"], debrief["corrected"], debrief["recorded"]) == (True, True, True)
    assert debrief["correction"]["reason"] == REASON  # trimmed
    assert (debrief["correction"]["done"], debrief["correction"]["by"]) == (True, "Bard")
    lecturer_id = rows("SELECT id FROM users WHERE email = %s", LECTURER)[0][0]
    assert stored() == [(me, sid, "debrief", True, REASON, lecturer_id)]
    [(actor, target, change)] = audited()
    assert actor == lecturer_id
    assert target == {
        "class_session_id": session_id,
        "user_id": str(me),
        "correction_id": target["correction_id"],
    }
    assert change == {"step": "debrief", "done": True, "was_done": False}
    assert REASON not in json.dumps(change)
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["reports.correct_completion"]
    assert set(emitted) == {("user", str(me)), ("session", session_id)}

    # The Student's Hjem: the step counts and is marked corrected; never the reason.
    item = await home(email(0))
    assert counts(item)["debrief"] is True
    assert {s["step"]: s["corrected"] for s in item["steps"]}["debrief"] is True
    assert {s["step"]: s["corrected"] for s in item["steps"]}["quiz"] is False
    assert "Holdt følge" not in json.dumps(item)

    # A correction on a step with no step event changes Completion only: no gate, no funnel.
    progress_replay = await progress.has_step(me, sid, "replay")
    assert (await correct(LECTURER, session_id, me, "class_game", True, "Utspillingen.")).is_success
    assert rows("SELECT step, at FROM progress_steps WHERE user_id = %s ORDER BY step", me) == (
        steps_before
    )
    assert await progress.has_step(me, sid, "replay") is progress_replay
    assert await reports.funnel(sid) == funnel_before
    assert rows("SELECT count(*), max(id::text) FROM seat_weeks") == seat_weeks_before

    # A later correction of the same step is a new row; the latest applies; the audit keeps all.
    again = await correct(LECTURER, session_id, me, "debrief", False, "Forklaringen mangler.")
    debrief = step_of(again.json(), "debrief")
    assert (debrief["done"], debrief["correction"]["reason"]) == (False, "Forklaringen mangler.")
    assert [row[2:4] for row in stored()] == [
        ("debrief", True),
        ("class_game", True),
        ("debrief", False),
    ]
    assert [row[2]["was_done"] for row in audited()] == [False, False, True]
    status = await reports.completion_status(me, sid)
    assert (status.step("debrief").done, status.step("debrief").corrected) == (False, True)
    assert status.step("class_game").done is True
    assert counts(await home(email(0)))["debrief"] is False

    # An Assistant lecturer reads the correction and its reason, but may not correct.
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")
    assisted = (await record(ASSISTANT, session_id, me)).json()
    assert assisted["can_correct"] is False
    assert step_of(assisted, "debrief")["correction"]["reason"] == "Forklaringen mangler."

    # Stored once and never changed, except the actor's key set to NULL when that User is deleted:
    # the record then names nobody.
    with pytest.raises(psycopg.errors.RestrictViolation):
        execute("UPDATE completion_corrections SET reason = 'endret'")
    with pytest.raises(psycopg.errors.RestrictViolation):
        execute("UPDATE completion_corrections SET actor_user_id = NULL, done = NOT done")
    execute("UPDATE completion_corrections SET actor_user_id = NULL")
    gone = step_of((await record(LECTURER, session_id, me)).json(), "debrief")
    assert (gone["correction"]["by"], gone["correction"]["reason"]) == (
        None,
        "Forklaringen mangler.",
    )

    # The longest reason is 1000 characters after trimming.
    longest = await correct(LECTURER, session_id, me, "replay", True, f" {'x' * 1000} ")
    assert longest.status_code == 200


async def test_corrections_are_refused_and_write_nothing(klass):
    session_id = await dated(klass)
    me, _ = await students(klass, 2)
    await make(OTHER_LECTURER)
    await make(ADMIN, roles=(AccountRole.admin,))
    await make(OUTSIDER, roles=())
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")

    # Not obligatory: no requirement to correct, and the page offers no correction.
    assert (await record(LECTURER, session_id, me)).json()["can_correct"] is False
    assert code(await correct(LECTURER, session_id, me, "replay", True, REASON)) == (
        409,
        "not_obligatory",
    )
    obligatory(session_id)
    assert (await record(LECTURER, session_id, me)).json()["can_correct"] is True

    # An empty or a too long reason.
    for reason, why in (("", "required"), ("   \n ", "required"), ("x" * 1001, "too_long")):
        refused = await correct(LECTURER, session_id, me, "replay", True, reason)
        assert code(refused) == (422, "invalid_correction")
        assert refused.json()["error"]["fields"] == {"reason": why}
    # A step outside the requirement and a status that is not a boolean.
    assert (await correct(LECTURER, session_id, me, "explanation", True, REASON)).status_code == 422
    assert (await correct(LECTURER, session_id, me, "replay", "yes", REASON)).status_code == 422

    # Anyone but a Lecturer of the Class: one answer, whether or not the Student exists.
    refusals = [
        await correct(ASSISTANT, session_id, me, "replay", True, REASON),
        await correct(OTHER_LECTURER, session_id, me, "replay", True, REASON),
        await correct(ADMIN, session_id, me, "replay", True, REASON),
        await correct(OUTSIDER, session_id, me, "replay", True, REASON),
        await correct("s1@x.no", session_id, me, "replay", True, REASON),  # another Student
        await correct(LECTURER, session_id, uuid.uuid7(), "replay", True, REASON),
        await correct(LECTURER, session_id, "not-an-id", "replay", True, REASON),
        await correct(LECTURER, str(uuid.uuid7()), me, "replay", True, REASON),
    ]
    bodies = {(r.status_code, r.text) for r in refusals}
    assert len(bodies) == 1 and code(refusals[0]) == (403, "forbidden")

    # An archived Class takes no correction.
    execute("UPDATE classes SET archived_at = now() WHERE id = %s", klass)
    assert (await record(LECTURER, session_id, me)).json()["can_correct"] is False
    assert code(await correct(LECTURER, session_id, me, "replay", True, REASON)) == (
        409,
        "class_archived",
    )
    assert stored() == [] and audited() == []


async def test_deleting_the_users_rows_passes_the_append_only_trigger(klass):
    """User erasure (Story 15.2) deletes the users row: the corrector's key goes to NULL through
    the trigger's one allowed change, and the Student's corrections go with the Student."""
    session_id = await dated(klass)
    me, _ = await students(klass, 2)
    obligatory(session_id)
    co_owner = await make("medeier@x.no")
    put_staff(klass, co_owner, "owner")
    assert (await correct("medeier@x.no", session_id, me, "replay", True, REASON)).is_success

    execute("DELETE FROM users WHERE id = %s", co_owner)
    assert [row[5] for row in stored()] == [None]
    execute("DELETE FROM users WHERE id = %s", me)
    assert stored() == []


def test_the_correctable_steps_are_the_steps_of_the_requirement():
    """One list, kept by hand in three places: the table's, the api's and Completion's."""
    assert tuple(CORRECTABLE_STEPS) == COMPLETION_STEPS
    assert get_args(CompletionStepName) == COMPLETION_STEPS
