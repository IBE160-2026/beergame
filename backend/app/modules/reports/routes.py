"""The api of `modules/reports` (Story 13.2): `GET /api/class-sessions/{id}/students/{user_id}/
record`, the Studentside's record of one Student for the staff of the Class; Story 13.3: `POST
…/corrections`, «Lagre retting», for its Lecturers. Story 13.7: the Student's own Student report
(`/api/me/class-sessions/{id}/report`, its `/file`) and the print route's snapshot read
(`/api/internal/report-snapshots/{id}`, which the proxy refuses: only the frontend server reaches
it). Story 13.12: the staff's download of one Student's report (`…/students/{user_id}/report`, its
`/file`). Story 13.13: the ZIP of all Student reports of a Class session
(`/api/class-sessions/{id}/reports/zip`, its `/file`). Story 13.14: the Completion export
(`/api/class-sessions/{id}/completion-export`). Story 14.8: the Game data export
(`/api/class-sessions/{id}/game-data-export`), only while `FEATURE_GAME_DATA_EXPORT` is on.

An id that is not one, a Class session that does not exist, a Class outside the caller's scope and
a User who is no Student of the Class all answer the same 403 `forbidden` (FR-5)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse, Response, StreamingResponse

from app.modules.reports import (
    bundle,
    completion_export,
    corrections,
    game_data_export,
    makeup,
    report,
    snapshot,
    studentside,
)
from app.modules.reports.report_data import ReportDataOut
from app.modules.reports.schemas import (
    CorrectionIn,
    ReportRequestIn,
    ReportStateOut,
    StudentRecordOut,
    ZipStateOut,
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
        deleted=found.deleted,
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


STUDENT_REPORT = "/class-sessions/{session_id}/students/{user_id}/report"


@router.get(
    STUDENT_REPORT,
    response_model=ReportStateOut,
    responses=documented(401, 403),
    operation_id="getStudentReport",
)
async def get_student_report(
    session_id: str,
    user_id: str,
    user: Annotated[authz.Principal, Depends(authz.require(report.DOWNLOAD))],
    ai: Annotated[bool, AI_QUERY] = False,
) -> Response:
    """One Student's report as the staff of the Class download it from the Studentside (Story
    13.12, FR-59, FR-63): always open, shared by its Lecturers and Assistant lecturers, apart from
    the Student's own. `ai_available` while the Student's AI assessment is ready and the reader may
    read it (FR-55); with `ai` the state of the report with the AI section, never with the
    Indicative letter (FR-56). 403 `forbidden` as `getStudentRecord`."""
    found = await report.staff_state(user, _id(session_id), _id(user_id), ai=ai)
    if found is None:
        raise authz.Forbidden
    return JSONResponse(_state(found), headers=PERSONAL)


@router.post(
    STUDENT_REPORT,
    response_model=ReportStateOut,
    status_code=202,
    responses=documented(401, 403, 409),
    operation_id="requestStudentReport",
)
async def request_student_report(
    session_id: str,
    user_id: str,
    user: Annotated[authz.Principal, Depends(authz.require(report.DOWNLOAD))],
    body: Annotated[ReportRequestIn | None, Body()] = None,
) -> Response:
    """«Lag Studentrapport» on the Studentside (Story 13.12, FR-59, AD-9, AD-18): before or after
    the Test deadline, the same request and `reports-single` job as the Student's own, recorded in
    the audit log. 202 with the state; 409 `data_deleted` once the Student's data is deleted
    (`deleted` in the state), 409 `not_counted` for a Student reports leave out, 409
    `ai_assessment_unavailable` when `ai` asks for the section and it cannot be added. 403
    `forbidden` as `getStudentRecord`, with nothing recorded."""
    try:
        found = await report.request_staff(
            user, _id(session_id), _id(user_id), ai=body is not None and body.ai
        )
    except report.ReportRefused as refused:
        return error_response(409, refused.code, "The report cannot be made now.")
    if found is None:
        raise authz.Forbidden
    return JSONResponse(_state(found), status_code=202, headers=PERSONAL)


@router.get(
    STUDENT_REPORT + "/file",
    status_code=303,
    responses={**documented(401, 403, 409, 503), 303: {"description": "To a signed URL"}},
    operation_id="downloadStudentReport",
)
async def download_student_report(
    session_id: str,
    user_id: str,
    user: Annotated[authz.Principal, Depends(authz.require(report.DOWNLOAD))],
    ai: Annotated[bool, AI_QUERY] = False,
) -> Response:
    """The staff's latest PDF of the Student (Story 13.12, NFR-7, AD-12): 303 to a signed URL
    made only now that the policy allowed it, recorded in the audit log. 409 `report_not_ready`,
    `data_deleted`, `not_counted`,
    `ai_assessment_unavailable`; 503 `storage_unavailable`; 403 `forbidden` as
    `getStudentRecord`. Without `ai` never the PDF with the AI section."""
    try:
        url = await report.staff_file_url(user, _id(session_id), _id(user_id), ai=ai)
    except report.ReportRefused as refused:
        return error_response(409, refused.code, "No report to download.")
    except storage.StorageError:
        return error_response(503, "storage_unavailable", "The download cannot be made now.")
    if url is None:
        raise authz.Forbidden
    return RedirectResponse(url, status_code=303, headers=PERSONAL)


REPORTS_ZIP = "/class-sessions/{session_id}/reports/zip"


def _zip_state(found: bundle.ZipState) -> dict:
    return ZipStateOut(
        status=found.status,
        generated_at=found.generated_at,
        students=found.students,
        deleted=found.deleted,
        completion_export=found.completion_export,
        game_data_export=found.game_data_export,
    ).model_dump(mode="json")


@router.get(
    REPORTS_ZIP,
    response_model=ZipStateOut,
    responses=documented(401, 403),
    operation_id="getReportsZip",
)
async def get_reports_zip(
    session_id: str,
    user: Annotated[authz.Principal, Depends(authz.require(report.DOWNLOAD))],
) -> Response:
    """The ZIP of all Student reports of the Class session (Story 13.13, FR-59), for the
    Lecturers and Assistant lecturers of its Class: shared by them, the latest request's status
    and when the ZIP to download was made. 403 `forbidden` for anyone else, an Admin without a
    staff role in the Class included, and for a Class session that does not exist (FR-5)."""
    found = await bundle.zip_state(user, _id(session_id))
    if found is None:
        raise authz.Forbidden
    return JSONResponse(_zip_state(found), headers=PERSONAL)


@router.post(
    REPORTS_ZIP,
    response_model=ZipStateOut,
    status_code=202,
    responses=documented(401, 403, 409),
    operation_id="requestReportsZip",
)
async def request_reports_zip(
    session_id: str,
    user: Annotated[authz.Principal, Depends(authz.require(report.DOWNLOAD))],
) -> Response:
    """«Last ned alle Studentrapporter (ZIP)» (Story 13.13, FR-59, AD-9, AD-18): records the
    request and defers its job on `reports-bulk` with ids only, recorded in the audit log; the
    job builds one report per Student reports count, never with the AI assessment, whatever the
    request holds. While one is pending, a press answers it. The requester is told when it is
    ready. 202 with the state; 409 `data_deleted` once the Student data is deleted, 409
    `no_students` when reports count no Student; 403 `forbidden` as `getReportsZip`, with
    nothing recorded."""
    try:
        found = await bundle.request_zip(user, _id(session_id))
    except report.ReportRefused as refused:
        return error_response(409, refused.code, "The ZIP cannot be made now.")
    if found is None:
        raise authz.Forbidden
    return JSONResponse(_zip_state(found), status_code=202, headers=PERSONAL)


@router.get(
    REPORTS_ZIP + "/file",
    status_code=303,
    responses={**documented(401, 403, 409, 503), 303: {"description": "To a signed URL"}},
    operation_id="downloadReportsZip",
)
async def download_reports_zip(
    session_id: str,
    user: Annotated[authz.Principal, Depends(authz.require(report.DOWNLOAD))],
) -> Response:
    """The Class session's latest ZIP (Story 13.13, NFR-7, AD-12): 303 to a signed URL that lives
    `SIGNED_URL_TTL_SECONDS` (300), made only now that the policy allowed it, recorded in the
    audit log. 409 `zip_not_ready`, `data_deleted`; 503 `storage_unavailable`; 403 `forbidden`
    as `getReportsZip`."""
    try:
        url = await bundle.zip_file_url(user, _id(session_id))
    except report.ReportRefused as refused:
        return error_response(409, refused.code, "No ZIP to download.")
    except storage.StorageError:
        return error_response(503, "storage_unavailable", "The download cannot be made now.")
    if url is None:
        raise authz.Forbidden
    return RedirectResponse(url, status_code=303, headers=PERSONAL)


@router.get(
    "/class-sessions/{session_id}/completion-export",
    responses={
        **documented(401, 403, 409, 422),
        200: {
            "description": "The file, CSV or .xlsx",
            "content": {
                completion_export.CSV_TYPE.split(";")[0]: {},
                completion_export.XLSX_TYPE: {},
            },
        },
    },
    response_class=Response,
    operation_id="downloadCompletionExport",
)
async def download_completion_export(
    session_id: str,
    user: Annotated[authz.Principal, Depends(authz.require(completion_export.EXPORT))],
    format: Annotated[
        completion_export.Format,
        Query(description="`csv` (Norwegian Excel: UTF-8 with BOM, `;`) or `xlsx`."),
    ] = "csv",
) -> Response:
    """«Last ned fullføringsliste (CSV eller Excel)» (Story 13.14, FR-60, FR-17, AD-14, AD-16):
    one row per Student reports count, with the fixed columns `completion_export.COLUMNS` (name,
    email, the date each step was done, the shares, the Oppfølgingsspill, the correction mark and
    whether the requirement is met), every value from the one Completion assembler. Never an AI
    score, AI feedback or Indicative letter. Built now and sent, never stored; recorded in the
    audit log once the file is built. 409 `data_deleted` once the Student data is deleted; 403
    `forbidden` for an Assistant lecturer, anyone else outside the Class's Lecturers and a Class
    session that does not exist (FR-5, AD-12)."""
    class_session_id = _id(session_id)
    try:
        found = await completion_export.export(user, class_session_id)
    except report.ReportRefused as refused:
        return error_response(409, refused.code, "No Completion export can be made now.")
    if found is None:
        raise authz.Forbidden
    if format == "xlsx":
        body, media_type = completion_export.to_xlsx(found.rows), completion_export.XLSX_TYPE
    else:
        body, media_type = (
            b"".join(completion_export.to_csv(found.rows)),
            completion_export.CSV_TYPE,
        )
    await completion_export.record_download(user, class_session_id, format, len(found.rows))
    headers = {
        **PERSONAL,
        "Content-Disposition": (
            f'attachment; filename="{completion_export.file_name(found.number, format)}"'
        ),
    }
    return Response(body, media_type=media_type, headers=headers)


def _game_data_export_exists() -> None:
    """While `FEATURE_GAME_DATA_EXPORT` is off the route does not exist (AD-17): it answers what
    an unknown route answers, before any policy or read."""
    if not game_data_export.enabled():
        raise HTTPException(status_code=404)


@router.get(
    "/class-sessions/{session_id}/game-data-export",
    dependencies=[Depends(_game_data_export_exists)],
    responses={
        **documented(401, 403, 404, 409),
        200: {"description": "The CSV file", "content": {"text/csv": {}}},
    },
    response_class=Response,
    operation_id="downloadGameDataExport",
)
async def download_game_data_export(
    session_id: str,
    user: Annotated[authz.Principal, Depends(authz.require(game_data_export.EXPORT))],
) -> Response:
    """«Last ned spilldata (CSV)» (Story 14.8, cut list, FR-88, AD-13, AD-14, AD-15, AD-17): one
    row per Game, Week and Seat of the Decision log, for the Class games, make-up games and
    Replays `reporting_games()` counts, with the fixed columns `game_data_export.COLUMNS` (the
    purpose, the game, the Week, the Role, what the Seat saw, the Order, its cost, who decided it,
    the AD-15 mark and the occupant kind). Never an AI score, AI feedback, Indicative letter, name
    or id. Streamed, never stored; recorded in the audit log once the rows are read. 404 as an
    unknown route while `FEATURE_GAME_DATA_EXPORT` is off; 409 `data_deleted` once the Student
    data is deleted; 403 `forbidden` for an Assistant lecturer, anyone else outside the Class's
    Lecturers and a Class session that does not exist (FR-5, AD-12)."""
    class_session_id = _id(session_id)
    try:
        found = await game_data_export.export(user, class_session_id)
    except report.ReportRefused as refused:
        return error_response(409, refused.code, "No Game data export can be made now.")
    if found is None:
        raise authz.Forbidden
    await game_data_export.record_download(user, class_session_id, found)
    headers = {
        **PERSONAL,
        "Content-Disposition": (
            f'attachment; filename="{game_data_export.file_name(found.number)}"'
        ),
    }
    return StreamingResponse(
        game_data_export.to_csv(found.rows), media_type=game_data_export.CSV_TYPE, headers=headers
    )


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
