"""`/api/auth/*`: login, logout and the current session (Story 3.2), the password reset
(Story 3.6) and accepting an Invitation (Story 3.8). `/api/admin/*`: the Admin's actions on
accounts, from the Invitation (Story 3.7)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from app.modules.identity import service
from app.modules.identity.schemas import (
    AcceptExistingIn,
    AcceptInvitationIn,
    InvitationCheckOut,
    InvitationIn,
    InvitationOut,
    InvitationTokenIn,
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


INVITATION_REFUSALS = {
    "invitation_link_invalid": (410, "The link is expired, used or unknown."),
    "account_exists": (409, "The address already has an account; log in to accept."),
    "invalid_credentials": (401, "Wrong e-mail or password."),
    "rate_limited": (429, "Too many attempts; wait until the window ends."),
}


def _accepted(outcome: UserOut | service.AcceptRefused) -> Response:
    """A logged-in session for the accepted Invitation, or the refusal."""
    if isinstance(outcome, service.AcceptRefused):
        status, message = INVITATION_REFUSALS[outcome.code]
        headers = {"Retry-After": str(outcome.retry_after)} if outcome.retry_after else None
        return error_response(status, outcome.code, message, headers=headers)
    response = JSONResponse(SessionOut(user=outcome).model_dump(mode="json"))
    auth.set_session_cookie(response, outcome.id)
    return response


@router.post(
    "/invitation/check",
    response_model=InvitationCheckOut,
    responses=documented(410, 422),
    operation_id="checkInvitation",
    dependencies=[Depends(authz.public)],
)
async def check_invitation(body: InvitationTokenIn) -> Response:
    """Whether an Invitation link still works, and what «Du er invitert» shows for it."""
    checked = await service.check_invitation(body.token, now=auth.utcnow())
    if checked is None:
        return _accepted(service.AcceptRefused("invitation_link_invalid"))
    out = InvitationCheckOut(
        email=checked.email,
        role=checked.role,
        valid_days=checked.valid_days,
        has_account=checked.has_account,
    )
    return JSONResponse(out.model_dump(mode="json"))


@router.post(
    "/invitation/accept",
    response_model=SessionOut,
    responses=documented(409, 410, 422, 429),
    operation_id="acceptInvitation",
    dependencies=[Depends(authz.public)],
)
async def accept_invitation(body: AcceptInvitationIn, request: Request) -> Response:
    """Create the account an Invitation offers, with its role, and log in (FR-1, FR-4)."""
    return _accepted(
        await service.accept_invitation_new(
            body.token,
            body.name,
            body.password,
            ip=ratelimit.client_ip(request),
            now=auth.utcnow(),
        )
    )


@router.post(
    "/invitation/accept-login",
    response_model=SessionOut,
    responses=documented(401, 410, 422, 429),
    operation_id="acceptInvitationWithLogin",
    dependencies=[Depends(authz.public)],
)
async def accept_invitation_with_login(body: AcceptExistingIn, request: Request) -> Response:
    """Add an Invitation's role to the account its address already has, and log in."""
    return _accepted(
        await service.accept_invitation_existing(
            body.token, body.password, ip=ratelimit.client_ip(request), now=auth.utcnow()
        )
    )


@router.post(
    "/invitation/renewal",
    status_code=202,
    responses=documented(422, 429),
    operation_id="requestInvitationRenewal",
    dependencies=[Depends(authz.public)],
)
async def request_invitation_renewal(body: InvitationTokenIn, request: Request) -> Response:
    """Ask for a new Invitation from a link that no longer works. The answer is the same `202`
    for any link (UX-DR61)."""
    retry_after = await service.request_invitation_renewal(
        body.token, ip=ratelimit.client_ip(request), now=auth.utcnow()
    )
    if retry_after is not None:
        return error_response(
            429,
            "rate_limited",
            INVITATION_REFUSALS["rate_limited"][1],
            headers={"Retry-After": str(retry_after)},
        )
    return Response(status_code=202)


admin_router = APIRouter(prefix="/api/admin", tags=["admin"])


@admin_router.post(
    "/invitations",
    status_code=201,
    response_model=InvitationOut,
    responses=documented(401, 403, 422),
    operation_id="sendInvitation",
)
async def send_invitation(
    body: InvitationIn,
    user: Annotated[UserOut, Depends(authz.require("users.manage"))],
) -> Response:
    """Invite an address to the Lecturer or Admin role (FR-1). Sending again to the same address
    and role voids the earlier link."""
    try:
        sent = await service.send_invitation(user.id, body.email, body.role, now=auth.utcnow())
    except service.InvalidEmail:
        return error_response(
            422, "invalid_request", "The e-mail address is not valid.", {"email": "invalid_email"}
        )
    return JSONResponse(sent.model_dump(mode="json"), status_code=201)
