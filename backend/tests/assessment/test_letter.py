"""The Indicative letter (Story 12.6, FR-56, FR-3, FR-66, AD-1, AD-12, C-2).

The Lecturer chooses `all`, `student_choice` (default) or `unavailable` and the lower bounds of A
to E on the Klasseøkt («Lagre Klasseøkt»); the Admin can forbid the letter for an Institution;
a Student turns it on for their own view where it is left to them
(`PUT …/test/assessment/letter`). `assessment.letter_for` decides who gets a letter. On the mock
provider; the api's clock is fixed and moved by hand."""

import uuid

import psycopg
import pytest

from app.ai import seed
from app.analysis.letter import indicative_letter
from app.modules.assessment import service as assessment
from app.modules.identity.schemas import AccountRole
from app.modules.sessions import service as sessions
from app.platform.events.registry import COMMAND_TOPICS
from tests.assessment.test_assess import (
    HOUR,
    LONG,
    answer_all,
    assessment_url,
    attempt_id_of,
    closed,
    stored_facts,
)
from tests.assessment.test_flags import ADMIN, ASSISTANT, staff_url
from tests.classes.test_classes import LECTURER, OTHER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import clock, klass
from tests.classes.test_staff import call, put_staff
from tests.classes.test_student_registration import emitted
from tests.debrief.test_explanation import user_id
from tests.individual_test.test_adapted import locked_with, stand_in
from tests.individual_test.test_open import path
from tests.messaging.helpers import rows
from tests.sessions.test_dates import TEST, at, refusal
from tests.sessions.test_lock import _empty
from tests.sessions.test_rerun import copy, flag
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "emitted", "klass"]

DEFAULTS = {"A": 90, "B": 80, "C": 60, "D": 50, "E": 40}
TIGHT = {"A": 95, "B": 85, "C": 75, "D": 65, "E": 55}


def letter_url(session_id: str) -> str:
    return f"{assessment_url(session_id)}/letter"


async def save(session_id: str, who: str = LECTURER, **body):
    return await call(
        who, "PUT", f"/api/class-sessions/{session_id}", json={"ai_mode": "rule_based", **body}
    )


async def letter_block(session_id: str, who: str = LECTURER) -> dict:
    response = await call(who, "GET", f"/api/class-sessions/{session_id}")
    assert response.status_code == 200, response.text
    return response.json()["ai_assessment"]["letter"]


def institution_of(class_id: str) -> str:
    [(found,)] = rows("SELECT institution_id FROM classes WHERE id = %s", class_id)
    return str(found)


async def no_letter(institution_id: str, on: bool, who: str = ADMIN):
    return await call(
        who, "PUT", f"/api/admin/institutions/{institution_id}/no-letter", json={"on": on}
    )


async def locked(klass: str, monkeypatch, n: int = 1) -> str:
    """A locked Class session of `n` Students through the Replay; no Test attempt yet, the api's
    clock before the Test deadline."""
    await seed.ensure_zero_config()
    sets = stand_in(monkeypatch, own=range(1, 13))
    stored_facts(monkeypatch, sets)
    session_id, _ = await locked_with(klass, 30, n=n)
    return session_id


async def assessed(session_id: str, monkeypatch, status: str = "ready") -> None:
    """The first Student opens, answers and hands in; the lock and the close run at the Test
    deadline and the assessment is `status`; the clock stands an hour after the deadline."""
    opened = await call(email(0), "POST", path(session_id))
    assert opened.status_code == 201, opened.text
    await answer_all(session_id, opened.json())
    await closed(session_id)
    assert await assessment.assess(attempt_id_of(session_id)) == "ready"
    if status == "incomplete":
        execute("DELETE FROM ai_item_scores WHERE item_id = %s", LONG[0])
    if status != "ready":
        execute("UPDATE ai_assessments SET status = %s", status)
    at(monkeypatch, TEST + HOUR)


async def own(session_id: str, who: str = email(0)) -> dict:
    response = await call(who, "GET", assessment_url(session_id))
    assert response.status_code == 200, response.text
    return response.json()


def expected(body: dict, bounds: dict = DEFAULTS) -> str:
    return indicative_letter(body["total"], bounds, body["total_max"])


