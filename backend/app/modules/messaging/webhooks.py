"""`POST /api/webhooks/resend`: what the mail provider reports about sent mails (Story 4.6, AD-11,
AD-14, NFR-10).

The one mutating route exempt from `X-Requested-With` (the `/api/webhooks/` prefix in
`platform/auth`): the provider cannot send the header, so the Svix signature under
`RESEND_WEBHOOK_SECRET` is what admits a request. Mounted in every environment. The body is read
up to `MAX_BODY` bytes, verified before it is parsed, and never logged.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response

from app.modules.messaging import service
from app.platform import auth, authz
from app.platform.errors import error_response

# Not in the OpenAPI schema: the web client never calls it.
router = APIRouter(prefix="/api/webhooks", tags=["webhooks"], include_in_schema=False)

MAX_BODY = 256 * 1024
"""Resend's events are a few KiB; anything far larger is refused unread."""


async def _capped_body(request: Request) -> bytes | None:
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_BODY:
        return None
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > MAX_BODY:
            return None
    return bytes(body)


@router.post(
    "/resend",
    operation_id="resendWebhook",
    dependencies=[Depends(authz.public)],  # admitted by its signature, checked below
)
async def resend_webhook(request: Request) -> Response:
    """Store one delivery, delay or bounce event on the mail it names. 401
    `webhook_signature_invalid` for a missing, wrong or stale signature; 400 `invalid_request` for
    a signed body that is no readable event; 413 `payload_too_large`. An event of another type, or
    for a mail this system does not know, is acknowledged (200) and ignored."""
    body = await _capped_body(request)
    if body is None:
        return error_response(413, "payload_too_large", "The event is too large.")
    headers = {name.lower(): value for name, value in request.headers.items()}
    try:
        outcome = await service.receive_webhook(body, headers, auth.utcnow())
    except service.SignatureInvalid:
        return error_response(401, "webhook_signature_invalid", "The signature is not valid.")
    except service.EventUnreadable:
        return error_response(400, "invalid_request", "The event cannot be read.")
    return JSONResponse({"outcome": outcome})
