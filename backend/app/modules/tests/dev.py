"""The local dev close of an Individual test (Story 12.4): `POST /api/dev/class-sessions/{id}/test/
close` moves the logged-in Student's own attempt deadline to now and closes it as the sweep would
(`commands.close_attempt`), so the AI assessment is deferred at once and `worker-batch` assesses it
on the mock provider. Run the dev Test-deadline lock (`…/lock-test`) first, as the sweep does.

The end-to-end test of «KI-vurderingen er klar» on Hjem uses it, as the dev lock (Story 6.15)
stands in for the Start date. `create_app()` mounts it only when `APP_ENV` is not `production`;
there it does not exist at all. It is not in the OpenAPI schema.
"""

import uuid
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tests import commands
from app.modules.tests.models import test_attempts
from app.platform import auth, authz
from app.platform.db import get_sessionmaker
from app.platform.errors import documented, error_response

router = APIRouter(prefix="/api/dev", tags=["dev"], include_in_schema=False)


async def _deadline(s: AsyncSession, attempt_id: uuid.UUID, when: datetime | None) -> None:
    await s.execute(
        update(test_attempts)
        .where(test_attempts.c.id == attempt_id, test_attempts.c.closed_at.is_(None))
        .values(effective_deadline=when)
    )


@router.post(
    "/class-sessions/{class_session_id}/test/close",
    status_code=204,
    response_class=Response,
    response_model=None,
    responses=documented(403, 404, 409),
    operation_id="devCloseOwnTest",
)
async def close_own_test(
    class_session_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("tests.take_own"))],
) -> Response | JSONResponse:
    """Close the User's own attempt now (204 for one closed already). 404 `not_found` without an
    attempt in the session; 409 `not_closed` when it could not be closed (the Test-deadline lock
    has not run, say)."""
    try:
        session_id = uuid.UUID(class_session_id)
    except ValueError:
        return error_response(404, "not_found", "No such Class session.")
    now = auth.utcnow()
    async with get_sessionmaker().begin() as s:
        attempt = await commands.attempt_of(s, user.id, session_id)
        if attempt is None:
            return error_response(404, "not_found", "No attempt in this Class session.")
        if attempt["closed_at"] is not None:
            return Response(status_code=204)
        await _deadline(s, attempt["id"], now - timedelta(seconds=1))
    if not await commands.close_attempt(attempt["id"], now):
        # Not closed (no Test-deadline lock yet): the attempt keeps its own deadline.
        async with get_sessionmaker().begin() as s:
            await _deadline(s, attempt["id"], attempt["effective_deadline"])
        return error_response(409, "not_closed", "The attempt could not be closed.")
    return Response(status_code=204)
