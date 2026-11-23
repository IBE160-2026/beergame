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
it, or with none, a press is refused with `report_not_open`. Story 15.1's «Mine data» reuses this
one.

Story 13.12 (policy `reports.download`): the staff of the Class make and download one Student's
report at any time through the same request and job (`_press`). Their downloads are the variants
`staff` and `staff_ai`, shared by the staff and apart from the Student's own; no staff download
ever carries the Indicative letter."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reports import repo, scope
from app.modules.reports.report_data import ReportVariant
from app.modules.sessions import service as sessions
from app.modules.tests import service as tests
from app.platform import audit, auth, authz, events, jobs, storage
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker

__all__ = [
    "DOWNLOAD",
    "DOWNLOAD_OWN",
    "RENDER_TASK",
    "ReportRefused",
    "ReportState",
    "download_name",
    "object_path",
    "own_file_url",
    "own_state",
    "request_own",
    "request_staff",
    "staff_file_url",
    "staff_state",
]

log = structlog.get_logger(__name__)

DOWNLOAD_OWN = "reports.download_own"
"""A Student's own report: any User, held to their own Class session here."""

RENDER_TASK = "reports.render_report"
REQUESTED = "reports.request_report"
"""The registry name of a press: it emits the Student's `user` topic (the pending state)."""


class ReportRefused(Exception):
    """409: `report_not_open` (before the Student's effective Test deadline, or none),
    `not_counted` (a Student reports leave out), `report_not_ready` (no PDF to download yet),
    `ai_assessment_unavailable` (the AI section asked for while the Student's AI assessment is not
    ready, Story 13.11), `data_deleted` (the staff's report of a Student whose data is deleted,
    Story 13.12)."""

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
    ai: bool = False
    """Story 13.11: this state is the variant with the AI assessment section."""
    ai_available: bool = False
    """Story 13.11: the Student's AI assessment is ready, so the section may be added."""
    deleted: bool = False
    """Story 13.12: the Student's data in the Class session is deleted; no report is built."""


@dataclass(frozen=True)
class _Choice:
    variant: ReportVariant
    ai_available: bool


STANDARD = _Choice("standard", False)
"""The standard report, without reading the AI assessment (a press or a download without `ai`)."""


async def _available(user_id: uuid.UUID, class_session_id: uuid.UUID) -> bool:
    """Whether the Bryter is offered (Story 13.11). A fault reading the AI assessment only hides
    the Bryter: the standard report's state, press and download never depend on it."""
    try:
        return (await _choice(user_id, class_session_id, False)).ai_available
    except Exception as exc:
        log.warning("report_ai_available_unread", exc_type=type(exc).__name__)
        return False


async def _choice(user_id: uuid.UUID, class_session_id: uuid.UUID, ai: bool) -> _Choice:
    """The variant the Student's choice names now (Story 13.11): `standard` unless they add the
    AI section and their AI assessment is ready; then `ai_letter` when the Indicative letter's
    gate (`letter_for`, reader `report`, asked by the Student) gives a letter, else `ai`. The
    letter's state is part of the variant, so a later change of their letter choice never serves
    a PDF made under the other."""
    found = await tests.report_assessment(user_id, class_session_id, requested_by_student=True)
    if found is None:
        return _Choice("standard", False)
    if not ai:
        return _Choice("standard", True)
    return _Choice("ai_letter" if found.letter is not None else "ai", True)


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
    user: authz.Principal, class_session_id: uuid.UUID, *, ai: bool = False
) -> ReportState | None:
    """The Student's own report state in the Class session, for the variant `ai` names (the
    standard one while the AI section cannot be added); None (403) for every other case."""
    now = auth.utcnow()
    async with get_sessionmaker()() as s:
        row = await sessions.own_report_session(s, user, class_session_id)
    if row is None:
        return None
    if ai:
        choice = await _choice(user.id, class_session_id, True)
    else:
        choice = _Choice("standard", await _available(user.id, class_session_id))
    async with get_sessionmaker()() as s:
        latest, ready = await repo.latest_report_requests(
            s, class_session_id, user.id, choice.variant
        )
    opens_at = sessions.report_opens_at(user, row)
    return ReportState(
        opens_at=opens_at,
        open=_is_open(opens_at, now),
        status=_status(latest, now),
        generated_at=None if ready is None else ready.finished_at,
        ai=choice.variant != "standard",
        ai_available=choice.ai_available,
    )


