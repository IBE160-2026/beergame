"""The Klasserapport's endpoint (Story 14.1, FR-64, FR-5, AD-12):
`GET /api/class-sessions/{id}/class-report`, for the Lecturers who own the Class.

An Assistant lecturer, a Lecturer of another Class, an Admin without a staff role in the Class,
a Student, a Class session that does not exist and an id that is no id all answer the same 403
`forbidden` (FR-5, NFR-7). The answer is never cached (`no-store`): the report changes as
Students progress, and the page refetches it on `session:<id>` (AD-8)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.modules.reports import class_report
from app.modules.reports.class_report_schemas import ClassReportOut
from app.platform import authz
from app.platform.errors import documented

router = APIRouter(prefix="/api", tags=["reports"])


@router.get(
    "/class-sessions/{session_id}/class-report",
    response_model=ClassReportOut,
    responses=documented(401, 403),
    operation_id="getClassReport",
)
async def get_class_report(
    session_id: str,
    response: Response,
    user: Annotated[authz.Principal, Depends(authz.require(class_report.READ))],
) -> ClassReportOut:
    """The Klasserapport (Story 14.1): the Trakt, Kjedekost and Kostnad per Rolle, Forsterkning per
    Rolle, «Mønstre», the AI play and the plausibility ratings per AI mode over the Class session's
    finished Class games, every figure computed here (AD-10)."""
    try:
        key = uuid.UUID(session_id)
    except ValueError:
        raise authz.Forbidden from None
    found = await class_report.class_report(user, key)
    if found is None:
        raise authz.Forbidden
    response.headers["Cache-Control"] = "no-store"
    return found
