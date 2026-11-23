"""The Klasserapport's endpoint (Story 14.1, FR-64, FR-5, AD-12):
`GET /api/class-sessions/{id}/class-report`, for the Lecturers who own the Class.

An Assistant lecturer, a Lecturer of another Class, an Admin without a staff role in the Class,
a Student, a Class session that does not exist and an id that is no id all answer the same 403
`forbidden` (FR-5, NFR-7). The answer is never cached (`no-store`): the report changes as
Students progress, and the page refetches it on `session:<id>` (AD-8).

Story 14.5: `GET /api/me/class-sessions/{id}/all-games`, «Alle spill side om side» for a Student
of the Class session (`class_report_all_games`).

Story 14.6: `GET /api/class-sessions/{id}/plenary`, «Alle spill i plenum» for the readers of the
Oversikt (`class_report_plenary`)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse

from app.modules.reports import (
    class_report,
    class_report_all_games,
    class_report_learning,
    class_report_plenary,
)
from app.modules.reports.class_report_all_games_schemas import ClassGamesOut
from app.modules.reports.class_report_learning_schemas import ClassLearningOut
from app.modules.reports.class_report_plenary_schemas import PlenaryOut
from app.modules.reports.class_report_schemas import ClassReportOut
from app.platform import auth, authz
from app.platform.errors import documented, error_response

router = APIRouter(prefix="/api", tags=["reports"])

LOCKED = "All games open once your Debrief is done and the Play deadline has passed."


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


@router.get(
    "/class-sessions/{session_id}/class-report/learning",
    response_model=ClassLearningOut,
    responses=documented(401, 403),
    operation_id="getClassLearningReport",
)
async def get_class_learning_report(
    session_id: str,
    response: Response,
    user: Annotated[authz.Principal, Depends(authz.require(class_report.READ))],
) -> ClassLearningOut:
    """The Klasserapport's learning part (Story 14.2): the Starting task beside the matching test
    items, results per question and the AI assessment totals with the Core-only subscore, over the
    Class session's reporting Students; every figure computed here (AD-10), never a letter
    (FR-56). Access and answers as `getClassReport`."""
    try:
        key = uuid.UUID(session_id)
    except ValueError:
        raise authz.Forbidden from None
    found = await class_report_learning.class_learning(user, key, auth.utcnow())
    if found is None:
        raise authz.Forbidden
    response.headers["Cache-Control"] = "no-store"
    return found


@router.get(
    "/me/class-sessions/{session_id}/all-games",
    response_model=ClassGamesOut,
    responses=documented(401, 403),
    operation_id="getMyClassGames",
)
async def get_my_class_games(
    session_id: str,
    response: Response,
    user: Annotated[authz.Principal, Depends(authz.require(class_report_all_games.OWN))],
) -> ClassGamesOut | JSONResponse:
    """«Alle spill side om side» (Story 14.5, FR-86): every Class game's Orders per Role and Week
    keyed by game number, the Student's own game marked; no name, id, occupant or cost (AD-14).
    403 `all_games_locked` until the Student's Debrief is done and the Play deadline has passed;
    403 `forbidden` for a Class session that is not their own locked one, alike for all (FR-5)."""
    try:
        key = uuid.UUID(session_id)
    except ValueError:
        raise authz.Forbidden from None
    try:
        found = await class_report_all_games.class_games(user, key, auth.utcnow())
    except class_report_all_games.Locked as locked:
        return error_response(403, locked.code, LOCKED)
    if found is None:
        raise authz.Forbidden
    response.headers["Cache-Control"] = "no-store"
    return found


@router.get(
    "/class-sessions/{session_id}/plenary",
    response_model=PlenaryOut,
    responses=documented(401, 403),
    operation_id="getClassPlenary",
)
async def get_class_plenary(
    session_id: str,
    response: Response,
    user: Annotated[authz.Principal, Depends(authz.require(class_report_plenary.READ))],
) -> PlenaryOut:
    """«Alle spill i plenum» (Story 14.6, FR-86): every Class game's Netto lager and Orders per Role
    and Week keyed by game number, for the projector; no name, id, occupant, status, wait or cost
    (AD-14). Read by the Oversikt's readers; 403 `forbidden` for anyone else and for a Class
    session that does not exist, alike (FR-5)."""
    try:
        key = uuid.UUID(session_id)
    except ValueError:
        raise authz.Forbidden from None
    found = await class_report_plenary.plenary(user, key)
    if found is None:
        raise authz.Forbidden
    response.headers["Cache-Control"] = "no-store"
    return found
