"""The Student's Replay (Story 10.3, FR-48): `POST /api/me/class-sessions/{session_id}/replay`.

A Class session that is not one of the User's own locked sessions, one that does not exist and an
id that is not one all answer the same 403 `forbidden` (FR-5)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from app.modules.replay import service
from app.platform import authz
from app.platform.errors import documented, error_response

router = APIRouter(prefix="/api", tags=["replay"])


class ReplayStartOut(BaseModel):
    """The Student's Replay Game: the one this request made (201) or the one they had (200)."""

    game_id: uuid.UUID


REFUSED = {
    "quiz_required": "Pass the Debrief quiz first.",
    "test_deadline_passed": "Your Test deadline has passed.",
}


@router.post(
    "/me/class-sessions/{session_id}/replay",
    status_code=201,
    response_model=ReplayStartOut,
    responses={**documented(401, 403, 409), 200: {"model": ReplayStartOut}},
    operation_id="startMyReplay",
)
async def start_my_replay(
    session_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("games.start_own"))],
) -> Response:
    """«Start Replay» (Story 10.3, FR-48): the Student's one Replay in the Class session, made in
    the Role of their own game against three AI players and started at once; 201 with the new
    Game, 200 with the one they have already (also when two starts run at once). 403
    `quiz_required` before the Debrief quiz is passed, 409 `test_deadline_passed` after the
    Student's Test deadline, 403 `forbidden` for any session that is not theirs (FR-5)."""
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise authz.Forbidden from None
    try:
        started = await service.start(user, session_uuid)
    except service.ReplayRefused as refused:
        return error_response(refused.status, refused.code, REFUSED[refused.code])
    if started is None:
        raise authz.Forbidden
    return JSONResponse(
        ReplayStartOut(game_id=started.game_id).model_dump(mode="json"),
        status_code=201 if started.created else 200,
    )
