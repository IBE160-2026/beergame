"""The ZIP of all Student reports of a Class session (Story 13.13, FR-59, NFR-7, AD-9, AD-12,
AD-13, AD-14, AD-18).

A press of «Last ned alle Studentrapporter (ZIP)» in the Klasseøkt's «Eksport» block records a
`report_zips` row and defers `reports.build_zip(zip_id)` on `reports-bulk` in the same
transaction (ids only). One ZIP is pending per Class session; a second press, by anyone of its
staff, answers it. A pending ZIP older than `REPORT_ZIP_STALE_SECONDS` reads as failed (a crashed
worker), and the next press replaces it.

The job renders one report per Student in `scope.reporting_students` through the one assembler
(`report_data.build_report_data`), always with `ReportOptions(variant="staff")`: never the AI
assessment section and never the Indicative letter, whatever the press asked (C-2). Each report
goes through a snapshot with a single-use render token, the print route and the converter, as the
single report (`render.py`); `REPORT_ZIP_CONCURRENCY` of them at once. The PDFs are written into a
ZIP in a temporary file, named by the Student's name so a Lecturer finds a Student; the ZIP is
stored in the `reports` bucket under the Class session's path, keyed by the request, never a
name (AD-14). A Student who stops being reportable meanwhile is left out; any other failure fails
the whole ZIP (`render_failed`), never a partial one.

Idempotent on Class session and request: a ZIP no longer pending is left alone, so a job
delivered twice builds once, and a retried job writes its own object again. Once ready, the
Class session's earlier ZIPs are deleted, so one stays; the requester gets a `reports_zip_ready`
notice. The download is a signed URL made only after the policy (`reports.download`) allowed
the caller."""

from __future__ import annotations

import asyncio
import re
import secrets
import tempfile
import unicodedata
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

import structlog

from app.modules.classes import service as classes
from app.modules.reports import render, repo, scope
from app.modules.reports.report import DOWNLOAD, ReportRefused
from app.modules.reports.report_data import NotReportable, ReportOptions, build_report_data
from app.modules.sessions import service as sessions
from app.platform import audit, auth, authz, events, jobs, notify, storage
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker

__all__ = [
    "BUILD_TASK",
    "OPTIONS",
    "ZipState",
    "build",
    "build_zip",
    "file_names",
    "request_zip",
    "zip_file_url",
    "zip_object_path",
    "zip_state",
]

log = structlog.get_logger(__name__)

BUILD_TASK = "reports.build_zip"
REQUESTED = "reports.request_zip"
"""The registry name of a press: it emits the requester's `user` topic (the pending state)."""

REQUESTED_AUDIT = "report_zip.requested"
DOWNLOADED_AUDIT = "report_zip.downloaded"

OPTIONS = ReportOptions(variant="staff")
"""The one option set every report in the ZIP is built with: no AI assessment section, no
Indicative letter (FR-59, C-2). Nothing a caller sends reaches it."""

Status = Literal["none", "pending", "ready", "failed"]


@dataclass(frozen=True)
class ZipState:
    """Where the Class session's ZIP stands: the latest request's status, when the ZIP that can be
    downloaded was made and how many reports it holds; `deleted` once the Student data is."""

    status: Status
    generated_at: datetime | None
    students: int | None
    deleted: bool = False


def zip_object_path(class_session_id: uuid.UUID, zip_id: uuid.UUID) -> str:
    """Where the ZIP lives in the `reports` bucket: under the Class session's path, keyed by the
    request, never a name (AD-14)."""
    return f"class-sessions/{class_session_id}/bundles/student-reports-{zip_id}.zip"


def download_name(number: int | None) -> str:
    """The file name the browser saves: no name of a person in it."""
    return "studentrapporter.zip" if number is None else f"studentrapporter-klasseokt-{number}.zip"


_UNSAFE = re.compile(r'[\x00-\x1f\x7f/\\:*?"<>|]+')


def _plain(name: str) -> str:
    cleaned = " ".join(_UNSAFE.sub("-", unicodedata.normalize("NFC", name)).split()).strip(" .-")
    return cleaned[:120].rstrip(" .-")


