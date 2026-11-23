"""A Student's own Student report (Story 13.7, FR-57, NFR-7, AD-8, AD-9, AD-12, AD-14, AD-18).

The api never builds report content. A press records a `report_requests` row and defers
`reports.render_report(request_id)` on `reports-single` in the same transaction (ids only); the job
(`render.py`) builds, renders and stores the PDF and emits `user:<student>`. A pending request
answers a second press, so one render runs at a time per Student, Class session and variant. A
pending request older than `REPORT_STALE_SECONDS` reads as failed (a crashed worker), and the next
press replaces it. The download is a signed URL made only after the policy allowed it.

Reach (policy `reports.download_own`): the Student's own Class session, through
`sessions.own_report_session` (enrolled, listed on Hjem, locked); every other case is one answer,
None (403). It opens at the Student's effective Test deadline (`sessions.report_opens_at`); before
it, or with none, a press is refused with `report_not_open`. Story 13.12 adds the staff's way in to
the same request and job; Story 15.1's «Mine data» reuses this one."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

import structlog

from app.modules.reports import repo, scope
from app.modules.reports.report_data import ReportOptions
from app.modules.sessions import service as sessions
from app.platform import auth, authz, events, jobs, storage
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker

__all__ = [
    "DOWNLOAD_OWN",
    "RENDER_TASK",
    "ReportRefused",
    "ReportState",
    "download_name",
    "object_path",
    "own_file_url",
    "own_state",
    "request_own",
]

log = structlog.get_logger(__name__)

DOWNLOAD_OWN = "reports.download_own"
"""A Student's own report: any User, held to their own Class session here."""

RENDER_TASK = "reports.render_report"
REQUESTED = "reports.request_report"
"""The registry name of a press: it emits the Student's `user` topic (the pending state)."""


class ReportRefused(Exception):
    """409: `report_not_open` (before the Student's effective Test deadline, or none),
    `not_counted` (a Student reports leave out), `report_not_ready` (no PDF to download yet)."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


Status = Literal["none", "pending", "ready", "failed"]


@dataclass(frozen=True)
class ReportState:
    """Where the Student's report stands: when it opens, whether it is open now, the latest
    request's status, and when the PDF that can be downloaded was made."""

    opens_at: datetime | None
    open: bool
    status: Status
    generated_at: datetime | None


def object_path(
    class_session_id: uuid.UUID, user_id: uuid.UUID, variant: str, request_id: uuid.UUID
) -> str:
    """Where a render's PDF lives in the `reports` bucket: keyed by Class session and `user_id`,
    never a name (AD-14), and by the request, so a late render never overwrites a newer one. The
    job deletes the earlier PDFs once a new one is ready."""
    name = "student-report" if variant == "standard" else f"student-report-{variant}"
    return f"class-sessions/{class_session_id}/{user_id}/{name}-{request_id}.pdf"


def download_name(number: int | None = None) -> str:
    """The file name the browser saves: no name of a person in it."""
    return "studentrapport.pdf" if number is None else f"studentrapport-klasseokt-{number}.pdf"


def _status(latest: repo.ReportRequest | None, now: datetime) -> Status:
    if latest is None:
        return "none"
    if latest.status == "pending":
        stale = timedelta(seconds=get_settings().report_stale_seconds)
        return "failed" if latest.requested_at + stale <= now else "pending"
    return latest.status  # type: ignore[return-value]


def _is_open(opens_at: datetime | None, now: datetime) -> bool:
    return opens_at is not None and opens_at <= now


async def own_state(
    user: authz.Principal, class_session_id: uuid.UUID, options: ReportOptions | None = None
) -> ReportState | None:
    """The Student's own report state in the Class session; None (403) for every other case."""
    options = options or ReportOptions()
    now = auth.utcnow()
    async with get_sessionmaker()() as s:
        row = await sessions.own_report_session(s, user, class_session_id)
        if row is None:
            return None
        latest, ready = await repo.latest_report_requests(
            s, class_session_id, user.id, options.variant
        )
    opens_at = sessions.report_opens_at(user, row)
    return ReportState(
        opens_at=opens_at,
        open=_is_open(opens_at, now),
        status=_status(latest, now),
        generated_at=None if ready is None else ready.finished_at,
    )


async def request_own(
    user: authz.Principal, class_session_id: uuid.UUID, options: ReportOptions | None = None
) -> ReportState | None:
    """«Lag Studentrapport»: record the request and defer its render; a pending one answers
    itself. None (403) for every other case; raises `ReportRefused`."""
    options = options or ReportOptions()
    now = auth.utcnow()
    async with get_sessionmaker().begin() as s:
        row = await sessions.own_report_session(s, user, class_session_id)
        if row is None:
            return None
        opens_at = sessions.report_opens_at(user, row)
        if not _is_open(opens_at, now):
            raise ReportRefused("report_not_open")
        if user.id not in await scope.reporting_students(s, class_session_id):
            raise ReportRefused("not_counted")
        latest, ready = await repo.latest_report_requests(
            s, class_session_id, user.id, options.variant
        )
        if latest is not None and latest.status == "pending" and _status(latest, now) == "failed":
            # A render that never ended (a crashed worker): it gives way to this press.
            await repo.finish_report_request(s, latest.id, status="failed", at=now, failure="stale")
        request_id = await repo.insert_report_request(
            s,
            class_session_id=class_session_id,
            user_id=user.id,
            requested_by=user.id,
            variant=options.variant,
            requested_at=now,
        )
        if request_id is not None:
            await jobs.defer(
                s,
                RENDER_TASK,
                queue=jobs.REPORTS_SINGLE,
                queueing_lock=f"report:{request_id}",
                request_id=str(request_id),
            )
            await events.emit(s, "user", str(user.id))
            log.info(
                "report_requested",
                request_id=str(request_id),
                class_session_id=str(class_session_id),
            )
    return ReportState(
        opens_at=opens_at,
        open=True,
        status="pending",
        generated_at=None if ready is None else ready.finished_at,
    )


async def own_file_url(
    user: authz.Principal, class_session_id: uuid.UUID, options: ReportOptions | None = None
) -> str | None:
    """A signed URL of the Student's latest ready PDF, made only now that the policy allowed it
    (NFR-7, AD-12). None (403) for every other case; raises `ReportRefused`."""
    options = options or ReportOptions()
    now = auth.utcnow()
    async with get_sessionmaker()() as s:
        row = await sessions.own_report_session(s, user, class_session_id)
        if row is None:
            return None
        if not _is_open(sessions.report_opens_at(user, row), now):
            raise ReportRefused("report_not_open")
        if user.id not in await scope.reporting_students(s, class_session_id):
            raise ReportRefused("not_counted")
        _, ready = await repo.latest_report_requests(s, class_session_id, user.id, options.variant)
        heading = await sessions.report_heading(s, class_session_id, user.id)
    if ready is None or ready.object_path is None:
        raise ReportRefused("report_not_ready")
    number = None if heading is None else heading.number
    return await storage.get_storage().signed_url(
        storage.REPORTS, ready.object_path, download_name=download_name(number)
    )
