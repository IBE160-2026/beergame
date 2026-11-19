"""Class sessions (Story 5.1, FR-5, FR-11, AD-12): created under their Class
(`/api/classes/{class_id}/class-sessions`) and read and saved by id (`/api/class-sessions/{id}`).

A Class or Class session the User may not reach, one that does not exist and an id that is not
one all answer the same 403 `forbidden` (FR-5). A change to a Class session of an archived Class
answers 409 `class_archived` (`classes.service.ClassArchived`, mapped in `main.py`).

Story 5.2 adds the four dates to the save, the Student's read `/api/me/class-sessions` and the
Lærerhjem's read `/api/lecturer-home/class-sessions`."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response

from app.modules.sessions import service
from app.modules.sessions.schemas import (
    ClassSessionListOut,
    ClassSessionOut,
    ClassSessionSaveIn,
    EnrolledSessionListOut,
    LecturerOverviewOut,
)
from app.platform import auth, authz
from app.platform.errors import documented, error_response

router = APIRouter(prefix="/api", tags=["sessions"])

LLM_UNAVAILABLE = "llm_unavailable"


def _id(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise authz.Forbidden from None


@router.post(
    "/classes/{class_id}/class-sessions",
    status_code=201,
    response_model=ClassSessionOut,
    responses=documented(401, 403, 409),
    operation_id="createClassSession",
)
async def create_class_session(
    class_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.manage"))],
) -> Response:
    """«Lag Klasseøkt»: a Class session filled in with the Classic defaults (FR-11). When no model
    config is pinned as the default, it gets Rule-based players and `llm_unavailable` says why."""
    created = await service.create_session(user, _id(class_id), now=auth.utcnow())
    if created is None:
        raise authz.Forbidden
    return JSONResponse(created.model_dump(mode="json"), status_code=201)


@router.get(
    "/classes/{class_id}/class-sessions",
    response_model=ClassSessionListOut,
    responses=documented(401, 403),
    operation_id="listClassSessions",
)
async def list_class_sessions(
    class_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.read"))],
) -> Response:
    """The Class's sessions, newest first, for the Klasse page."""
    found = await service.list_sessions(user, _id(class_id))
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


@router.get(
    "/class-sessions/{session_id}",
    response_model=ClassSessionOut,
    responses=documented(401, 403),
    operation_id="getClassSession",
)
async def get_class_session(
    session_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.read"))],
) -> Response:
    """One Class session, for the Klasseøkt screen. Its Class's Assistant lecturers read it too."""
    found = await service.get_session(user, _id(session_id))
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


@router.put(
    "/class-sessions/{session_id}",
    response_model=ClassSessionOut,
    responses=documented(401, 403, 409, 422),
    operation_id="saveClassSession",
)
async def save_class_session(
    session_id: str,
    body: ClassSessionSaveIn,
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.manage"))],
) -> Response:
    """«Lagre Klasseøkt»: saves the Class session as it stands. LLM players while no model config
    is pinned as the default answer 409 `llm_unavailable`, and nothing changes.

    With `dates` the four dates are replaced (FR-18). `fields` names each date in question:
    422 `invalid_dates` (`past`, `order` for the later date of a pair out of order, `before` for
    the earlier one when only it changed, `required` once locked), 409 `deadline_passed`
    (`passed`). Once the Start date has passed, a changed AI mode answers 409 `session_locked`.
    Dates count to the whole minute."""
    try:
        saved = await service.save_session(
            user, _id(session_id), body.ai_mode, now=auth.utcnow(), dates=body.dates
        )
    except service.LlmUnavailableError:
        return error_response(
            409, LLM_UNAVAILABLE, "LLM players are unavailable until a default model is pinned."
        )
    except service.InvalidDates as refused:
        return error_response(422, refused.code, "The dates break a rule.", refused.fields)
    except (service.DeadlinePassed, service.SessionLocked) as refused:
        return error_response(409, refused.code, "This can no longer change.", refused.fields)
    if saved is None:
        raise authz.Forbidden
    return JSONResponse(saved.model_dump(mode="json"))


@router.get(
    "/me/class-sessions",
    response_model=EnrolledSessionListOut,
    responses=documented(401),
    operation_id="listMyClassSessions",
)
async def list_my_class_sessions(
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.read_enrolled"))],
) -> Response:
    """The Class sessions of the Classes the User is a Student in: dates and the next deadline,
    never the Game settings (FR-18). Empty for a User who is no Student."""
    found = await service.enrolled_sessions(user)
    return JSONResponse(found.model_dump(mode="json"))


@router.get(
    "/lecturer-home/class-sessions",
    response_model=LecturerOverviewOut,
    responses=documented(401, 403),
    operation_id="lecturerHomeClassSessions",
)
async def lecturer_home_class_sessions(
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.read"))],
) -> Response:
    """The Lærerhjem's «Venter» and «Neste frist» over the User's Classes that are not archived
    (UX-DR56)."""
    found = await service.lecturer_overview(user)
    return JSONResponse(found.model_dump(mode="json"))
