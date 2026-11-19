"""The local dev mailbox (Story 3.6): `GET /api/dev/mailbox/latest?to=<e-mail>`, and
`POST /api/dev/mailbox/bounce` (Story 4.6), which makes the newest mail to an address bounce.

Locally every mail is the `[email:mock]` sender, which logs ids only, so a Playwright test cannot
read a link from it. This route renders the newest mail sent to a User again, as `messaging`
rendered it. `create_app()` mounts it only when `APP_ENV` is not `production`; there it does
not exist at all. The request log keeps the path, never the query.
"""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.modules.messaging import service
from app.platform import auth, authz
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


class DevBounceIn(BaseModel):
    to: str = Field(max_length=320)
    bounce_class: Literal["hard", "soft"]


class DevBounceOut(BaseModel):
    delivery_id: uuid.UUID


@router.post(
    "/mailbox/bounce",
    response_model=DevBounceOut,
    responses=documented(404),
    operation_id="devBounceMail",
    dependencies=[Depends(authz.public)],  # local only: not mounted in production
)
async def bounce_mail(body: DevBounceIn) -> DevBounceOut | JSONResponse:
    """Make the newest mail sent to `to` bounce, as the provider would report it (Story 4.6):
    a signed `email.bounced` event through the webhook's own handler. 404 when no mail was sent
    there."""
    delivery_id = await service.simulate_bounce(body.to, body.bounce_class, auth.utcnow())
    if delivery_id is None:
        return error_response(404, "not_found", "No mail sent to that address.")
    return DevBounceOut(delivery_id=delivery_id)
