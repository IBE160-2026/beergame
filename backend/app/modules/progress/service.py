"""Record and read the steps a Student has done (Story 6.1, AD-16).

A module records a step only through `record_step` and reads a gate only through `has_step` (or
`steps_of` for many sessions at once). `record_step` is idempotent on `(user, class_session,
step)`: the first call stores the row and emits `user:<id>` and `session:<id>`; a repeat stores
and emits nothing. This module imports no feature module, so any module may call it.

A Lecturer's correction of a Completion step (Story 13.3) is stored through `record_correction`
and read through `corrections`. It is no step event: it never touches `progress_steps`, so gates
(`has_step`) and the funnel stay as they are (AD-16)."""

import uuid
from collections.abc import AsyncIterator, Collection, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Text, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.progress.models import (
    CORRECTABLE_STEPS,
    Step,
    completion_corrections,
    progress_steps,
)
from app.platform import events
from app.platform.db import get_sessionmaker

__all__ = [
    "own_records",
    "CORRECTABLE_STEPS",
    "FUNNEL_STEPS",
    "CompletionCorrection",
    "Funnel",
    "Step",
    "corrections",
    "funnel",
    "has_step",
    "record_correction",
    "record_step",
    "step_events",
    "steps_of",
    "steps_since",
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


async def steps_since(
    session: AsyncSession, step: Step | str, since: datetime
) -> list[tuple[uuid.UUID, uuid.UUID]]:
    """`(user_id, class_session_id)` of every `step` done at or after `since`, oldest first, read
    in the caller's session (Story 11.8: the Students whose Adapted items the sweep prepares)."""
    result = await session.execute(
        select(progress_steps.c.user_id, progress_steps.c.class_session_id)
        .where(progress_steps.c.step == Step(step).value, progress_steps.c.at >= since)
        .order_by(progress_steps.c.at, progress_steps.c.id)
    )
    return [(user_id, session_id) for user_id, session_id in result.all()]


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


async def step_events(
    session: AsyncSession, user_id: uuid.UUID, class_session_id: uuid.UUID
) -> dict[Step, datetime]:
    """The steps the User has done in the Class session with when each was done, in the caller's
    session (Story 13.1: the step events Completion reads)."""
    result = await session.execute(
        select(progress_steps.c.step, progress_steps.c.at).where(
            progress_steps.c.user_id == user_id,
            progress_steps.c.class_session_id == class_session_id,
        )
    )
    return {Step(step): at for step, at in result.all()}


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


@dataclass(frozen=True)
class CompletionCorrection:
    """One stored correction of a Completion step (Story 13.3): the step, the new status, the
    reason, who made it (None once that User is gone) and when."""

    id: uuid.UUID
    step: str
    done: bool
    reason: str
    actor_user_id: uuid.UUID | None
    at: datetime


async def record_correction(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    class_session_id: uuid.UUID,
    step: str,
    done: bool,
    reason: str,
    actor_user_id: uuid.UUID,
    at: datetime,
) -> uuid.UUID:
    """Store a correction of `step` in the caller's transaction and return its id. Always a new
    row: an earlier correction of the step stays, and the latest applies (AD-15). Records no step
    event and emits nothing; the caller audits and emits."""
    if step not in CORRECTABLE_STEPS:
        raise ValueError(f"not a step of the requirement: {step}")
    correction_id = uuid.uuid7()
    await session.execute(
        completion_corrections.insert().values(
            id=correction_id,
            user_id=user_id,
            class_session_id=class_session_id,
            step=step,
            done=done,
            reason=reason,
            actor_user_id=actor_user_id,
            at=at,
        )
    )
    return correction_id


async def delete_corrections_of(session: AsyncSession, user_id: uuid.UUID) -> None:
    """The erasure of a Student (Story 15.2, AD-14): delete every correction of their Completion
    status, whose reason is a Lecturer's free text about them. The append-only trigger refuses
    an UPDATE only; a Lecturer's corrections of other Students stay. Idempotent."""
    await session.execute(
        completion_corrections.delete().where(completion_corrections.c.user_id == user_id)
    )


async def corrections(
    session: AsyncSession, user_id: uuid.UUID, class_session_id: uuid.UUID
) -> list[CompletionCorrection]:
    """Every correction of the User's steps in the Class session, oldest first by (`at`, `id`),
    so the last one of a step is the one that applies. In the caller's session."""
    c = completion_corrections.c
    result = await session.execute(
        select(c.id, c.step, c.done, c.reason, c.actor_user_id, c.at)
        .where(c.user_id == user_id, c.class_session_id == class_session_id)
        .order_by(c.at, c.id)
    )
    return [CompletionCorrection(**row) for row in result.mappings()]


# «Mine data» (Story 15.1, FR-75): the Student's own rows of this module, by their own id.
from app.modules.progress.own_data import own_records  # noqa: E402
