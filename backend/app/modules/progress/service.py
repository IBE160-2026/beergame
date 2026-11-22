"""Record and read the steps a Student has done (Story 6.1, AD-16).

A module records a step only through `record_step` and reads a gate only through `has_step` (or
`steps_of` for many sessions at once). `record_step` is idempotent on `(user, class_session,
step)`: the first call stores the row and emits `user:<id>` and `session:<id>`; a repeat stores
and emits nothing. This module imports no feature module, so any module may call it."""

import uuid
from collections.abc import AsyncIterator, Collection, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Text, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.progress.models import Step, progress_steps
from app.platform import events
from app.platform.db import get_sessionmaker

__all__ = [
    "FUNNEL_STEPS",
    "Funnel",
    "Step",
    "funnel",
    "has_step",
    "record_step",
    "steps_of",
    "users_with_step",
]


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
    # The Trakt counts this step from now on (Story 7.6); a read before the caller's commit is
    # counted again by the stamp.
    _funnels.pop(class_session_id, None)
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


FUNNEL_STEPS: tuple[Step, ...] = (
    Step.CLASS_GAME,
    Step.DEBRIEF,
    Step.QUIZ_PASSED,
    Step.REPLAY,
    Step.TEST_SUBMITTED,
    Step.ASSESSMENT_READY,
)
"""The Trakt's stages after «Registrert», in order (FR-39). A step nobody records yet counts 0."""


@dataclass(frozen=True)
class Funnel:
    """How many of the given Students there are, and how many of them have each step of
    `FUNNEL_STEPS` recorded in the Class session."""

    registered: int
    steps: tuple[tuple[Step, int], ...]


_funnels: dict[uuid.UUID, tuple[frozenset[uuid.UUID], tuple[int, str | None], Funnel]] = {}
"""The funnel per Class session in this process, with the Students it counted and the stamp of
the session's steps it was counted at (Story 7.6, AD-25)."""


async def funnel(
    session: AsyncSession, class_session_id: uuid.UUID, student_ids: Collection[uuid.UUID]
) -> Funnel:
    """The Trakt of the Class session over `student_ids` (the caller's Students, AD-16): their
    number, and per stage how many of them have that step recorded. Reads step events only, never
    an AI score or text (C-2). Cached per Class session; the cache holds while the Students and the
    session's steps are the same: `record_step` drops it here, and the stamp (number of step rows
    and the newest id) shows a step another process recorded. In the caller's `session`."""
    students = frozenset(student_ids)
    stamp_row = (
        await session.execute(
            select(func.count(), func.max(progress_steps.c.id.cast(Text))).where(
                progress_steps.c.class_session_id == class_session_id
            )
        )
    ).one()
    stamp = (int(stamp_row[0]), stamp_row[1])
    cached = _funnels.get(class_session_id)
    if cached is not None and cached[0] == students and cached[1] == stamp:
        return cached[2]
    counts: dict[str, int] = {}
    if students:
        result = await session.execute(
            select(progress_steps.c.step, func.count(func.distinct(progress_steps.c.user_id)))
            .where(
                progress_steps.c.class_session_id == class_session_id,
                progress_steps.c.user_id.in_(list(students)),
                progress_steps.c.step.in_([step.value for step in FUNNEL_STEPS]),
            )
            .group_by(progress_steps.c.step)
        )
        counts = {step: count for step, count in result.all()}
    found = Funnel(
        registered=len(students),
        steps=tuple((step, counts.get(step.value, 0)) for step in FUNNEL_STEPS),
    )
    _funnels[class_session_id] = (students, stamp, found)
    return found