async def test_the_lecturer_saves_the_setting_and_the_bounds(klass, monkeypatch, emitted):
    session_id = await locked(klass, monkeypatch)
    block = await letter_block(session_id)
    assert block == {
        "setting": "student_choice",
        "stored": "student_choice",
        "forced": False,
        "thresholds": DEFAULTS,
        "thresholds_open": True,
        "can_change": True,
    }
    emitted.clear()
    saved = await save(session_id, letter_setting="all", letter_thresholds=TIGHT)
    assert saved.status_code == 200, saved.text
    assert saved.json()["ai_assessment"]["letter"]["setting"] == "all"
    assert saved.json()["ai_assessment"]["letter"]["thresholds"] == TIGHT
    assert ("session", session_id) in emitted
    assert rows(
        "SELECT letter_setting, letter_thresholds FROM assessment_switches "
        "WHERE class_session_id = %s",
        session_id,
    ) == [("all", TIGHT)]
    # Left out, both are kept; the bounds in force sent again are no change.
    assert (await save(session_id)).json()["ai_assessment"]["letter"]["setting"] == "all"
    assert (await save(session_id, letter_thresholds=TIGHT)).status_code == 200


async def test_bad_bounds_are_refused_and_nothing_is_stored(klass, monkeypatch):
    session_id = await locked(klass, monkeypatch)
    for bounds, reason in (
        ({**DEFAULTS, "B": 95}, "out_of_order"),
        ({**DEFAULTS, "A": 101}, "out_of_range"),
        ({**DEFAULTS, "E": 0}, "out_of_range"),
    ):
        refused = await save(session_id, letter_thresholds=bounds)
        assert refusal(refused) == (422, "invalid_session_values", {"letter_thresholds": reason})
    unreadable = await save(session_id, letter_thresholds={**DEFAULTS, "A": "90"})
    assert unreadable.status_code == 422
    assert rows("SELECT letter_thresholds FROM assessment_switches") == []


async def test_the_bounds_are_read_only_once_a_test_attempt_is_opened(klass, monkeypatch):
    session_id = await locked(klass, monkeypatch)
    assert (await call(email(0), "POST", path(session_id))).status_code == 201
    assert (await letter_block(session_id))["thresholds_open"] is False
    refused = await save(session_id, letter_thresholds=TIGHT)
    assert refusal(refused) == (409, "letter_thresholds_locked", {"letter_thresholds": "locked"})
    # The setting itself still changes until the Test deadline.
    assert (await save(session_id, letter_setting="all")).status_code == 200


async def test_only_the_owners_change_it_and_never_after_the_pin(klass, monkeypatch):
    session_id = await locked(klass, monkeypatch)
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")
    block = await letter_block(session_id, ASSISTANT)
    assert block["can_change"] is False and block["thresholds_open"] is False
    refused = await save(session_id, ASSISTANT, letter_setting="all")
    assert (refused.status_code, refused.json()["error"]["code"]) == (403, "forbidden")
    assert (await save(session_id, letter_thresholds=TIGHT)).status_code == 200
    # The Test-deadline lock pins the setting and the bounds in force with the switch.
    assert await sessions.lock_test(uuid.UUID(session_id), now=TEST) is True
    at(monkeypatch, TEST + HOUR)
    assert (await letter_block(session_id))["can_change"] is False
    for body, field in (
        ({"letter_setting": "all"}, "letter_setting"),
        ({"letter_thresholds": DEFAULTS}, "letter_thresholds"),
    ):
        refused = await save(session_id, **body)
        assert refusal(refused) == (409, "ai_assessment_pinned", {field: "pinned"})
    with pytest.raises(psycopg.errors.RestrictViolation):
        execute("UPDATE assessment_switches SET letter_setting = 'all'")
    with pytest.raises(psycopg.errors.RestrictViolation):
        execute("""UPDATE assessment_switches SET letter_thresholds = '{"A": 99}'::jsonb""")


async def test_the_pin_stores_the_default_bounds_in_force(klass, monkeypatch):
    session_id = await locked(klass, monkeypatch)
    assert await sessions.lock_test(uuid.UUID(session_id), now=TEST) is True
    assert rows("SELECT letter_setting, letter_thresholds FROM assessment_switches") == [
        ("student_choice", DEFAULTS)
    ]


