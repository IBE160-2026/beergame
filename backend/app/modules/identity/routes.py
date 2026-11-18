"""`/api/auth/*`: login, logout and the current session (Story 3.2)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from app.modules.identity import service
from app.modules.identity.schemas import LoginIn, SessionOut, UserOut
from app.platform import auth, ratelimit
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


@router.post("/logout", status_code=204, responses=documented(403), operation_id="logout")
async def logout() -> Response:
    response = Response(status_code=204)
    auth.clear_session_cookie(response)
    return response


@router.get("/me", response_model=SessionOut, responses=documented(401), operation_id="me")
async def me(user: Annotated[UserOut, Depends(service.current_user)]) -> SessionOut:
    return SessionOut(user=user)
