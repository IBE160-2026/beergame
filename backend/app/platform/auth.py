"""Passwords, the session cookie and the CSRF guard (AD-11, Story 3.2).

- A password is SHA-256 hashed and base64-encoded before bcrypt, because bcrypt 5 rejects input
  over 72 bytes. The cost is `BCRYPT_ROUNDS`.
- The session is an HS256 JWT in an `httpOnly; Secure; SameSite=Lax` cookie. Its claims are
  `user_id`, `iat` and `exp`: no name, e-mail or role. Who the User is and which roles they hold
  is loaded from the database on every request (`authz.current_principal`, which calls the
  loader `identity` registers).
- Every mutating `/api` request must carry `X-Requested-With: olspillet`; only `/api/webhooks/*`
  is exempt (it verifies the sender's signature instead).

This module imports no `app.modules` code: loading the User is the `identity` module's job.
"""

import base64
import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

from app.platform.config import get_settings

COOKIE_NAME = "olspillet_session"
ALGORITHM = "HS256"
CSRF_HEADER = "x-requested-with"
CSRF_VALUE = "olspillet"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
CSRF_EXEMPT_PREFIX = "/api/webhooks/"


def _prehash(password: str) -> bytes:
    return base64.b64encode(hashlib.sha256(password.encode("utf-8")).digest())


def hash_password(password: str) -> str:
    rounds = get_settings().bcrypt_rounds
    return bcrypt.hashpw(_prehash(password), bcrypt.gensalt(rounds=rounds)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_prehash(password), password_hash.encode("ascii"))
    except ValueError:  # a malformed stored hash never verifies
        return False


_dummy_hash: dict[int, str] = {}


def dummy_hash() -> str:
    """A hash to check against when no User has the e-mail, so an unknown e-mail costs the same
    bcrypt work as a wrong password and the timing reveals nothing."""
    rounds = get_settings().bcrypt_rounds
    if rounds not in _dummy_hash:
        _dummy_hash[rounds] = hash_password(uuid.uuid4().hex)
    return _dummy_hash[rounds]


def utcnow() -> datetime:
    return datetime.now(UTC)


def link_token(purpose: str, record_id: uuid.UUID) -> str:
    """The secret token of a mailed link (password reset, Story 3.6): HMAC-SHA256 of the record's
    id under a key derived from `JWT_SECRET` (so the session key itself signs nothing else),
    base64url without padding. The owner stores only `token_hash`, and the mail job rebuilds the
    link at send time, so the token is never in a row, job or log line."""
    secret = get_settings().jwt_secret.encode("utf-8")
    key = hmac.new(secret, b"olspillet link tokens", hashlib.sha256).digest()
    message = f"{purpose}:{record_id}".encode()
    digest = hmac.new(key, message, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def token_hash(token: str) -> str:
    """What the owner stores and looks a link token up by: SHA-256 hex of the token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_token(user_id: uuid.UUID, now: datetime | None = None) -> str:
    now = now or utcnow()
    max_age = timedelta(hours=get_settings().session_max_age_hours)
    claims = {"user_id": str(user_id), "iat": now, "exp": now + max_age}
    return jwt.encode(claims, get_settings().jwt_secret, algorithm=ALGORITHM)


def read_token(token: str | None, now: datetime | None = None) -> uuid.UUID | None:
    """The token's `user_id`, or None when it is missing, tampered, signed with another secret,
    expired or malformed."""
    if not token:
        return None
    now = now or utcnow()
    try:
        claims = jwt.decode(
            token,
            get_settings().jwt_secret,
            algorithms=[ALGORITHM],
            # Expiry is checked below against the caller's clock, so tests control it.
            options={
                "require": ["user_id", "exp", "iat"],
                "verify_exp": False,
                "verify_iat": False,
            },
        )
        if datetime.fromtimestamp(claims["exp"], UTC) <= now:
            return None
        user_id = claims["user_id"]
        return uuid.UUID(user_id) if isinstance(user_id, str) else None
    # A validly signed token can still hold an absurd `exp` or a non-string `user_id`.
    except jwt.InvalidTokenError, ValueError, TypeError, KeyError, OverflowError, OSError:
        return None


def set_session_cookie(response: Response, user_id: uuid.UUID, now: datetime | None = None) -> None:
    response.set_cookie(
        COOKIE_NAME,
        issue_token(user_id, now),
        max_age=get_settings().session_max_age_hours * 3600,
        path="/",
        httponly=True,
        secure=True,
        samesite="lax",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, secure=True, samesite="lax")


class CsrfMiddleware:
    """Rejects a mutating `/api` request that lacks `X-Requested-With: olspillet` with 403
    `csrf_header_missing`, before any handler runs."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and self._refused(scope):
            body = {
                "error": {
                    "code": "csrf_header_missing",
                    "message": "Mutating requests must carry X-Requested-With: olspillet.",
                    "fields": {},
                }
            }
            response = Response(json.dumps(body), status_code=403, media_type="application/json")
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)

    @staticmethod
    def _refused(scope: Scope) -> bool:
        path: str = scope.get("path", "")
        if scope.get("method", "GET") in SAFE_METHODS:
            return False
        if not (path == "/api" or path.startswith("/api/")):
            return False
        if path.startswith(CSRF_EXEMPT_PREFIX):
            return False
        for name, value in scope.get("headers", []):
            if name.decode("latin-1").lower() == CSRF_HEADER:
                return value.decode("latin-1") != CSRF_VALUE
        return True
