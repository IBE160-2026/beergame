"""The local demo Class and its Students (AD-17, Stories 4.1 and 4.5).

With `APP_ENV=local`, the api adds at start one Class, «class-of-1994» with the course code
«IBE160» at «Demohøgskolen», owned by the demo Lecturer, when that User exists and is staff of no
Class yet. Then, on every start, the demo Class (the Class of that name the demo Lecturer owns)
gets its eight registered demo Students: the demo Student of `identity/seed.py` and seven more,
each a User with the demo password and a Roster entry linked to it, and the demo Assistant
(`assistent@example.com`, Story 4.9) is its Assistant lecturer. A User, an address or a staff row
already there is left as it is. Nothing is seeded in any other environment.
"""

import uuid

import structlog
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.modules.classes import repo
from app.modules.classes.schemas import StaffRole
from app.modules.identity import service as identity
from app.platform import auth
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker

log = structlog.get_logger(__name__)

DEMO_LECTURER = "faglaerer@example.com"
"""The demo Lecturer of `identity/seed.py` (`DEMO_USERS`)."""
DEMO_ASSISTANT = "assistent@example.com"
"""The demo Assistant lecturer of `identity/seed.py` (Story 4.9)."""
DEMO_CLASS = "class-of-1994"
DEMO_COURSE_CODE = "IBE160"
DEMO_PASSWORD = "olspillet-demo"
"""The password of every demo User (`identity/seed.py`)."""
DEMO_STUDENTS: tuple[tuple[str, str], ...] = (
    ("student@example.com", "Demo Student"),
    *((f"student{n}@example.com", f"Demo Student {n}") for n in range(2, 9)),
)
"""The eight registered Students of the demo Class (Story 4.5): address and name."""

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


async def ensure_demo_students() -> int:
    """Give the demo Class its registered demo Students when `APP_ENV=local`; returns how many
    Roster entries were added (0 when there is no demo Class)."""
    if get_settings().app_env != "local":
        return 0
    now = auth.utcnow()
    added = 0
    async with get_sessionmaker().begin() as s:
        await s.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": SEED_LOCK})
        lecturer = await identity.user_id_for_email(s, DEMO_LECTURER)
        class_id = await repo.demo_class_of(s, lecturer, DEMO_CLASS) if lecturer else None
        if class_id is None:
            return 0
        for email, name in DEMO_STUDENTS:
            if await identity.seed_registered_student(s, class_id, email, name, DEMO_PASSWORD, now):
                added += 1
        assistant = await identity.user_id_for_email(s, DEMO_ASSISTANT)
        if assistant is not None and await repo.put_staff(
            s, class_id, assistant, StaffRole.assistant, now, replace=False
        ):
            log.info("demo_assistant_seeded", class_id=str(class_id))
    if added:
        log.info("demo_students_seeded", class_id=str(class_id), count=added)
    return added


async def ensure_demo_class_logged() -> None:
    """For process start: a database error is logged, never raised."""
    try:
        await ensure_demo_class()
        await ensure_demo_students()
    except DBAPIError as exc:
        log.warning(
            "demo_class_failed",
            error_code="db_error",
            exc_type=type(getattr(exc, "orig", exc)).__name__,
        )