def file_names(names: dict[uuid.UUID, str], students: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    """Each Student's file in the ZIP, by their name now so a Lecturer finds them
    (`Kari Nordmann.pdf`): characters a file system refuses are replaced; a name that repeats
    (ignoring case), and a Student without one, gets the last 8 hex digits of the `user_id`
    (its random part: a UUIDv7 begins with its creation time)."""
    plain = {student: _plain(names.get(student, "")) for student in students}
    seen: dict[str, int] = {}
    for name in plain.values():
        seen[name.casefold()] = seen.get(name.casefold(), 0) + 1
    out = {}
    for student, name in plain.items():
        short = student.hex[-8:]
        if not name:
            out[student] = f"Student {short}.pdf"
        elif seen[name.casefold()] > 1:
            out[student] = f"{name} ({short}).pdf"
        else:
            out[student] = f"{name}.pdf"
    return out


def _status(latest: repo.ReportZip | None, now: datetime) -> Status:
    if latest is None:
        return "none"
    if latest.status == "pending":
        stale = timedelta(seconds=get_settings().report_zip_stale_seconds)
        return "failed" if latest.requested_at + stale <= now else "pending"
    return latest.status  # type: ignore[return-value]


async def _reached(user: authz.Principal, class_session_id: uuid.UUID):
    """The Class session's row when `user` is staff of its Class with `reports.download`; None,
    one answer, for every other case (FR-5)."""
    return await sessions.staff_session_row(user, class_session_id, DOWNLOAD)


async def zip_state(user: authz.Principal, class_session_id: uuid.UUID) -> ZipState | None:
    """The Class session's ZIP for its staff; None (403) for every other case."""
    row = await _reached(user, class_session_id)
    if row is None:
        return None
    now = auth.utcnow()
    if sessions.data_deleted(row, now):
        return ZipState(status="none", generated_at=None, students=None, deleted=True)
    async with get_sessionmaker()() as s:
        latest, ready = await repo.latest_zips(s, class_session_id)
    return ZipState(
        status=_status(latest, now),
        generated_at=None if ready is None else ready.finished_at,
        students=None if ready is None else ready.students,
    )


async def request_zip(user: authz.Principal, class_session_id: uuid.UUID) -> ZipState | None:
    """«Last ned alle Studentrapporter (ZIP)»: record the request and defer its job on
    `reports-bulk`, recorded in the audit log; a pending one answers itself. None (403) for every
    other case, with nothing written; raises `ReportRefused` (`data_deleted`, `no_students`)."""
    row = await _reached(user, class_session_id)
    if row is None:
        return None
    now = auth.utcnow()
    if sessions.data_deleted(row, now):
        raise ReportRefused("data_deleted")
    async with get_sessionmaker().begin() as s:
        if not await scope.reporting_students(s, class_session_id):
            raise ReportRefused("no_students")
        latest, ready = await repo.latest_zips(s, class_session_id)
        if latest is not None and latest.status == "pending" and _status(latest, now) == "failed":
            # A job that never ended (a crashed worker): it gives way to this press.
            await repo.finish_zip(s, latest.id, status="failed", at=now, failure="stale")
        zip_id = await repo.insert_zip(
            s, class_session_id=class_session_id, requested_by=user.id, requested_at=now
        )
        if zip_id is not None:
            await jobs.defer(
                s,
                BUILD_TASK,
                queue=jobs.REPORTS_BULK,
                queueing_lock=f"zip:{zip_id}",
                zip_id=str(zip_id),
            )
            await events.emit(s, "user", str(user.id))
            await audit.record(
                s,
                user.id,
                REQUESTED_AUDIT,
                {"class_session_id": class_session_id, "zip_id": zip_id},
                {},
                now,
            )
            log.info("reports_zip_requested", zip_id=str(zip_id))
    return ZipState(
        status="pending",
        generated_at=None if ready is None else ready.finished_at,
        students=None if ready is None else ready.students,
    )


async def zip_file_url(user: authz.Principal, class_session_id: uuid.UUID) -> str | None:
    """A signed URL of the Class session's latest ready ZIP, made only now that the policy allowed
    it (NFR-7, AD-12), recorded in the audit log. None (403) for every other case; raises
    `ReportRefused` (`data_deleted`, `zip_not_ready`)."""
    row = await _reached(user, class_session_id)
    if row is None:
        return None
    now = auth.utcnow()
    if sessions.data_deleted(row, now):
        raise ReportRefused("data_deleted")
    async with get_sessionmaker()() as s:
        _, ready = await repo.latest_zips(s, class_session_id)
        heading = await sessions.report_heading(s, class_session_id, user.id)
    if ready is None or ready.object_path is None:
        raise ReportRefused("zip_not_ready")
    url = await storage.get_storage().signed_url(
        storage.REPORTS,
        ready.object_path,
        download_name=download_name(None if heading is None else heading.number),
    )
    async with get_sessionmaker().begin() as s:
        await audit.record(
            s,
            user.id,
            DOWNLOADED_AUDIT,
            {"class_session_id": class_session_id, "zip_id": ready.id},
            {},
            now,
        )
    return url


# The job.


async def _render_one(found: repo.ReportZip, student: uuid.UUID) -> bytes | None:
    """One Student's report through a snapshot, the print route and the converter; None when the
    Student is no longer one reports count. The snapshot goes whatever happens."""
    now = auth.utcnow()
    token = secrets.token_urlsafe(32)
    try:
        async with get_sessionmaker().begin() as s:
            data = await build_report_data(s, student, found.class_session_id, OPTIONS, now=now)
            snapshot_id = await repo.insert_snapshot(
                s,
                zip_id=found.id,
                token_hash=render.token_hash(token),
                expires_at=now + render.TOKEN_LIFETIME,
                data=data.model_dump(mode="json"),
            )
    except NotReportable:
        log.info("reports_zip_student_left_out", zip_id=str(found.id))
        return None
    try:
        pdf = await render.to_pdf(render.print_url(snapshot_id, token))
        if not pdf.startswith(b"%PDF-"):
            raise RuntimeError("not a PDF")
        async with get_sessionmaker()() as s:
            if not await repo.snapshot_used(s, snapshot_id):
                raise RuntimeError("the print route did not read the snapshot")
        return pdf
    finally:
        async with get_sessionmaker().begin() as s:
            await repo.delete_snapshot(s, snapshot_id)


async def _write_zip(found: repo.ReportZip, students: list[uuid.UUID], names: dict) -> tuple:
    """The ZIP's bytes and how many reports it holds, rendering `REPORT_ZIP_CONCURRENCY` reports
    at once and writing each PDF as it is ready. After the first failure no further report is
    started; the ones under way end on their own (so each deletes its snapshot, never cut off in
    the middle of a transaction), and the failure is raised."""
    waiting = list(reversed(students))
    failures: list[BaseException] = []
    written = 0
    with tempfile.SpooledTemporaryFile(max_size=16 * 1024 * 1024) as spool:
        with zipfile.ZipFile(spool, "w", compression=zipfile.ZIP_STORED) as archive:

            async def renderer() -> None:
                nonlocal written
                while waiting and not failures:
                    student = waiting.pop()
                    try:
                        pdf = await _render_one(found, student)
                    except Exception as exc:
                        failures.append(exc)
                        return
                    if pdf is not None:
                        # No await while writing: one renderer writes at a time.
                        archive.writestr(names[student], pdf)
                        written += 1

            slots = min(get_settings().report_zip_concurrency, max(len(students), 1))
            await asyncio.gather(*(renderer() for _ in range(slots)))
        if failures:
            raise failures[0]
        spool.seek(0)
        return spool.read(), written


async def build(zip_id: uuid.UUID) -> str:
    """Build the ZIP; answers what happened: `ready`, `failed` or `skipped`."""
    now = auth.utcnow()
    async with get_sessionmaker().begin() as s:
        found = await repo.report_zip(s, zip_id)
        if found is None or found.status != "pending":
            return "skipped"
        await repo.delete_expired_snapshots(s, now)
        row = await sessions.session_row(s, found.class_session_id)
        deleted = row is None or sessions.data_deleted(row, now)
        students = [] if deleted else await scope.reporting_students(s, found.class_session_id)
        class_id = await sessions.class_id_of(s, found.class_session_id)
        names = (
            {} if class_id is None else await classes.student_names(class_id, students, session=s)
        )
    outcome, path, failure, count = "failed", None, "render_failed", None
    try:
        if deleted:
            # The deletion date came while the job waited: no ZIP of Student data any more.
            raise ReportRefused("data_deleted")
        data, count = await _write_zip(found, students, file_names(names, students))
        if count == 0:
            failure = "no_students"
        else:
            path = zip_object_path(found.class_session_id, found.id)
            await storage.get_storage().put(storage.REPORTS, path, data, "application/zip")
            outcome, failure = "ready", None
    except ReportRefused as refused:
        failure = refused.code
        log.info("reports_zip_refused", zip_id=str(found.id), failure=failure)
    except Exception as exc:  # the type only: a message could hold a URL with a token
        log.error("reports_zip_failed", zip_id=str(found.id), exc_type=type(exc).__name__)
    replaced: list[str] = []
    async with get_sessionmaker().begin() as s:
        finished = await repo.finish_zip(
            s,
            found.id,
            status=outcome,
            at=auth.utcnow(),
            object_path=path if outcome == "ready" else None,
            failure=failure,
            students=count if outcome == "ready" else None,
        )
        if finished:
            if outcome == "ready":
                replaced = await repo.release_older_zips(s, found)
                if found.requested_by is not None:
                    await notify.enqueue(
                        s,
                        found.requested_by,
                        sessions.REPORTS_ZIP_READY_NOTICE,
                        f"{sessions.REPORTS_ZIP_READY_NOTICE}:{found.id}",
                        ref=found.class_session_id,
                    )
            if found.requested_by is not None:
                await events.emit(s, "user", str(found.requested_by))
    # A job no longer wanted (replaced as stale) removes its own object.
    gone = replaced if finished else ([path] if outcome == "ready" and path else [])
    for old in gone:
        try:
            await storage.get_storage().delete(storage.REPORTS, old)
        except Exception as exc:  # best effort: the row no longer points at it
            log.warning("reports_zip_delete_failed", exc_type=type(exc).__name__)
    if not finished:
        return "skipped"
    log.info("reports_zip_built", zip_id=str(found.id), outcome=outcome, students=count)
    return outcome


@jobs.app.task(name=BUILD_TASK, queue=jobs.REPORTS_BULK)
async def build_zip(zip_id: str) -> None:
    await build(uuid.UUID(zip_id))
