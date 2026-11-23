"""Flag feedback, and read assessments as staff (Story 12.5, FR-55, FR-5, AD-12).

A Student marks a piece of written feedback as wrong («Marker som feil») and takes it back
(«Angre») at `PUT`/`DELETE …/test/assessment/items/{item_id}/flag`; the staff of the Class (its
owners and Assistant lecturers) read the Student's assessment with those flags on the Studentside
(`GET /api/class-sessions/{id}/students/{user_id}/assessment`) and each Student's state and flag
count on the Klasseøkt (`GET /api/class-sessions/{id}/assessments`). On the mock provider."""

import uuid
from types import SimpleNamespace

from app.ai import seed
from app.modules.assessment import service as assessment
from app.modules.identity.schemas import AccountRole
from app.modules.sessions import service as sessions
from app.modules.tests import assessed
from app.platform.db import get_sessionmaker
from app.platform.events.registry import COMMAND_TOPICS
from tests.assessment.test_assess import (
    HOUR,
    LONG,
    answer_all,
    assessment_url,
    attempt_id_of,
    closed,
    stored_facts,
)
from tests.classes.test_classes import LECTURER, OTHER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import clock, klass
from tests.classes.test_staff import call, put_staff
from tests.classes.test_student_registration import emitted
from tests.debrief.test_explanation import user_id
from tests.individual_test.test_adapted import locked_with, stand_in
from tests.individual_test.test_open import path
from tests.messaging.helpers import rows
from tests.sessions.test_dates import TEST, at
from tests.sessions.test_lock import _empty
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "emitted", "klass"]

ASSISTANT = "assistent-125@x.no"
ADMIN = "admin-125@x.no"
ITEM = LONG[0]


def flag_url(session_id: str, item_id: str = ITEM) -> str:
    return f"{assessment_url(session_id)}/items/{item_id}/flag"


def staff_url(session_id: str, student: str = email(0)) -> str:
    return f"/api/class-sessions/{session_id}/students/{user_id(student)}/assessment"


def list_url(session_id: str) -> str:
    return f"/api/class-sessions/{session_id}/assessments"


def item_of(body: dict, item_id: str = ITEM) -> dict:
    return next(item for item in body["items"] if item["id"] == item_id)


def flags() -> list[tuple]:
    return rows("SELECT item_id FROM ai_feedback_flags ORDER BY item_id")


async def ready(klass: str, monkeypatch, n: int = 1) -> str:
    """A Class session of `n` Students whose first Student's assessment is ready, with feedback on
    every AI item; the others opened no test. The clock stands an hour after the Test deadline."""
    await seed.ensure_zero_config()
    sets = stand_in(monkeypatch, own=range(1, 13))
    stored_facts(monkeypatch, sets)
    session_id, _ = await locked_with(klass, 30, n=n)
    opened = await call(email(0), "POST", path(session_id))
    assert opened.status_code == 201, opened.text
    await answer_all(session_id, opened.json())
    await closed(session_id)
    assert await assessment.assess(attempt_id_of(session_id)) == "ready"
    at(monkeypatch, TEST + HOUR)
    return session_id


async def admin() -> None:
    """An Admin with no staff role in the Class."""
    await make(ADMIN, roles=(AccountRole.admin,))


async def test_flag_and_undo_are_stored_at_once_and_idempotent(klass, monkeypatch, emitted):
    session_id = await ready(klass, monkeypatch)
    student = str(user_id(email(0)))
    emitted.clear()
    flagged = await call(email(0), "PUT", flag_url(session_id))
    assert flagged.status_code == 200, flagged.text
    assert item_of(flagged.json())["ai"]["flagged"] is True
    assert flags() == [(ITEM,)]
    # Its own view keeps it, and every other item stays unflagged.
    body = (await call(email(0), "GET", assessment_url(session_id))).json()
    assert [i["id"] for i in body["items"] if i["ai"] and i["ai"]["flagged"]] == [ITEM]
    # The Student's other tabs and the Class's staff read it again (AD-8).
    assert set(emitted) == {("user", student), ("session", session_id)}
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["assessment.set_flag"]

    # A repeat stores nothing more and emits nothing.
    emitted.clear()
    again = await call(email(0), "PUT", flag_url(session_id))
    assert again.status_code == 200 and item_of(again.json())["ai"]["flagged"] is True
    assert flags() == [(ITEM,)] and emitted == []

    # «Angre» removes it and tells the same readers; a repeat is the same answer and emits nothing.
    for repeat in range(2):
        emitted.clear()
        undone = await call(email(0), "DELETE", flag_url(session_id))
        assert undone.status_code == 200 and item_of(undone.json())["ai"]["flagged"] is False
        assert flags() == []
        assert set(emitted) == (set() if repeat else {("user", student), ("session", session_id)})


