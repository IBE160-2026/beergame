"""The Starting task routes (Story 6.3, FR-85): `/api/me/games/{game_id}/starting-task`. Any game
that is not the Student's own locked Class game answers 403 `forbidden`, the same for one that
does not exist (FR-5)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response

from app.modules.tests import service
from app.modules.tests.schemas import AnswerIn, FinalIn, StartingTaskOut
from app.platform import auth, authz
from app.platform.errors import documented, error_response

router = APIRouter(prefix="/api", tags=["tests"])

_PATH = "/me/games/{game_id}/starting-task"


def _state(found: StartingTaskOut) -> Response:
    return JSONResponse(found.model_dump(mode="json"))


@router.get(
    _PATH,
    response_model=StartingTaskOut,
    responses=documented(401, 403),
    operation_id="getMyStartingTask",
)
async def get_starting_task(
    game_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("games.read_own"))],
) -> Response:
    """The Student's Starting task: the items in order, each answered one with its result, the
    final question's choice and whether the task is done."""
    return _state(await service.read(user, game_id))


@router.post(
    f"{_PATH}/answers",
    response_model=StartingTaskOut,
    responses=documented(401, 403, 422),
    operation_id="answerStartingTaskItem",
)
async def answer_starting_task_item(
    game_id: str,
    body: AnswerIn,
    user: Annotated[authz.Principal, Depends(authz.require("starting_task.answer_own"))],
) -> Response:
    """Send the answer to one item: scored by computed rules and stored once (a repeat keeps
    the first answer). 422 `unknown_item` for an item the task does not have."""
    try:
        found = await service.answer(user, game_id, body.item_id, body.answer, auth.utcnow())
    except service.UnknownItem:
        return error_response(422, "unknown_item", "The Starting task has no such item.")
    return _state(found)


@router.post(
    f"{_PATH}/final",
    response_model=StartingTaskOut,
    responses=documented(401, 403, 409, 422),
    operation_id="finishStartingTask",
)
async def finish_starting_task(
    game_id: str,
    body: FinalIn,
    user: Annotated[authz.Principal, Depends(authz.require("starting_task.answer_own"))],
) -> Response:
    """Answer or skip the final question; the task is then done and `starting_task` recorded.
    409 `items_open` while an item has no answer."""
    try:
        found = await service.finish(user, game_id, body.choice, auth.utcnow())
    except service.ItemsOpen:
        return error_response(409, "items_open", "Answer every item first.")
    return _state(found)
