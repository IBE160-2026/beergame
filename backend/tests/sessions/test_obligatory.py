"""The obligatory mark, its required share of Weeks and the Inactivity limit of a Class session
(Story 5.7, FR-17, FR-18, FR-36, AD-8, AD-9, AD-16): saved with «Lagre Klasseøkt», judged by the
api, locked at the Start date; switching the mark on tells every registered Student through one
digest notice holding ids only. The api's clock is fixed; the database clock is never read."""

from datetime import timedelta

import pytest

from app.modules.messaging import delivery
from app.modules.sessions import service
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_staff import ASSISTANT, call, put_staff
from tests.classes.test_student_registration import emitted
from tests.messaging.helpers import mails, rows
from tests.sessions.test_dates import PLAN, at, iso, new_session, refusal, student_of
from tests.sessions.test_lab_hours import notices, sweep_at, two_students

__all__ = ["clock", "emitted", "klass"]

HOUR = timedelta(hours=1)


@pytest.fixture(autouse=True)
def _empty(ai_db, mail_db):
    """No model config (Rule-based sessions), and no notices, deliveries or mails."""


async def save(session_id: str, email=LECTURER, **body):
    return await call(
        email, "PUT", f"/api/class-sessions/{session_id}", json={"ai_mode": "rule_based", **body}
    )


def stored(session_id: str) -> tuple:
    return rows(
        "SELECT obligatory, required_share_percent, inactivity_limit_hours FROM class_sessions "
        "WHERE id = %s",
        session_id,
    )[0]


async def test_a_new_session_is_not_obligatory_requires_80_and_waits_24_hours(klass):
    session_id = await new_session(klass)
    body = (await call(LECTURER, "GET", f"/api/class-sessions/{session_id}")).json()
    assert (body["obligatory"], body["required_share_percent"], body["inactivity_limit_hours"]) == (
        False,
        80,
        24,
    )
    assert service.required_share(body) == 80


async def test_the_default_share_comes_from_configuration(klass, monkeypatch):
    configured = service.get_settings().model_copy(update={"completion_default_share_percent": 60})
    monkeypatch.setattr(service, "get_settings", lambda: configured)
    session_id = await new_session(klass)
    assert stored(session_id) == (False, 60, 24)


async def test_switching_on_stores_the_mark_and_tells_each_registered_student_once(klass, emitted):
    students = await two_students(klass)
    session_id = await new_session(klass)
    emitted.clear()
    response = await save(session_id, obligatory=True, required_share_percent=75)
    assert response.status_code == 200
    assert (response.json()["obligatory"], response.json()["required_share_percent"]) == (True, 75)
    assert stored(session_id) == (True, 75, 24)
    key = f"class_session_obligatory:{session_id}:{NOW.isoformat()}"
    assert notices() == [
        ("class_session_obligatory", f"{key}:{s}", s, session_id) for s in students
    ]
    assert emitted == [("session", session_id), *(("user", s) for s in students)]
    assert {topic for topic, _ in emitted} <= COMMAND_TOPICS["sessions.save"]
    # Saved on again: nobody is told again. Switched off: nobody is told.
    assert (await save(session_id, obligatory=True)).status_code == 200
    assert (await save(session_id, obligatory=False)).status_code == 200
    assert stored(session_id) == (False, 75, 24) and len(notices()) == 2
    # The required share is the one source others read.
    read = (await call(LECTURER, "GET", f"/api/class-sessions/{session_id}")).json()
    assert service.required_share(read) == 75


async def test_a_save_that_leaves_the_three_out_keeps_them(klass):
    session_id = await new_session(klass)
    assert (
        await save(session_id, obligatory=True, required_share_percent=1, inactivity_limit_hours=20)
    ).status_code == 200
    assert (await save(session_id)).status_code == 200
    assert stored(session_id) == (True, 1, 20)
    assert (await save(session_id, required_share_percent=100, inactivity_limit_hours=48)).json()[
        "inactivity_limit_hours"
    ] == 48
    assert stored(session_id) == (True, 100, 48)


@pytest.mark.parametrize(
    ("body", "fields"),
    [
        ({"required_share_percent": 0}, {"required_share_percent": "out_of_range"}),
        ({"required_share_percent": 101}, {"required_share_percent": "out_of_range"}),
        ({"inactivity_limit_hours": 19}, {"inactivity_limit_hours": "below_minimum"}),
        (
            {"required_share_percent": -1, "inactivity_limit_hours": 0},
            {"required_share_percent": "out_of_range", "inactivity_limit_hours": "below_minimum"},
        ),
    ],
)
async def test_a_value_out_of_range_is_refused_and_nothing_is_stored(klass, body, fields):
    await student_of(klass)
    session_id = await new_session(klass)
    response = await save(session_id, obligatory=True, **body)
    assert refusal(response) == (422, "invalid_session_values", fields)
    assert stored(session_id) == (False, 80, 24) and notices() == []


