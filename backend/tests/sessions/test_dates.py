"""The four dates of a Class session (Story 5.2, FR-18, AD-3, AD-8, AD-12): saved with «Lagre
Klasseøkt» in order and never in the past, the Start-date lock, moving a deadline after the start,
the Student's read with the next deadline, the Lærerhjem's read, and the running number of
Issue #98. The api's clock is fixed (2026-11-19 09:00 UTC) and moved by hand; the database clock
is never read."""

import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.modules.sessions import service
from app.platform import auth
from app.platform.config import get_settings
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_staff import ASSISTANT, call, put_staff
from tests.classes.test_student_registration import emitted, second_class
from tests.messaging.helpers import rows

__all__ = ["clock", "emitted", "klass"]

STUDENT = "student@x.no"
OUTSIDER = "utenfor@x.no"
DAY = timedelta(days=1)
START = NOW + 5 * DAY
PLAY = NOW + 19 * DAY
DEBRIEF = NOW + 22 * DAY
TEST = NOW + 29 * DAY
PLAN = {
    "start_at": START,
    "play_deadline": PLAY,
    "debrief_deadline": DEBRIEF,
    "test_deadline": TEST,
}


@pytest.fixture(autouse=True)
def _empty_ai(ai_db):
    """No model config: the sessions are Rule-based, which the dates do not care about."""


def iso(plan: dict) -> dict:
    return {name: value.isoformat() if value else None for name, value in plan.items()}


async def new_session(class_id: str) -> str:
    response = await call(LECTURER, "POST", f"/api/classes/{class_id}/class-sessions")
    assert response.status_code == 201
    return response.json()["id"]


async def save(session_id: str, plan: dict | None, ai_mode: str = "rule_based", email=LECTURER):
    body: dict = {"ai_mode": ai_mode}
    if plan is not None:
        body["dates"] = iso(plan)
    return await call(email, "PUT", f"/api/class-sessions/{session_id}", json=body)


def stored_dates(session_id: str) -> tuple:
    return rows(
        "SELECT start_at, play_deadline, debrief_deadline, test_deadline FROM class_sessions "
        "WHERE id = %s",
        session_id,
    )[0]


def at(monkeypatch, when: datetime) -> None:
    monkeypatch.setattr(auth, "utcnow", lambda: when)


async def student_of(class_id: str, email: str = STUDENT) -> uuid.UUID:
    user_id = await make(email, roles=())
    execute(
        "INSERT INTO roster_entries (id, class_id, email, user_id, registration, added_at) "
        "VALUES (gen_random_uuid(), %s, %s, %s, 'registered', %s)",
        class_id,
        email,
        user_id,
        NOW,
    )
    return user_id


def refusal(response) -> tuple:
    error = response.json()["error"]
    return response.status_code, error["code"], error["fields"]


async def test_four_dates_are_stored_in_utc_and_each_registered_student_is_told(klass, emitted):
    student = await student_of(klass)
    session_id = await new_session(klass)
    emitted.clear()
    # Sent with the Europe/Oslo offset; stored and answered in UTC.
    oslo = {name: value.astimezone(ZoneInfo("Europe/Oslo")) for name, value in PLAN.items()}
    assert iso(oslo)["start_at"] == "2026-11-24T10:00:00+01:00"
    response = await save(session_id, oslo)
    assert response.status_code == 200
    body = response.json()
    assert stored_dates(session_id) == (START, PLAY, DEBRIEF, TEST)
    assert datetime.fromisoformat(body["start_at"]) == START
    assert datetime.fromisoformat(body["start_at"]).utcoffset() == timedelta(0)
    assert (body["locked"], body["passed_dates"], body["play_time_warning"]) == (False, [], False)
    assert emitted == [("session", session_id), ("user", str(student))]
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["sessions.save"]


