"""The local dev lock (Story 6.15): `POST /api/dev/class-sessions/{id}/lock` locks a Class
session now, whatever its Start date, and opens its Class games (`service.lock`). Story 12.1 adds
`POST /api/dev/class-sessions/{id}/lock-test`, the Test-deadline lock now (`service.lock_test`).
The local dev
Takeover (Story 8.3): `POST /api/dev/games/{id}/seats/{role}/takeover` runs the sweep's Takeover
of one Seat at its stored due time, the injected clock, so no test waits the Inactivity limit. The
local dev playout (Story 8.14): `POST /api/dev/games/{id}/playout` runs the Play deadline playout
of one Class game at its Class session's Play deadline. Story 13.7:
`POST /api/dev/class-sessions/{id}/test-deadline-passed` moves the dates into the past, so the
Student report opens at once.

A real started Class game needs its Start date to pass and the sweep; the end-to-end tests of the
play screen use this route instead, as the stand-in for the Lecturer's early lock of Epic 8.
`create_app()` mounts it only when `APP_ENV` is not `production`, like the dev mailbox; there it
does not exist at all. It is not in the OpenAPI schema.
"""

import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import update

from app.engine.settings import Role
from app.modules.games import commands as games_commands
from app.modules.games import service as games_service
from app.modules.sessions import repo, service
from app.modules.sessions.models import class_sessions
from app.platform import auth, authz
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


@router.post(
    "/class-sessions/{class_session_id}/lock-test",
    response_model=DevLockOut,
    responses=documented(404),
    operation_id="devLockClassSessionTest",
    dependencies=[Depends(authz.public)],  # local only: not mounted in production
)
async def lock_test_now(class_session_id: str) -> DevLockOut | JSONResponse:
    """Story 12.1: run the Test-deadline lock now, whatever the Test deadline (`service.lock_test`),
    so the end-to-end tests see the «KI-vurdering» switch pinned. 404 `not_found` for no such
    session."""
    try:
        session_id = uuid.UUID(class_session_id)
    except ValueError:
        return error_response(404, "not_found", "No such Class session.")
    async with get_sessionmaker()() as s:
        if await repo.session_row(s, session_id) is None:
            return error_response(404, "not_found", "No such Class session.")
    return DevLockOut(locked=await service.lock_test(session_id, now=auth.utcnow()))


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


class DevPlayoutOut(BaseModel):
    played_out: bool
    """True when this call played the Game out; False when it was played out or finished."""


@router.post(
    "/games/{game_id}/playout",
    response_model=DevPlayoutOut,
    responses=documented(404, 409),
    operation_id="devPlayOutGame",
    dependencies=[Depends(authz.public)],  # local only: not mounted in production
)
async def play_out_now(game_id: str) -> DevPlayoutOut | JSONResponse:
    """Run the Play deadline playout of one Class game (Story 8.14) as the sweep would at its
    Class session's Play deadline: `games.commands.playout` with that deadline as the injected
    clock, whatever the time is now, so no test waits for the deadline. 404 `not_found` for no
    such Game or a Class session with no Play deadline; 409 with the command's refusal code."""
    try:
        game_uuid = uuid.UUID(game_id)
    except ValueError:
        return error_response(404, "not_found", "No such Game.")
    async with get_sessionmaker()() as s:
        head = await games_service.game_class_info(s, game_uuid)
        row = None if head is None else await repo.session_row(s, head[0])
    if head is None:
        return error_response(404, "not_found", "No such Game.")
    if row is None or row["play_deadline"] is None:
        return error_response(404, "not_found", "No Play deadline for that Game.")
    try:
        played = await games_commands.playout(
            game_id, now=row["play_deadline"], latest=row["play_deadline"]
        )
    except games_commands.CommandError as refused:
        return error_response(refused.status, refused.code, "The playout was refused.")
    return DevPlayoutOut(played_out=played)


class DevDeadlineOut(BaseModel):
    test_deadline: str
    """The Class session's new Test deadline, a minute ago."""


@router.post(
    "/class-sessions/{class_session_id}/test-deadline-passed",
    response_model=DevDeadlineOut,
    responses=documented(404),
    operation_id="devPassTestDeadline",
    dependencies=[Depends(authz.public)],  # local only: not mounted in production
)
async def pass_test_deadline(class_session_id: str) -> DevDeadlineOut | JSONResponse:
    """Story 13.7: move the Class session's dates into the past, in order, so its Test deadline
    passed a minute ago: the Student report opens without waiting. A date already earlier stays.
    404 `not_found` for no such session."""
    try:
        session_id = uuid.UUID(class_session_id)
    except ValueError:
        return error_response(404, "not_found", "No such Class session.")
    now = auth.utcnow()
    async with get_sessionmaker().begin() as s:
        row = await repo.session_row(s, session_id, lock=True)
        if row is None:
            return error_response(404, "not_found", "No such Class session.")
        moved = {
            name: min(row[name], now - timedelta(minutes=minutes))
            if row[name] is not None
            else now - timedelta(minutes=minutes)
            for name, minutes in (
                ("start_at", 4),
                ("play_deadline", 3),
                ("debrief_deadline", 2),
                ("test_deadline", 1),
            )
        }
        await s.execute(
            update(class_sessions).where(class_sessions.c.id == session_id).values(**moved)
        )
    return DevDeadlineOut(test_deadline=moved["test_deadline"].isoformat())
