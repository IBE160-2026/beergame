"""A Class session made from an earlier one (Story 5.18, cut list, `FEATURE_RERUN`, FR-66, FR-78,
AD-4, AD-6, AD-12, AD-17): the source's editable Game settings, AI mode, Effort level, Debrief mode
and Inactivity limit, the active default model config, a fresh seed unless the old one is kept,
and nothing of the dates, Lab hours, Roster, allocation or obligatory mark. Off, both routes
answer `feature_disabled`. The api's clock is fixed; the database clock is never read."""

import json
import uuid

import pytest

from app.ai import config, seed
from app.engine import GameSettings
from app.modules.sessions import service
from app.platform.config import get_settings
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_classes import LECTURER, OTHER
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_staff import call, put_staff
from tests.classes.test_student_registration import emitted, second_class
from tests.messaging.helpers import rows
from tests.sessions.test_ai_mode import TWO_LEVELS
from tests.sessions.test_dates import PLAN, iso, new_session, refusal
from tests.sessions.test_lab_hours import add
from tests.sessions.test_settings import save, stored

__all__ = ["clock", "emitted", "klass"]


@pytest.fixture(autouse=True)
def _empty(ai_db, monkeypatch):
    """No model config, pin or budget; `FEATURE_RERUN` on unless a test says otherwise."""
    flag(monkeypatch, True)


def flag(monkeypatch, on: bool, name: str = "FEATURE_RERUN") -> None:
    monkeypatch.setenv(name, "true" if on else "false")
    get_settings.cache_clear()


async def copy(class_id: str, source_id: str, email: str = LECTURER, **body):
    return await call(
        email,
        "POST",
        f"/api/classes/{class_id}/class-sessions/copy",
        json={"source_id": source_id, **body},
    )


async def sources(class_id: str, email: str = LECTURER):
    return await call(email, "GET", f"/api/classes/{class_id}/class-sessions/copy-sources")


def row_of(session_id: str) -> dict:
    (found,) = rows(
        "SELECT class_id, ai_mode, effort_level, debrief_mode, inactivity_limit_hours, obligatory, "
        "required_share_percent, model_config_id, allocation_method, copied_from, "
        "effort_level_replaced, start_at, play_deadline, locked_at, saved_at "
        "FROM class_sessions WHERE id = %s",
        session_id,
    )
    names = (
        "class_id ai_mode effort_level debrief_mode inactivity_limit_hours obligatory "
        "required_share_percent model_config_id allocation_method copied_from "
        "effort_level_replaced start_at play_deadline locked_at saved_at"
    ).split()
    return dict(zip(names, found, strict=True))


async def two_level_default() -> uuid.UUID:
    """A mock config offering `standard` and `careful`, pinned as the active default."""
    row = await config.add(
        config.parse({**seed.MOCK_SPEC, "name": "mock-two", "effort_levels": TWO_LEVELS})
    )
    for level in ("standard", "careful"):
        await config.add_mock_measurement(row.id, level)
    await config.pin(row.id)
    return row.id


async def a_class_of(email: str, name: str) -> str:
    (institution,) = rows("SELECT id FROM institutions")[0]
    created = await call(
        email, "POST", "/api/classes", json={"name": name, "institution_id": str(institution)}
    )
    assert created.status_code == 201
    return created.json()["id"]


async def changed_source(class_id: str) -> str:
    """A session with changed settings, Personal debrief, a 30 h limit, dates, a Lab hour, the
    obligatory mark and Student choice: what a copy keeps and what it leaves."""
    session_id = await new_session(class_id)
    assert (await save(session_id, {"order_delay": 3, "holding_cost": "0.75"})).status_code == 200
    saved = await call(
        LECTURER,
        "PUT",
        f"/api/class-sessions/{session_id}",
        json={
            "ai_mode": "rule_based",
            "debrief_mode": "personal",
            "obligatory": True,
            "required_share_percent": 60,
            "dates": iso(PLAN),
        },
    )
    assert saved.status_code == 200, saved.text
    limit = await call(
        LECTURER,
        "PUT",
        f"/api/class-sessions/{session_id}",
        json={"ai_mode": "rule_based", "inactivity_limit_hours": 30},
    )
    assert limit.status_code == 200, limit.text
    assert (await add(session_id)).status_code == 201
    execute(
        "UPDATE class_sessions SET allocation_method = 'student_choice' WHERE id = %s", session_id
    )
    (lecturer,) = rows("SELECT id FROM users WHERE email = %s", LECTURER)[0]
    execute(
        "INSERT INTO allocation_drafts (id, class_session_id, revision, seed, assignments, "
        "drawn_by, drawn_at, confirmed_at, confirmed_by) "
        "VALUES (%s, %s, 1, 7, %s::jsonb, %s, %s, %s, %s)",
        uuid.uuid4(),
        session_id,
        json.dumps([{"user_id": str(lecturer), "game_number": 1, "role": "retailer"}]),
        lecturer,
        NOW,
        NOW,
        lecturer,
    )
    return session_id


