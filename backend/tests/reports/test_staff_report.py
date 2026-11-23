"""Story 13.12 at the api and in the job (FR-59, FR-58, FR-56, FR-63, FR-5, NFR-7, AD-9, AD-12,
AD-18): the staff of the Class download one Student's report from the Studentside, at any time.

The same request and `reports-single` job as the Student's own (`test_student_report`); the staff's
variants `staff` and `staff_ai` are their own requests and objects. On the storage mock, with the
fake converter that reads the snapshot as the print route does."""

import asyncio
import json
from datetime import date

from app.modules.identity.schemas import AccountRole
from app.modules.reports import scope
from app.platform import jobs
from app.platform.db import get_sessionmaker
from app.platform.events.registry import COMMAND_TOPICS
from tests.assessment.test_letter import (
    TIGHT,
    _empty,
    assessed,
    clock,
    emitted,
    klass,
    letter_url,
    locked,
    save,
)
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_staff import ASSISTANT, call, put_staff
from tests.debrief.test_explanation import user_id
from tests.messaging.helpers import rows
from tests.reports.test_student_report import (
    code,
    converter,
    files,
    queued,
    report_path,
    run_reports,
    snapshots,
)
from tests.reports.test_studentside import ADMIN, OTHER_LECTURER
from tests.sessions.test_dates import OUTSIDER
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "converter", "emitted", "files", "klass"]

ME = email(0)


def staff_path(session_id: str, student: object) -> str:
    return f"/api/class-sessions/{session_id}/students/{student}/report"


async def state(session_id: str, student: object, *, ai: bool = False, who: str = LECTURER):
    return await call(who, "GET", staff_path(session_id, student) + ("?ai=true" if ai else ""))


async def press(session_id: str, student: object, *, ai: bool | None = None, who: str = LECTURER):
    body = None if ai is None else {"ai": ai}
    return await call(who, "POST", staff_path(session_id, student), json=body)


async def file(session_id: str, student: object, *, ai: bool = False, who: str = LECTURER):
    suffix = "/file" + ("?ai=true" if ai else "")
    return await call(who, "GET", staff_path(session_id, student) + suffix)


def variants(session_id: str) -> list[tuple]:
    return rows(
        "SELECT variant, status, requested_by, object_path FROM report_requests "
        "WHERE class_session_id = %s ORDER BY requested_at, id",
        session_id,
    )


def section(data: dict, kind: str) -> dict | None:
    return next((each for each in data["sections"] if each["kind"] == kind), None)


def audits(action: str = "report.requested") -> list[tuple]:
    return rows(
        "SELECT actor_user_id, target_ids, change FROM audit_events "
        "WHERE action = %s ORDER BY occurred_at, id",
        action,
    )


async def test_staff_make_a_students_report_before_the_test_deadline_through_the_same_job(
    klass, monkeypatch, emitted, files, converter
):
    session_id = await locked(klass, monkeypatch, n=2)  # the clock before the Test deadline
    me = user_id(ME)
    lecturer = user_id(LECTURER)
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")

    before = await state(session_id, me)
    assert before.status_code == 200 and before.headers["cache-control"] == "no-store"
    assert before.json() == {
        "opens_at": None,
        "open": True,  # staff download at any time
        "status": "none",
        "generated_at": None,
        "ai": False,
        "ai_available": False,  # no test handed in
        "deleted": False,
    }
    # The Student's own report is still closed.
    assert code(await call(ME, "POST", report_path(session_id))) == (409, "report_not_open")

    emitted.clear()
    pressed = await press(session_id, me)
    assert pressed.status_code == 202 and pressed.json()["status"] == "pending"
    assert set(emitted) == {("user", str(lecturer))}  # the requester's, not the Student's
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["reports.request_report"]
    # A second press, by anyone of the staff, answers the pending one.
    assert (await press(session_id, me, who=ASSISTANT)).json()["status"] == "pending"
    assert queued() == 1
    assert code(await file(session_id, me)) == (409, "report_not_ready")
    [(actor, target, change)] = audits()
    assert (actor, target["user_id"], target["class_session_id"]) == (
        lecturer,
        str(me),
        session_id,
    )
    assert change == {"variant": "staff"}
    [(request_id,)] = rows("SELECT id FROM report_requests WHERE class_session_id = %s", session_id)
    assert target["request_id"] == str(request_id)

    emitted.clear()
    assert await run_reports() < 30  # the placeholder target, on the storage mock
    assert set(emitted) == {("user", str(lecturer))}
    [(variant, status, by, path)] = variants(session_id)
    assert (variant, status, by) == ("staff", "ready", lecturer)
    assert f"/{me}/student-report-staff-" in path
    assert snapshots() == 0

    [data] = converter["data"]
    # Steps not yet done read as not done (the Individual test is not handed in).
    steps = {step["step"]: step["done"] for step in section(data, "completion")["steps"]}
    assert steps["test_submitted"] is False
    assert section(data, "assessment") is None
    # No other Student in it.
    other = rows("SELECT name FROM users WHERE id = %s", user_id(email(1)))[0][0]
    assert other not in json.dumps(data)

    # Shared by the staff of the Class: the Assistant lecturer reads and downloads the same PDF.
    shared = (await state(session_id, me, who=ASSISTANT)).json()
    assert (shared["status"], shared["generated_at"] is not None) == ("ready", True)
    assistant = user_id(ASSISTANT)
    got = await file(session_id, me, who=ASSISTANT)
    # The download is recorded too: who was given which Student's PDF.
    [(by, gave, what)] = audits("report.downloaded")
    assert (by, gave["user_id"], gave["request_id"], what) == (
        assistant,
        str(me),
        str(request_id),
        {"variant": "staff"},
    )
    assert got.status_code == 303 and path in got.headers["location"]
    assert "studentrapport-klasseokt-1.pdf" in got.headers["location"]

    # The Student's own report is untouched: no request of theirs, nothing to download.
    mine = (await call(ME, "GET", report_path(session_id))).json()
    assert (mine["status"], mine["generated_at"]) == ("none", None)


