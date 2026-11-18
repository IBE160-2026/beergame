"""`/api/auth/*`: login, logout and the current session (Story 3.2), the password reset
(Story 3.6) and accepting an Invitation (Story 3.8). `/api/admin/*`: the Admin's actions on
accounts: Invitations (Stories 3.7, 3.10), roles (3.9), deactivation and reactivation (3.10)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse

from app.modules.identity import service
from app.modules.identity.schemas import (
    INVITATION_PAGE_DEFAULT,
    INVITATION_PAGE_MAX,
    SEARCH_MAX_LENGTH,
    USER_PAGE_DEFAULT,
    USER_PAGE_MAX,
    AcceptExistingIn,
    AcceptInvitationIn,
    AccountRole,
    InvitationCheckOut,
    InvitationIn,
    InvitationListOut,
    InvitationOut,
    InvitationTokenIn,
    LoginIn,
    NewPasswordIn,
    PasswordResetIn,
    ResetEmailOut,
    ResetTokenIn,
    RoleIn,
    SessionOut,
    UserListItem,
    UserListOut,
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
    return _signed_in(outcome)


def _signed_in(outcome: service.LoginOk) -> Response:
    """The session answer: the User, and the cookie at their current session version."""
    response = JSONResponse(SessionOut(user=outcome.user).model_dump(mode="json"))
    auth.set_session_cookie(response, outcome.user.id, session_version=outcome.session_version)
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


def _invitation_answer(outcome: service.LoginOk | service.AcceptRefused) -> Response:
    """The answer to an Invitation route: a logged-in session for an accepted Invitation, or the
    refusal."""
    if isinstance(outcome, service.AcceptRefused):
        status, message = INVITATION_REFUSALS[outcome.code]
        headers = {"Retry-After": str(outcome.retry_after)} if outcome.retry_after else None
        return error_response(status, outcome.code, message, headers=headers)
    return _signed_in(outcome)


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
        return _invitation_answer(service.AcceptRefused("invitation_link_invalid"))
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
    return _invitation_answer(
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
    return _invitation_answer(
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


ROLE_REFUSALS = {
    "not_found": (404, "No such User."),
    "last_admin": (409, "The product would be left without an active Admin."),
    "role_revoke_blocked": (409, "The User owns Classes; add another Lecturer or archive them."),
}


def _role_answer(outcome: UserListItem | service.RoleRefused) -> Response:
    if isinstance(outcome, service.RoleRefused):
        status, message = ROLE_REFUSALS[outcome.code]
        fields = {"classes": outcome.classes} if outcome.code == "role_revoke_blocked" else None
        return error_response(status, outcome.code, message, fields)
    return JSONResponse(outcome.model_dump(mode="json"))


@admin_router.get(
    "/users",
    response_model=UserListOut,
    responses=documented(401, 403, 422),
    operation_id="listUsers",
)
async def list_users(
    _: Annotated[UserOut, Depends(authz.require("users.list"))],
    q: Annotated[str, Query(max_length=SEARCH_MAX_LENGTH)] = "",
    cursor: Annotated[str | None, Query(max_length=64)] = None,
    limit: Annotated[int, Query(ge=1, le=USER_PAGE_MAX)] = USER_PAGE_DEFAULT,
) -> Response:
    """Users with their account roles and status, by name, searched by part of the e-mail or
    the name (FR-2, FR-3). The search text is never logged (AD-14)."""
    try:
        page = await service.list_users(q, cursor, limit)
    except service.InvalidCursor:
        return error_response(
            422, "invalid_request", "The cursor is not valid.", {"cursor": "invalid_cursor"}
        )
    return JSONResponse(page.model_dump(mode="json"))


@admin_router.post(
    "/users/{user_id}/roles",
    response_model=UserListItem,
    responses=documented(401, 403, 404, 422),
    operation_id="grantRole",
)
async def grant_role(
    user_id: uuid.UUID,
    body: RoleIn,
    user: Annotated[UserOut, Depends(authz.require("users.manage"))],
) -> Response:
    """Give a User the Lecturer or Admin role; it holds from their next request (FR-2)."""
    return _role_answer(await service.grant_role(user.id, user_id, body.role, now=auth.utcnow()))


@admin_router.delete(
    "/users/{user_id}/roles/{role}",
    response_model=UserListItem,
    responses=documented(401, 403, 404, 409, 422),
    operation_id="revokeRole",
)
async def revoke_role(
    user_id: uuid.UUID,
    role: AccountRole,
    user: Annotated[UserOut, Depends(authz.require("users.manage"))],
) -> Response:
    """Take the Lecturer or Admin role from a User; it ends at their next request (FR-2). Refused
    with `last_admin` or `role_revoke_blocked` (`fields.classes`)."""
    return _role_answer(await service.revoke_role(user.id, user_id, role, now=auth.utcnow()))


STATUS_REFUSALS = {
    "not_found": (404, "No such User."),
    "last_admin": (409, "The product would be left without an active Admin."),
}


def _status_answer(outcome: UserListItem | service.StatusRefused) -> Response:
    if isinstance(outcome, service.StatusRefused):
        status, message = STATUS_REFUSALS[outcome.code]
        return error_response(status, outcome.code, message)
    return JSONResponse(outcome.model_dump(mode="json"))


@admin_router.post(
    "/users/{user_id}/deactivate",
    response_model=UserListItem,
    responses=documented(401, 403, 404, 409, 422),
    operation_id="deactivateUser",
)
async def deactivate_user(
    user_id: uuid.UUID,
    user: Annotated[UserOut, Depends(authz.require("users.manage"))],
) -> Response:
    """Deactivate a User: they cannot log in, their sessions end at once, and none of their data
    is deleted (FR-3). Refused with `last_admin` for oneself or the last active Admin."""
    return _status_answer(await service.deactivate_user(user.id, user_id, now=auth.utcnow()))


@admin_router.post(
    "/users/{user_id}/reactivate",
    response_model=UserListItem,
    responses=documented(401, 403, 404, 422),
    operation_id="reactivateUser",
)
async def reactivate_user(
    user_id: uuid.UUID,
    user: Annotated[UserOut, Depends(authz.require("users.manage"))],
) -> Response:
    """Reactivate a User: they log in again with the same password and roles (FR-3)."""
    return _status_answer(await service.reactivate_user(user.id, user_id, now=auth.utcnow()))


@admin_router.get(
    "/invitations",
    response_model=InvitationListOut,
    responses=documented(401, 403, 422),
    operation_id="listInvitations",
)
async def list_invitations(
    _: Annotated[UserOut, Depends(authz.require("users.list"))],
    cursor: Annotated[str | None, Query(max_length=64)] = None,
    limit: Annotated[int, Query(ge=1, le=INVITATION_PAGE_MAX)] = INVITATION_PAGE_DEFAULT,
) -> Response:
    """The newest Invitation to each address and role, newest first, with its status and whether
    the recipient asked for a new one (FR-1, FR-3)."""
    try:
        page = await service.list_invitations(cursor, limit, now=auth.utcnow())
    except service.InvalidCursor:
        return error_response(
            422, "invalid_request", "The cursor is not valid.", {"cursor": "invalid_cursor"}
        )
    return JSONResponse(page.model_dump(mode="json"))


RESEND_REFUSALS = {
    "not_found": (404, "No such Invitation."),
    "invitation_accepted": (409, "The Invitation is accepted."),
    "invitation_superseded": (409, "A newer Invitation to the address and role exists."),
    "account_deactivated": (409, "The address belongs to a deactivated account."),
}


@admin_router.post(
    "/invitations/{invitation_id}/resend",
    status_code=201,
    response_model=InvitationOut,
    responses=documented(401, 403, 404, 409, 422),
    operation_id="resendInvitation",
)
async def resend_invitation(
    invitation_id: uuid.UUID,
    user: Annotated[UserOut, Depends(authz.require("users.manage"))],
) -> Response:
    """Send an open or expired Invitation again with a new link and expiry; the old link stops
    working (FR-3)."""
    outcome = await service.resend_invitation(user.id, invitation_id, now=auth.utcnow())
    if isinstance(outcome, service.ResendRefused):
        status, message = RESEND_REFUSALS[outcome.code]
        return error_response(status, outcome.code, message)
    return JSONResponse(outcome.model_dump(mode="json"), status_code=201)
