"""The «KI-vurdering» switch of a Class session (Story 12.1, FR-61, FR-66, AD-8, AD-9, AD-12): on
by default, stored through `assessment.service` by «Lagre Klasseøkt» also after the Start date,
pinned once by the Test-deadline lock (`sessions.lock_test`, the sweep's due action), refused with
409 `ai_assessment_pinned` once the original Test deadline has passed, read only by Assistant
lecturers, copied by «Lag kopi», and the gate `assessment.assessment_due` Story 12.2 asks. The
api's clock is fixed and moved by hand; the database clock is never read."""

from datetime import timedelta

import psycopg
import pytest

from app.modules.assessment import service as assessment
from app.modules.ops import sweep
from app.modules.sessions import service
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_staff import EMAIL, call, shared
from tests.classes.test_student_registration import emitted
from tests.messaging.helpers import rows
from tests.sessions.test_dates import PLAN, START, TEST, at, iso, new_session, refusal
from tests.sessions.test_rerun import copy, flag

__all__ = ["clock", "emitted", "klass", "shared"]

MINUTE = timedelta(minutes=1)
OPEN = {"enabled": True, "pinned_at": None, "open": True, "can_change": True}


@pytest.fixture(autouse=True)
def _empty_ai(ai_db):
    """No model config: the sessions are Rule-based, which the switch does not care about."""


async def save(session_id: str, email: str = EMAIL["owner"], **body):
    return await call(
        email, "PUT", f"/api/class-sessions/{session_id}", json={"ai_mode": "rule_based", **body}
    )


async def read(session_id: str, email: str = EMAIL["owner"]) -> dict:
    response = await call(email, "GET", f"/api/class-sessions/{session_id}")
    assert response.status_code == 200
    return response.json()["ai_assessment"]


def stored(session_id: str) -> list[tuple]:
    return rows(
        "SELECT enabled, pinned_at FROM assessment_switches WHERE class_session_id = %s", session_id
    )


async def planned(class_id: str) -> str:
    session_id = await new_session(class_id)
    assert (await save(session_id, dates=iso(PLAN))).status_code == 200
    return session_id


async def test_a_new_class_session_has_the_switch_on_and_nothing_stored(klass):
    session_id = await new_session(klass)
    assert await read(session_id) == OPEN
    assert stored(session_id) == []


async def test_the_owner_switches_it_off_and_on_and_the_staff_are_told(klass, emitted):
    session_id = await planned(klass)
    emitted.clear()
    response = await save(session_id, ai_assessment=False)
    assert response.status_code == 200
    assert response.json()["ai_assessment"] == {**OPEN, "enabled": False}
    assert stored(session_id) == [(False, None)]
    assert emitted == [("session", session_id)]
    assert {topic for topic, _ in emitted} <= COMMAND_TOPICS["sessions.save"]
    # Left out, it is kept; sent again unchanged, nothing changes.
    assert (await save(session_id)).json()["ai_assessment"]["enabled"] is False
    assert (await save(session_id, ai_assessment=False)).status_code == 200
    assert (await save(session_id, ai_assessment=True)).json()["ai_assessment"] == OPEN
    assert stored(session_id) == [(True, None)]


async def test_it_still_changes_after_the_start_date_until_the_test_deadline(klass, monkeypatch):
    session_id = await planned(klass)
    at(monkeypatch, START + MINUTE)
    response = await save(session_id, ai_assessment=False)
    assert response.status_code == 200
    assert response.json()["locked"] is True
    assert response.json()["ai_assessment"]["enabled"] is False
    # A setting frozen at the Start date is still refused in the same save.
    refused = await save(session_id, ai_assessment=True, debrief_ai_text=False)
    assert refusal(refused) == (409, "session_locked", {"debrief_ai_text": "locked"})
    assert stored(session_id) == [(False, None)]


async def test_once_the_test_deadline_has_passed_a_change_is_refused_before_the_sweep(
    klass, monkeypatch
):
    session_id = await planned(klass)
    at(monkeypatch, TEST)
    refused = await save(session_id, ai_assessment=False)
    assert refusal(refused) == (409, "ai_assessment_pinned", {"ai_assessment": "pinned"})
    assert stored(session_id) == []
    assert await read(session_id) == {**OPEN, "open": False, "can_change": False}
    # Unchanged, the save goes through.
    assert (await save(session_id, ai_assessment=True)).status_code == 200