async def test_a_copy_keeps_the_settings_and_leaves_dates_lab_hours_allocation_and_mark(
    klass, emitted
):
    default = uuid.UUID(await seed.ensure_zero_config())
    source = await changed_source(klass)
    emitted.clear()
    response = await copy(klass, source)
    assert response.status_code == 201, response.text
    body = response.json()
    new = body["id"]
    assert emitted == [("session", new)]
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["sessions.copy_from"]
    copied, was = stored(new), stored(source)
    assert copied.model_copy(update={"demand_seed": None}) == was.model_copy(
        update={"demand_seed": None}
    )
    assert copied.order_delay == 3 and str(copied.holding_cost) == "0.75"
    found = row_of(new)
    assert found["ai_mode"] == "rule_based" and found["effort_level"] is None
    assert (found["debrief_mode"], found["inactivity_limit_hours"]) == ("personal", 30)
    assert (found["obligatory"], found["required_share_percent"]) == (
        False,
        get_settings().completion_default_share_percent,
    )
    assert found["model_config_id"] == default
    assert found["allocation_method"] == "random"
    assert str(found["copied_from"]) == source
    assert (found["start_at"], found["play_deadline"], found["saved_at"]) == (None, None, None)
    assert rows("SELECT id FROM lab_hours WHERE class_session_id = %s", new) == []
    assert rows("SELECT id FROM allocation_drafts WHERE class_session_id = %s", new) == []
    assert rows("SELECT scope_id FROM ai_budgets WHERE scope_id = %s", new) == [(uuid.UUID(new),)]
    assert body["copied_from"] == {"id": source, "class_name": "class-of-1994", "number": 1}
    assert body["number"] == 2 and body["is_classic"] is False
    assert body["effort_level_replaced"] is None
    assert body["lab_hours"] == [] and body["obligatory"] is False
    # Prefilled and saved unchanged: the settings pass the engine again.
    resaved = await call(
        LECTURER,
        "PUT",
        f"/api/class-sessions/{new}",
        json={
            "ai_mode": body["ai_mode"],
            # What the screen sends: every editable setting, as copied.
            "game_settings": {
                key: value
                for key, value in body["game_settings"].items()
                if key in service.EDITABLE_SETTINGS
            },
        },
    )
    assert resaved.status_code == 200, resaved.text
    assert stored(new) == copied


async def test_a_fresh_seed_is_drawn_unless_the_old_one_is_kept(klass):
    source = await new_session(klass)
    old = stored(source).demand_seed
    fresh = (await copy(klass, source)).json()
    kept = (await copy(klass, source, keep_seed=True)).json()
    assert kept["game_settings"]["demand_seed"] == old
    assert fresh["game_settings"]["demand_seed"] != old


async def test_a_session_of_another_class_is_copied_into_this_one(klass):
    source = await new_session(klass)
    target = await second_class()
    response = await copy(target, source)
    assert response.status_code == 201
    body = response.json()
    assert (body["class_id"], body["number"]) == (target, 1)
    assert body["copied_from"]["class_name"] == "class-of-1994"
    listed = (await sources(target)).json()["items"]
    assert [(item["id"], item["class_name"]) for item in listed] == [
        (body["id"], "class-of-1995"),
        (source, "class-of-1994"),
    ]
    assert all(item["archived"] is False and item["start_at"] is None for item in listed)


