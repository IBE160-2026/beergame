"""Story 13.1 (FR-17): an Individual test handed in automatically at the Test deadline counts
for Completion only with content in each required part; the Student's own hand-in counts as it
is. Built on Story 11.11's fixtures (`tests/individual_test/test_auto_submit.py`)."""

import uuid
from datetime import timedelta

import pytest

from app.modules.ops import sweep
from app.modules.reports import service as reports
from app.modules.tests import service as tests_service
from app.platform.config import get_settings
from tests.classes.test_classes import LECTURER
from tests.classes.test_roster_upload import clock, klass
from tests.classes.test_staff import call
from tests.individual_test.test_answer import first, opened, put
from tests.individual_test.test_open import no_playout
from tests.sessions.test_dates import TEST
from tests.sessions.test_lock import _empty

__all__ = ["_empty", "clock", "klass", "no_playout"]

pytestmark = pytest.mark.usefixtures("no_playout")


async def test_an_auto_submitted_test_with_an_empty_part_does_not_count(klass, monkeypatch):
    session_id, seated, test = await opened(klass)
    sid = uuid.UUID(session_id)
    me = seated[0]
    assert await tests_service.attempt_status(me, sid) == "open"
    choice = first(test, "choice")
    assert (await put(session_id, choice["id"], choice["options"][0], 1)).status_code == 200
    await sweep.run(TEST + timedelta(minutes=3))
    assert await tests_service.attempt_status(me, sid) == "auto_submitted"
    status = await reports.completion_status(me, sid)
    step = status.step("test_submitted")
    assert (step.recorded, step.done) == (True, False)

    # With content in every part the attempt holds, the same hand-in counts.
    original = tests_service.parts_with_content
    parts = await original(me, sid)
    full = dict.fromkeys(parts, True)

    async def all_answered(user_id, class_session_id):
        return full

    monkeypatch.setattr(tests_service, "parts_with_content", all_answered)
    assert (await reports.completion_status(me, sid)).step("test_submitted").done is True
    # Not required by configuration: an empty part is not checked.
    monkeypatch.setattr(tests_service, "parts_with_content", original)
    monkeypatch.setattr(get_settings(), "completion_test_required_parts", "choice")
    assert (await reports.completion_status(me, sid)).step("test_submitted").done is True


async def test_no_attempt_has_no_status(klass):
    session_id, seated, _ = await opened(klass, 2)
    assert await tests_service.attempt_status(seated[1], uuid.UUID(session_id)) is None


async def test_the_studentside_shows_the_attempt_and_its_parts_never_an_answer(klass):
    """Story 13.2 (FR-63): the record's Individual test part, read through `attempt_summary`."""
    session_id, seated, test = await opened(klass)
    me = seated[0]
    choice = first(test, "choice")
    assert (await put(session_id, choice["id"], choice["options"][0], 1)).status_code == 200
    path = f"/api/class-sessions/{session_id}/students/{me}/record"
    part = (await call(LECTURER, "GET", path)).json()["test"]
    assert (part["status"], part["submitted_at"]) == ("open", None)
    await sweep.run(TEST + timedelta(minutes=3))
    found = await call(LECTURER, "GET", path)
    part = found.json()["test"]
    assert part["status"] == "auto_submitted" and part["submitted_at"] is not None
    assert part["parts"]["choice"] is True and False in part["parts"].values()
    assert set(part) == {"status", "submitted_at", "parts"}
    assert all(isinstance(value, bool) for value in part["parts"].values())
