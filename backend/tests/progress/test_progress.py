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