async def test_only_feedback_the_view_shows_can_be_flagged(klass, monkeypatch):
    session_id = await ready(klass, monkeypatch)
    body = (await call(email(0), "GET", assessment_url(session_id))).json()
    computed = next(item["id"] for item in body["items"] if item["ai"] is None)
    # A dropped feedback: the score stands, the note is shown, nothing to flag.
    execute(
        "UPDATE ai_item_scores SET feedback = NULL, feedback_note = 'dropped' WHERE item_id = %s",
        LONG[1],
    )
    for item_id in (computed, LONG[1], "no-such-item"):
        refused = await call(email(0), "PUT", flag_url(session_id, item_id))
        assert refused.status_code == 409, item_id
        assert refused.json()["error"]["code"] == "feedback_not_flaggable"
        undo = await call(email(0), "DELETE", flag_url(session_id, item_id))
        # «Angre» needs only a stored score: on the dropped one it removes nothing.
        assert undo.status_code == (200 if item_id == LONG[1] else 409), item_id
    assert flags() == []
    # A stopped, not ready assessment shows no items: nothing to flag either; but «Angre» still
    # takes back a flag set before the stop.
    assert (await call(email(0), "PUT", flag_url(session_id))).status_code == 200
    execute("UPDATE ai_assessments SET status = 'incomplete'")
    await assessment.stop_for_session(uuid.UUID(session_id), None, now=TEST + HOUR)
    stopped = await call(email(0), "PUT", flag_url(session_id, LONG[0]))
    assert stopped.json()["error"]["code"] == "feedback_not_flaggable"
    undone = await call(email(0), "DELETE", flag_url(session_id))
    assert undone.status_code == 200 and undone.json()["state"] == "switched_off"
    assert flags() == []


async def test_only_the_student_flags_their_own(klass, monkeypatch):
    session_id = await ready(klass, monkeypatch, n=2)
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")
    await admin()
    for who in (LECTURER, ASSISTANT, ADMIN, OTHER):
        refused = await call(who, "PUT", flag_url(session_id))
        assert refused.status_code == 403, who
        assert refused.json()["error"]["code"] == "forbidden"
    # The route is the caller's own: the other Student reaches only their own, which they lack.
    mine = await call(email(1), "PUT", flag_url(session_id))
    assert mine.json()["error"]["code"] == "feedback_not_flaggable"
    unknown = await call(email(0), "PUT", flag_url(str(uuid.uuid7())))
    assert unknown.status_code == 403
    assert flags() == []


async def test_the_staff_read_the_students_view_with_its_flags(klass, monkeypatch):
    session_id = await ready(klass, monkeypatch, n=2)
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")
    await admin()
    assert (await call(email(0), "PUT", flag_url(session_id))).status_code == 200
    own = (await call(email(0), "GET", assessment_url(session_id))).json()
    for who in (LECTURER, ASSISTANT):
        read = await call(who, "GET", staff_url(session_id))
        assert read.status_code == 200, read.text
        assert read.headers["cache-control"] == "no-store"
        body = read.json()
        # The same scores, feedback, notes and unchecked notice as the Student, and the flag.
        assert {k: v for k, v in body.items() if k != "letter"} == {
            k: v for k, v in own.items() if k != "letter"
        }
        assert item_of(body)["ai"]["flagged"] is True
        # Nothing only the Student sees: exactly these fields. Story 12.6: the staff's own letter
        # (null unless shown to everyone), never the Student's letter block or choice.
        assert set(body) == {
            "state",
            "items",
            "unassessed",
            "total",
            "total_max",
            "checked",
            "letter",
        }
        assert body["letter"] is None
        assert own["letter"] == {"setting": "student_choice", "chosen": False, "value": None}
    # A Student who opened no test reads `no_test` for the staff.
    other = (await call(LECTURER, "GET", staff_url(session_id, email(1)))).json()
    assert other["state"] == "no_test" and other["items"] == []


async def test_the_staff_read_is_refused_to_everyone_else_alike(klass, monkeypatch):
    session_id = await ready(klass, monkeypatch, n=2)
    await admin()
    # The other Student, the Student themselves, an Admin with no staff role, another Class's
    # Lecturer; a User who is no Student of the Class; unknown and malformed ids.
    for who in (email(1), email(0), ADMIN, OTHER):
        refused = await call(who, "GET", staff_url(session_id))
        assert refused.status_code == 403, who
        assert refused.json()["error"]["code"] == "forbidden"
        assert (await call(who, "GET", list_url(session_id))).status_code == 403, who
    stranger = f"/api/class-sessions/{session_id}/students/{user_id(LECTURER)}/assessment"
    assert (await call(LECTURER, "GET", stranger)).status_code == 403
    # A Student removed from the Roster is no Student of the Class now.
    assert (await call(LECTURER, "GET", staff_url(session_id))).status_code == 200
    execute("UPDATE roster_entries SET removed_at = now() WHERE user_id = %s", user_id(email(0)))
    assert (await call(LECTURER, "GET", staff_url(session_id))).status_code == 403
    for bad in (str(uuid.uuid7()), "nope"):
        url = f"/api/class-sessions/{bad}/students/{user_id(email(0))}/assessment"
        assert (await call(LECTURER, "GET", url)).status_code == 403
        assert (await call(LECTURER, "GET", list_url(bad))).status_code == 403


