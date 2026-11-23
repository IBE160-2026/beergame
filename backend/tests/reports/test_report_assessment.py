"""Story 13.11 (FR-58, FR-55, FR-56, FR-61, FR-34, AD-18): the Student adds the AI assessment
section to their own Student report.

The choice is a report variant: `standard` (default, no AI data), `ai`, or `ai_letter` when the
Indicative letter's gate (`assessment.letter_for`, reader `report`) gives the Student a letter.
Each variant is its own request and its own stored PDF. On the mock provider; the converter is
the fake of `test_student_report` that reads the snapshot as the print route does."""

import json
import uuid

from app.modules.identity.schemas import AccountRole
from app.modules.reports import report, report_data
from app.platform.db import get_sessionmaker
from tests.assessment.test_assess import LONG
from tests.assessment.test_letter import (
    ADMIN,
    TIGHT,
    _empty,
    assessed,
    clock,
    emitted,
    expected,
    institution_of,
    klass,
    letter_url,
    locked,
    no_letter,
    own,
    save,
)
from tests.classes.test_classes import make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_staff import call
from tests.debrief.test_explanation import user_id
from tests.messaging.helpers import rows
from tests.reports.test_student_report import (
    code,
    converter,
    files,
    report_path,
    run_reports,
    snapshots,
)
from tests.sessions.test_dates import TEST
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "converter", "emitted", "files", "klass"]

ME = email(0)


async def state(session_id: str, *, ai: bool = False, who: str = ME) -> dict:
    found = await call(who, "GET", report_path(session_id) + ("?ai=true" if ai else ""))
    assert found.status_code == 200, found.text
    return found.json()


async def press(session_id: str, *, ai: bool | None = None, who: str = ME):
    body = None if ai is None else {"ai": ai}
    return await call(who, "POST", report_path(session_id), json=body)


async def file(session_id: str, *, ai: bool = False, who: str = ME):
    return await call(who, "GET", report_path(session_id) + "/file" + ("?ai=true" if ai else ""))


def variants(session_id: str) -> list[tuple]:
    return rows(
        "SELECT variant, status, failure, object_path FROM report_requests "
        "WHERE class_session_id = %s ORDER BY requested_at, id",
        session_id,
    )


def section(data: dict, kind: str) -> dict | None:
    return next((each for each in data["sections"] if each["kind"] == kind), None)


async def test_off_by_default_the_report_has_no_ai_data_and_on_it_has_its_own_section(
    klass, monkeypatch, files, converter
):
    session_id = await locked(klass, monkeypatch, n=2)
    await assessed(session_id, monkeypatch)
    view = await own(session_id)

    # The Bryter is offered; untouched, the standard report, as before Story 13.11.
    before = await state(session_id)
    assert (before["ai_available"], before["ai"], before["status"]) == (True, False, "none")
    assert (await press(session_id)).status_code == 202
    await run_reports()
    standard = converter["data"][-1]
    assert [each["kind"] for each in standard["sections"]] == [
        "completion",
        "game",
        "debrief",
        "replay",
        "test",
    ]
    dumped = json.dumps(standard)
    for key in ('"assessment"', '"letter"', '"feedback"', '"total_max"', '"feedback_dropped"'):
        assert key not in dumped

    # On: a request of its own, the section with every item, the total and no letter (the
    # Student has not turned the letter on for their own view).
    asked = await state(session_id, ai=True)
    assert (asked["ai"], asked["status"], asked["generated_at"]) == (True, "none", None)
    pressed = await press(session_id, ai=True)
    assert pressed.status_code == 202 and pressed.json()["ai"] is True
    await run_reports()
    added = section(converter["data"][-1], "assessment")
    assert added is not None
    assert (added["total"], added["total_max"], added["letter"]) == (
        view["total"],
        view["total_max"],
        None,
    )
    assert [item["number"] for item in added["items"]] == [i["number"] for i in view["items"]]
    long_item = next(item for item in added["items"] if item["ai"] is not None)
    assert long_item["ai"]["feedback"]["ai_generated"] is True
    assert long_item["computed"] is None and "flagged" not in json.dumps(added)

    # Stored apart: the standard download never serves the PDF with the section.
    [(v1, s1, _, plain), (v2, s2, _, with_ai)] = variants(session_id)
    assert (v1, s1, v2, s2) == ("standard", "ready", "ai", "ready")
    assert "/student-report-ai-" in with_ai and "/student-report-ai-" not in plain
    assert plain in (await file(session_id)).headers["location"]
    assert with_ai in (await file(session_id, ai=True)).headers["location"]
    assert (await state(session_id))["status"] == "ready"