async def test_the_test_deadline_lock_pins_the_switch_once_and_the_api_refuses_a_change(
    klass, monkeypatch, emitted
):
    session_id = await planned(klass)
    untouched = await new_session(klass)  # no Test deadline: never due
    assert (await save(session_id, ai_assessment=False)).status_code == 200
    assert str(session_id) not in map(str, await service.due_test_locks(TEST - MINUTE))
    due = [str(found) for found in await service.due_test_locks(TEST)]
    assert due == [session_id] and untouched not in due
    emitted.clear()
    # The sweep runs late: the switch is pinned as of the Test deadline, the lock when it ran.
    late = TEST + 5 * MINUTE
    (item,) = await service.due_test_locks(late)
    assert await service.lock_test_due(item, late) is True
    assert emitted == [("session", session_id)]
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["sessions.lock_test"]
    assert stored(session_id) == [(False, TEST)]
    assert rows("SELECT test_locked_at FROM class_sessions WHERE id = %s", session_id) == [(late,)]
    # Once and idempotently: a second run changes and emits nothing, and nothing is due any more.
    emitted.clear()
    assert await service.lock_test(item, now=TEST + MINUTE) is False
    assert emitted == [] and stored(session_id) == [(False, TEST)]
    assert await service.due_test_locks(TEST + MINUTE) == []
    at(monkeypatch, TEST + MINUTE)
    assert await read(session_id) == {
        "enabled": False,
        "pinned_at": TEST.isoformat().replace("+00:00", "Z"),
        "open": False,
        "can_change": False,
    }
    refused = await save(session_id, ai_assessment=True)
    assert refusal(refused) == (409, "ai_assessment_pinned", {"ai_assessment": "pinned"})
    # The database refuses it too.
    with pytest.raises(psycopg.errors.RestrictViolation):
        execute("UPDATE assessment_switches SET enabled = true WHERE class_session_id = %s", item)


async def test_the_sweep_runs_the_test_deadline_lock_after_closing_the_replays():
    names = [action.name for action in sweep.DUE_ACTIONS]
    assert names.index("sessions.lock_test") == names.index("games.close_at_test_deadline") + 1


async def test_a_session_never_saved_with_the_switch_is_pinned_on(klass):
    session_id = await planned(klass)
    assert await assessment.assessment_due(session_id) is False  # not before the Test deadline
    assert await service.lock_test(session_id, now=TEST) is True
    assert stored(session_id) == [(True, TEST)]
    assert await assessment.assessment_due(session_id) is True


async def test_with_the_pinned_switch_off_nothing_is_to_be_assessed(klass):
    """FR-61, AD-9: the gate Story 12.2's assessment asks before it creates an assessment or makes
    an LLM call says no for a pinned switch that is off."""
    session_id = await planned(klass)
    assert (await save(session_id, ai_assessment=False)).status_code == 200
    assert await assessment.assessment_due(session_id) is False
    await service.lock_test(session_id, now=TEST)
    assert await assessment.assessment_due(session_id) is False
    assert rows("SELECT count(*) FROM llm_call") == [(0,)]


@pytest.mark.parametrize("role", ["assistant", "lecturer_assistant"])
async def test_an_assistant_lecturer_reads_the_switch_but_cannot_change_it(shared, role):
    session_id = await planned(shared)
    assert (await save(session_id, ai_assessment=False)).status_code == 200
    assert await read(session_id, EMAIL[role]) == {**OPEN, "enabled": False, "can_change": False}
    refused = await save(session_id, EMAIL[role], ai_assessment=True)
    assert (refused.status_code, refused.json()["error"]["code"]) == (403, "forbidden")
    assert stored(session_id) == [(False, None)]


async def test_an_archived_class_reads_the_switch_as_unchangeable(klass):
    session_id = await planned(klass)
    execute("UPDATE classes SET archived_at = %s WHERE id = %s", NOW, klass)
    assert (await read(session_id))["can_change"] is False


async def test_a_copy_takes_the_value_but_not_the_pin(klass, monkeypatch):
    flag(monkeypatch, True)
    source = await planned(klass)
    assert (await save(source, ai_assessment=False)).status_code == 200
    await service.lock_test(source, now=TEST)
    copied = await copy(klass, source)
    assert copied.status_code == 201
    assert copied.json()["ai_assessment"] == {**OPEN, "enabled": False}
    assert stored(copied.json()["id"]) == [(False, None)]
    # A source with the switch on gives the default, with nothing stored.
    plain = (await copy(klass, await new_session(klass))).json()
    assert plain["ai_assessment"] == OPEN and stored(plain["id"]) == []