async def test_the_klasseokt_list_names_each_student_with_state_and_flags(klass, monkeypatch):
    session_id = await ready(klass, monkeypatch, n=2)
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")
    for item_id in LONG:
        assert (await call(email(0), "PUT", flag_url(session_id, item_id))).status_code == 200
    for who in (LECTURER, ASSISTANT):
        listed = await call(who, "GET", list_url(session_id))
        assert listed.status_code == 200, listed.text
        by_id = {row["user_id"]: row for row in listed.json()["students"]}
        first, second = by_id[str(user_id(email(0)))], by_id[str(user_id(email(1)))]
        assert (first["state"], first["flags"]) == ("ready", 2) and first["name"]
        assert (second["state"], second["flags"]) == ("no_test", 0)
        names = [row["name"] for row in listed.json()["students"]]
        assert names == sorted(names, key=str.casefold)

    async def first_row() -> tuple[str, int]:
        listed = (await call(LECTURER, "GET", list_url(session_id))).json()["students"]
        row = next(row for row in listed if row["user_id"] == str(user_id(email(0))))
        return row["state"], row["flags"]

    # An incomplete assessment (one item still unscored) lists its flags, as its view shows them.
    execute("UPDATE ai_assessments SET status = 'incomplete'")
    execute("DELETE FROM ai_item_scores WHERE item_id = %s", LONG[1])  # its flag goes with it
    assert await first_row() == ("incomplete", 1)
    # A failed assessment shows no items, so no flags.
    execute("UPDATE ai_assessments SET status = 'failed'")
    assert await first_row() == ("failed", 0)
    # An attempt open again (no closed_at) reads not ready.
    execute("UPDATE ai_assessments SET status = 'incomplete'")
    execute("UPDATE test_attempts SET closed_at = NULL WHERE class_session_id = %s", session_id)
    assert await first_row() == ("not_ready", 0)
    execute("UPDATE test_attempts SET closed_at = now() WHERE class_session_id = %s", session_id)
    # A stop hides a not-ready assessment, as the Student's own view does.
    await assessment.stop_for_session(uuid.UUID(session_id), None, now=TEST + HOUR)
    assert await first_row() == ("switched_off", 0)


async def test_summaries_for_session_counts_flags_per_student(klass, monkeypatch):
    session_id = await ready(klass, monkeypatch)
    assert (await call(email(0), "PUT", flag_url(session_id))).status_code == 200
    async with get_sessionmaker()() as s:
        found = await assessment.summaries_for_session(s, uuid.UUID(session_id))
    [(student, summary)] = found.items()
    assert student == user_id(email(0))
    assert summary == assessment.AssessmentSummary(
        attempt_id=attempt_id_of(session_id), status="ready", runs=1, flags=1
    )
    # A flag goes with its assessment.
    execute("DELETE FROM ai_assessments")
    assert flags() == []


async def test_the_write_itself_refuses_a_flag_the_view_would_not_show(klass, monkeypatch):
    """The check and the write in one transaction: `assessment.set_flag` judges again."""
    session_id = await ready(klass, monkeypatch)
    attempt_id = attempt_id_of(session_id)
    execute("UPDATE ai_assessments SET status = 'incomplete'")
    await assessment.stop_for_session(uuid.UUID(session_id), None, now=TEST + HOUR)
    assert await assessment.set_flag(attempt_id, ITEM, True, now=TEST + HOUR) is False
    assert flags() == []
    # A ready assessment stays flaggable through a stop; dropped feedback never is.
    execute("UPDATE ai_assessments SET status = 'ready'")
    assert await assessment.set_flag(attempt_id, ITEM, True, now=TEST + HOUR) is True
    execute(
        "UPDATE ai_item_scores SET feedback = NULL, feedback_note = 'dropped' WHERE item_id = %s",
        LONG[1],
    )
    assert await assessment.set_flag(attempt_id, LONG[1], True, now=TEST + HOUR) is False
    assert flags() == [(ITEM,)]


def test_an_unmapped_status_reads_as_not_ready():
    on = assessment.Switch(enabled=True, pinned_at=TEST)
    assert assessed._state_of(on, True, "something_new", 1) == "not_ready"
    assert assessed._state_of(on, True, "ready", 1) == "ready"


async def test_an_unknown_action_refuses_the_student_target(klass, monkeypatch):
    session_id = await ready(klass, monkeypatch)
    found = await sessions.student_target(
        SimpleNamespace(id=user_id(LECTURER), roles=("lecturer",)),
        uuid.UUID(session_id),
        user_id(email(0)),
        "no.such_action",
    )
    assert found is None
