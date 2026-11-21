"""Record and read the steps a Student has done (Story 6.1, AD-16).

A module records a step only through `record_step` and reads a gate only through `has_step` (or
`steps_of` for many sessions at once). `record_step` is idempotent on `(user, class_session,
step)`: the first call stores the row and emits `user:<id>` and `session:<id>`; a repeat stores
and emits nothing. This module imports no feature module, so any module may call it."""

import uuid
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.progress.models import Step, progress_steps
from app.platform import events
from app.platform.db import get_sessionmaker

__all__ = ["Step", "has_step", "record_step", "steps_of", "users_with_step"]


@asynccontextmanager
async def _transaction(within: AsyncSession | None) -> AsyncIterator[AsyncSession]:
    if within is not None:
        yield within
        return
    async with get_sessionmaker().begin() as session:
        yield session


async def record_step(
    user_id: uuid.UUID,
    class_session_id: uuid.UUID,
    step: Step | str,
    at: datetime,
    *,
    within: AsyncSession | None = None,
) -> bool:
    """Record that the User did `step` in the Class session at `at`. True when this call stored
    it; False when it was already recorded (the first `at` is kept). `within` is the caller's
    transaction, which then commits the row and its events together."""
    step = Step(step)
    async with _transaction(within) as session:
        result = await session.execute(
            insert(progress_steps)
            .values(
                id=uuid.uuid7(),
                user_id=user_id,
                class_session_id=class_session_id,
                step=step.value,
                at=at,
            )
            .on_conflict_do_nothing(constraint="uq_progress_steps_step")
            .returning(progress_steps.c.id)
        )
        if result.first() is None:
            return False
        await events.emit(session, "user", str(user_id))
        await events.emit(session, "session", str(class_session_id))
    return True


async def has_step(user_id: uuid.UUID, class_session_id: uuid.UUID, step: Step | str) -> bool:
    """Whether the User has done `step` in the Class session."""
    async with get_sessionmaker()() as session:
        found = await steps_of(session, user_id, [class_session_id])
    return Step(step) in found.get(class_session_id, set())


async def users_with_step(
    session: AsyncSession, class_session_id: uuid.UUID, step: Step | str
) -> list[uuid.UUID]:
    """The Users who have done `step` in the Class session, by id, read in the caller's session
    (Story 9.2: every Student whose Class game finished, for the Debrief release)."""
    result = await session.scalars(
        select(progress_steps.c.user_id)
        .where(
            progress_steps.c.class_session_id == class_session_id,
            progress_steps.c.step == Step(step).value,
        )
        .order_by(progress_steps.c.user_id)
    )
    return list(result)


async def steps_of(
    session: AsyncSession, user_id: uuid.UUID, class_session_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, set[Step]]:
    """The steps the User has done in each of these Class sessions, in one read in the caller's
    session; a session with none is left out."""
    if not class_session_ids:
        return {}
    result = await session.execute(
        select(progress_steps.c.class_session_id, progress_steps.c.step).where(
            progress_steps.c.user_id == user_id,
            progress_steps.c.class_session_id.in_(list(class_session_ids)),
        )
    )
    found: dict[uuid.UUID, set[Step]] = {}
    for session_id, step in result.all():
        found.setdefault(session_id, set()).add(Step(step))
    return found