async def test_a_save_without_dates_leaves_them_and_tells_no_student(klass, emitted):
    await student_of(klass)
    session_id = await new_session(klass)
    assert (await save(session_id, PLAN)).status_code == 200
    emitted.clear()
    assert (await save(session_id, None)).status_code == 200
    assert stored_dates(session_id) == (START, PLAY, DEBRIEF, TEST)
    assert emitted == [("session", session_id)]
    # The same dates again change nothing either.
    emitted.clear()
    assert (await save(session_id, PLAN)).status_code == 200
    assert emitted == [("session", session_id)]


async def test_a_plan_with_gaps_is_kept_in_order(klass):
    session_id = await new_session(klass)
    plan = {**PLAN, "play_deadline": None, "test_deadline": None}
    assert (await save(session_id, plan)).status_code == 200
    assert stored_dates(session_id) == (START, None, DEBRIEF, None)
    refused = await save(session_id, {**plan, "debrief_deadline": START})
    assert refusal(refused) == (422, "invalid_dates", {"debrief_deadline": "order"})


async def test_dates_out_of_order_name_the_date_that_breaks_it_and_store_nothing(klass, emitted):
    session_id = await new_session(klass)
    emitted.clear()
    refused = await save(session_id, {**PLAN, "play_deadline": START - DAY})
    assert refusal(refused) == (422, "invalid_dates", {"play_deadline": "order"})
    refused = await save(session_id, {**PLAN, "test_deadline": DEBRIEF})
    assert refusal(refused) == (422, "invalid_dates", {"test_deadline": "order"})
    assert stored_dates(session_id) == (None, None, None, None)
    assert emitted == []


async def test_a_new_date_in_the_past_is_refused(klass):
    session_id = await new_session(klass)
    refused = await save(session_id, {**PLAN, "start_at": NOW - DAY})
    assert refusal(refused) == (422, "invalid_dates", {"start_at": "past"})
    refused = await save(session_id, {**PLAN, "start_at": NOW})
    assert refusal(refused) == (422, "invalid_dates", {"start_at": "past"})
    assert stored_dates(session_id) == (None, None, None, None)


async def test_a_date_without_an_offset_is_refused(klass):
    session_id = await new_session(klass)
    body = {"ai_mode": "rule_based", "dates": {**iso(PLAN), "start_at": "2026-11-24T10:00:00"}}
    response = await call(LECTURER, "PUT", f"/api/class-sessions/{session_id}", json=body)
    assert response.status_code == 422


async def test_after_the_start_a_deadline_ahead_moves_for_the_whole_session(
    klass, emitted, monkeypatch
):
    student = await student_of(klass)
    session_id = await new_session(klass)
    assert (await save(session_id, PLAN)).status_code == 200
    at(monkeypatch, START + DAY)
    read = await call(LECTURER, "GET", f"/api/class-sessions/{session_id}")
    assert (read.json()["locked"], read.json()["passed_dates"]) == (True, ["start_at"])
    as_row = dict(zip(PLAN, stored_dates(session_id), strict=True))
    assert service.is_locked(as_row) is True
    emitted.clear()
    moved = await save(
        session_id, {**PLAN, "play_deadline": PLAY + DAY, "test_deadline": TEST + DAY}
    )
    assert moved.status_code == 200
    assert stored_dates(session_id) == (START, PLAY + DAY, DEBRIEF, TEST + DAY)
    assert emitted == [("session", session_id), ("user", str(student))]


async def test_after_the_start_a_passed_date_does_not_move(klass, monkeypatch):
    session_id = await new_session(klass)
    assert (await save(session_id, PLAN)).status_code == 200
    at(monkeypatch, PLAY + DAY)
    refused = await save(session_id, {**PLAN, "start_at": PLAY + 2 * DAY})
    assert refusal(refused) == (409, "deadline_passed", {"start_at": "passed"})
    refused = await save(session_id, {**PLAN, "play_deadline": DEBRIEF - DAY / 2})
    assert refusal(refused) == (409, "deadline_passed", {"play_deadline": "passed"})
    assert stored_dates(session_id) == (START, PLAY, DEBRIEF, TEST)
    read = await call(LECTURER, "GET", f"/api/class-sessions/{session_id}")
    assert read.json()["passed_dates"] == ["start_at", "play_deadline"]


