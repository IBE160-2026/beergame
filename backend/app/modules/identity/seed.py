"""The local demo accounts (AD-17, Story 3.2).

With `APP_ENV=local` and an empty `users` table, the api adds one demo Admin and one demo
Lecturer at start. Nothing is seeded in any other environment. The sign-in details are in the
README; Playwright tests and visual checks log in with them (`frontend/e2e/support/auth.ts`).
They use the RFC 2606 domain `example.com`, which never receives mail.
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
)

SEED_LOCK = 0x3_02_1D
"""The advisory lock key that keeps processes starting together from seeding twice."""


async def ensure_demo_users() -> int:
    """Add the demo Users when `APP_ENV=local` and no User exists; returns how many were added."""
    if get_settings().app_env != "local":
        return 0
    async with get_sessionmaker().begin() as s:
        await s.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": SEED_LOCK})
        if await repo.any_user(s):
            return 0
        for demo in DEMO_USERS:
            await service.create_user(
                email=demo.email,
                name=demo.name,
                password=DEMO_PASSWORD,
                roles=demo.roles,
                session=s,
            )
    log.info("demo_users_seeded")
    return len(DEMO_USERS)


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