async def test_the_student_turns_the_letter_on_and_off_for_their_own_view(
    klass, monkeypatch, emitted
):
    session_id = await locked(klass, monkeypatch, n=2)
    await assessed(session_id, monkeypatch)
    body = await own(session_id)
    assert body["letter"] == {"setting": "student_choice", "chosen": False, "value": None}
    emitted.clear()
    on = await call(email(0), "PUT", letter_url(session_id), json={"on": True})
    assert on.status_code == 200, on.text
    assert on.headers["cache-control"] == "no-store"
    assert on.json()["letter"] == {
        "setting": "student_choice",
        "chosen": True,
        "value": expected(body),
    }
    student = str(user_id(email(0)))
    assert emitted == [("user", student)]
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["assessment.set_letter_choice"]
    assert (await own(session_id))["letter"]["value"] == expected(body)
    # The staff never get it, nor the choice.
    staff = (await call(LECTURER, "GET", staff_url(session_id))).json()
    assert staff["letter"] is None and "chosen" not in str(staff)
    # Again is the same answer and emits nothing; off hides it.
    emitted.clear()
    assert (
        await call(email(0), "PUT", letter_url(session_id), json={"on": True})
    ).status_code == 200
    assert emitted == []
    off = await call(email(0), "PUT", letter_url(session_id), json={"on": False})
    assert off.json()["letter"] == {"setting": "student_choice", "chosen": False, "value": None}


async def test_the_choice_is_refused_where_it_is_not_the_students(klass, monkeypatch):
    session_id = await locked(klass, monkeypatch, n=2)
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")
    # Not handed in: no assessment, nothing to choose.
    not_ready = await call(email(0), "PUT", letter_url(session_id), json={"on": True})
    assert refusal(not_ready)[:2] == (409, "letter_not_available")
    await assessed(session_id, monkeypatch)
    # Someone else's, or no Student of the session at all.
    for who in (LECTURER, ASSISTANT, OTHER):
        refused = await call(who, "PUT", letter_url(session_id), json={"on": True})
        assert refused.status_code == 403, who
    mine = await call(email(1), "PUT", letter_url(session_id), json={"on": True})
    assert mine.json()["error"]["code"] == "letter_not_available"
    assert (
        await call(email(0), "PUT", letter_url(str(uuid.uuid7())), json={"on": True})
    ).status_code == 403
    assert rows("SELECT letter_chosen FROM ai_assessments") == [(False,)]


async def test_shown_to_everyone_the_student_and_the_staff_read_the_same_letter(klass, monkeypatch):
    session_id = await locked(klass, monkeypatch)
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")
    assert (
        await save(session_id, letter_setting="all", letter_thresholds=TIGHT)
    ).status_code == 200
    await assessed(session_id, monkeypatch)
    body = await own(session_id)
    letter = expected(body, TIGHT)
    assert body["letter"] == {"setting": "all", "chosen": False, "value": letter}
    for who in (LECTURER, ASSISTANT):
        assert (await call(who, "GET", staff_url(session_id))).json()["letter"] == letter
    # Nothing to choose: it is shown already.
    refused = await call(email(0), "PUT", letter_url(session_id), json={"on": False})
    assert refused.json()["error"]["code"] == "letter_not_available"


async def test_unavailable_shows_no_letter_and_no_control_anywhere(klass, monkeypatch):
    session_id = await locked(klass, monkeypatch)
    assert (await save(session_id, letter_setting="unavailable")).status_code == 200
    await assessed(session_id, monkeypatch)
    assert (await own(session_id))["letter"] is None
    assert (await call(LECTURER, "GET", staff_url(session_id))).json()["letter"] is None
    refused = await call(email(0), "PUT", letter_url(session_id), json={"on": True})
    assert refused.json()["error"]["code"] == "letter_not_available"


@pytest.mark.parametrize("status", ["incomplete", "failed"])
async def test_no_letter_for_an_assessment_that_is_not_ready(klass, monkeypatch, status):
    session_id = await locked(klass, monkeypatch)
    assert (await save(session_id, letter_setting="all")).status_code == 200
    await assessed(session_id, monkeypatch, status=status)
    body = await own(session_id)
    assert body["state"] == status and body["letter"] is None
    assert (await call(LECTURER, "GET", staff_url(session_id))).json()["letter"] is None


async def test_the_institution_forbids_the_letter_everywhere(klass, monkeypatch, emitted):
    session_id = await locked(klass, monkeypatch)
    await make(ADMIN, roles=(AccountRole.admin,))
    institution = institution_of(klass)
    assert (await save(session_id, letter_setting="all")).status_code == 200
    await assessed(session_id, monkeypatch)
    assert (await own(session_id))["letter"]["value"] is not None
    switched = await no_letter(institution, True)
    assert switched.status_code == 200, switched.text
    assert switched.json()["no_letter"] is True
    # No letter is derived or shown, though the Lecturer chose `all` before.
    assert (await own(session_id))["letter"] is None
    assert (await call(LECTURER, "GET", staff_url(session_id))).json()["letter"] is None
    block = await letter_block(session_id)
    assert (block["setting"], block["stored"], block["forced"]) == ("unavailable", "all", True)


