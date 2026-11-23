"""The api of `modules/reports` (Story 13.2): `GET /api/class-sessions/{id}/students/{user_id}/
record`, the Studentside's record of one Student for the staff of the Class; Story 13.3: `POST
…/corrections`, «Lagre retting», for its Lecturers. Story 13.7: the Student's own Student report
(`/api/me/class-sessions/{id}/report`, its `/file`) and the print route's snapshot read
(`/api/internal/report-snapshots/{id}`, which the proxy refuses: only the frontend server reaches
it).

An id that is not one, a Class session that does not exist, a Class outside the caller's scope and
a User who is no Student of the Class all answer the same 403 `forbidden` (FR-5)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Header, Query
from fastapi.responses import JSONResponse, RedirectResponse, Response

from app.modules.reports import corrections, makeup, report, snapshot, studentside
from app.modules.reports.report_data import ReportDataOut
from app.modules.reports.schemas import (
    CorrectionIn,
    ReportRequestIn,
    ReportStateOut,
    StudentRecordOut,
)
from app.platform import authz, storage
from app.platform.errors import documented, error_response

router = APIRouter(prefix="/api", tags=["reports"])

PERSONAL = {"Cache-Control": "no-store"}
"""A Student's record is personal data: no cache keeps it."""


def _id(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise authz.Forbidden from None


@router.get(
    "/class-sessions/{session_id}/students/{user_id}/record",
    response_model=StudentRecordOut,
    responses=documented(401, 403),
    operation_id="getStudentRecord",
)
async def get_student_record(
    session_id: str,
    user_id: str,
    user: Annotated[authz.Principal, Depends(authz.require(studentside.READ))],
) -> Response:
    """The Studentside's record (Story 13.2, FR-63, FR-17, UX-DR54, UX-DR55): one Student of the
    Class session with the Completion status per step, the participation signals (information
    only), the game, the Explanation, the Debrief summary, the Debrief quiz attempts, the Replay,
    the Individual test and the AI assessment's state, for the Lecturers and Assistant lecturers
    of its Class. 403 `forbidden` for anyone else, an Admin without a staff role in the Class
    included, for a User who is no Student of the Class now and for a Class session that does not
    exist (FR-5, AD-12)."""
    found = await studentside.student_record(user, _id(session_id), _id(user_id))
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"), headers=PERSONAL)


@router.post(
    "/class-sessions/{session_id}/students/{user_id}/corrections",
    response_model=StudentRecordOut,
    responses=documented(401, 403, 409, 422),
    operation_id="correctCompletion",
)
async def correct_completion(
    session_id: str,
    user_id: str,
    body: CorrectionIn,
    user: Annotated[authz.Principal, Depends(authz.require(studentside.CORRECT))],
) -> Response:
    """«Lagre retting» (Story 13.3, FR-17, FR-3, AD-15, AD-16): a Lecturer of the Class sets one
    step of the Student's Completion status to done or not done, with a required reason. A new
    row every time; the latest per step applies. Recorded in the audit log; the Studentside and
    the Student's Hjem read it again. It records no step event. Answers the Studentside's record.
    422 `invalid_correction` with `fields.reason` `required` or `too_long`; 409 `not_obligatory`
    for a Class session that is not obligatory, 409 `class_archived`; 403 `forbidden` for an
    Assistant lecturer and anyone else as `getStudentRecord`."""
    try:
        found = await corrections.correct(user, _id(session_id), _id(user_id), body)
    except corrections.InvalidCorrection as refused:
        return error_response(422, refused.code, "The correction breaks a rule.", refused.fields)
    except corrections.NotObligatory as refused:
        return error_response(409, refused.code, "The Class session is not obligatory.")
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"), headers=PERSONAL)


@router.post(
    "/class-sessions/{session_id}/students/{user_id}/makeup",
    response_model=StudentRecordOut,
    responses=documented(401, 403, 409),
    operation_id="giveMakeup",
)
async def give_makeup(
    session_id: str,
    user_id: str,
    user: Annotated[authz.Principal, Depends(authz.require(makeup.GIVE))],
) -> Response:
    """«Gi oppfølgingsspill» (Story 13.4, FR-17, FR-20, FR-30, AD-13): a Lecturer of the Class
    gives the Student a make-up game: a Class game of their own against three AI players on the
    Class session's frozen snapshot, open until the Student's Test deadline. Recorded in the audit
    log; the Student is told on Hjem and by mail. One per Student: a second press answers the
    existing one and writes nothing. Answers the Studentside's record. 409 `not_counted` for a
    Student reports leave out (a test student, a Control test Class session),
    `session_not_locked` before the Class session's lock, `no_test_deadline`,
    `test_deadline_passed`, `class_archived`; 403 `forbidden` for an Assistant lecturer and
    anyone else as `getStudentRecord`."""
    student_id = _id(user_id)
    class_session_id = _id(session_id)
    try:
        given = await makeup.give(user, class_session_id, student_id)
    except makeup.MakeupRefused as refused:
        return error_response(409, refused.code, "No Oppfølgingsspill can be given now.")
    if given is None:
        raise authz.Forbidden
    found = await studentside.student_record(user, class_session_id, student_id)
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"), headers=PERSONAL)


def _state(found: report.ReportState) -> dict:
    return ReportStateOut(
        opens_at=found.opens_at,
        open=found.open,
        status=found.status,
        generated_at=found.generated_at,
        ai=found.ai,
        ai_available=found.ai_available,
    ).model_dump(mode="json")


AI_QUERY = Query(
    description="Story 13.11: the report with the AI assessment section (off by default).",
)


@router.get(
    "/me/class-sessions/{session_id}/report",
    response_model=ReportStateOut,
    responses=documented(401, 403),
    operation_id="getMyReport",
)
async def get_my_report(
    session_id: str,
    user: Annotated[authz.Principal, Depends(authz.require(report.DOWNLOAD_OWN))],
    ai: Annotated[bool, AI_QUERY] = False,
) -> Response:
    """The Student's own Student report in the Class session (Story 13.7, FR-57): when it opens
    (their effective Test deadline), whether it is open, the latest request's status and when
    the PDF to download was made. Story 13.11: `ai_available` while their AI assessment is ready;
    with `ai` the state of the report with the AI section (`ai` true in the answer), or the
    standard one's while it cannot be added. 403 `forbidden` for a Class session that is not the
    Student's own (not enrolled, not listed on Hjem, not locked, no such session)."""
    found = await report.own_state(user, _id(session_id), ai=ai)
    if found is None:
        raise authz.Forbidden
    return JSONResponse(_state(found), headers=PERSONAL)


@router.post(
    "/me/class-sessions/{session_id}/report",
    response_model=ReportStateOut,
    status_code=202,
    responses=documented(401, 403, 409),
    operation_id="requestMyReport",
)
async def request_my_report(
    session_id: str,
    user: Annotated[authz.Principal, Depends(authz.require(report.DOWNLOAD_OWN))],
    body: Annotated[ReportRequestIn | None, Body()] = None,
) -> Response:
    """«Lag Studentrapport» (Story 13.7, FR-57, AD-9, AD-18): records the request and defers its
    render on `reports-single` with ids only; the api builds no report content. While one is
    pending, a press answers it and starts no second render. The finished job emits the
    Student's `user` topic. 202 with the state; 409 `report_not_open` before the Student's
    effective Test deadline or with none, 409 `not_counted` for a Student reports leave out;
    Story 13.11: `ai` in the body adds the AI assessment section, a report of its own; 409
    `ai_assessment_unavailable` while the Student's AI assessment is not ready. 403 `forbidden`
    as `getMyReport`."""
    try:
        found = await report.request_own(user, _id(session_id), ai=body is not None and body.ai)
    except report.ReportRefused as refused:
        return error_response(409, refused.code, "The report cannot be made now.")
    if found is None:
        raise authz.Forbidden
    return JSONResponse(_state(found), status_code=202, headers=PERSONAL)


@router.get(
    "/me/class-sessions/{session_id}/report/file",
    status_code=303,
    responses={**documented(401, 403, 409, 503), 303: {"description": "To a signed URL"}},
    operation_id="downloadMyReport",
)
async def download_my_report(
    session_id: str,
    user: Annotated[authz.Principal, Depends(authz.require(report.DOWNLOAD_OWN))],
    ai: Annotated[bool, AI_QUERY] = False,
) -> Response:
    """The Student's latest PDF (Story 13.7, NFR-7, AD-12): 303 to a signed URL that lives
    `SIGNED_URL_TTL_SECONDS` (300), made only now that the policy allowed it. 409
    `report_not_ready` without a ready PDF, `report_not_open` before the deadline,
    `not_counted` for a Student reports leave out; 503 `storage_unavailable`; 403
    `forbidden` as `getMyReport`. Story 13.11: with `ai` the PDF with the AI section (409
    `ai_assessment_unavailable` while the assessment is not ready); without it always the
    standard PDF."""
    try:
        url = await report.own_file_url(user, _id(session_id), ai=ai)
    except report.ReportRefused as refused:
        return error_response(409, refused.code, "No report to download.")
    except storage.StorageError:
        return error_response(503, "storage_unavailable", "The download cannot be made now.")
    if url is None:
        raise authz.Forbidden
    return RedirectResponse(url, status_code=303, headers=PERSONAL)


@router.get(
    "/internal/report-snapshots/{snapshot_id}",
    response_model=ReportDataOut,
    responses=documented(404),
    operation_id="readReportSnapshot",
    dependencies=[Depends(authz.public)],  # admitted by its single-use render token only
)
async def read_report_snapshot(
    snapshot_id: str,
    x_render_token: Annotated[str, Header()] = "",
) -> Response:
    """The print route's read of one report snapshot (Story 13.7, AD-18), with its render token in
    `X-Render-Token`: the data once, while the token is unused and unexpired (5 minutes). A
    used, expired or wrong token, and an unknown snapshot, all answer 404 `not_found` with no
    data. The proxy refuses `/api/internal/*`: only the frontend server reaches it."""
    data = await snapshot.read(snapshot_id, x_render_token)
    if data is None:
        return error_response(404, "not_found", "No such report snapshot.")
    return JSONResponse(data, headers=PERSONAL)
