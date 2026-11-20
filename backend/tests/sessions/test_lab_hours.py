"""Lab hours of a Class session (Story 5.6, FR-19, FR-18, AD-8, AD-9, AD-14): added, changed and
removed on their own routes at any time, each change told to every registered Student through a
digest notice holding ids only, the Student's read of the upcoming ones, `current_lab_hour`, and
the digest mail that names the Lab hour. The api's clock is fixed (2026-11-19 09:00 UTC) and moved
by hand; the database clock is never read."""

from datetime import datetime, timedelta

import pytest

from app.modules.messaging import delivery
from app.modules.ops import sweep
from app.modules.sessions import service
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_staff import ASSISTANT, call, put_staff
from tests.classes.test_student_registration import emitted
from tests.messaging.helpers import drain, mails, rows
from tests.sessions.test_dates import PLAN, at, new_session, refusal, save, student_of

__all__ = ["clock", "emitted", "klass"]

HOUR = timedelta(hours=1)
DAY = timedelta(days=1)
STARTS = NOW + 2 * DAY + 4 * HOUR  # 2026-11-21 13:00 UTC, 14:00 in Oslo (a Saturday)
ENDS = STARTS + 2 * HOUR


@pytest.fixture(autouse=True)
def _empty(ai_db, mail_db):
    """No model config (Rule-based sessions), and no notices, deliveries or mails."""


def body(starts=STARTS, ends=ENDS, place="Datalab A2") -> dict:
    return {"starts_at": starts.isoformat(), "ends_at": ends.isoformat(), "place": place}


async def add(session_id: str, email=LECTURER, **kw):
    return await call(email, "POST", f"/api/class-sessions/{session_id}/lab-hours", json=body(**kw))


async def change(session_id: str, lab_id: str, email=LECTURER, **kw):
    path = f"/api/class-sessions/{session_id}/lab-hours/{lab_id}"
    return await call(email, "PUT", path, json=body(**kw))


async def remove(session_id: str, lab_id: str, email=LECTURER):
    return await call(email, "DELETE", f"/api/class-sessions/{session_id}/lab-hours/{lab_id}")


async def listed(session_id: str) -> list[dict]:
    return (await call(LECTURER, "GET", f"/api/class-sessions/{session_id}")).json()["lab_hours"]


def notices() -> list[tuple]:
    """`(kind, dedupe_key, user_id, ref)` of every notice, oldest first."""
    return rows("SELECT kind, dedupe_key, user_id::text, ref::text FROM notices ORDER BY id")


async def two_students(class_id: str) -> list[str]:
    return [str(await student_of(class_id)), str(await student_of(class_id, "student2@x.no"))]


async def test_a_lab_hour_is_stored_and_each_registered_student_gets_one_notice(klass, emitted):
    students = await two_students(klass)
    session_id = await new_session(klass)
    emitted.clear()
    response = await add(session_id)
    assert response.status_code == 201
    lab = response.json()
    assert (lab["place"], lab["ended"]) == ("Datalab A2", False)
    assert datetime.fromisoformat(lab["starts_at"]) == STARTS
    assert [item["id"] for item in await listed(session_id)] == [lab["id"]]
    assert notices() == [
        ("lab_hour_added", f"lab_hour_added:{lab['id']}:{student}", student, lab["id"])
        for student in students
    ]
    # Ids only: no place, name or address in the notice rows (AD-14).
    assert "Datalab" not in str(rows("SELECT * FROM notices"))
    assert emitted == [("session", session_id), *(("user", s) for s in students)]
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["sessions.add_lab_hour"]


async def test_as_many_lab_hours_as_needed_are_listed_by_start(klass):
    session_id = await new_session(klass)
    for days in (3, 1, 2):
        start = NOW + days * DAY
        assert (await add(session_id, starts=start, ends=start + HOUR)).status_code == 201
    starts = [datetime.fromisoformat(item["starts_at"]) for item in await listed(session_id)]
    assert starts == sorted(starts) and len(starts) == 3


