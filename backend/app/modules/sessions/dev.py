"""The local dev lock (Story 6.15): `POST /api/dev/class-sessions/{id}/lock` locks a Class
session now, whatever its Start date, and opens its Class games (`service.lock`). The local dev
Takeover (Story 8.3): `POST /api/dev/games/{id}/seats/{role}/takeover` runs the sweep's Takeover
of one Seat at its stored due time, the injected clock, so no test waits the Inactivity limit.

A real started Class game needs its Start date to pass and the sweep; the end-to-end tests of the
play screen use this route instead, as the stand-in for the Lecturer's early lock of Epic 8.
`create_app()` mounts it only when `APP_ENV` is not `production`, like the dev mailbox; there it
does not exist at all. It is not in the OpenAPI schema.
"""

import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.engine.settings import Role
from app.modules.games import commands as games_commands
from app.modules.games import service as games_service
from app.modules.sessions import repo, service
from app.platform import authz
from app.platform.db import get_sessionmaker
from app.platform.errors import documented, error_response

router = APIRouter(prefix="/api/dev", tags=["dev"], include_in_schema=False)


class DevLockOut(BaseModel):
    locked: bool
    """True when this call locked it; False when it was locked already."""


@router.post(
    "/class-sessions/{class_session_id}/lock",
    response_model=DevLockOut,
    responses=documented(404, 409),
    operation_id="devLockClassSession",
    dependencies=[Depends(authz.public)],  # local only: not mounted in production
)
async def lock_now(class_session_id: str) -> DevLockOut | JSONResponse:
    """Lock the Class session now and open its games. 404 `not_found` for no such session;
    409 `provider_key_missing` when its LLM players could not answer here."""
    try:
        session_id = uuid.UUID(class_session_id)
    except ValueError:
        return error_response(404, "not_found", "No such Class session.")
    async with get_sessionmaker()() as s:
        if await repo.session_row(s, session_id) is None:
            return error_response(404, "not_found", "No such Class session.")
    try:
        locked = await service.lock(session_id)
    except service.ProviderKeyMissing:
        return error_response(409, "provider_key_missing", "The AI players cannot answer here.")
    return DevLockOut(locked=locked)


class DevTakeoverOut(BaseModel):
    occupancy_id: str
    """The occupancy row the Takeover appended."""


@router.post(
    "/games/{game_id}/seats/{role}/takeover",
    response_model=DevTakeoverOut,
    responses=documented(404, 409),
    operation_id="devTakeOverSeat",
    dependencies=[Depends(authz.public)],  # local only: not mounted in production
)
async def take_over_now(game_id: str, role: Role) -> DevTakeoverOut | JSONResponse:
    """Run `games.commands.takeover` for the Seat with `actor` `system` at the Seat's stored
    `takeover_due_at` in the open Week, as the sweep would at that time. 404 `not_found` for no
    such Game or no due time; 409 with the command's refusal code."""
    try:
        game_uuid = uuid.UUID(game_id)
    except ValueError:
        return error_response(404, "not_found", "No such Game.")
    due = await games_service.open_takeover_due(game_uuid, str(role))
    if due is None:
        return error_response(404, "not_found", "No due Takeover for that Seat.")
    try:
        occupancy = await games_commands.takeover(game_id, role, actor="system", now=due)
    except games_commands.CommandError as refused:
        return error_response(refused.status, refused.code, "The Takeover was refused.")
    return DevTakeoverOut(occupancy_id=occupancy)
