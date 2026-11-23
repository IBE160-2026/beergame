"""Story 13.2 at the api (FR-63, FR-17, FR-5, AD-12, AD-16): the Studentside's record,
`GET /api/class-sessions/{id}/students/{user_id}/record`.

One short Class game (6 Weeks, 1 Guided Week) per test, as in `test_completion_status.py`."""

import uuid

from app.modules.identity.schemas import AccountRole
from app.modules.reports import service as reports
from app.modules.sessions import service as sessions
from app.platform.db import get_sessionmaker
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_staff import ASSISTANT, call, put_staff
from tests.reports.test_completion_status import (
    WEEKS,
    every_later_step,
    explanation,
    obligatory,
)
from tests.sessions.test_allocation import students
from tests.sessions.test_dates import OUTSIDER
from tests.sessions.test_game_end import _empty, clock, klass, play_weeks, short_game
from tests.sessions.test_lock import dated
from tests.sessions.test_open_games import confirmed
from tests.sessions.test_orders import code
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "klass"]

ADMIN = "admin-uten-klasse@x.no"
OTHER_LECTURER = "annen-faglaerer@x.no"


def record_path(session_id: str, student: object) -> str:
    return f"/api/class-sessions/{session_id}/students/{student}/record"


async def record(who: str, session_id: str, student: object):
    return await call(who, "GET", record_path(session_id, student))


def keys(value: object) -> set[str]:
    """Every key anywhere in a JSON value."""
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in keys(v)}
    if isinstance(value, list):
        return {k for v in value for k in keys(v)}
    return set()


async def test_the_staff_of_the_class_read_one_students_record(klass):
    session_id, game_id, seated = await short_game(klass)
    obligatory(session_id)
    await play_weeks(game_id, WEEKS)
    me = seated[0]
    await every_later_step(me, session_id)
    explanation(me, session_id, game_id, "Jeg bestilte for mye fordi jeg så bare min egen kunde.")

    found = await record(LECTURER, session_id, me)
    assert found.status_code == 200
    assert found.headers["cache-control"] == "no-store"
    body = found.json()
    assert body["can_manage"] is True
    assert body["session_number"] == 1 and "report" not in body  # Story 13.12: its own endpoint
    # Every Completion value comes from the one assembler (Story 13.1).
    status = await reports.completion_status(me, uuid.UUID(session_id))
    completion = body["completion"]
    assert (completion["obligatory"], completion["requirement_met"]) == (True, True)
    assert (completion["ordered_share"], completion["playout_share"]) == (100, 0)
    assert (completion["required_share"], completion["adjusted"]) == (80, False)
    assert [(s["step"], s["recorded"], s["done"]) for s in completion["steps"]] == [
        (s.step, s.recorded, s.done) for s in status.steps
    ]
    # The game, its link target and where it stands.
    assert body["game"]["game_id"] == game_id
    assert (body["game"]["state"], body["game"]["played_out"]) == ("finished", False)
    assert body["game"]["finished_at"] is not None
    # Participation: information only. `play_weeks` orders 4 + Week, so never constant.
    signals = body["participation"]
    assert signals["own_orders"] >= WEEKS - 1 and signals["seconds"] >= 0
    assert signals["constant"] is False
    # The Explanation as written; no summary, quiz, Replay Game or test attempt in this fixture.
    assert body["debrief"]["explanation"].startswith("Jeg bestilte for mye")
    assert (body["debrief"]["finished_at"], body["debrief"]["moments"]) == (None, 0)
    assert (body["quiz"], body["replay"], body["test"]) == ([], None, None)
    # Story 12.5's «KI-vurdering» as the staff read it: no test attempt, so nothing to assess.
    assert body["assessment"]["state"] == "no_test"
    assert body["assessment"]["items"] == [] and body["assessment"]["letter"] is None
    # Only the staff's own letter read (Story 12.6: shown to everyone, else null); never the
    # Student's own choice.
    assert [key for key in keys(body) if "letter" in key] == ["letter"]
    assert not any("chosen" in key for key in keys(body))

    # An Assistant lecturer reads the same record, without the Lecturer-only blocks.
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")
    assisted = await record(ASSISTANT, session_id, me)
    assert assisted.status_code == 200
    assert assisted.json()["can_manage"] is False
    assert assisted.json()["completion"] == completion
    # Story 12.5: the Studentside answers an Assistant lecturer too, without the owners' blocks.
    page = await call(ASSISTANT, "GET", f"/api/class-sessions/{session_id}/students/{me}")
    assert page.status_code == 200
    assert (page.json()["can_manage"], page.json()["deadlines"]) == (False, None)


