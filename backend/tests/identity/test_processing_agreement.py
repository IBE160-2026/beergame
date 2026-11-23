"""The Institution's data processing agreement and the hold on Student Invitations (Story 15.12,
FR-8, FR-82, PRD §6.1, AD-12, AD-15): the Admin records who signed and the day, audited, behind
its own policy; while `REQUIRE_DPA_FOR_INVITATIONS` is on, a Class whose Institution has none
refuses to send Student Invitations, reminders and manual registrations, and changes nothing; off,
the send goes on and the missing agreement is logged with ids. Lecturer, Admin and Assistant
Invitations never wait, and neither does the operator's own Institution nor a Control test. The
api's clock is fixed; the database clock is never read."""

import uuid

import psycopg
import pytest
from structlog.testing import capture_logs

from app.modules.identity import service as identity
from app.platform.config import get_settings
from tests.classes.test_classes import LECTURER, institution
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import clock, klass
from tests.classes.test_staff import call
from tests.messaging.helpers import rows
from tests.sessions.test_control_test import ADMIN, control, mark, people
from tests.sessions.test_test_students import invite

__all__ = ["clock", "control", "klass", "people"]

SIGNED = {"signed_by": "Prorektor for utdanning", "signed_on": "2026-11-02"}


@pytest.fixture(autouse=True)
def _empty(ai_db, mail_db, games_db):
    """No model config, notices or games but what a test adds."""


def require(monkeypatch, on: bool) -> None:
    monkeypatch.setenv("REQUIRE_DPA_FOR_INVITATIONS", "true" if on else "false")
    get_settings.cache_clear()


def agreement_path(institution_id: str) -> str:
    return f"/api/admin/institutions/{institution_id}/processing-agreement"


async def record(institution_id: str, body: dict | None = None, email: str = ADMIN):
    return await call(email, "PUT", agreement_path(institution_id), json=body or SIGNED)


def class_institution(class_id: str) -> str:
    return str(rows("SELECT institution_id FROM classes WHERE id = %s", class_id)[0][0])


def changed_rows() -> tuple:
    """What a refused send must leave as it was."""
    return (
        rows("SELECT count(*) FROM invitations WHERE kind = 'student'")[0][0],
        sorted(rows("SELECT email, registration, user_id FROM roster_entries")),
        rows("SELECT count(*) FROM roster_uploads")[0][0],
        rows("SELECT count(*) FROM notices")[0][0],
    )


async def stage(class_id: str, text: str = "a@x.no b@x.no") -> str:
    pasted = await call(
        LECTURER, "POST", f"/api/classes/{class_id}/roster-paste", json={"text": text}
    )
    assert pasted.status_code == 201, pasted.text
    return pasted.json()["id"]


async def send(class_id: str, upload_id: str):
    return await call(
        LECTURER,
        "POST",
        f"/api/classes/{class_id}/invitations",
        json={"upload_id": upload_id, "valid_days": 14},
    )


# Recording the agreement.


async def test_the_admin_records_the_agreement_and_it_is_audited(people):
    place = people["other"]
    assert await identity.has_processing_agreement(uuid.UUID(place)) is False
    response = await record(place)
    assert response.status_code == 200, response.text
    assert response.json()["processing_agreement"] == {
        **SIGNED,
        "recorded_at": "2026-11-19T09:00:00Z",
    }
    assert await identity.has_processing_agreement(uuid.UUID(place)) is True
    listed = (await call(ADMIN, "GET", "/api/admin/institutions")).json()["items"]
    found = {item["id"]: item["processing_agreement"] for item in listed}
    assert found[place]["signed_by"] == SIGNED["signed_by"]
    assert found[people["operator"]] is None
    # The same agreement again writes nothing; a new one replaces it, audited again.
    assert (await record(place)).status_code == 200
    changed = await record(place, {"signed_by": "  Rektor  ", "signed_on": "2026-11-19"})
    assert changed.json()["processing_agreement"]["signed_by"] == "Rektor"
    audited = rows(
        "SELECT target_ids, change FROM audit_events "
        "WHERE action = 'institution.processing_agreement_recorded' ORDER BY change->>'replaced'"
    )
    assert audited == [
        ({"institution_id": place}, {"signed_on": "2026-11-02", "replaced": False}),
        ({"institution_id": place}, {"signed_on": "2026-11-19", "replaced": True}),
    ]


async def test_only_the_admin_records_and_bad_bodies_store_nothing(people):
    place = people["other"]
    assert (await record(place, email=LECTURER)).status_code == 403
    blank = await record(place, {"signed_by": "   ", "signed_on": "2026-11-02"})
    assert (blank.status_code, blank.json()["error"]["code"]) == (422, "invalid_request")
    future = await record(place, {"signed_by": "Rektor", "signed_on": "2026-11-20"})
    assert future.status_code == 422
    assert future.json()["error"]["fields"] == {"signed_on": "in_future"}
    extra = await record(place, {**SIGNED, "controller": "x"})
    assert extra.status_code == 422
    assert (await record(str(uuid.uuid4()))).status_code == 404
    assert rows("SELECT count(*) FROM institutions WHERE dpa_signed_on IS NOT NULL") == [(0,)]
    assert rows(
        "SELECT count(*) FROM audit_events "
        "WHERE action = 'institution.processing_agreement_recorded'"
    ) == [(0,)]


# The hold on Student Invitations.


