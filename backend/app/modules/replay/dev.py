"""The local dev quiz pass (Story 10.5): `POST /api/dev/class-sessions/{id}/quiz-passed` records
the logged-in Student's steps up to the passed Debrief quiz (`class_game`, `debrief`,
`quiz_passed`) in the Class session, so «Start Replay» opens without a finished Class game, a
Debrief and a quiz. `POST …/replay-done` (Story 11.3) records the steps up to `replay` as well, so
the Individual test opens without a played Replay.

The end-to-end test of the Replay's play screen uses it to start a real Replay on the stack, as
the dev lock (Story 6.15) stands in for the Start date. `create_app()` mounts it only when
`APP_ENV` is not `production`; there it does not exist at all. It is not in the OpenAPI schema.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response

from app.modules.games import service as games_service
from app.modules.progress import service as progress
from app.modules.sessions import service as sessions
from app.platform import authz
from app.platform.db import get_sessionmaker
from app.platform.errors import documented, error_response

router = APIRouter(prefix="/api/dev", tags=["dev"], include_in_schema=False)

STEPS = (progress.Step.CLASS_GAME, progress.Step.DEBRIEF, progress.Step.QUIZ_PASSED)


@router.post(
    "/class-sessions/{class_session_id}/quiz-passed",
    status_code=204,
    response_class=Response,
    response_model=None,
    responses=documented(403, 404),
    operation_id="devPassQuiz",
)
async def pass_quiz(
    class_session_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("games.start_own"))],
) -> Response | JSONResponse:
    """Record the User's steps up to `quiz_passed` now. 404 `not_found` unless the session is one
    of their own locked Class sessions in which they have a game."""
    try:
        session_id = uuid.UUID(class_session_id)
    except ValueError:
        return error_response(404, "not_found", "No such Class session.")
    async with get_sessionmaker().begin() as s:
        row = await sessions.replay_session_of(s, user, session_id)
        if row is None or await games_service.student_game(s, user.id, session_id) is None:
            return error_response(404, "not_found", "No such Class session.")
        at = await games_service.database_now(s)
        for step in STEPS:
            await progress.record_step(user.id, session_id, step, at, within=s)
    return Response(status_code=204)


@router.post(
    "/class-sessions/{class_session_id}/replay-done",
    status_code=204,
    response_class=Response,
    response_model=None,
    responses=documented(403, 404),
    operation_id="devCompleteReplay",
)
async def complete_replay(
    class_session_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("games.start_own"))],
) -> Response | JSONResponse:
    """Record the User's steps up to `replay` now (Story 11.3), so the Individual test opens
    without a played Replay. 404 `not_found` as for the quiz pass."""
    try:
        session_id = uuid.UUID(class_session_id)
    except ValueError:
        return error_response(404, "not_found", "No such Class session.")
    async with get_sessionmaker().begin() as s:
        row = await sessions.replay_session_of(s, user, session_id)
        if row is None or await games_service.student_game(s, user.id, session_id) is None:
            return error_response(404, "not_found", "No such Class session.")
        at = await games_service.database_now(s)
        for step in (*STEPS, progress.Step.REPLAY):
            await progress.record_step(user.id, session_id, step, at, within=s)
    return Response(status_code=204)