@pytest.mark.parametrize(
    ("kw", "fields"),
    [
        ({"ends": STARTS - HOUR}, {"ends_at": "not_after_start"}),
        ({"ends": STARTS}, {"ends_at": "not_after_start"}),
        ({"place": "   "}, {"place": "required"}),
        ({"place": "x" * 121}, {"place": "too_long"}),
        ({"ends": STARTS + 12 * HOUR + timedelta(minutes=1)}, {"ends_at": "too_long"}),
        ({"starts": NOW - 2 * HOUR, "ends": NOW}, {"ends_at": "past"}),
        ({"ends": STARTS - HOUR, "place": ""}, {"ends_at": "not_after_start", "place": "required"}),
    ],
)
async def test_a_lab_hour_that_breaks_a_rule_is_refused_and_nothing_is_stored(klass, kw, fields):
    await student_of(klass)
    session_id = await new_session(klass)
    response = await add(session_id, **kw)
    assert refusal(response) == (422, "invalid_lab_hour", fields)
    assert await listed(session_id) == [] and notices() == []


async def test_a_lab_hour_already_on_may_be_added_and_the_place_is_trimmed(klass):
    session_id = await new_session(klass)
    response = await add(session_id, starts=NOW - HOUR, ends=NOW + HOUR, place="  Rom 101 ")
    assert response.status_code == 201 and response.json()["place"] == "Rom 101"
    # Twelve hours exactly is the longest.
    assert (await add(session_id, ends=STARTS + 12 * HOUR)).status_code == 201


async def test_a_change_raises_the_revision_and_tells_each_student_once(klass, emitted):
    students = await two_students(klass)
    session_id = await new_session(klass)
    lab_id = (await add(session_id)).json()["id"]
    emitted.clear()
    response = await change(session_id, lab_id, place="Datalab B1")
    assert response.status_code == 200 and response.json()["place"] == "Datalab B1"
    assert rows("SELECT revision FROM lab_hours WHERE id = %s", lab_id) == [(2,)]
    assert notices()[2:] == [
        ("lab_hour_changed", f"lab_hour_changed:{lab_id}:2:{s}", s, lab_id) for s in students
    ]
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["sessions.change_lab_hour"]
    # The same values again store and tell nothing.
    emitted.clear()
    assert (await change(session_id, lab_id, place="Datalab B1")).status_code == 200
    assert rows("SELECT revision FROM lab_hours WHERE id = %s", lab_id) == [(2,)]
    assert len(notices()) == 6 - 2 and emitted == []
    # A second change gets a notice of its own.
    assert (await change(session_id, lab_id, ends=ENDS + HOUR)).status_code == 200
    assert [n[1] for n in notices()[4:]] == [f"lab_hour_changed:{lab_id}:3:{s}" for s in students]


async def test_a_removed_lab_hour_is_kept_cancelled_and_each_student_is_told(klass, emitted):
    students = await two_students(klass)
    session_id = await new_session(klass)
    lab_id = (await add(session_id)).json()["id"]
    emitted.clear()
    response = await remove(session_id, lab_id)
    assert response.status_code == 204
    assert await listed(session_id) == []
    assert rows("SELECT cancelled_at FROM lab_hours WHERE id = %s", lab_id) == [(NOW,)]
    assert notices()[2:] == [
        ("lab_hour_cancelled", f"lab_hour_cancelled:{lab_id}:{s}", s, lab_id) for s in students
    ]
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["sessions.remove_lab_hour"]
    # Gone: it neither changes nor goes again.
    assert (await change(session_id, lab_id)).status_code == 403
    assert (await remove(session_id, lab_id)).status_code == 403