async def test_only_sessions_of_classes_the_lecturer_is_staff_of_are_offered_or_copied(klass):
    mine = await new_session(klass)
    theirs_class = await a_class_of(OTHER, "kari-sin")
    theirs = (await call(OTHER, "POST", f"/api/classes/{theirs_class}/class-sessions")).json()["id"]
    assert [item["id"] for item in (await sources(klass)).json()["items"]] == [mine]
    before = rows("SELECT count(*) FROM class_sessions")
    for source in (theirs, str(uuid.uuid4()), "not-an-id"):
        refused = await copy(klass, source)
        assert (refused.status_code, refused.json()["error"]["code"]) == (403, "forbidden")
    assert rows("SELECT count(*) FROM class_sessions") == before
    # Into a Class the Lecturer does not own: refused, as is its list.
    assert (await copy(theirs_class, mine)).status_code == 403
    assert (await sources(theirs_class)).status_code == 403


async def test_an_assistant_lecturer_may_copy_what_they_read_but_not_into_that_class(klass):
    theirs_class = await a_class_of(OTHER, "kari-sin")
    theirs = (await call(OTHER, "POST", f"/api/classes/{theirs_class}/class-sessions")).json()["id"]
    (lecturer,) = rows("SELECT id FROM users WHERE email = %s", LECTURER)[0]
    put_staff(theirs_class, lecturer, "assistant")
    listed = [item["id"] for item in (await sources(klass)).json()["items"]]
    assert theirs in listed
    response = await copy(klass, theirs)
    assert response.status_code == 201
    assert response.json()["copied_from"]["class_name"] == "kari-sin"
    assert (await copy(theirs_class, theirs)).status_code == 403


async def test_with_the_flag_off_both_routes_answer_feature_disabled(klass, monkeypatch):
    source = await new_session(klass)
    flag(monkeypatch, False)
    listed = await call(LECTURER, "GET", f"/api/classes/{klass}/class-sessions")
    assert listed.json()["rerun_enabled"] is False
    for response in (await copy(klass, source), await sources(klass)):
        assert refusal(response) == (422, "feature_disabled", {"rerun": "feature_disabled"})
    assert len(rows("SELECT id FROM class_sessions")) == 1
    flag(monkeypatch, True)
    listed = await call(LECTURER, "GET", f"/api/classes/{klass}/class-sessions")
    assert listed.json()["rerun_enabled"] is True


async def test_a_level_the_new_default_does_not_offer_becomes_its_default_and_is_named(klass):
    first = await two_level_default()
    source = await new_session(klass)
    saved = await call(
        LECTURER,
        "PUT",
        f"/api/class-sessions/{source}",
        json={"ai_mode": "llm", "effort_level": "careful"},
    )
    assert saved.json()["effort_level"] == "careful"
    # A newer default that offers only `standard`.
    newer = await config.add(
        config.parse({**seed.MOCK_SPEC, "name": "mock-one", "effort_levels": TWO_LEVELS[:1]})
    )
    await config.add_mock_measurement(newer.id, "standard")
    await config.pin(newer.id)
    body = (await copy(klass, source)).json()
    assert (body["ai_mode"], body["effort_level"]) == ("llm", "standard")
    assert body["effort_level_replaced"] == {"name": "careful", "label": "Grundig"}
    found = row_of(body["id"])
    assert (found["model_config_id"], found["effort_level_replaced"]) == (newer.id, "careful")
    assert found["model_config_id"] != first
    # A level the new default does offer is kept, and nothing is named.
    saved = await call(
        LECTURER,
        "PUT",
        f"/api/class-sessions/{source}",
        json={"ai_mode": "llm", "effort_level": "standard"},
    )
    assert saved.status_code == 200
    body = (await copy(klass, source)).json()
    assert (body["effort_level"], body["effort_level_replaced"]) == ("standard", None)


async def test_with_no_active_default_an_llm_source_is_copied_with_rule_based_players(klass):
    await seed.ensure_zero_config()
    source = await new_session(klass)
    assert row_of(source)["ai_mode"] == "llm"
    execute("DELETE FROM ai_default_pins")
    body = (await copy(klass, source)).json()
    assert (body["ai_mode"], body["llm_unavailable"], body["effort_level"]) == (
        "rule_based",
        "no_default_model",
        None,
    )
    assert row_of(body["id"])["model_config_id"] is None
    assert rows("SELECT scope_id FROM ai_budgets WHERE scope_id = %s", body["id"]) == []


