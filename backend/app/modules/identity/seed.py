"""The local demo accounts (AD-17, Story 3.2).

With `APP_ENV=local`, the api adds at start each demo User whose e-mail is not taken yet: an
Admin, a Lecturer, a User with both roles, and a User with no account role (who lands on Hjem,
Story 3.3). Existing Users are never changed. Nothing is seeded in any other environment. The
sign-in details are in the README; Playwright tests and visual checks log in with them
(`frontend/e2e/support/auth.ts`). They use the RFC 2606 domain `example.com`, which never
receives mail.
"""

from dataclasses import dataclass

import structlog
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.modules.identity import repo, service
from app.modules.identity.schemas import AccountRole
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker

log = structlog.get_logger(__name__)

DEMO_PASSWORD = "olspillet-demo"


@dataclass(frozen=True)
class DemoUser:
    email: str
    name: str
    roles: tuple[AccountRole, ...]


DEMO_USERS = (
    DemoUser("admin@example.com", "Demo Admin", (AccountRole.admin,)),
    DemoUser("faglaerer@example.com", "Demo Faglærer", (AccountRole.lecturer,)),
    DemoUser(
        "admin-faglaerer@example.com",
        "Demo Admin og Faglærer",
        (AccountRole.admin, AccountRole.lecturer),
    ),
    DemoUser("student@example.com", "Demo Student", ()),
)

SEED_LOCK = 0x3_02_1D
"""The advisory lock key that keeps processes starting together from seeding twice."""


async def ensure_demo_users() -> int:
    """Add the missing demo Users when `APP_ENV=local`; returns how many were added."""
    if get_settings().app_env != "local":
        return 0
    added = 0
    async with get_sessionmaker().begin() as s:
        await s.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": SEED_LOCK})
        for demo in DEMO_USERS:
            if await repo.user_by_email(s, demo.email) is not None:
                continue
            await service.create_user(
                email=demo.email,
                name=demo.name,
                password=DEMO_PASSWORD,
                roles=demo.roles,
                session=s,
            )
            added += 1
    if added:
        log.info("demo_users_seeded")
    return added


async def ensure_demo_users_logged() -> None:
    """For process start: a database error is logged, never raised."""
    try:
        await ensure_demo_users()
    except DBAPIError as exc:
        log.warning(
            "demo_users_failed",
            error_code="db_error",
            exc_type=type(getattr(exc, "orig", exc)).__name__,
        )
