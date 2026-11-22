"""The api of `modules/reports` (Story 13.2): `GET /api/class-sessions/{id}/students/{user_id}/
record`, the Studentside's record of one Student for the staff of the Class.

An id that is not one, a Class session that does not exist, a Class outside the caller's scope and
a User who is no Student of the Class all answer the same 403 `forbidden` (FR-5)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response

from app.modules.reports import studentside
from app.modules.reports.schemas import StudentRecordOut
from app.platform import authz
from app.platform.errors import documented

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
