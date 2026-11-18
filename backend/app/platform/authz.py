"""Authorization: who may do what (AD-12, FR-5, NFR-7, Story 3.3).

Every API route declares a policy as a FastAPI dependency: `Depends(authz.require(action))`, or
`Depends(authz.public)` for the short public list (login, logout, password reset, Invitation
acceptance, the lecturer-access request, health, webhooks). `tests/test_authz_rules.py` walks the
routes and fails on a route without a policy, and on a role comparison inside `app/modules/`:
modules ask `can(user, action, resource)`, they never compare roles themselves.

- `current_principal` reads the session cookie and loads the User and their roles from the
  database on every request, through the loader `identity` registers at app start
  (`register_principal_loader`). A role granted or revoked takes effect at the next request; a
  deactivated or deleted User is `NotAuthenticated`.
- A policy runs before the route handler, so a refusal is the same 403 `forbidden` whether or not
  the item exists: the answer never reveals what is there.
- The account roles are `admin` and `lecturer`. A Student or an Assistent is not an account role:
  Class membership makes them (Epic 4). Class-scoped helpers such as `classes_visible_to(user)`
  and the Class-scoped actions (a Student's own answers, an Assistent's Classes) are added here by
  the epic that creates the tables they join; until then no account role reads Student answers or
  AI assessments, the Admin role included.

This module imports no `app.modules` code.
"""

import uuid
from collections.abc import Awaitable, Callable, Collection
from typing import Any, Protocol

from fastapi import Request

from app.platform import auth

ADMIN = "admin"
LECTURER = "lecturer"


class Principal(Protocol):
    """The logged-in User as `authz` sees it: an id and the account roles."""

    id: uuid.UUID
    roles: Collection[str]


class NotAuthenticated(Exception):
    """No valid session: no cookie, a bad token, or a User who is gone or deactivated."""


class Forbidden(Exception):
    """The User's roles do not allow the action (403 `forbidden`)."""


ANY_USER = "any_user"
"""A policy marker: every logged-in User, whatever roles they hold."""

POLICIES: dict[str, frozenset[str]] = {
    # The Admin-område (FR-1–FR-3, FR-69).
    "admin_area.view": frozenset({ADMIN}),
    "users.list": frozenset({ADMIN}),
    "users.manage": frozenset({ADMIN}),
    "institutions.manage": frozenset({ADMIN}),
    "audit.read": frozenset({ADMIN}),
    # The Lærerhjem; Class-scoped actions come with Epic 4.
    "lecturer_home.view": frozenset({LECTURER}),
    # The own session.
    "session.read": frozenset({ANY_USER}),
    # FR-5: no account role grants these. Epic 4+ adds the Class-scoped grants.
    "student_answers.read": frozenset(),
    "ai_assessments.read": frozenset(),
}
"""Action → the account roles that may do it. Closed: an unknown action is a KeyError."""


def can(user: Principal, action: str, resource: Any = None) -> bool:
    """Whether `user` may do `action` (on `resource`, for the Class-scoped checks to come)."""
    allowed = POLICIES[action]
    return ANY_USER in allowed or not allowed.isdisjoint(user.roles)


PrincipalLoader = Callable[[uuid.UUID], Awaitable[Principal | None]]
_loader: PrincipalLoader | None = None


def register_principal_loader(loader: PrincipalLoader) -> None:
    """Called once by `create_app()` with `identity.service.load_user`."""
    global _loader
    _loader = loader


async def current_principal(request: Request) -> Principal:
    """FastAPI dependency: the active User of the session cookie, read from the database."""
    if _loader is None:  # pragma: no cover - create_app() always registers it
        raise RuntimeError("no principal loader registered")
    user_id = auth.read_token(request.cookies.get(auth.COOKIE_NAME))
    user = await _loader(user_id) if user_id else None
    if user is None:
        raise NotAuthenticated
    return user


class Policy:
    """`require(action)`: a dependency that returns the principal, or raises `Forbidden`."""

    def __init__(self, action: str) -> None:
        POLICIES[action]  # a typo fails at import, not at the first request
        self.action = action

    async def __call__(self, request: Request) -> Principal:
        user = await current_principal(request)
        if not can(user, self.action):
            raise Forbidden
        return user

    def __repr__(self) -> str:
        return f"require({self.action!r})"


def require(action: str) -> Policy:
    return Policy(action)


async def public() -> None:
    """The policy of a public route. Only the routes on the public list may use it."""