async def test_staff_add_the_ai_section_and_never_the_indicative_letter(
    klass, monkeypatch, files, converter
):
    session_id = await locked(klass, monkeypatch, n=2)
    # The Lecturer shows the letter to everyone.
    assert (
        await save(session_id, letter_setting="all", letter_thresholds=TIGHT)
    ).status_code == 200
    await assessed(session_id, monkeypatch)
    me = user_id(ME)

    found = (await state(session_id, me)).json()
    assert (found["ai_available"], found["ai"]) == (True, False)
    # Off by default: without `ai` the report has no AI data.
    assert (await press(session_id, me)).status_code == 202
    await run_reports()
    plain = converter["data"][-1]
    assert section(plain, "assessment") is None and '"letter"' not in json.dumps(plain)

    added = await press(session_id, me, ai=True)
    assert added.status_code == 202 and added.json()["ai"] is True
    await run_reports()
    with_ai = section(converter["data"][-1], "assessment")
    assert with_ai is not None and with_ai["letter"] is None
    assert [v[:2] for v in variants(session_id)] == [("staff", "ready"), ("staff_ai", "ready")]
    plain_path, ai_path = (v[3] for v in variants(session_id))
    assert plain_path in (await file(session_id, me)).headers["location"]
    assert ai_path in (await file(session_id, me, ai=True)).headers["location"]

    # The Student's own report with the section carries the letter; the staff's never.
    assert (await call(ME, "POST", report_path(session_id), json={"ai": True})).status_code == 202
    await run_reports()
    assert section(converter["data"][-1], "assessment")["letter"] is not None
    assert variants(session_id)[-1][:2] == ("ai_letter", "ready")
    assert (await press(session_id, me, ai=True)).status_code == 202
    await run_reports()
    assert section(converter["data"][-1], "assessment")["letter"] is None
    # The Student's own download still serves their own PDF.
    own = variants(session_id)[2][3]
    assert (
        own
        in (await call(ME, "GET", report_path(session_id) + "/file?ai=true")).headers["location"]
    )


async def test_the_students_own_choice_of_the_letter_never_reaches_a_staff_download(
    klass, monkeypatch, files, converter
):
    session_id = await locked(klass, monkeypatch)
    await assessed(session_id, monkeypatch)
    assert (await call(ME, "PUT", letter_url(session_id), json={"on": True})).status_code == 200
    me = user_id(ME)
    assert (await press(session_id, me, ai=True, who=LECTURER)).status_code == 202
    await run_reports()
    assert section(converter["data"][-1], "assessment")["letter"] is None
    assert variants(session_id)[-1][:2] == ("staff_ai", "ready")


async def test_without_a_ready_assessment_the_section_is_refused(
    klass, monkeypatch, files, converter
):
    session_id = await locked(klass, monkeypatch)
    await assessed(session_id, monkeypatch, status="incomplete")
    me = user_id(ME)
    found = (await state(session_id, me, ai=True)).json()
    assert (found["ai_available"], found["ai"]) == (False, False)
    assert code(await press(session_id, me, ai=True)) == (409, "ai_assessment_unavailable")
    assert code(await file(session_id, me, ai=True)) == (409, "ai_assessment_unavailable")
    assert variants(session_id) == [] and audits() == []