async def test_while_forbidden_only_unavailable_can_be_chosen(klass, monkeypatch):
    session_id = await locked(klass, monkeypatch)
    await make(ADMIN, roles=(AccountRole.admin,))
    assert (await no_letter(institution_of(klass), True)).status_code == 200
    for setting in ("all", "student_choice"):
        if setting == "student_choice":
            # The stored default: sending it is no change, so the save goes through.
            assert (await save(session_id, letter_setting=setting)).status_code == 200
            continue
        refused = await save(session_id, letter_setting=setting)
        assert refusal(refused) == (409, "letter_unavailable", {"letter_setting": "institution"})
    assert (await save(session_id, letter_setting="unavailable")).status_code == 200
    refused = await save(session_id, letter_setting="student_choice")
    assert refusal(refused) == (409, "letter_unavailable", {"letter_setting": "institution"})


async def test_the_admin_switch_is_audited_and_admin_only(klass, monkeypatch):
    await make(ADMIN, roles=(AccountRole.admin,))
    institution = institution_of(klass)
    for on in (True, True, False):
        assert (await no_letter(institution, on)).json()["no_letter"] is on
    audits = rows(
        "SELECT action, target_ids, change FROM audit_events "
        "WHERE action = 'institution.no_letter_changed' ORDER BY id"
    )
    assert audits == [
        ("institution.no_letter_changed", {"institution_id": institution}, {"on": True}),
        ("institution.no_letter_changed", {"institution_id": institution}, {"on": False}),
    ]
    assert (await no_letter(str(uuid.uuid7()), True)).status_code == 404
    assert (await no_letter(institution, True, LECTURER)).status_code == 403
    assert (
        await call(
            ADMIN, "PUT", f"/api/admin/institutions/{institution}/no-letter", json={"on": "yes"}
        )
    ).status_code == 422


async def test_a_copy_takes_the_setting_and_the_bounds(klass, monkeypatch):
    flag(monkeypatch, True)
    session_id = await locked(klass, monkeypatch)
    assert (
        await save(session_id, letter_setting="unavailable", letter_thresholds=TIGHT)
    ).status_code == 200
    copied = await copy(klass, session_id)
    assert copied.status_code == 201, copied.text
    block = copied.json()["ai_assessment"]["letter"]
    assert (block["setting"], block["thresholds"], block["thresholds_open"]) == (
        "unavailable",
        TIGHT,
        True,
    )
    # A pinned source gives the bounds its pin stored, never the configuration's later ones.
    assert await sessions.lock_test(uuid.UUID(session_id), now=TEST) is True
    monkeypatch.setattr(assessment, "default_thresholds", lambda: dict(DEFAULTS, A=99))
    again = (await copy(klass, session_id)).json()["ai_assessment"]["letter"]
    assert (again["setting"], again["thresholds"]) == ("unavailable", TIGHT)


RULES = {
    setting: assessment.LetterRules(setting=setting, thresholds=DEFAULTS)
    for setting in ("all", "student_choice", "unavailable")
}


@pytest.mark.parametrize(
    ("setting", "opted_in", "reader", "by_student", "letter"),
    [
        ("all", False, "student", False, "B"),
        ("all", False, "staff", False, "B"),
        ("all", False, "export", False, None),
        ("all", False, "zip", False, None),
        ("all", False, "report", True, "B"),
        ("all", False, "report", False, None),
        ("student_choice", True, "student", False, "B"),
        ("student_choice", False, "student", False, None),
        ("student_choice", False, "staff", False, None),
        ("student_choice", False, "report", True, None),
        ("student_choice", True, "staff", False, None),
        ("student_choice", True, "export", False, None),
        ("student_choice", True, "zip", False, None),
        ("student_choice", True, "report", True, "B"),
        ("student_choice", True, "report", False, None),
        ("unavailable", True, "student", False, None),
        ("unavailable", True, "report", True, None),
    ],
)
def test_letter_for_gives_each_reader_only_what_it_may_have(
    setting, opted_in, reader, by_student, letter
):
    found = assessment.letter_for(
        RULES[setting],
        total=85,
        total_max=100,
        ready=True,
        opted_in=opted_in,
        reader=reader,
        requested_by_student=by_student,
    )
    assert found == letter


def test_letter_for_gives_no_letter_without_a_ready_total():
    for total, ready in ((None, True), (85, False)):
        assert (
            assessment.letter_for(
                RULES["all"],
                total=total,
                total_max=100,
                ready=ready,
                opted_in=True,
                reader="student",
            )
            is None
        )