async def test_after_the_start_settings_are_locked_and_no_date_is_cleared(klass, monkeypatch):
    session_id = await new_session(klass)
    assert (await save(session_id, PLAN)).status_code == 200
    at(monkeypatch, START + DAY)
    refused = await save(session_id, None, ai_mode="llm")
    assert refusal(refused) == (409, "session_locked", {"ai_mode": "locked"})
    refused = await save(session_id, {**PLAN, "test_deadline": None})
    assert refusal(refused) == (422, "invalid_dates", {"test_deadline": "required"})
    assert stored_dates(session_id) == (START, PLAY, DEBRIEF, TEST)
    # The AI mode as it stands is no change.
    assert (await save(session_id, None)).status_code == 200


async def test_before_the_start_a_date_may_be_cleared(klass):
    session_id = await new_session(klass)
    assert (await save(session_id, PLAN)).status_code == 200
    assert (await save(session_id, {**PLAN, "test_deadline": None})).status_code == 200
    assert stored_dates(session_id) == (START, PLAY, DEBRIEF, None)


async def test_the_lock_predicate_and_the_effective_deadlines():
    plan = dict(PLAN)
    assert service.is_locked(plan, now=START - timedelta(seconds=1)) is False
    assert service.is_locked(plan, now=START) is True
    assert service.is_locked({**plan, "start_at": None}, now=TEST) is False
    user = uuid.uuid4()
    assert service.effective_debrief_deadline(user, plan) == DEBRIEF
    assert service.effective_test_deadline(user, plan) == TEST


async def test_a_short_play_time_warns_only_when_the_least_time_is_configured(klass, monkeypatch):
    session_id = await new_session(klass)
    # 36 Weeks between a Start date and a Play deadline one day apart.
    plan = {**PLAN, "play_deadline": START + DAY}
    assert (await save(session_id, plan)).json()["play_time_warning"] is False
    configured = get_settings().model_copy(update={"min_play_minutes_per_week": 60})
    monkeypatch.setattr(service, "get_settings", lambda: configured)
    read = await call(LECTURER, "GET", f"/api/class-sessions/{session_id}")
    assert read.json()["play_time_warning"] is True
    # Long enough: 14 days for 36 hours of play.
    assert (await save(session_id, PLAN)).json()["play_time_warning"] is False


async def test_the_student_reads_dates_and_the_next_deadline_never_the_settings(klass, monkeypatch):
    await student_of(klass)
    await make(OUTSIDER, roles=())
    session_id = await new_session(klass)
    assert (await save(session_id, PLAN)).status_code == 200
    response = await call(STUDENT, "GET", "/api/me/class-sessions")
    assert response.status_code == 200
    [item] = response.json()["items"]
    assert set(item) == {
        "id",
        "class_id",
        "class_name",
        "number",
        "start_at",
        "play_deadline",
        "debrief_deadline",
        "test_deadline",
        "next_deadline",
        "obligatory",
    }
    assert (item["id"], item["class_name"], item["number"]) == (session_id, "class-of-1994", 1)
    assert item["next_deadline"]["kind"] == "play"
    at(monkeypatch, PLAY + DAY)
    [item] = (await call(STUDENT, "GET", "/api/me/class-sessions")).json()["items"]
    assert item["next_deadline"]["kind"] == "debrief"
    at(monkeypatch, TEST + DAY)
    [item] = (await call(STUDENT, "GET", "/api/me/class-sessions")).json()["items"]
    assert item["next_deadline"] is None
    # Another User, and a removed Student, read no session.
    assert (await call(OUTSIDER, "GET", "/api/me/class-sessions")).json() == {"items": []}
    execute("UPDATE roster_entries SET removed_at = %s", NOW)
    assert (await call(STUDENT, "GET", "/api/me/class-sessions")).json() == {"items": []}


