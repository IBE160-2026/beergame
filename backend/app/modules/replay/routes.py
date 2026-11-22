"""The Student's Replay (Story 10.3, FR-48): `POST /api/me/class-sessions/{session_id}/replay`;
its walkthrough (Story 10.7, FR-50): `GET /api/me/games/{game_id}/walkthrough`; the
another-round question after it (Story 10.8): `GET`/`POST /api/me/games/{game_id}/another-round`.

A Class session that is not one of the User's own locked sessions, one that does not exist and an
id that is not one all answer the same 403 `forbidden` (FR-5); so does a Game that is not the
User's own Replay."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from app.modules.games import service as games_service
from app.modules.replay import questions, service, walkthrough
from app.modules.replay.schemas import AnotherRoundIn, AnotherRoundOut, ReplayWalkthroughOut
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


UNAVAILABLE = {
    "replay_closed": "The Replay was closed at the Test deadline and has no walkthrough.",
    "replay_not_finished": "The Replay has not finished.",
}


@router.get(
    "/me/games/{game_id}/walkthrough",
    response_model=ReplayWalkthroughOut,
    responses=documented(401, 403, 404, 409),
    operation_id="getMyReplayWalkthrough",
)
async def get_my_replay_walkthrough(
    game_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("games.read_own"))],
) -> Response:
    """The Replay-gjennomgang (Story 10.7, FR-50, AD-7): the Student's finished Replay beside
    their own Class game, every number from the two Games' stored Week rows and facts sets.
    `pending` while the line is being worded (`retry_after_seconds`); 409 `replay_closed` for a
    Replay closed at the Test deadline (Story 10.6) and `replay_not_finished` before its end;
    403 `forbidden` for any Game that is not the User's own Replay (FR-5, AD-12)."""
    try:
        found = await walkthrough.walkthrough(user, game_id)
    except walkthrough.Unavailable as refused:
        return error_response(409, refused.code, UNAVAILABLE[refused.code])
    except games_service.ViewError as failed:
        return error_response(failed.status, failed.code, "No walkthrough can be built.")
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


@router.get(
    "/me/games/{game_id}/another-round",
    response_model=AnotherRoundOut,
    responses=documented(401, 403, 409),
    operation_id="getMyAnotherRound",
)
async def get_my_another_round(
    game_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("games.read_own"))],
) -> Response:
    """«Ville du spilt en runde til?» after the Replay-gjennomgang (Story 10.8, FR-50): the
    Student's own answer, null until given. 409 `replay_closed` or `replay_not_finished`; 403
    `forbidden` for any Game that is not the User's own Replay (FR-5, AD-12)."""
    try:
        found = await questions.another_round(user, game_id)
    except walkthrough.Unavailable as refused:
        return error_response(409, refused.code, UNAVAILABLE[refused.code])
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


@router.post(
    "/me/games/{game_id}/another-round",
    status_code=201,
    response_model=AnotherRoundOut,
    responses=documented(401, 403, 409, 422),
    operation_id="answerMyAnotherRound",
)
async def answer_my_another_round(
    game_id: str,
    body: AnotherRoundIn,
    user: Annotated[authz.Principal, Depends(authz.require("games.read_own"))],
) -> Response:
    """«Send svar» on «Ville du spilt en runde til?» (Story 10.8, FR-50, SM-10): stored once per
    Student and Class session. 409 `already_answered` (the first answer stands), `replay_closed`
    or `replay_not_finished`; 403 `forbidden` for any Game that is not the User's own Replay."""
    try:
        found = await questions.answer_another_round(user, game_id, body.answer)
    except walkthrough.Unavailable as refused:
        return error_response(409, refused.code, UNAVAILABLE[refused.code])
    except questions.AlreadyAnswered:
        return error_response(409, "already_answered", "You have answered already.")
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"), status_code=201)