async def _press(
    s: AsyncSession,
    *,
    class_session_id: uuid.UUID,
    student_id: uuid.UUID,
    requested_by: uuid.UUID,
    variant: ReportVariant,
    now: datetime,
) -> tuple[uuid.UUID | None, repo.ReportRequest | None]:
    """Record a pending request of `variant` and defer its render on `reports-single` in `s`
    (ids only), emitting the requester's `user` topic; a pending one answers itself (None). Also
    answers the latest ready request of the variant. The one press of the Student's own report
    and of the staff's (Story 13.12): one pipeline."""
    latest, ready = await repo.latest_report_requests(s, class_session_id, student_id, variant)
    if latest is not None and latest.status == "pending" and _status(latest, now) == "failed":
        # A render that never ended (a crashed worker): it gives way to this press.
        await repo.finish_report_request(s, latest.id, status="failed", at=now, failure="stale")
    request_id = await repo.insert_report_request(
        s,
        class_session_id=class_session_id,
        user_id=student_id,
        requested_by=requested_by,
        variant=variant,
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
        await events.emit(s, "user", str(requested_by))
        log.info(
            "report_requested",
            request_id=str(request_id),
            class_session_id=str(class_session_id),
            variant=variant,
        )
    return request_id, ready


async def request_own(
    user: authz.Principal, class_session_id: uuid.UUID, *, ai: bool = False
) -> ReportState | None:
    """«Lag Studentrapport»: record the request and defer its render; a pending one answers
    itself. `ai`: with the AI assessment section (Story 13.11). None (403) for every other case;
    raises `ReportRefused`."""
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
        # Without `ai` the AI assessment is never read: the standard report stands on its own.
        choice = await _choice(user.id, class_session_id, ai) if ai else STANDARD
        if ai and not choice.ai_available:
            raise ReportRefused("ai_assessment_unavailable")
        _, ready = await _press(
            s,
            class_session_id=class_session_id,
            student_id=user.id,
            requested_by=user.id,
            variant=choice.variant,
            now=now,
        )
    return ReportState(
        opens_at=opens_at,
        open=True,
        status="pending",
        generated_at=None if ready is None else ready.finished_at,
        ai=choice.variant != "standard",
        ai_available=choice.ai_available if ai else await _available(user.id, class_session_id),
    )


async def own_file_url(
    user: authz.Principal, class_session_id: uuid.UUID, *, ai: bool = False
) -> str | None:
    """A signed URL of the Student's latest ready PDF of the variant `ai` names, made only now
    that the policy allowed it (NFR-7, AD-12). Without `ai` it is always the standard PDF, never
    one with the AI section (Story 13.11). None (403) for every other case; raises
    `ReportRefused`."""
    now = auth.utcnow()
    async with get_sessionmaker()() as s:
        row = await sessions.own_report_session(s, user, class_session_id)
        if row is None:
            return None
        if not _is_open(sessions.report_opens_at(user, row), now):
            raise ReportRefused("report_not_open")
        if user.id not in await scope.reporting_students(s, class_session_id):
            raise ReportRefused("not_counted")
        # Without `ai` the AI assessment is never read: the standard report stands on its own.
        choice = await _choice(user.id, class_session_id, ai) if ai else STANDARD
        if ai and not choice.ai_available:
            raise ReportRefused("ai_assessment_unavailable")
        _, ready = await repo.latest_report_requests(s, class_session_id, user.id, choice.variant)
        heading = await sessions.report_heading(s, class_session_id, user.id)
    if ready is None or ready.object_path is None:
        raise ReportRefused("report_not_ready")
    number = None if heading is None else heading.number
    return await storage.get_storage().signed_url(
        storage.REPORTS, ready.object_path, download_name=download_name(number)
    )


# The staff's download of one Student's report (Story 13.12, FR-59, FR-58, FR-56, AD-12).

DOWNLOAD = "reports.download"
"""One Student's report for the staff of the Class at any time: its owners and Assistant
lecturers, reached through `sessions.student_target`."""

AI_READ = "ai_assessments.read"
"""Who may add the AI assessment section to a staff download (FR-55)."""

REQUESTED_AUDIT = "report.requested"
"""The audit action of a staff press: who made which Student's report, and which variant."""

DOWNLOADED_AUDIT = "report.downloaded"
"""The audit action of a staff download: who was given which Student's PDF."""

STAFF = _Choice("staff", False)
"""The staff's report without the AI section, without reading the AI assessment."""


async def _reached(
    user: authz.Principal, class_session_id: uuid.UUID, student_id: uuid.UUID
) -> sessions.StudentTarget | None:
    """The Student when `user` is staff of the Class with `reports.download` and `student_id` a
    Student of it now; None, one answer, for every other case (FR-5)."""
    return await sessions.student_target(user, class_session_id, student_id, DOWNLOAD)


async def _staff_choice(
    user: authz.Principal, class_session_id: uuid.UUID, student_id: uuid.UUID, ai: bool
) -> _Choice:
    """The staff's variant: `staff_ai` when they add the AI section, may read the Student's AI
    assessment (`ai_assessments.read`) and it is ready; else `staff`. Never a letter: the gate is
    asked as a reader who is not the Student (FR-56)."""
    if not await sessions.class_staff_may(user, class_session_id, AI_READ):
        return STAFF
    found = await tests.report_assessment(student_id, class_session_id, requested_by_student=False)
    if found is None:
        return STAFF
    return _Choice("staff_ai" if ai else "staff", True)


async def _staff_available(
    user: authz.Principal, class_session_id: uuid.UUID, student_id: uuid.UUID
) -> bool:
    """Whether the staff's Bryter is offered; a fault reading the AI assessment only hides it."""
    try:
        return (await _staff_choice(user, class_session_id, student_id, False)).ai_available
    except Exception as exc:
        log.warning("report_ai_available_unread", exc_type=type(exc).__name__)
        return False


async def staff_state(
    user: authz.Principal, class_session_id: uuid.UUID, student_id: uuid.UUID, *, ai: bool = False
) -> ReportState | None:
    """The staff's report of `student_id` in the Class session, for the variant `ai` names (the one
    without the section while it cannot be added): open at any time, shared by the staff of the
    Class; `deleted` once the Student's data is deleted. None (403) for every other case."""
    reached = await _reached(user, class_session_id, student_id)
    if reached is None:
        return None
    now = auth.utcnow()
    if sessions.data_deleted(reached.row, now):
        return ReportState(opens_at=None, open=True, status="none", generated_at=None, deleted=True)
    if ai:
        choice = await _staff_choice(user, class_session_id, student_id, True)
    else:
        choice = _Choice("staff", await _staff_available(user, class_session_id, student_id))
    async with get_sessionmaker()() as s:
        latest, ready = await repo.latest_report_requests(
            s, class_session_id, student_id, choice.variant
        )
    return ReportState(
        opens_at=None,
        open=True,
        status=_status(latest, now),
        generated_at=None if ready is None else ready.finished_at,
        ai=choice.variant == "staff_ai",
        ai_available=choice.ai_available,
    )


async def request_staff(
    user: authz.Principal, class_session_id: uuid.UUID, student_id: uuid.UUID, *, ai: bool = False
) -> ReportState | None:
    """«Lag Studentrapport» on the Studentside: the same request and `reports-single` job as the
    Student's own, at any time, recorded in the audit log. None (403) for every other case, with
    nothing written; raises `ReportRefused` (`data_deleted`, `not_counted`,
    `ai_assessment_unavailable`)."""
    reached = await _reached(user, class_session_id, student_id)
    if reached is None:
        return None
    now = auth.utcnow()
    if sessions.data_deleted(reached.row, now):
        raise ReportRefused("data_deleted")
    async with get_sessionmaker().begin() as s:
        if student_id not in await scope.reporting_students(s, class_session_id):
            raise ReportRefused("not_counted")
        choice = await _staff_choice(user, class_session_id, student_id, ai) if ai else STAFF
        if ai and not choice.ai_available:
            raise ReportRefused("ai_assessment_unavailable")
        request_id, ready = await _press(
            s,
            class_session_id=class_session_id,
            student_id=student_id,
            requested_by=user.id,
            variant=choice.variant,
            now=now,
        )
        if request_id is not None:
            await audit.record(
                s,
                user.id,
                REQUESTED_AUDIT,
                {
                    "class_session_id": class_session_id,
                    "user_id": student_id,
                    "request_id": request_id,
                },
                {"variant": choice.variant},
                now,
            )
    return ReportState(
        opens_at=None,
        open=True,
        status="pending",
        generated_at=None if ready is None else ready.finished_at,
        ai=choice.variant == "staff_ai",
        ai_available=(
            choice.ai_available
            if ai
            else await _staff_available(user, class_session_id, student_id)
        ),
    )


async def staff_file_url(
    user: authz.Principal, class_session_id: uuid.UUID, student_id: uuid.UUID, *, ai: bool = False
) -> str | None:
    """A signed URL of the staff's latest ready PDF of `student_id` of the variant `ai` names,
    made only now that the policy allowed it (NFR-7, AD-12); without `ai` never the one with the
    section. Recorded in the audit log (`report.downloaded`). None (403) for every other case;
    raises `ReportRefused`."""
    reached = await _reached(user, class_session_id, student_id)
    if reached is None:
        return None
    now = auth.utcnow()
    if sessions.data_deleted(reached.row, now):
        raise ReportRefused("data_deleted")
    async with get_sessionmaker()() as s:
        if student_id not in await scope.reporting_students(s, class_session_id):
            raise ReportRefused("not_counted")
        choice = await _staff_choice(user, class_session_id, student_id, ai) if ai else STAFF
        if ai and not choice.ai_available:
            raise ReportRefused("ai_assessment_unavailable")
        _, ready = await repo.latest_report_requests(
            s, class_session_id, student_id, choice.variant
        )
        heading = await sessions.report_heading(s, class_session_id, student_id)
    if ready is None or ready.object_path is None:
        raise ReportRefused("report_not_ready")
    number = None if heading is None else heading.number
    url = await storage.get_storage().signed_url(
        storage.REPORTS, ready.object_path, download_name=download_name(number)
    )
    async with get_sessionmaker().begin() as s:
        await audit.record(
            s,
            user.id,
            DOWNLOADED_AUDIT,
            {"class_session_id": class_session_id, "user_id": student_id, "request_id": ready.id},
            {"variant": choice.variant},
            now,
        )
    return url
