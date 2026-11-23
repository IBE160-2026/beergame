"""One timed sitting for the Individual test (Story 11.12, FR-51, FR-17, FR-66, AD-9).

A Class session's time limit in whole minutes is kept in `test_sittings` (a row: timed; none:
not). «Lagre Klasseøkt» stores it through `tests.service`, which registers `minutes_of` and
`write` with `sessions` (`sessions.register_test_sitting`), since `sessions` never imports `tests`:
`sessions.save_session` judges the range (configuration), refuses a change once the Class session
is locked, and calls `write` in its transaction. `copy_sitting`, registered there with
`sessions.register_copier`, carries it into a Class session made from this one.

The Student's own limit is the Class session's times their time factor, read through Story 8.9's
`sessions.get_adjustment` (`time_factor`)."""

import uuid
from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sessions import service as sessions
from app.modules.tests.models import test_sittings

__all__ = ["copy_sitting", "minutes_of", "time_factor", "write"]

ONE = Decimal(1)


async def minutes_of(s: AsyncSession, class_session_id: uuid.UUID) -> int | None:
    """The Class session's time limit in whole minutes, read in `s`; None when the test is not
    taken in one timed sitting."""
    return await s.scalar(
        select(test_sittings.c.minutes).where(test_sittings.c.class_session_id == class_session_id)
    )


async def write(
    s: AsyncSession,
    class_session_id: uuid.UUID,
    minutes: int | None,
    user_id: uuid.UUID,
    now: datetime,
) -> None:
    """Store the time limit (None: no timed sitting), in the caller's transaction. Judged by
    `sessions.save_session` before this runs."""
    if minutes is None:
        await s.execute(
            delete(test_sittings).where(test_sittings.c.class_session_id == class_session_id)
        )
        return
    values = {"minutes": minutes, "updated_by": user_id, "updated_at": now}
    await s.execute(
        insert(test_sittings)
        .values(class_session_id=class_session_id, **values)
        .on_conflict_do_update(index_elements=["class_session_id"], set_=values)
    )


async def copy_sitting(
    s: AsyncSession, source: Mapping[str, Any], target_id: uuid.UUID, now: datetime
) -> None:
    """`sessions.copy_from`'s copier (FR-66): the source's time limit, if it has one."""
    minutes = await minutes_of(s, source["id"])
    if minutes is not None:
        await s.execute(
            insert(test_sittings).values(
                class_session_id=target_id, minutes=minutes, updated_by=None, updated_at=now
            )
        )


async def time_factor(s: AsyncSession, class_session_id: uuid.UUID, user_id: uuid.UUID) -> Decimal:
    """The Student's time factor on a timed sitting (FR-17): the factor of their Tilrettelegging
    from `sessions.get_adjustment` (Story 8.9) where one above 1 is recorded, else 1."""
    found = await sessions.get_adjustment(s, class_session_id, user_id)
    if found is None:
        return ONE
    factor = Decimal(str(found.time_factor))
    return factor if factor > ONE else ONE
