"""Creating, reading and saving a Class session (Story 5.1, FR-5, FR-6, FR-11, FR-13, FR-15, AD-4,
AD-6, AD-8, AD-12): the Classic defaults with a server-drawn seed, the model config and budget row
in the same transaction or Rule-based players when no default is pinned, the one archive guard,
and who may do what. The api's clock is fixed; the database clock is never read."""

import uuid

import pytest
import structlog.testing

from app.ai import seed
from app.engine import GameSettings
from app.engine.demand import SEED_MAX
from app.modules.sessions import service
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_classes import LECTURER
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_staff import EMAIL, MANAGERS, READERS, ROLES, call, shared
from tests.classes.test_student_registration import emitted
from tests.messaging.helpers import rows

__all__ = ["clock", "emitted", "klass", "shared"]


@pytest.fixture(autouse=True)
def _empty_ai(ai_db):
    """No model config, pin or budget: each test says whether a default is active."""


@pytest.fixture
async def default_model() -> uuid.UUID:
    """The seeded mock config, pinned as the active default (AD-17)."""
    return uuid.UUID(await seed.ensure_zero_config())


async def create(class_id: str, email: str = LECTURER):
    return await call(email, "POST", f"/api/classes/{class_id}/class-sessions")


async def save(session_id: str, ai_mode: str, email: str = LECTURER):
    return await call(email, "PUT", f"/api/class-sessions/{session_id}", json={"ai_mode": ai_mode})


def stored() -> list[tuple]:
    return rows(
        "SELECT class_id, ai_mode, debrief_mode, inactivity_limit_hours, obligatory, "
        "model_config_id, created_at, saved_at FROM class_sessions"
    )


def budgets() -> list[tuple]:
    return rows("SELECT scope_id FROM ai_budgets WHERE scope_kind = 'class_session'")


def archive(class_id: str) -> None:
    execute("UPDATE classes SET archived_at = %s WHERE id = %s", NOW, class_id)


async def test_a_new_class_session_holds_the_classic_defaults_the_default_model_and_a_budget(
    klass, default_model, emitted
):
    with structlog.testing.capture_logs() as logs:
        response = await create(klass)
    assert response.status_code == 201
    body = response.json()
    session_id = uuid.UUID(body["id"])
    assert stored() == [(uuid.UUID(klass), "llm", "group", 24, False, default_model, NOW, None)]
    assert budgets() == [(session_id,)]
    assert emitted == [("session", str(session_id))]
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["sessions.create"]
    # The engine's Classic preset, with a seed drawn by the server: no second copy of a value.
    (settings,) = rows("SELECT game_settings FROM class_sessions")[0]
    seed_value = settings["demand_seed"]
    assert isinstance(seed_value, int) and 0 <= seed_value <= SEED_MAX
    assert GameSettings.model_validate(settings) == GameSettings(demand_seed=seed_value)
    assert settings["schema_version"] == 1
    assert (settings["starting_inventory"], settings["supply_line"], settings["weeks"]) == (
        12,
        4,
        36,
    )
    assert (body["class_name"], body["is_classic"], body["llm_unavailable"]) == (
        "class-of-1994",
        True,
        None,
    )
    assert (body["ai_mode"], body["debrief_mode"], body["can_manage"]) == ("llm", "group", True)
    assert body["game_settings"]["holding_cost"] == "0.50"
    created = next(e for e in logs if e["event"] == "class_session_created")
    assert set(created) == {"event", "log_level", "class_session_id", "class_id", "model_config_id"}


async def test_two_class_sessions_draw_their_own_seeds_and_list_newest_first(klass, default_model):
    listed = await call(LECTURER, "GET", f"/api/classes/{klass}/class-sessions")
    assert (listed.status_code, listed.json()["items"]) == (200, [])
    first = (await create(klass)).json()
    second = (await create(klass)).json()
    assert first["game_settings"]["demand_seed"] != second["game_settings"]["demand_seed"]
    listed = await call(LECTURER, "GET", f"/api/classes/{klass}/class-sessions")
    assert [i["id"] for i in listed.json()["items"]] == [second["id"], first["id"]]


@pytest.mark.parametrize("body", [{}, {"ai_mode": "human"}, {"ai_mode": "llm", "obligatory": True}])
async def test_a_save_body_that_is_not_valid_is_refused_and_changes_nothing(
    klass, default_model, body
):
    session_id = (await create(klass)).json()["id"]
    response = await call(LECTURER, "PUT", f"/api/class-sessions/{session_id}", json=body)
    assert (response.status_code, response.json()["error"]["code"]) == (422, "invalid_request")
    assert stored()[0][7] is None