async def test_the_letter_goes_in_only_as_the_students_own_view_shows_it(
    klass, monkeypatch, files, converter
):
    session_id = await locked(klass, monkeypatch, n=2)
    await assessed(session_id, monkeypatch)
    view = await own(session_id)
    assert (await call(ME, "PUT", letter_url(session_id), json={"on": True})).status_code == 200

    # Turned on for their own view: the variant with the letter, and the letter in the section.
    assert (await press(session_id, ai=True)).status_code == 202
    await run_reports()
    assert section(converter["data"][-1], "assessment")["letter"] == expected(view)
    assert variants(session_id)[-1][:2] == ("ai_letter", "ready")

    # Turned off again: that PDF is not this variant's; the next one has no letter.
    assert (await call(ME, "PUT", letter_url(session_id), json={"on": False})).status_code == 200
    now = await state(session_id, ai=True)
    assert (now["ai"], now["status"], now["generated_at"]) == (True, "none", None)
    assert code(await file(session_id, ai=True)) == (409, "report_not_ready")

    # Turned off between the press and the render: built without the letter.
    assert (await call(ME, "PUT", letter_url(session_id), json={"on": True})).status_code == 200
    assert (await press(session_id, ai=True)).status_code == 202
    assert (await call(ME, "PUT", letter_url(session_id), json={"on": False})).status_code == 200
    await run_reports()
    assert section(converter["data"][-1], "assessment")["letter"] is None


async def test_shown_to_everyone_the_letter_is_in_and_where_unavailable_never(
    klass, monkeypatch, files, converter
):
    session_id = await locked(klass, monkeypatch)
    assert (
        await save(session_id, letter_setting="all", letter_thresholds=TIGHT)
    ).status_code == 200
    await assessed(session_id, monkeypatch)
    view = await own(session_id)
    assert (await press(session_id, ai=True)).status_code == 202
    await run_reports()
    assert section(converter["data"][-1], "assessment")["letter"] == expected(view, TIGHT)

    # A report not asked by the Student never carries it (the gate's `requested_by_student`).
    async with get_sessionmaker()() as s:
        built = await report_data.build_report_data(
            s,
            user_id(ME),
            uuid.UUID(session_id),
            report_data.ReportOptions(variant="ai_letter", requested_by_student=False),
            now=TEST,
        )
    assert section(built.model_dump(mode="json"), "assessment")["letter"] is None

    # The Institution forbids the letter: the variant without it, and no letter in the section.
    await make(ADMIN, roles=(AccountRole.admin,))
    assert (await no_letter(institution_of(klass), True)).status_code == 200
    assert (await press(session_id, ai=True)).status_code == 202
    await run_reports()
    assert variants(session_id)[-1][:2] == ("ai", "ready")
    assert section(converter["data"][-1], "assessment")["letter"] is None


async def test_dropped_feedback_keeps_its_note(klass, monkeypatch, files, converter):
    session_id = await locked(klass, monkeypatch)
    await assessed(session_id, monkeypatch)
    execute(
        "UPDATE ai_item_scores SET feedback = NULL, feedback_note = 'dropped' WHERE item_id = %s",
        LONG[0],
    )
    assert (await press(session_id, ai=True)).status_code == 202
    await run_reports()
    added = section(converter["data"][-1], "assessment")
    dropped = next(item for item in added["items"] if item["ai"] and item["ai"]["feedback_dropped"])
    assert dropped["ai"]["feedback"] is None and dropped["ai"]["step"] is not None


async def test_without_a_ready_assessment_the_section_is_not_offered_and_is_refused(
    klass, monkeypatch, files, converter
):
    session_id = await locked(klass, monkeypatch, n=2)
    await assessed(session_id, monkeypatch, status="incomplete")
    for who in (ME, email(1)):  # incomplete; no test handed in at all
        found = await state(session_id, who=who)
        assert (found["ai_available"], found["ai"]) == (False, False)
        # Asked anyway, the state is the standard report's.
        assert (await state(session_id, ai=True, who=who))["ai"] is False
        assert code(await press(session_id, ai=True, who=who)) == (409, "ai_assessment_unavailable")
        assert code(await file(session_id, ai=True, who=who)) == (409, "ai_assessment_unavailable")
    assert variants(session_id) == []
    # The standard report is made as before.
    assert (await press(session_id, ai=False)).status_code == 202
    assert variants(session_id)[0][0] == "standard"


async def test_no_longer_ready_between_the_press_and_the_render_fails_and_stores_nothing(
    klass, monkeypatch, files, converter
):
    session_id = await locked(klass, monkeypatch)
    await assessed(session_id, monkeypatch)
    assert (await press(session_id, ai=True)).status_code == 202
    # No longer ready (the switch is pinned at the Test deadline; a run that failed is the case).
    execute("UPDATE ai_assessments SET status = 'failed'")
    await run_reports()
    assert variants(session_id) == [("ai", "failed", "ai_unavailable", None)]
    assert snapshots() == 0 and converter["data"] == []
    assert (await state(session_id))["ai_available"] is False


async def test_a_fault_reading_the_assessment_never_stops_the_standard_report(
    klass, monkeypatch, files, converter
):
    session_id = await locked(klass, monkeypatch)
    await assessed(session_id, monkeypatch)

    async def broken(*args, **kwargs):
        raise RuntimeError("the assessment cannot be read")

    monkeypatch.setattr(report.tests, "report_assessment", broken)
    found = await state(session_id)
    assert (found["ai_available"], found["ai"]) == (False, False)
    assert (await press(session_id)).status_code == 202
    await run_reports()
    assert variants(session_id)[0][:2] == ("standard", "ready")
    assert (await file(session_id)).status_code == 303
