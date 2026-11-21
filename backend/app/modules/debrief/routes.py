"""The Debrief routes (Story 9.2, FR-42, AD-3, AD-12).

- `POST /api/me/class-sessions/{id}/debrief`: «Gå til Debrief» and Stegene's Debrief step open
  the Student's Debrief session (created at step 1 the first time) and answer it.
- `GET /api/debriefs/{id}`: the same Debrief session by its id.

Every Debrief route answers 403 `debrief_not_open` while the Student's Class game has not
finished and 403 `debrief_held` while the Lecturer holds the Debriefs and a Class game has not
finished, with the error envelope only: no demand series, number of Weeks or other Seats' data
(FR-14). A Class session that is not the Student's own locked one, another Student's Debrief and
an id that is not one all answer the same 403 `forbidden` (FR-5)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response

from app.modules.debrief import service
from app.modules.debrief.schemas import DebriefOut
from app.platform import authz
from app.platform.errors import documented, error_response

router = APIRouter(prefix="/api", tags=["debrief"])

MESSAGES = {
    "debrief_not_open": "The Debrief opens when the Class game has finished.",
    "debrief_held": "The Debrief opens when all Class games have finished.",
}


def _id(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise authz.Forbidden from None


def _refused(refused: service.NotAvailable) -> Response:
    return error_response(403, refused.code, MESSAGES[refused.code])


@router.post(
    "/me/class-sessions/{session_id}/debrief",
    response_model=DebriefOut,
    responses=documented(401, 403),
    operation_id="openMyDebrief",
)
async def open_my_debrief(
    session_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("debriefs.own"))],
) -> Response:
    """Opens the Student's Debrief in the Class session (FR-42): the Debrief session of their
    game, created with its step pointer at step 1 if none exists, and answered as it stands.
    403 `debrief_not_open`, `debrief_held` or `forbidden`."""
    try:
        found = await service.open_mine(user, _id(session_id))
    except service.NotAvailable as refused:
        return _refused(refused)
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


@router.get(
    "/debriefs/{debrief_id}",
    response_model=DebriefOut,
    responses=documented(401, 403),
    operation_id="getMyDebrief",
)
async def get_my_debrief(
    debrief_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("debriefs.own"))],
) -> Response:
    """The Student's own Debrief session by id. 403 `debrief_not_open`, `debrief_held` or
    `forbidden`, as above."""
    try:
        found = await service.mine(user, _id(debrief_id))
    except service.NotAvailable as refused:
        return _refused(refused)
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))
