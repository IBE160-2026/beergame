"""Story 13.7 at the api and in the job (FR-57, FR-58, NFR-7, AD-8, AD-9, AD-12, AD-14, AD-18): a
Student's own Student report.

`POST /api/me/class-sessions/{id}/report` records a request and defers `reports.render_report` on
`reports-single`; the job builds the content, stores a snapshot with a single-use token, has the
converter read the print route (here a fake that reads the snapshot through the api, as the print
route does: WeasyPrint needs Pango, which the e2e and CI's veraPDF step cover), stores the PDF in
the storage mock and emits `user:<id>`. `GET …/report/file` answers a signed URL.

One locked Class session of two Students serves each test; the app's clock is fixed and moved past
the Test deadline where the report must be open."""

import json
import time
import uuid
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from structlog.testing import capture_logs

from app.modules.ops import sweep
from app.modules.reports import render, scope
from app.platform import jobs
from app.platform.config import get_settings
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_classes import LECTURER, OTHER
from tests.classes.test_invitation_counts import execute
from tests.classes.test_staff import call
from tests.classes.test_student_registration import emitted, set_clock
from tests.identity.helpers import client
from tests.messaging.helpers import rows
from tests.reports.test_completion_status import obligatory
from tests.sessions.test_dates import START, TEST
from tests.sessions.test_lock import MINUTE
from tests.sessions.test_open_games import confirmed
from tests.sessions.test_student_choice import email
from tests.sessions.test_student_home import _empty, clock, home, klass

__all__ = ["_empty", "clock", "emitted", "klass"]

AFTER = TEST + MINUTE
FAKE_PDF = b"%PDF-1.7\n% a fake report\n"


def report_path(session_id: str) -> str:
    return f"/api/me/class-sessions/{session_id}/report"


async def state(who: str, session_id: str):
    return await call(who, "GET", report_path(session_id))


async def press(who: str, session_id: str):
    return await call(who, "POST", report_path(session_id))


async def file(who: str, session_id: str):
    return await call(who, "GET", report_path(session_id) + "/file")


