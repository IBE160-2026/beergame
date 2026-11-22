"""The local dev lock (Story 6.15): `POST /api/dev/class-sessions/{id}/lock` locks a Class
session now, whatever its Start date, and opens its Class games (`service.lock`). Story 12.1 adds
`POST /api/dev/class-sessions/{id}/lock-test`, the Test-deadline lock now (`service.lock_test`).

A real started Class game needs its Start date to pass and the sweep; the end-to-end tests of the
play screen use this route instead, as the stand-in for the Lecturer's early lock of Epic 8.
`create_app()` mounts it only when `APP_ENV` is not `production`, like the dev mailbox; there it
does not exist at all. It is not in the OpenAPI schema.
"""

import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.modules.sessions import repo, service
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