async def test_with_the_setting_on_a_send_without_agreement_is_refused_and_changes_nothing(
    people, monkeypatch
):
    require(monkeypatch, True)
    klass = people["class"]
    upload_id = await stage(klass)
    before = changed_rows()
    refused = await send(klass, upload_id)
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "processing_agreement_missing"
    assert changed_rows() == before
    # Recorded, the same staging is sent.
    assert (await record(class_institution(klass))).status_code == 200
    sent = await send(klass, upload_id)
    assert (sent.status_code, sent.json()["sent"]) == (201, 2)


async def test_with_the_setting_on_reminders_and_manual_registration_are_refused(
    people, monkeypatch
):
    klass = people["class"]
    added = await call(
        LECTURER, "POST", f"/api/classes/{klass}/roster/entries", json={"email": "late@x.no"}
    )
    assert added.status_code == 201
    require(monkeypatch, True)
    before = changed_rows()
    reminded = await call(LECTURER, "POST", f"/api/classes/{klass}/reminders", json={})
    manual = await call(
        LECTURER,
        "POST",
        f"/api/classes/{klass}/roster/manual",
        json={"email": "hand@x.no", "name": "Per Hand"},
    )
    assert [r.status_code for r in (reminded, manual)] == [409, 409]
    assert {r.json()["error"]["code"] for r in (reminded, manual)} == {
        "processing_agreement_missing"
    }
    assert changed_rows() == before
    assert rows("SELECT count(*) FROM users WHERE email = 'hand@x.no'") == [(0,)]


async def test_with_the_setting_on_a_reminder_with_nothing_to_send_answers_as_before(
    people, monkeypatch
):
    # Only the Student of `people` is on the Roster, registered: no address to remind, so the
    # agreement is not asked and the answer stays `nothing_to_send`.
    require(monkeypatch, True)
    reminded = await call(LECTURER, "POST", f"/api/classes/{people['class']}/reminders", json={})
    assert (reminded.status_code, reminded.json()["error"]["code"]) == (422, "nothing_to_send")


def test_the_database_refuses_a_half_recorded_agreement(people):
    place = people["other"]
    for sets in (
        "dpa_signed_on = '2026-11-02', dpa_recorded_at = now()",
        "dpa_signed_by = ' ', dpa_signed_on = '2026-11-02', dpa_recorded_at = now()",
        "dpa_signed_by = 'Rektor'",
    ):
        with pytest.raises(psycopg.errors.CheckViolation):
            execute(f"UPDATE institutions SET {sets} WHERE id = %s", place)


async def test_with_the_setting_off_the_send_goes_on_and_logs_ids_only(people, monkeypatch):
    require(monkeypatch, False)
    klass = people["class"]
    upload_id = await stage(klass)
    with capture_logs() as logs:
        sent = await send(klass, upload_id)
    assert (sent.status_code, sent.json()["sent"]) == (201, 2)
    [line] = [e for e in logs if e["event"] == "invitation_without_processing_agreement"]
    assert line["log_level"] == "warning"
    assert set(line) == {"event", "log_level", "class_id", "institution_id"}
    assert (line["class_id"], line["institution_id"]) == (klass, class_institution(klass))


async def test_with_an_agreement_no_line_is_logged(people, monkeypatch):
    require(monkeypatch, False)
    klass = people["class"]
    assert (await record(class_institution(klass))).status_code == 200
    upload_id = await stage(klass)
    with capture_logs() as logs:
        assert (await send(klass, upload_id)).status_code == 201
    assert not [e for e in logs if e["event"] == "invitation_without_processing_agreement"]


async def test_staff_and_role_invitations_never_wait(people, monkeypatch):
    require(monkeypatch, True)
    assistant = await call(
        LECTURER,
        "POST",
        f"/api/classes/{people['class']}/staff/assistants",
        json={"email": "ny-assistent@x.no"},
    )
    assert assistant.status_code == 201, assistant.text
    for role in ("lecturer", "admin"):
        sent = await call(
            ADMIN, "POST", "/api/admin/invitations", json={"email": f"{role}@ny.no", "role": role}
        )
        assert sent.status_code == 201, sent.text


async def test_a_test_student_is_invited_to_a_control_test_with_the_setting_on(
    control, monkeypatch
):
    require(monkeypatch, True)
    operator = class_institution(control["class_id"])
    assert await identity.has_processing_agreement(uuid.UUID(operator)) is False
    links = await invite(control["class_id"], "test1@x.no")
    assert set(links) == {"test1@x.no"}


async def test_a_control_test_still_passes_after_the_operator_mark_moved(
    people, control, monkeypatch
):
    require(monkeypatch, True)
    elsewhere = str(await institution("Tredje AS"))
    assert (await mark(elsewhere)).status_code == 200
    links = await invite(control["class_id"], "test2@x.no")
    assert set(links) == {"test2@x.no"}


async def test_an_ordinary_class_of_the_operator_institution_passes(people, monkeypatch):
    require(monkeypatch, True)
    klass = people["class"]
    assert (await mark(class_institution(klass))).status_code == 200
    sent = await send(klass, await stage(klass))
    assert sent.status_code == 201, sent.text


def test_the_setting_is_off_until_the_founder_decides(monkeypatch):
    monkeypatch.delenv("REQUIRE_DPA_FOR_INVITATIONS", raising=False)
    get_settings.cache_clear()
    assert get_settings().require_dpa_for_invitations is False