async def test_with_no_default_model_it_gets_rule_based_players_no_config_and_no_budget(klass):
    response = await create(klass)
    assert response.status_code == 201
    body = response.json()
    assert (body["ai_mode"], body["llm_unavailable"]) == ("rule_based", "no_default_model")
    assert stored()[0][1:6] == ("rule_based", "group", 24, False, None)
    assert budgets() == []
    # Saving as it stands works; LLM players are refused with a stable code, and nothing changes.
    assert (await save(body["id"], "rule_based")).status_code == 200
    refused = await save(body["id"], "llm")
    assert (refused.status_code, refused.json()["error"]["code"]) == (409, "llm_unavailable")
    assert stored()[0][1] == "rule_based" and stored()[0][5] is None
    assert budgets() == []


async def test_saving_llm_players_once_a_default_exists_attaches_it_and_its_budget(klass):
    session_id = (await create(klass)).json()["id"]
    config_id = uuid.UUID(await seed.ensure_zero_config())
    response = await save(session_id, "llm")
    assert response.status_code == 200
    assert (response.json()["ai_mode"], response.json()["llm_unavailable"]) == ("llm", None)
    assert stored()[0][1] == "llm" and stored()[0][5] == config_id
    assert budgets() == [(uuid.UUID(session_id),)]


async def test_saving_unchanged_stamps_it_and_tells_the_staff(klass, default_model, emitted):
    session_id = (await create(klass)).json()["id"]
    before = rows("SELECT game_settings FROM class_sessions")
    emitted.clear()
    response = await save(session_id, "llm")
    assert response.status_code == 200
    assert response.json()["saved_at"] is not None
    assert stored()[0][7] == NOW
    assert rows("SELECT game_settings FROM class_sessions") == before
    # No date changed, so no Student is told (Story 5.2 adds `user` for a date change).
    assert emitted == [("session", session_id)]
    assert {topic for topic, _ in emitted} <= COMMAND_TOPICS["sessions.save"]
    listed = await call(LECTURER, "GET", f"/api/classes/{klass}/class-sessions")
    assert [(i["id"], i["saved_at"] is not None) for i in listed.json()["items"]] == [
        (session_id, True)
    ]


async def test_an_archived_class_takes_no_new_or_saved_class_session(klass, default_model):
    session_id = (await create(klass)).json()["id"]
    archive(klass)
    refused = await create(klass)
    assert (refused.status_code, refused.json()["error"]["code"]) == (409, "class_archived")
    refused = await save(session_id, "llm")
    assert (refused.status_code, refused.json()["error"]["code"]) == (409, "class_archived")
    assert len(stored()) == 1 and stored()[0][7] is None
    read = await call(LECTURER, "GET", f"/api/class-sessions/{session_id}")
    assert (read.status_code, read.json()["can_manage"]) == (200, False)


@pytest.mark.parametrize("role", ROLES)
async def test_each_role_reaches_exactly_its_class_session_routes(shared, default_model, role):
    session_id = (await create(shared)).json()["id"]
    email = EMAIL[role]
    created = await create(shared, email)
    read = await call(email, "GET", f"/api/class-sessions/{session_id}")
    listed = await call(email, "GET", f"/api/classes/{shared}/class-sessions")
    saved = await save(session_id, "llm", email)
    manager, reader = role in MANAGERS, role in READERS
    assert created.status_code == (201 if manager else 403)
    assert saved.status_code == (200 if manager else 403)
    assert (read.status_code, listed.status_code) == ((200, 200) if reader else (403, 403))
    if reader:
        assert read.json()["can_manage"] is manager
    assert len(stored()) == (2 if manager else 1)


async def test_an_id_that_names_nothing_is_refused_like_any_other(klass, default_model):
    nobody = str(uuid.uuid4())
    for method, path in [
        ("GET", "/api/class-sessions/not-an-id"),
        ("GET", f"/api/class-sessions/{nobody}"),
        ("POST", f"/api/classes/{nobody}/class-sessions"),
        ("POST", "/api/classes/not-an-id/class-sessions"),
    ]:
        response = await call(LECTURER, method, path)
        assert response.status_code == 403, path
    assert (await save(nobody, "llm")).status_code == 403
    assert stored() == []


def test_is_classic_ignores_the_seed_and_sees_any_other_change():
    assert service.is_classic(GameSettings(demand_seed=7))
    assert not service.is_classic(GameSettings(demand_seed=7, weeks=30))