async def test_anyone_else_is_refused_the_same_whether_or_not_the_student_exists(klass):
    session_id, _, seated = await short_game(klass)
    me = seated[0]
    await make(OTHER_LECTURER)
    await make(ADMIN, roles=(AccountRole.admin,))
    await make(OUTSIDER, roles=())
    refusals = [
        await record(OTHER_LECTURER, session_id, me),
        await record(ADMIN, session_id, me),  # an Admin not attached to the Class
        await record(OUTSIDER, session_id, me),
        await record(email(1), session_id, me),  # another Student of the Class
        await record(email(0), session_id, me),  # the Student themselves
        await record(LECTURER, session_id, uuid.uuid7()),  # no such Student
        await record(LECTURER, session_id, "not-an-id"),
        await record(LECTURER, str(uuid.uuid7()), me),  # no such Class session
    ]
    bodies = {(r.status_code, r.text) for r in refusals}
    assert len(bodies) == 1 and code(refusals[0]) == (403, "forbidden")


async def test_a_session_that_is_not_obligatory_and_an_ai_switch_that_is_off(klass):
    session_id, game_id, seated = await short_game(klass)
    await play_weeks(game_id, 2)
    execute(
        "INSERT INTO assessment_switches (class_session_id, enabled) VALUES (%s, false)",
        session_id,
    )
    body = (await record(LECTURER, session_id, seated[0])).json()
    completion = body["completion"]
    assert (completion["obligatory"], completion["requirement_met"]) == (False, None)
    assert body["game"]["state"] == "running"
    assert all(not step["done"] for step in completion["steps"])
    # No test attempt: the staff view reads `no_test` before the switch (Story 12.5).
    assert body["assessment"]["state"] == "no_test"


async def test_an_adjusted_share_is_the_students_own(klass):
    session_id, game_id, seated = await short_game(klass)
    obligatory(session_id)
    me = seated[0]
    saved = await call(
        LECTURER,
        "PUT",
        f"/api/class-sessions/{session_id}/students/{me}/adjustment",
        json={"time_factor": 1, "share_percent": 60},
    )
    assert saved.status_code == 200
    async with get_sessionmaker()() as s:
        assert (await sessions.get_adjustment(s, uuid.UUID(session_id), me)).share_percent == 60
    completion = (await record(LECTURER, session_id, me)).json()["completion"]
    assert (completion["required_share"], completion["adjusted"]) == (60, True)


async def test_the_roster_names_each_registered_student_for_the_studentside_link(klass):
    _, _, seated = await short_game(klass)
    items = (await call(LECTURER, "GET", f"/api/classes/{klass}/registrations")).json()["items"]
    by_email = {item["email"]: item["user_id"] for item in items}
    assert {by_email[email(0)], by_email[email(1)]} == {str(user) for user in seated}
    execute("UPDATE roster_entries SET registration = 'invited' WHERE email = %s", email(1))
    items = (await call(LECTURER, "GET", f"/api/classes/{klass}/registrations")).json()["items"]
    assert {item["email"]: item["user_id"] for item in items}[email(1)] is None


async def test_before_the_lock_there_is_no_game_and_nothing_is_done(klass):
    seated = await students(klass, 2)
    session_id = await dated(klass, "rule_based")
    obligatory(session_id)
    body = (await record(LECTURER, session_id, seated[0])).json()
    assert (body["game"], body["participation"], body["replay"], body["test"]) == (
        None,
        None,
        None,
        None,
    )
    completion = body["completion"]
    assert (completion["requirement_met"], completion["ordered_share"]) == (False, None)
    assert [step["done"] for step in completion["steps"]] == [False] * 5


async def test_an_allocated_game_before_the_lock_is_not_ready_and_has_no_participation(klass):
    session_id, seated = await confirmed(klass, 2)
    body = (await record(LECTURER, session_id, seated[0])).json()
    assert body["game"]["state"] == "not_ready"
    assert body["participation"] is None
