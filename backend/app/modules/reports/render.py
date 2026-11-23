"""The `reports-single` task: render one Student report (Story 13.7, FR-57, AD-9, AD-14, AD-18).

`reports.render_report(request_id)`, ids only. For a pending request it

1. deletes snapshots a crashed render left behind once expired;
2. builds the content with `report_data.build_report_data` and stores it as a report snapshot
   with the SHA-256 of a fresh single-use render token that expires after 5 minutes (a retried
   job builds a new snapshot and a new token);
3. has WeasyPrint fetch `WEB_INTERNAL_URL/print/report/<snapshot_id>?token=…` and convert it in
   its `pdf/ua-1` variant (only that origin is fetched: the page, its stylesheet, its fonts);
4. stores the PDF through `platform/storage` in the private `reports` bucket under a path keyed by
   Class session and `user_id`;
5. marks the request `ready`, or `failed` with the code `render_failed` (`not_reportable`, or
   `ai_unavailable` when the AI section was asked for and the assessment is no longer ready),
   deletes the snapshot whether the render succeeded or failed, and emits `user:<student>` (and
   `user:<requester>` when another asked), so the Student's page updates without reload (AD-8).

A request no longer pending (done, or replaced as stale) is left alone, so a job delivered twice
renders once. Failures are logged with ids and the error's type only, never a name or a text."""

from __future__ import annotations

import asyncio
import hashlib
import secrets
import uuid
from datetime import timedelta
from typing import Any
from urllib.parse import urlencode, urlsplit

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reports import pdf_marks, repo
from app.modules.reports.report import RENDER_TASK, object_path
from app.modules.reports.report_data import (
    AssessmentUnavailable,
    NotReportable,
    ReportOptions,
    build_report_data,
)
from app.platform import auth, events, jobs, storage
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker

__all__ = ["RENDERED", "TOKEN_LIFETIME", "print_url", "render_report", "to_pdf"]

log = structlog.get_logger(__name__)

TOKEN_LIFETIME = timedelta(minutes=5)
RENDERED = "reports.render_report"
"""The registry name of the render's end: it emits the `user` topic."""


def token_hash(token: str) -> bytes:
    return hashlib.sha256(token.encode()).digest()


def print_url(snapshot_id: uuid.UUID, token: str) -> str:
    base = get_settings().web_internal_url.rstrip("/")
    return f"{base}/print/report/{snapshot_id}?{urlencode({'token': token})}"


def _convert(url: str) -> bytes:
    """WeasyPrint's `pdf/ua-1` of the print page at `url`, fetching only from its origin, with
    AI-generated text marked in its structure tree (`pdf_marks`, Story 13.10)."""
    import pydyf
    from weasyprint import HTML, URLFetcher  # needs Pango: only where it runs

    pdf_marks.install()

    home = urlsplit(url)[:2]

    class SameOrigin(URLFetcher):
        def fetch(self, target: str, headers: Any = None) -> Any:
            if not target.startswith("data:") and urlsplit(target)[:2] != home:
                raise ValueError("the report fetches only from the app")
            return super().fetch(target, headers)

    # No redirects, so the origin check holds for every fetch.
    document = HTML(url=url, url_fetcher=SameOrigin(fail_on_errors=True, allow_redirects=False))
    pdf = document.write_pdf(
        pdf_variant="pdf/ua-1", finisher=lambda _, out: pdf_marks.mark_catalog(out, pydyf)
    )
    if not pdf:
        raise RuntimeError("WeasyPrint wrote no PDF")
    return pdf


RENDER_TIMEOUT_SECONDS = 90
"""A conversion still running after this fails, so it frees its `reports-single` slot (the
thread itself cannot be stopped and ends on its own); below `REPORT_STALE_SECONDS`."""


async def to_pdf(url: str) -> bytes:
    """The PDF of the print page; tests put a fake here (WeasyPrint needs Pango)."""
    return await asyncio.wait_for(asyncio.to_thread(_convert, url), RENDER_TIMEOUT_SECONDS)