async def test_cut_list_values_whose_flag_is_off_now_are_left_out(klass, monkeypatch):
    flag(monkeypatch, True, "FEATURE_CAPACITY")
    flag(monkeypatch, True, "FEATURE_INFO_VISIBILITY")
    source = await new_session(klass)
    response = await save(
        source, {"capacity": {"retailer": 20}, "info_visibility": {"upstream": True}}
    )
    assert response.status_code == 200, response.text
    kept = (await copy(klass, source)).json()["game_settings"]
    assert kept["capacity"] == {"retailer": 20} and kept["info_visibility"]["upstream"] is True
    flag(monkeypatch, False, "FEATURE_CAPACITY")
    flag(monkeypatch, False, "FEATURE_INFO_VISIBILITY")
    left = (await copy(klass, source)).json()["game_settings"]
    assert left.get("capacity") is None
    assert left["info_visibility"] == {"upstream": False, "downstream": False}


async def test_a_locked_source_gives_its_editable_settings_not_its_snapshot(klass):
    source = await new_session(klass)
    assert (await save(source, {"weeks": 30})).status_code == 200
    snapshot = {"settings": {**stored(source).model_dump(mode="json"), "weeks": 52}}
    execute(
        "UPDATE class_sessions SET locked_at = %s, snapshot = %s::jsonb WHERE id = %s",
        NOW,
        json.dumps(snapshot),
        source,
    )
    body = (await copy(klass, source)).json()
    assert body["game_settings"]["weeks"] == 30
    assert (body["locked"], row_of(body["id"])["locked_at"]) == (False, None)


async def test_copied_settings_the_engine_refuses_now_are_refused(klass):
    source = await new_session(klass)
    broken = stored(source).model_dump(mode="json")
    broken["order_delay"] = 99
    execute(
        "UPDATE class_sessions SET game_settings = %s::jsonb WHERE id = %s",
        json.dumps(broken),
        source,
    )
    status, code, fields = refusal(await copy(klass, source))
    assert (status, code) == (422, "invalid_settings")
    assert fields["order_delay"]["code"] == "out_of_range"
    assert len(rows("SELECT id FROM class_sessions")) == 1


async def test_an_archived_class_takes_no_copy_but_its_sessions_may_be_copied(klass):
    source = await new_session(klass)
    target = await second_class()
    execute("UPDATE classes SET archived_at = %s WHERE id = %s", NOW, klass)
    listed = (await sources(target)).json()["items"]
    assert [(item["id"], item["archived"]) for item in listed] == [(source, True)]
    assert (await copy(target, source)).status_code == 201
    refused = await copy(klass, source)
    assert (refused.status_code, refused.json()["error"]["code"]) == (409, "class_archived")


async def test_a_copy_forgets_a_source_that_is_gone(klass):
    source = await new_session(klass)
    new = (await copy(klass, source)).json()["id"]
    execute("DELETE FROM class_sessions WHERE id = %s", source)
    body = (await call(LECTURER, "GET", f"/api/class-sessions/{new}")).json()
    assert body["copied_from"] is None
    assert GameSettings.model_validate(body["game_settings"]) == stored(new)


async def test_the_source_is_named_only_to_readers_of_its_class(klass):
    source = await new_session(klass)
    target = await second_class()
    new = (await copy(target, source)).json()["id"]
    (other,) = rows("SELECT id FROM users WHERE email = %s", OTHER)[0]
    put_staff(target, other, "owner")
    body = (await call(OTHER, "GET", f"/api/class-sessions/{new}")).json()
    assert body["copied_from"] is None
    mine = (await call(LECTURER, "GET", f"/api/class-sessions/{new}")).json()
    assert mine["copied_from"]["id"] == source


async def test_a_copy_carries_the_engines_warnings_of_its_settings(klass):
    source = await new_session(klass)
    assert (await save(source, {"supply_line": 6})).status_code == 200
    body = (await copy(klass, source)).json()
    assert body["game_settings"]["supply_line"] == 6
    assert "supply_line_differs_from_demand" in {w["code"] for w in body["settings_warnings"]}
