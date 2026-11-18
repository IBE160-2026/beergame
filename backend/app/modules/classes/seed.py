"""The local demo Class (AD-17, Story 4.1).

With `APP_ENV=local`, the api adds at start one Class, «class-of-1994» with the course code
«IBE160» at «Demohøgskolen», owned by the demo Lecturer, when that User exists and is staff of no
Class yet. Nothing else is changed, and nothing is seeded in any other environment. Its eight
registered demo Students come with Story 4.5, the first story in which a Student can be in a Class.
"""

import uuid

import structlog
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.modules.classes import repo
from app.modules.identity import service as identity
from app.platform import auth
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker

log = structlog.get_logger(__name__)

DEMO_LECTURER = "faglaerer@example.com"
"""The demo Lecturer of `identity/seed.py` (`DEMO_USERS`)."""
DEMO_CLASS = "class-of-1994"
DEMO_COURSE_CODE = "IBE160"

SEED_LOCK = 0x4_01_C1
"""The advisory lock key that keeps processes starting together from seeding twice."""


async def ensure_demo_class() -> bool:
    """Add the demo Class when `APP_ENV=local` and the demo Lecturer has none; True when added."""
    if get_settings().app_env != "local":
        return False
    now = auth.utcnow()
    async with get_sessionmaker().begin() as s:
        await s.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": SEED_LOCK})
        lecturer = await identity.user_id_for_email(s, DEMO_LECTURER)
        if lecturer is None or await repo.any_class_of(s, lecturer):
            return False
        institution = await identity.ensure_demo_institution(s, now)
        await repo.insert_class(
            s,
            class_id=uuid.uuid7(),
            name=DEMO_CLASS,
            course_code=DEMO_COURSE_CODE,
            institution_id=institution,
            owner=lecturer,
            now=now,
        )
    log.info("demo_class_seeded")
    return True


async def ensure_demo_class_logged() -> None:
    """For process start: a database error is logged, never raised."""
    try:
        await ensure_demo_class()
    except DBAPIError as exc:
        log.warning(
            "demo_class_failed",
            error_code="db_error",
            exc_type=type(getattr(exc, "orig", exc)).__name__,
        )
