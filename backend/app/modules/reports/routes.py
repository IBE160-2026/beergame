"""The api of `modules/reports` (Story 13.2): `GET /api/class-sessions/{id}/students/{user_id}/
record`, the Studentside's record of one Student for the staff of the Class; Story 13.3: `POST
…/corrections`, «Lagre retting», for its Lecturers.

An id that is not one, a Class session that does not exist, a Class outside the caller's scope and
a User who is no Student of the Class all answer the same 403 `forbidden` (FR-5)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response

from app.modules.reports import corrections, makeup, studentside
from app.modules.reports.schemas import CorrectionIn, StudentRecordOut
from app.platform import authz
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