async def test_the_lecturer_home_names_what_waits_and_the_next_date(klass, monkeypatch):
    empty = await call(LECTURER, "GET", "/api/lecturer-home/class-sessions")
    assert empty.status_code == 200
    assert empty.json() == {"waiting": [], "next_date": None}
    first = await new_session(klass)
    second = await new_session(klass)
    assert (await save(first, PLAN)).status_code == 200
    body = (await call(LECTURER, "GET", "/api/lecturer-home/class-sessions")).json()
    assert body["waiting"] == [
        {
            "class_id": klass,
            "class_name": "class-of-1994",
            "sessions": [{"id": second, "number": 2}],
        }
    ]
    assert (body["next_date"]["kind"], body["next_date"]["session_id"]) == ("start", first)
    assert body["next_date"]["number"] == 1
    at(monkeypatch, START + DAY)
    body = (await call(LECTURER, "GET", "/api/lecturer-home/class-sessions")).json()
    assert body["next_date"]["kind"] == "play"
    # An Assistant lecturer of the Class reads the same; an archived Class drops out.
    assistant = await make(ASSISTANT, roles=())
    put_staff(klass, assistant, "assistant")
    as_assistant = await call(ASSISTANT, "GET", "/api/lecturer-home/class-sessions")
    assert as_assistant.status_code == 200
    assert as_assistant.json() == body
    execute("UPDATE classes SET archived_at = %s WHERE id = %s", NOW, klass)
    body = (await call(LECTURER, "GET", "/api/lecturer-home/class-sessions")).json()
    assert body == {"waiting": [], "next_date": None}


async def test_a_student_may_not_read_the_lecturer_home(klass):
    await student_of(klass)
    response = await call(STUDENT, "GET", "/api/lecturer-home/class-sessions")
    assert response.status_code == 403


async def test_sessions_are_numbered_per_class_in_creation_order(klass):
    first = await new_session(klass)
    second = await new_session(klass)
    other = await second_class()
    third = await new_session(other)
    listed = (await call(LECTURER, "GET", f"/api/classes/{klass}/class-sessions")).json()["items"]
    assert [(i["id"], i["number"]) for i in listed] == [(second, 2), (first, 1)]
    read = await call(LECTURER, "GET", f"/api/class-sessions/{third}")
    assert read.json()["number"] == 1


async def test_dates_count_to_the_minute_the_fields_hold(klass, emitted, monkeypatch):
    """A date sent with seconds is stored to the minute, and the screen's whole-minute value of
    a stored date is no change, also once that date has passed (review of Story 5.2)."""
    session_id = await new_session(klass)
    exact = {name: value + timedelta(seconds=42, microseconds=7) for name, value in PLAN.items()}
    assert (await save(session_id, exact)).status_code == 200
    assert stored_dates(session_id) == (START, PLAY, DEBRIEF, TEST)
    execute("UPDATE class_sessions SET start_at = %s WHERE id = %s", exact["start_at"], session_id)
    at(monkeypatch, START + DAY)
    emitted.clear()
    assert (await save(session_id, PLAN)).status_code == 200
    assert emitted == [("session", session_id)]


async def test_an_earlier_date_set_after_a_later_one_passed_carries_the_reason(klass, monkeypatch):
    session_id = await new_session(klass)
    assert (await save(session_id, {**PLAN, "debrief_deadline": None})).status_code == 200
    at(monkeypatch, TEST + DAY)
    refused = await save(session_id, {**PLAN, "debrief_deadline": TEST + 2 * DAY})
    assert refusal(refused) == (422, "invalid_dates", {"debrief_deadline": "before"})