async def test_a_lab_hour_that_has_ended_no_longer_changes_or_goes(klass, monkeypatch):
    session_id = await new_session(klass)
    lab_id = (await add(session_id)).json()["id"]
    at(monkeypatch, ENDS)
    assert (await listed(session_id))[0]["ended"] is True
    assert refusal(await change(session_id, lab_id, ends=ENDS + DAY))[:2] == (
        409,
        "lab_hour_ended",
    )
    assert refusal(await remove(session_id, lab_id))[:2] == (409, "lab_hour_ended")
    assert rows("SELECT revision, cancelled_at FROM lab_hours") == [(1, None)]


async def test_lab_hours_still_change_once_the_session_is_locked(klass, monkeypatch):
    session_id = await new_session(klass)
    assert (await save(session_id, PLAN)).status_code == 200
    at(monkeypatch, PLAN["start_at"] + HOUR)
    locked = (await call(LECTURER, "GET", f"/api/class-sessions/{session_id}")).json()
    assert locked["locked"] is True
    start = PLAN["start_at"] + DAY
    added = await add(session_id, starts=start, ends=start + HOUR)
    assert added.status_code == 201
    lab_id = added.json()["id"]
    assert (
        await change(session_id, lab_id, starts=start, ends=start + 2 * HOUR)
    ).status_code == 200
    assert (await remove(session_id, lab_id)).status_code == 204


async def test_an_archived_class_an_assistant_and_another_session_change_nothing(klass):
    session_id = await new_session(klass)
    lab_id = (await add(session_id)).json()["id"]
    assistant = await make(ASSISTANT, roles=())
    put_staff(klass, assistant, "assistant")
    # The Assistant reads the Lab hours and changes none.
    read = await call(ASSISTANT, "GET", f"/api/class-sessions/{session_id}")
    assert [item["id"] for item in read.json()["lab_hours"]] == [lab_id]
    assert (await add(session_id, email=ASSISTANT)).status_code == 403
    assert (await change(session_id, lab_id, email=ASSISTANT)).status_code == 403
    assert (await remove(session_id, lab_id, email=ASSISTANT)).status_code == 403
    # A Lab hour of another session, and an id that is no id, reach nothing.
    other = await new_session(klass)
    assert (await change(other, lab_id)).status_code == 403
    assert (await remove(other, "nope")).status_code == 403
    execute("UPDATE classes SET archived_at = %s WHERE id = %s", NOW, klass)
    assert refusal(await add(session_id))[:2] == (409, "class_archived")
    assert refusal(await change(session_id, lab_id, place="B"))[:2] == (409, "class_archived")
    assert refusal(await remove(session_id, lab_id))[:2] == (409, "class_archived")
    assert len(await listed(session_id)) == 1 and notices() == []


async def test_a_student_reads_only_the_upcoming_lab_hours(klass, monkeypatch):
    await student_of(klass)
    session_id = await new_session(klass)
    past = (await add(session_id, starts=NOW + HOUR, ends=NOW + 2 * HOUR)).json()["id"]
    upcoming = (await add(session_id)).json()["id"]
    removed = (await add(session_id, starts=STARTS + DAY, ends=ENDS + DAY)).json()["id"]
    assert (await remove(session_id, removed)).status_code == 204
    at(monkeypatch, NOW + 2 * HOUR)
    [item] = (await call("student@x.no", "GET", "/api/me/class-sessions")).json()["items"]
    assert item["lab_hours"] == [
        {
            "id": upcoming,
            "starts_at": STARTS.isoformat().replace("+00:00", "Z"),
            "ends_at": ENDS.isoformat().replace("+00:00", "Z"),
            "place": "Datalab A2",
        }
    ]
    assert past not in str(item)


async def test_current_lab_hour_answers_the_lab_hour_in_progress_or_none(klass):
    session_id = await new_session(klass)
    lab_id = (await add(session_id)).json()["id"]
    later = (await add(session_id, starts=STARTS + HOUR, ends=ENDS + HOUR)).json()["id"]
    removed = (await add(session_id, starts=STARTS - HOUR, ends=ENDS)).json()["id"]
    assert (await remove(session_id, removed)).status_code == 204
    sid = service.uuid.UUID(session_id)
    assert await service.current_lab_hour(sid, STARTS - timedelta(minutes=1)) is None
    assert str((await service.current_lab_hour(sid, STARTS)).id) == lab_id
    # Two on at once: the earliest started.
    assert str((await service.current_lab_hour(sid, STARTS + HOUR)).id) == lab_id
    assert str((await service.current_lab_hour(sid, ENDS)).id) == later
    assert await service.current_lab_hour(sid, ENDS + HOUR) is None