async def test_outsiders_are_refused_alike_and_nothing_is_recorded(
    klass, monkeypatch, files, converter
):
    session_id = await locked(klass, monkeypatch, n=2)
    me = user_id(ME)
    await make(OTHER_LECTURER)
    await make(ADMIN, roles=(AccountRole.admin,))
    await make(OUTSIDER, roles=())
    for who, student in (
        (OTHER_LECTURER, me),  # a Lecturer of another Class
        (ADMIN, me),  # an Admin without a staff role in the Class
        (email(1), me),  # another Student of the Class
        (ME, me),  # the Student: their own report has its own routes
        (LECTURER, user_id(OUTSIDER)),  # a User who is no Student of the Class
        (LECTURER, "not-an-id"),
    ):
        for answer in (
            await state(session_id, student, who=who),
            await press(session_id, student, who=who),
            await press(session_id, student, ai=True, who=who),
            await file(session_id, student, who=who),
        ):
            assert code(answer) == (403, "forbidden"), (who, answer.text)
    assert code(await state("00000000-0000-0000-0000-000000000000", me)) == (403, "forbidden")
    assert variants(session_id) == [] and queued() == 0 and snapshots() == 0 and audits() == []


async def test_a_student_the_reports_leave_out_gets_no_report(klass, monkeypatch, files, converter):
    session_id = await locked(klass, monkeypatch)
    me = user_id(ME)

    async def test_students(session, ids):
        return set(ids) & {me}

    monkeypatch.setattr(scope, "_test_students", [test_students])
    assert code(await press(session_id, me)) == (409, "not_counted")
    assert code(await file(session_id, me)) == (409, "not_counted")
    assert variants(session_id) == [] and queued() == 0 and audits() == []


async def test_once_the_students_data_is_deleted_the_action_says_so_and_builds_nothing(
    klass, monkeypatch, files, converter
):
    session_id = await locked(klass, monkeypatch)
    me = user_id(ME)
    assert (await press(session_id, me)).status_code == 202
    await run_reports()
    # The deletion date has come (Story 13.9's column; the deletion itself is Epic 15's).
    execute(
        "UPDATE class_sessions SET deletion_date = %s WHERE id = %s", date(2000, 1, 1), session_id
    )
    found = (await state(session_id, me)).json()
    assert (found["deleted"], found["status"], found["generated_at"]) == (True, "none", None)
    before = len(variants(session_id))
    assert code(await press(session_id, me)) == (409, "data_deleted")
    assert code(await press(session_id, me, ai=True)) == (409, "data_deleted")
    assert code(await file(session_id, me)) == (409, "data_deleted")
    assert len(variants(session_id)) == before and queued() == 0 and snapshots() == 0
    assert len(audits()) == 1 and audits("report.downloaded") == []


_bulk: dict = {}


@jobs.app.task(name="tests.reports.hold_bulk", queue=jobs.REPORTS_BULK)
async def hold_bulk() -> None:
    """A slow job on `reports-bulk` (the ZIP comes in Story 13.13): it holds its slot until the
    test lets it go."""
    _bulk["running"].set()
    await asyncio.wait_for(_bulk["release"].wait(), 60)


async def test_a_single_report_meets_its_target_while_a_slow_job_holds_reports_bulk(
    klass, monkeypatch, files, converter
):
    """AD-9: `worker-batch` keeps `REPORTS_SINGLE_RESERVED` slots for `reports-single`, so a
    single report is made while `reports-bulk` is busy."""
    session_id = await locked(klass, monkeypatch)
    me = user_id(ME)
    _bulk.update(running=asyncio.Event(), release=asyncio.Event())
    async with get_sessionmaker().begin() as s:
        await jobs.defer(
            s, "tests.reports.hold_bulk", queue=jobs.REPORTS_BULK, queueing_lock="hold"
        )
    assert (await press(session_id, me)).status_code == 202
    worker = asyncio.ensure_future(jobs.run_until_idle([jobs.REPORTS_BULK, jobs.REPORTS_SINGLE]))
    try:
        await asyncio.wait_for(_bulk["running"].wait(), 10)

        for _ in range(300):  # 30 s, the target
            if (await state(session_id, me)).json()["status"] == "ready":
                break
            await asyncio.sleep(0.1)
        assert (await state(session_id, me)).json()["status"] == "ready"
        assert not worker.done()  # the bulk job still holds its slot
    finally:
        _bulk["release"].set()
        await asyncio.wait_for(worker, 30)
