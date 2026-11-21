"""The local dev back-dating of a Group debrief step (Story 9.11): `POST
/api/dev/debriefs/{id}/backdate` moves the opening time of the Debrief session's current step back
by the move-on wait, so the end-to-end test of «Gå videre for alle» need not wait minutes.

`create_app()` mounts it only when `APP_ENV` is not `production`, like the dev lock; there it does
not exist at all. It is not in the OpenAPI schema. The write goes through `debrief.commands`."""

import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response

from app.modules.debrief import commands, service
from app.platform import authz
from app.platform.errors import error_response

router = APIRouter(prefix="/api/dev", tags=["dev"], include_in_schema=False)


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