def test_the_delivery_table_names_the_lab_hour_kinds_as_digest():
    assert delivery.LAB_HOUR_KINDS == service.LAB_HOUR_KINDS
    for kind in service.LAB_HOUR_KINDS:
        assert delivery.KINDS[kind].mode == delivery.DIGEST


async def sweep_at(now: datetime) -> None:
    await sweep.run(now)
    await drain(now)


async def test_the_digest_names_the_lab_hour_and_leaves_out_what_no_longer_holds(klass):
    await student_of(klass)
    session_id = await new_session(klass)
    lab_id = (await add(session_id)).json()["id"]
    assert (await change(session_id, lab_id, place="Datalab B1")).status_code == 200
    gone = (await add(session_id, starts=STARTS + DAY, ends=ENDS + DAY)).json()["id"]
    assert (await remove(session_id, gone)).status_code == 204
    await sweep_at(NOW + HOUR)  # 11:00 in Oslo, inside the digest hours
    [mail] = mails()
    assert mail.to == "student@x.no"
    assert (
        "Ny Labtime i Klassen class-of-1994: lørdag 21. november kl. 14:00–16:00, Datalab B1."
        in (mail.text)
    )
    assert "er endret. Den er nå lørdag 21. november kl. 14:00–16:00, Datalab B1." in mail.text
    # The removed one: its added notice is left out, its cancellation is told.
    assert "Ny Labtime i Klassen class-of-1994: søndag" not in mail.text
    assert "Labtimen søndag 22. november kl. 14:00–16:00, Datalab A2, i Klassen" in mail.text
    assert mail.text.count("Labtime") == 3
    for banned in ("Beer Game", "bullwhip", "uker", "Uke"):
        assert banned not in mail.text


async def test_a_lab_hour_over_before_the_digest_or_an_archived_class_gets_no_mail(klass):
    await student_of(klass)
    session_id = await new_session(klass)
    soon = (await add(session_id, starts=NOW + HOUR, ends=NOW + 2 * HOUR)).json()["id"]
    assert (await remove(session_id, soon)).status_code == 204
    assert (await add(session_id, starts=NOW + HOUR, ends=NOW + 2 * HOUR)).status_code == 201
    await sweep_at(NOW + 3 * HOUR)  # 12:00 in Oslo: both are over, added and cancelled alike
    assert mails() == []
    assert (await add(session_id)).status_code == 201
    execute("UPDATE classes SET archived_at = %s WHERE id = %s", NOW, klass)
    await sweep_at(NOW + DAY)
    assert mails() == []


async def test_times_are_stored_to_the_whole_minute(klass):
    session_id = await new_session(klass)
    seconds = timedelta(seconds=42)
    lab = (await add(session_id, starts=STARTS + seconds, ends=ENDS + seconds)).json()
    assert datetime.fromisoformat(lab["starts_at"]) == STARTS
    assert rows("SELECT starts_at, ends_at FROM lab_hours") == [(STARTS, ENDS)]
    # The same times with seconds again are unchanged.
    assert (await change(session_id, lab["id"], starts=STARTS + seconds)).status_code == 200
    assert rows("SELECT revision FROM lab_hours") == [(1,)]


async def test_a_student_removed_from_the_class_gets_no_lab_hour_mail(klass):
    await student_of(klass)
    session_id = await new_session(klass)
    assert (await add(session_id)).status_code == 201
    execute("UPDATE roster_entries SET removed_at = %s WHERE class_id = %s", NOW, klass)
    await sweep_at(NOW + HOUR)
    assert mails() == []
