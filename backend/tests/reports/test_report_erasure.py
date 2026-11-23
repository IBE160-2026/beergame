"""The erasure of a Student (Story 15.2, FR-76, AD-14) and Epic 13's data: the PDFs of every Student
report about them and their request rows go, every stored ZIP of their Class sessions goes and its
row keeps no path, and the corrections of their Completion status go. Another Student's report
stays."""

import uuid
from datetime import UTC, datetime

from app.modules.identity import service as identity
from app.platform import storage
from tests.classes.test_invitation_counts import execute
from tests.messaging.helpers import rows
from tests.reports.test_student_report import files
from tests.sessions.test_allocation import students
from tests.sessions.test_dates import new_session
from tests.sessions.test_student_home import _empty, clock, klass

__all__ = ["_empty", "clock", "files", "klass"]

AT = datetime(2026, 11, 1, 12, tzinfo=UTC)


async def stored(path: str) -> str:
    await storage.get_storage().put(storage.REPORTS, path, b"%PDF-1.7 x", "application/pdf")
    return path


def request(session_id: str, user_id: uuid.UUID, path: str) -> uuid.UUID:
    request_id = uuid.uuid7()
    execute(
        "INSERT INTO report_requests (id, class_session_id, user_id, requested_by, variant, "
        "status, requested_at, finished_at, object_path) "
        "VALUES (%s, %s, %s, %s, 'standard', 'ready', %s, %s, %s)",
        request_id,
        session_id,
        user_id,
        user_id,
        AT,
        AT,
        path,
    )
    return request_id


def zipped(session_id: str, path: str) -> None:
    execute(
        "INSERT INTO report_zips (id, class_session_id, status, requested_at, finished_at, "
        "object_path, students) VALUES (%s, %s, 'ready', %s, %s, %s, 2)",
        uuid.uuid7(),
        session_id,
        AT,
        AT,
        path,
    )


async def test_erasing_a_student_deletes_their_reports_and_the_zips_that_hold_them(klass, files):
    student, other = await students(klass, 2)
    session_id = await new_session(klass)
    mine = await stored(f"class-sessions/{session_id}/{student}/student-report-a.pdf")
    theirs = await stored(f"class-sessions/{session_id}/{other}/student-report-b.pdf")
    bundle = await stored(f"class-sessions/{session_id}/bundles/student-reports-c.zip")
    request(session_id, student, mine)
    kept = request(session_id, other, theirs)
    zipped(session_id, bundle)
    execute(
        "INSERT INTO completion_corrections (id, user_id, class_session_id, step, done, reason, "
        "at) VALUES (%s, %s, %s, 'debrief', true, 'Syk, levert muntlig', %s)",
        uuid.uuid7(),
        student,
        session_id,
        AT,
    )

    assert await identity.erase_user(student, now=AT) is True

    folder = files / storage.REPORTS
    assert not (folder / mine).exists() and not (folder / bundle).exists()
    assert (folder / theirs).exists()
    assert rows("SELECT id FROM report_requests") == [(kept,)]
    assert rows("SELECT object_path, status FROM report_zips") == [(None, "ready")]
    assert rows("SELECT count(*) FROM completion_corrections") == [(0,)]
    # A repeat finds nothing left to do.
    assert await identity.erase_user(student, now=AT) is True
    assert rows("SELECT id FROM report_requests") == [(kept,)]
