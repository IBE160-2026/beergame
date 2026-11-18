"""The local dev mailbox (Story 3.6): `GET /api/dev/mailbox/latest?to=<e-mail>`.

Locally every mail is the `[email:mock]` sender, which logs ids only, so a Playwright test cannot
read a link from it. This route renders the newest mail sent to a User again, as `messaging`
rendered it. `create_app()` mounts it only when `APP_ENV` is not `production`; there it does
not exist at all. The request log keeps the path, never the query.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.modules.messaging import service
from app.platform import authz
from app.platform.errors import documented, error_response

# Not in the OpenAPI schema, so the generated web client is the same in every environment.
router = APIRouter(prefix="/api/dev", tags=["dev"], include_in_schema=False)


class DevMailOut(BaseModel):
    subject: str
    text: str
    html: str
    sent_at: datetime


@router.get(
    "/mailbox/latest",
    response_model=DevMailOut,
    responses=documented(404),
    operation_id="devLatestMail",
    dependencies=[Depends(authz.public)],  # local only: not mounted in production
)
async def latest_mail(to: Annotated[str, Query(max_length=320)]) -> DevMailOut | JSONResponse:
    found = await service.latest_sent_mail(to)
    if found is None:
        return error_response(404, "not_found", "No mail sent to that address.")
    mail, sent_at = found
    return DevMailOut(subject=mail.subject, text=mail.text, html=mail.html, sent_at=sent_at)
