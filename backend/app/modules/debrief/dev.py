"""The local dev back-dating of a Group debrief step (Story 9.11): `POST
/api/dev/debriefs/{id}/backdate` moves the opening time of the Debrief session's current step back
by the move-on wait, so the end-to-end test of «Gå videre for alle» need not wait minutes.

Story 9.14: `POST /api/dev/games/{game_id}/seats/{seat}/narrate` runs a finished Class game
Seat's narration job in the api process now (the `llm-batch` job's own code), so an end-to-end
test need not wait on `worker-batch`. With `?outage=true` the Seat's stored AI texts are deleted
first and the mock provider fails every attempt (`app.ai.text.provider_failing`), so the code text
is stored.

`create_app()` mounts it only when `APP_ENV` is not `production`, like the dev lock; there it does
not exist at all. It is not in the OpenAPI schema. The write goes through `debrief.commands`."""

import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response

from app.ai import text as ai_text
from app.modules.debrief import commands, narration, service
from app.modules.games import service as games
from app.platform import authz
from app.platform.errors import error_response

router = APIRouter(prefix="/api/dev", tags=["dev"], include_in_schema=False)

OUTAGE_TRIES = 3
"""How often the outage narration clears and stores again when the worker stored in between."""


@router.post(
    "/debriefs/{debrief_id}/backdate",
    operation_id="devBackdateDebriefStep",
    dependencies=[Depends(authz.public)],  # local only: not mounted in production
)
async def backdate(debrief_id: str) -> Response:
    """Back-date the current shared step by the move-on wait. 404 `not_found` for a bad id."""
    try:
        found = uuid.UUID(debrief_id)
    except ValueError:
        return error_response(404, "not_found", "No such Debrief session.")
    await commands.backdate_step(found, service.move_on_wait())
    return JSONResponse({"backdated": True})


@router.post(
    "/games/{game_id}/seats/{seat}/narrate",
    operation_id="devNarrateSeat",
    dependencies=[Depends(authz.public)],  # local only: not mounted in production
)
async def narrate(game_id: str, seat: str, outage: bool = False) -> Response:
    """Narrate the Seat (its Role or id) of a finished Class game now. 404 `not_found` for a
    Game or Seat that is not there or not finished."""
    try:
        stored = await games.fact_set(game_id, seat)
    except games.ViewError:
        return error_response(404, "not_found", "No such finished Seat.")
    if not outage:
        done = await narration.narrate(stored.game_id, stored.seat_id)
        return JSONResponse({"narrated": done, "fact_set_id": stored.id})
    fact_set_id = uuid.UUID(stored.id)
    for _ in range(OUTAGE_TRIES):
        await commands.clear_ai_texts(fact_set_id)
        with ai_text.provider_failing():
            await narration.narrate(stored.game_id, stored.seat_id)
        # `worker-batch` may have stored the mock's answer in between: then once more.
        if not await narration.narration_is_ai(fact_set_id):
            return JSONResponse({"narrated": True, "fact_set_id": stored.id})
    return error_response(409, "conflict", "The Seat's narration kept being stored by the worker.")