async def _emit(s: AsyncSession, request: repo.ReportRequest) -> None:
    await events.emit(s, "user", str(request.user_id))
    if request.requested_by is not None and request.requested_by != request.user_id:
        await events.emit(s, "user", str(request.requested_by))


async def render(request_id: uuid.UUID) -> str:
    """Render the request; answers what happened: `ready`, `failed` or `skipped`."""
    now = auth.utcnow()
    async with get_sessionmaker().begin() as s:
        request = await repo.report_request(s, request_id)
        if request is None or request.status != "pending":
            return "skipped"
        await repo.delete_expired_snapshots(s, now)
    snapshot_id: uuid.UUID | None = None
    outcome, path, failure = "failed", None, "render_failed"
    try:
        token = secrets.token_urlsafe(32)
        async with get_sessionmaker().begin() as s:
            data = await build_report_data(
                s,
                request.user_id,
                request.class_session_id,
                ReportOptions(
                    variant=request.variant,  # type: ignore[arg-type]
                    # The Indicative letter's gate (Story 13.11): only a report the Student
                    # asked for may carry it.
                    requested_by_student=request.requested_by == request.user_id,
                ),
                now=now,
            )
            snapshot_id = await repo.insert_snapshot(
                s,
                request_id=request.id,
                token_hash=token_hash(token),
                expires_at=now + TOKEN_LIFETIME,
                data=data.model_dump(mode="json"),
            )
        pdf = await to_pdf(print_url(snapshot_id, token))
        if not pdf.startswith(b"%PDF-"):
            raise RuntimeError("not a PDF")
        async with get_sessionmaker()() as s:
            # The print route answers 404 unless it read the snapshot: a PDF of anything else
            # (an error page) is no report.
            if not await repo.snapshot_used(s, snapshot_id):
                raise RuntimeError("the print route did not read the snapshot")
        path = object_path(request.class_session_id, request.user_id, request.variant, request.id)
        await storage.get_storage().put(storage.REPORTS, path, pdf, "application/pdf")
        outcome, failure = "ready", None
    except NotReportable:
        failure = "not_reportable"
        log.warning("report_not_reportable", request_id=str(request.id))
    except AssessmentUnavailable:
        # Story 13.11: the AI section was asked for and the assessment is no longer ready (switched
        # off or stopped meanwhile): nothing stored, never a report quietly without the section.
        failure = "ai_unavailable"
        log.warning("report_ai_unavailable", request_id=str(request.id))
    except Exception as exc:  # the type only: a message could hold a URL with the token
        log.error("report_render_failed", request_id=str(request.id), exc_type=type(exc).__name__)
    finally:
        replaced: list[str] = []
        async with get_sessionmaker().begin() as s:
            if snapshot_id is not None:
                await repo.delete_snapshot(s, snapshot_id)
            finished = await repo.finish_report_request(
                s,
                request.id,
                status=outcome,
                at=auth.utcnow(),
                object_path=path if outcome == "ready" else None,
                failure=failure,
            )
            if finished:
                if outcome == "ready":
                    # One PDF per Student, Class session and variant: the earlier ones go.
                    replaced = await repo.release_older_objects(s, request)
                await _emit(s, request)
        # Each render writes its own object, so a late render never overwrites a newer one; a
        # render that was no longer wanted (replaced as stale) removes its own.
        gone = replaced if finished else ([path] if outcome == "ready" and path else [])
        for old in gone:
            try:
                await storage.get_storage().delete(storage.REPORTS, old)
            except Exception as exc:  # best effort: the row no longer points at it
                log.warning("report_object_delete_failed", exc_type=type(exc).__name__)
    if not finished:
        return "skipped"
    log.info("report_rendered", request_id=str(request.id), outcome=outcome)
    return outcome


@jobs.app.task(name=RENDER_TASK, queue=jobs.REPORTS_SINGLE)
async def render_report(request_id: str) -> None:
    await render(uuid.UUID(request_id))
