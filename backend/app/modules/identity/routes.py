"""`/api/auth/*`: login, logout and the current session (Story 3.2), and the password reset
(Story 3.6)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from app.modules.identity import service
from app.modules.identity.schemas import (
    LoginIn,
    NewPasswordIn,
    PasswordResetIn,
    ResetEmailOut,
    ResetTokenIn,
    SessionOut,
    UserOut,
)
from app.platform import auth, authz, ratelimit
from app.platform.errors import documented, error_response

router = APIRouter(prefix="/api/auth", tags=["auth"])

REFUSALS = {
    "invalid_credentials": (401, "Wrong e-mail or password."),
    "account_deactivated": (403, "The account is deactivated."),
    "rate_limited": (429, "Too many failed logins; wait until the window ends."),
}


@router.post(
    "/login",
    response_model=SessionOut,
    responses=documented(401, 403, 422, 429),
    operation_id="login",
    dependencies=[Depends(authz.public)],
)
async def login(body: LoginIn, request: Request) -> Response:
    outcome = await service.authenticate(
        body.email, body.password, ip=ratelimit.client_ip(request), now=auth.utcnow()
    )
    if isinstance(outcome, service.LoginRefused):
        status, message = REFUSALS[outcome.code]
        headers = {"Retry-After": str(outcome.retry_after)} if outcome.retry_after else None
        return error_response(status, outcome.code, message, headers=headers)
    response = JSONResponse(SessionOut(user=outcome.user).model_dump(mode="json"))
    auth.set_session_cookie(response, outcome.user.id)
    return response


@router.post(
    "/logout",
    status_code=204,
    responses=documented(403),
    operation_id="logout",
    dependencies=[Depends(authz.public)],  # needs no session: it only clears the cookie
)
async def logout() -> Response:
    response = Response(status_code=204)
    auth.clear_session_cookie(response)
    return response


@router.get("/me", response_model=SessionOut, responses=documented(401), operation_id="me")
async def me(
    user: Annotated[UserOut, Depends(authz.require("session.read"))],
) -> SessionOut:
    return SessionOut(user=user)


RESET_LINK_INVALID = (410, "reset_link_invalid", "The link is expired, used or unknown.")


@router.post(
    "/password-reset",
    status_code=202,
    responses=documented(422, 429),
    operation_id="requestPasswordReset",
    dependencies=[Depends(authz.public)],
)
async def request_password_reset(body: PasswordResetIn, request: Request) -> Response:
    """Mail a reset link if the address has an active account. The answer is the same `202`
    whether or not it has one (UX-DR61)."""
    retry_after = await service.request_password_reset(
        body.email, ip=ratelimit.client_ip(request), now=auth.utcnow()
    )
    if retry_after is not None:
        return error_response(
            429,
            "rate_limited",
            "Too many reset requests; wait until the window ends.",
            headers={"Retry-After": str(retry_after)},
        )
    return Response(status_code=202)


@router.post(
    "/password-reset/check",
    response_model=ResetEmailOut,
    responses=documented(410, 422),
    operation_id="checkPasswordReset",
    dependencies=[Depends(authz.public)],
)
async def check_password_reset(body: ResetTokenIn) -> Response:
    """Whether a reset link still works, and the address it belongs to."""
    address = await service.check_password_reset(body.token, now=auth.utcnow())
    if address is None:
        return error_response(*RESET_LINK_INVALID)
    return JSONResponse(ResetEmailOut(email=address).model_dump(mode="json"))


@router.post(
    "/password-reset/confirm",
    response_model=ResetEmailOut,
    responses=documented(410, 422),
    operation_id="confirmPasswordReset",
    dependencies=[Depends(authz.public)],
)
async def confirm_password_reset(body: NewPasswordIn) -> Response:
    """Set a new password through a reset link; the link then stops working."""
    address = await service.confirm_password_reset(body.token, body.password, now=auth.utcnow())
    if address is None:
        return error_response(*RESET_LINK_INVALID)
    return JSONResponse(ResetEmailOut(email=address).model_dump(mode="json"))
