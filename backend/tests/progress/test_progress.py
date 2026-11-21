"""The steps a Student has done (Story 6.1, AD-16): `record_step` is idempotent on
`(user, class_session, step)` and emits `user:<id>` and `session:<id>` only when it stores the
row; `has_step` and `steps_of` read them."""

import uuid

import pytest

from app.modules.progress import service as progress
from app.platform.db import get_sessionmaker
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_student_registration import emitted
from tests.sessions.test_dates import student_of
from tests.sessions.test_lock import _empty, dated

__all__ = ["_empty", "clock", "emitted", "klass"]


async def test_a_step_is_recorded_once_and_announced_once(klass, emitted):
    user_id = await student_of(klass, "p@x.no")
    session_id = uuid.UUID(await dated(klass))
    emitted.clear()
    assert await progress.record_step(user_id, session_id, "class_game", NOW) is True
    assert sorted(emitted) == sorted([("user", str(user_id)), ("session", str(session_id))])
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["progress.record_step"]
    emitted.clear()
    assert await progress.record_step(user_id, session_id, progress.Step.CLASS_GAME, NOW) is False
    assert emitted == []
    assert await progress.has_step(user_id, session_id, "class_game") is True
    assert await progress.has_step(user_id, session_id, "debrief") is False
    async with get_sessionmaker()() as s:
        found = await progress.steps_of(s, user_id, [session_id])
    assert found == {session_id: {progress.Step.CLASS_GAME}}


async def test_a_step_outside_the_catalogue_is_refused(klass):
    user_id = await student_of(klass, "p@x.no")
    session_id = uuid.UUID(await dated(klass))
    with pytest.raises(ValueError):
        await progress.record_step(user_id, session_id, "bullwhip", NOW)


async def test_the_funnel_counts_the_given_students_steps_and_sees_every_new_one(klass):
    """Story 7.6: registered is the number of ids given; each stage counts those of them with the
    step; another Student's step is left out; a step recorded here drops the cached funnel, and
    one written past `record_step` (as another process would) is seen by the stamp."""
    first = await student_of(klass, "f1@x.no")
    second = await student_of(klass, "f2@x.no")
    outside = await student_of(klass, "f3@x.no")
    session_id = uuid.UUID(await dated(klass))

    async def read(ids):
        async with get_sessionmaker()() as s:
            found = await progress.funnel(s, session_id, ids)
        return found.registered, dict(found.steps)

    assert await read([first, second]) == (2, dict.fromkeys(progress.FUNNEL_STEPS, 0))
    await progress.record_step(first, session_id, "class_game", NOW)
    await progress.record_step(outside, session_id, "class_game", NOW)
    await progress.record_step(first, session_id, "starting_task", NOW)  # not a Trakt stage
    registered, steps = await read([first, second])
    assert (registered, steps[progress.Step.CLASS_GAME], steps[progress.Step.DEBRIEF]) == (2, 1, 0)

    # Written past `record_step`, so nothing here drops the cache: the stamp shows it.
    async with get_sessionmaker().begin() as s:
        await s.execute(
            progress.progress_steps.insert().values(
                id=uuid.uuid7(),
                user_id=second,
                class_session_id=session_id,
                step="debrief",
                at=NOW,
            )
        )
    _, steps = await read([first, second])
    assert steps[progress.Step.DEBRIEF] == 1
    # Other Students given: counted again for them.
    assert (await read([outside]))[1][progress.Step.CLASS_GAME] == 1
    assert (await read([]))[0] == 0