def code(response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


def requests_of(session_id: str) -> list[tuple]:
    return rows(
        "SELECT status, failure, object_path IS NOT NULL FROM report_requests "
        "WHERE class_session_id = %s ORDER BY requested_at, id",
        session_id,
    )


def snapshots() -> int:
    return rows("SELECT count(*) FROM report_snapshots")[0][0]


def queued() -> int:
    return rows("SELECT count(*) FROM procrastinate_jobs WHERE queue_name = 'reports-single'")[0][0]


def report_step(item: dict) -> dict:
    return next(step for step in item["steps"] if step["step"] == "report")


@pytest.fixture
def files(tmp_path, monkeypatch):
    """The storage mock writes under a folder of this test's own."""
    monkeypatch.setattr(get_settings(), "local_storage_dir", str(tmp_path))
    return tmp_path


@pytest.fixture
def converter(monkeypatch):
    """The fake converter: reads the snapshot through the api with the token, as the print route
    does, keeps what it read and what a second read answered, and returns a fake PDF."""
    seen: dict = {"data": [], "again": [], "wrong": []}

    async def to_pdf(url: str) -> bytes:
        parts = urlsplit(url)
        snapshot_id = parts.path.rsplit("/", 1)[1]
        token = parse_qs(parts.query)["token"][0]
        path = f"/api/internal/report-snapshots/{snapshot_id}"
        async with client() as c:
            seen["wrong"].append(
                (await c.get(path, headers={"X-Render-Token": "x" + token})).status_code
            )
            first = await c.get(path, headers={"X-Render-Token": token})
            assert first.status_code == 200
            assert first.headers["cache-control"] == "no-store"
            seen["data"].append(first.json())
            seen["again"].append((await c.get(path, headers={"X-Render-Token": token})).status_code)
        return FAKE_PDF

    monkeypatch.setattr(render, "to_pdf", to_pdf)
    seen["to_pdf"] = to_pdf
    return seen


async def locked_session(klass: str) -> tuple[str, list[uuid.UUID]]:
    session_id, seated = await confirmed(klass, 2)
    await sweep.run(START + MINUTE)  # locks the Class session
    return session_id, seated


async def run_reports() -> float:
    """Run the waiting jobs (the mail queue beside, so `reports-single` takes its own slots)."""
    started = time.monotonic()
    await jobs.run_until_idle([jobs.MAIL, jobs.REPORTS_SINGLE])
    return time.monotonic() - started


async def test_the_report_opens_at_the_test_deadline_and_is_rendered_from_a_snapshot(
    klass, emitted, monkeypatch, files, converter
):
    session_id, seated = await locked_session(klass)
    obligatory(session_id)
    me = seated[0]

    # Before the Test deadline: locked on Hjem, closed at the api with a stable code.
    before = (await state(email(0), session_id)).json()
    assert before == {
        "opens_at": before["opens_at"],
        "open": False,
        "status": "none",
        "generated_at": None,
    }
    assert before["opens_at"].startswith(TEST.isoformat()[:16])
    assert code(await press(email(0), session_id)) == (409, "report_not_open")
    assert report_step(await home(email(0)))["state"] == "locked"
    assert requests_of(session_id) == []

    set_clock(monkeypatch, AFTER)
    assert report_step(await home(email(0)))["state"] == "current"
    emitted.clear()
    pressed = await press(email(0), session_id)
    assert pressed.status_code == 202
    assert pressed.headers["cache-control"] == "no-store"
    assert pressed.json()["status"] == "pending"
    assert set(emitted) == {("user", str(me))}
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["reports.request_report"]
    # A second press while it is pending answers it: one request, one job.
    assert (await press(email(0), session_id)).json()["status"] == "pending"
    assert requests_of(session_id) == [("pending", None, False)]
    assert queued() == 1
    assert code(await file(email(0), session_id)) == (409, "report_not_ready")

    emitted.clear()
    took = await run_reports()
    assert took < 30  # the placeholder target (FR-57), on the storage mock
    assert requests_of(session_id) == [("ready", None, True)]
    assert snapshots() == 0  # deleted when the render ended (AD-14)
    assert set(emitted) == {("user", str(me))}
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["reports.render_report"]

    # The print route read the snapshot once, with its token; a second read and a wrong token
    # get nothing.
    assert converter["again"] == [404] and converter["wrong"] == [404]
    [data] = converter["data"]
    name = rows("SELECT name FROM users WHERE id = %s", me)[0][0]
    other = rows("SELECT name FROM users WHERE id = %s", seated[1])[0][0]
    assert (data["student_name"], data["class_name"], data["session_number"]) == (
        name,
        "class-of-1994",
        1,
    )
    assert data["generated_at"].startswith(AFTER.isoformat()[:16])
    assert data["dates"]["test_deadline"].startswith(TEST.isoformat()[:16])
    section = data["sections"][0]
    assert [each["kind"] for each in data["sections"]][:2] == ["completion", "game"]  # 13.8
    assert (section["obligatory"], section["requirement_met"]) == (True, False)
    assert [step["step"] for step in section["steps"]] == [
        "class_game",
        "debrief",
        "quiz_passed",
        "replay",
        "test_submitted",
    ]
    assert not any(step["done"] for step in section["steps"])
    assert other not in json.dumps(data)

    ready = (await state(email(0), session_id)).json()
    assert (ready["open"], ready["status"]) == (True, "ready")
    assert ready["generated_at"] is not None

    # The download: a signed URL to the storage mock, made after the policy allowed it.
    sent = await file(email(0), session_id)
    assert sent.status_code == 303 and sent.headers["cache-control"] == "no-store"
    location = sent.headers["location"]
    assert location.startswith(f"/api/storage/local/reports/class-sessions/{session_id}/{me}/")
    assert name not in location
    async with client() as c:
        got = await c.get(location)
        assert got.status_code == 200 and got.content == FAKE_PDF
        assert got.headers["content-type"] == "application/pdf"
        assert "studentrapport-klasseokt-1.pdf" in got.headers["content-disposition"]
        tampered = location.replace("signature=", "signature=0")
        assert (await c.get(tampered)).status_code == 404
        query = parse_qs(urlsplit(location).query)
        late = location.replace(f"expires={query['expires'][0]}", "expires=1")
        assert (await c.get(late)).status_code == 404
    request_id = rows("SELECT id FROM report_requests")[0][0]
    folder = files / "reports" / "class-sessions" / session_id / str(me)
    assert (folder / f"student-report-{request_id}.pdf").read_bytes() == FAKE_PDF
    assert [p.name for p in folder.iterdir()] == [f"student-report-{request_id}.pdf"]
    async with client() as c:
        odd = location.replace("signature=", "signature=%C3%A6")
        assert (await c.get(odd)).status_code == 404  # never a 500

    # Another Student reaches only their own report, never this one.
    assert code(await file(email(1), session_id)) == (409, "report_not_ready")
    assert (await state(email(1), session_id)).json()["status"] == "none"


async def test_a_later_correction_shows_in_the_next_report(klass, monkeypatch, files, converter):
    session_id, seated = await locked_session(klass)
    obligatory(session_id)
    set_clock(monkeypatch, AFTER)
    await press(email(0), session_id)
    await run_reports()
    corrected = await call(
        LECTURER,
        "POST",
        f"/api/class-sessions/{session_id}/students/{seated[0]}/corrections",
        json={"step": "debrief", "done": True, "reason": "Levert på papir."},
    )
    assert corrected.status_code == 200
    assert (await press(email(0), session_id)).json()["status"] == "pending"
    await run_reports()
    assert requests_of(session_id) == [("ready", None, False), ("ready", None, True)]
    first, second = converter["data"]
    steps = {step["step"]: step for step in second["sections"][0]["steps"]}
    assert (steps["debrief"]["done"], steps["debrief"]["corrected"]) == (True, True)
    assert {s["step"]: s["done"] for s in first["sections"][0]["steps"]}["debrief"] is False
    assert "Levert på papir" not in json.dumps(second)  # never the reason
    # One PDF per Student: the earlier one is gone, the newer one is downloaded.
    [(newest,)] = rows("SELECT id FROM report_requests WHERE object_path IS NOT NULL")
    folder = files / "reports" / "class-sessions" / session_id / str(seated[0])
    assert [p.name for p in folder.iterdir()] == [f"student-report-{newest}.pdf"]
    assert str(newest) in (await file(email(0), session_id)).headers["location"]


async def test_a_student_reports_leave_out_gets_no_report(klass, monkeypatch, files, converter):
    session_id, seated = await locked_session(klass)
    set_clock(monkeypatch, AFTER)
    await press(email(0), session_id)
    left_out = {seated[0]}

    async def test_students(session, ids):
        return set(ids) & left_out

    # The Student turns out to be a test student between the press and the render (Story 12.8's
    # hook): the job builds nothing, and no new press or download is allowed.
    monkeypatch.setattr(scope, "_test_students", [test_students])
    await run_reports()
    assert requests_of(session_id) == [("failed", "not_reportable", False)]
    assert converter["data"] == [] and snapshots() == 0
    assert code(await press(email(0), session_id)) == (409, "not_counted")
    assert code(await file(email(0), session_id)) == (409, "not_counted")
    assert queued() == 0


async def test_a_failed_render_is_marked_failed_logged_without_names_and_can_be_retried(
    klass, monkeypatch, files, converter
):
    session_id, seated = await locked_session(klass)
    set_clock(monkeypatch, AFTER)
    name = rows("SELECT name FROM users WHERE id = %s", seated[0])[0][0]

    async def broken(url: str) -> bytes:
        raise RuntimeError(f"could not fetch {url} for {name}")

    monkeypatch.setattr(render, "to_pdf", broken)
    await press(email(0), session_id)
    with capture_logs() as logs:
        await run_reports()
    assert requests_of(session_id) == [("failed", "render_failed", False)]
    assert snapshots() == 0
    failed = [entry for entry in logs if entry["event"] == "report_render_failed"]
    assert failed and failed[0]["exc_type"] == "RuntimeError"
    assert name not in json.dumps(logs, default=str) and "token" not in json.dumps(
        logs, default=str
    )
    assert (await state(email(0), session_id)).json()["status"] == "failed"
    assert code(await file(email(0), session_id)) == (409, "report_not_ready")

    # «Prøv igjen»: a new request and a new render.
    monkeypatch.setattr(render, "to_pdf", converter["to_pdf"])
    assert (await press(email(0), session_id)).status_code == 202
    await run_reports()
    assert requests_of(session_id) == [("failed", "render_failed", False), ("ready", None, True)]


async def _fake(url: str) -> bytes:
    return FAKE_PDF


async def test_a_render_that_never_ended_gives_way_to_a_new_press(klass, monkeypatch, files):
    session_id, seated = await locked_session(klass)
    set_clock(monkeypatch, AFTER)
    old = AFTER - timedelta(seconds=get_settings().report_stale_seconds + 1)
    execute(
        "INSERT INTO report_requests (id, class_session_id, user_id, requested_by, variant, "
        "status, requested_at) VALUES (%s, %s, %s, %s, 'standard', 'pending', %s)",
        uuid.uuid7(),
        session_id,
        seated[0],
        seated[0],
        old,
    )
    assert (await state(email(0), session_id)).json()["status"] == "failed"
    assert (await press(email(0), session_id)).json()["status"] == "pending"
    assert requests_of(session_id) == [("failed", "stale", False), ("pending", None, False)]
    # A job delivered for a request no longer pending renders nothing.
    stale_id = rows("SELECT id FROM report_requests WHERE failure = 'stale'")[0][0]
    assert await render.render(stale_id) == "skipped"
    assert snapshots() == 0


async def test_the_report_is_refused_alike_outside_the_students_own_class_session(
    klass, monkeypatch
):
    session_id, _ = await locked_session(klass)
    set_clock(monkeypatch, AFTER)
    refusals = [
        await state(OTHER, session_id),
        await press(OTHER, session_id),
        await file(OTHER, session_id),
        await state(LECTURER, session_id),
        await press(LECTURER, session_id),
        await state(email(0), str(uuid.uuid7())),
        await press(email(0), "not-an-id"),
    ]
    assert {(r.status_code, r.text) for r in refusals} == {
        (refusals[0].status_code, refusals[0].text)
    }
    assert code(refusals[0]) == (403, "forbidden")
    # No Test deadline: never open.
    execute("UPDATE class_sessions SET test_deadline = NULL WHERE id = %s", session_id)
    assert (await state(email(0), session_id)).json()["opens_at"] is None
    assert code(await press(email(0), session_id)) == (409, "report_not_open")
    assert code(await file(email(0), session_id)) == (409, "report_not_open")


async def test_an_expired_snapshot_is_refused_and_swept_by_the_next_render(
    klass, monkeypatch, files
):
    session_id, seated = await locked_session(klass)
    set_clock(monkeypatch, AFTER)
    await press(email(0), session_id)
    request_id = rows("SELECT id FROM report_requests")[0][0]
    token = "a-token"
    execute(
        "INSERT INTO report_snapshots (id, request_id, token_hash, expires_at, data) "
        "VALUES (%s, %s, %s, %s, '{}')",
        uuid.uuid7(),
        request_id,
        render.token_hash(token),
        AFTER - MINUTE,
    )
    snapshot_id = rows("SELECT id FROM report_snapshots")[0][0]
    async with client() as c:
        late = await c.get(
            f"/api/internal/report-snapshots/{snapshot_id}", headers={"X-Render-Token": token}
        )
        assert code(late) == (404, "not_found")
        assert "data" not in late.text
        assert (await c.get("/api/internal/report-snapshots/nope")).status_code == 404
    monkeypatch.setattr(render, "to_pdf", _fake)
    await run_reports()
    assert snapshots() == 0


async def test_the_sweep_purges_a_snapshot_a_killed_render_left_behind(klass, monkeypatch):
    session_id, _ = await locked_session(klass)
    set_clock(monkeypatch, AFTER)
    await press(email(0), session_id)
    request_id = rows("SELECT id FROM report_requests")[0][0]
    for expires in (AFTER - MINUTE, AFTER + MINUTE):
        execute(
            "INSERT INTO report_snapshots (id, request_id, token_hash, expires_at, data) "
            "VALUES (%s, %s, %s, %s, '{}')",
            uuid.uuid7(),
            request_id,
            render.token_hash("t"),
            expires,
        )
    # The sweep's action (the whole sweep takes seconds: its own action is called here).
    [action] = [a for a in sweep.DUE_ACTIONS if a.name == "reports.purge_snapshots"]
    for item in await action.find(AFTER):
        assert await action.act(item, AFTER) == 1
    assert snapshots() == 1  # the live one stays for its render


async def test_a_print_page_that_did_not_read_the_snapshot_is_no_report(klass, monkeypatch, files):
    session_id, _ = await locked_session(klass)
    set_clock(monkeypatch, AFTER)
    monkeypatch.setattr(render, "to_pdf", _fake)  # a PDF, but of a page that read nothing
    await press(email(0), session_id)
    await run_reports()
    assert requests_of(session_id) == [("failed", "render_failed", False)]
    assert not (files / "reports").exists()