@pytest.mark.parametrize("value", [24.5, 48.0, "48", "24,5", "", True, None])
async def test_a_limit_or_share_that_is_no_json_integer_is_refused(klass, value):
    session_id = await new_session(klass)
    if value is None:
        # Sent as null, it keeps the stored limit.
        assert (await save(session_id, inactivity_limit_hours=None)).status_code == 200
    else:
        for field in ("inactivity_limit_hours", "required_share_percent"):
            response = await save(session_id, obligatory=True, **{field: value})
            assert (response.status_code, response.json()["error"]["code"]) == (
                422,
                "invalid_request",
            )
    assert stored(session_id) == (False, 80, 24)


async def test_once_locked_the_three_are_refused_when_changed_and_kept_when_not(klass, monkeypatch):
    await student_of(klass)
    session_id = await new_session(klass)
    response = await call(
        LECTURER,
        "PUT",
        f"/api/class-sessions/{session_id}",
        json={"ai_mode": "rule_based", "dates": iso(PLAN), "obligatory": True},
    )
    assert response.status_code == 200
    at(monkeypatch, PLAN["start_at"] + HOUR)
    refused = await save(
        session_id, obligatory=False, required_share_percent=50, inactivity_limit_hours=30
    )
    assert refusal(refused) == (
        409,
        "session_locked",
        {
            "obligatory": "locked",
            "required_share_percent": "locked",
            "inactivity_limit_hours": "locked",
        },
    )
    assert refusal(await save(session_id, inactivity_limit_hours=19))[:2] == (
        409,
        "session_locked",
    )
    unchanged = await save(
        session_id, obligatory=True, required_share_percent=80, inactivity_limit_hours=24
    )
    assert unchanged.status_code == 200
    assert stored(session_id) == (True, 80, 24)


async def test_an_assistant_and_an_archived_class_change_nothing(klass):
    session_id = await new_session(klass)
    assistant = await make(ASSISTANT, roles=())
    put_staff(klass, assistant, "assistant")
    assert (await save(session_id, email=ASSISTANT, obligatory=True)).status_code == 403
    execute("UPDATE classes SET archived_at = %s WHERE id = %s", NOW, klass)
    assert refusal(await save(session_id, obligatory=True))[:2] == (409, "class_archived")
    assert stored(session_id) == (False, 80, 24) and notices() == []


async def test_the_student_reads_the_obligatory_flag(klass):
    await student_of(klass)
    session_id = await new_session(klass)
    assert (await save(session_id, obligatory=True)).status_code == 200
    [item] = (await call("student@x.no", "GET", "/api/me/class-sessions")).json()["items"]
    assert item["obligatory"] is True
    for hidden in ("required_share_percent", "inactivity_limit_hours", "game_settings"):
        assert hidden not in item


def test_the_delivery_table_names_the_obligatory_kind_as_digest():
    assert delivery.OBLIGATORY_KIND == service.OBLIGATORY_NOTICE
    assert delivery.KINDS[service.OBLIGATORY_NOTICE].mode == delivery.DIGEST


async def test_the_digest_says_the_session_is_obligatory(klass):
    await student_of(klass)
    session_id = await new_session(klass)
    assert (await save(session_id, obligatory=True)).status_code == 200
    await sweep_at(NOW + HOUR)  # 11:00 in Oslo, inside the digest hours
    [mail] = mails()
    assert mail.to == "student@x.no"
    assert "Øvelsen i Klassen class-of-1994 er obligatorisk. Den står i emneplanen." in mail.text
    for banned in ("Beer Game", "bullwhip", "uker", "Uke"):
        assert banned not in mail.text


async def test_a_mark_switched_off_before_the_digest_or_a_removed_student_gets_no_mail(
    klass, monkeypatch
):
    await student_of(klass)
    session_id = await new_session(klass)
    assert (await save(session_id, obligatory=True)).status_code == 200
    assert (await save(session_id, obligatory=False)).status_code == 200
    await sweep_at(NOW + HOUR)
    assert mails() == []
    # On again later: a notice of its own, but the Student has left the Class.
    at(monkeypatch, NOW + 2 * HOUR)
    assert (await save(session_id, obligatory=True)).status_code == 200
    assert len(notices()) == 2
    execute("UPDATE roster_entries SET removed_at = %s WHERE class_id = %s", NOW, klass)
    await sweep_at(NOW + 3 * HOUR)
    assert mails() == []


async def test_an_archived_class_gets_no_obligatory_mail(klass):
    await student_of(klass)
    session_id = await new_session(klass)
    assert (await save(session_id, obligatory=True)).status_code == 200
    execute("UPDATE classes SET archived_at = %s WHERE id = %s", NOW, klass)
    await sweep_at(NOW + HOUR)
    assert len(notices()) == 1 and mails() == []
