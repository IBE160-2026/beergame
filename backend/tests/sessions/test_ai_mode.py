"""Choosing AI mode, Effort level and Debrief mode of a Class session (Story 5.5, FR-15, FR-16,
FR-33, FR-78, AD-17): saved with «Lagre Klasseøkt»; the levels, their default and their effect
lines are the model config's, the descriptions `players.service.describe`'s; nothing changes
once locked. The api's clock is fixed; the database clock is never read."""

import uuid

import psycopg
import pytest

from app.ai import config, seed
from app.modules.players import service as players
from tests.ai.test_effort import figures
from tests.classes.test_classes import LECTURER
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import clock, klass
from tests.classes.test_staff import call
from tests.conftest import enter_production
from tests.messaging.helpers import rows
from tests.sessions.test_dates import DAY, PLAN, START, at, iso, refusal

__all__ = ["clock", "klass"]

TWO_LEVELS = [
    {
        "name": "standard",
        "attempt_timeout_s": 4,
        "order_time_budget_s": 8,
        "label": "Standard",
        "effect": "Raskest og billigst.",
    },
    {
        "name": "careful",
        "attempt_timeout_s": 8,
        "order_time_budget_s": 16,
        "label": "Grundig",
        "effect": "Tenker lenger: tregere og dyrere.",
    },
    # Never measured, so never offered.
    {"name": "unmeasured", "attempt_timeout_s": 4, "order_time_budget_s": 8},
]


@pytest.fixture(autouse=True)
def _empty_ai(ai_db):
    """No model config, pin or budget: each test says whether a default is active."""


@pytest.fixture
async def two_levels() -> uuid.UUID:
    """A mock config whose first two levels are measured, pinned as the active default."""
    row = await config.add(
        config.parse({**seed.MOCK_SPEC, "name": "mock-two", "effort_levels": TWO_LEVELS})
    )
    for level in ("standard", "careful"):
        await config.add_mock_measurement(row.id, level)
    await config.pin(row.id)
    return row.id


async def create(class_id: str) -> dict:
    response = await call(LECTURER, "POST", f"/api/classes/{class_id}/class-sessions")
    assert response.status_code == 201
    return response.json()


async def save(session_id: str, ai_mode: str, **body):
    return await call(
        LECTURER, "PUT", f"/api/class-sessions/{session_id}", json={"ai_mode": ai_mode, **body}
    )


async def read(session_id: str) -> dict:
    return (await call(LECTURER, "GET", f"/api/class-sessions/{session_id}")).json()


def stored(session_id: str) -> tuple:
    return rows(
        "SELECT ai_mode, effort_level, debrief_mode FROM class_sessions WHERE id = %s", session_id
    )[0]


async def test_a_new_session_takes_the_default_level_and_offers_the_measured_ones(
    klass, two_levels
):
    body = await create(klass)
    assert (body["ai_mode"], body["effort_level"]) == ("llm", "standard")
    assert body["effort_levels"] == [
        {
            "name": "standard",
            "label": "Standard",
            "effect": "Raskest og billigst.",
            "default": True,
            "time_per_order_median_s": None,
            "cost_per_game_usd": None,
        },
        {
            "name": "careful",
            "label": "Grundig",
            "effect": "Tenker lenger: tregere og dyrere.",
            "default": False,
            "time_per_order_median_s": None,
            "cost_per_game_usd": None,
        },
    ]
    assert body["provider_unavailable"] is False
    assert stored(body["id"]) == ("llm", "standard", "group")


async def test_another_offered_level_is_stored_and_one_not_offered_is_refused(klass, two_levels):
    session_id = (await create(klass))["id"]
    response = await save(session_id, "llm", effort_level="careful")
    assert response.status_code == 200
    assert response.json()["effort_level"] == "careful"
    assert stored(session_id) == ("llm", "careful", "group")
    for wrong in ("turbo", "unmeasured"):
        refused = await save(session_id, "llm", effort_level=wrong, debrief_mode="personal")
        assert refusal(refused) == (422, "invalid_effort_level", {"effort_level": "not_offered"})
        assert stored(session_id) == ("llm", "careful", "group")
    # Left out, the level in force stays.
    assert (await save(session_id, "llm")).json()["effort_level"] == "careful"


async def test_rule_based_players_have_no_level_and_llm_again_takes_the_default(klass, two_levels):
    session_id = (await create(klass))["id"]
    assert (await save(session_id, "llm", effort_level="careful")).status_code == 200
    response = await save(session_id, "rule_based", effort_level="careful")
    assert response.status_code == 200
    assert (response.json()["ai_mode"], response.json()["effort_level"]) == ("rule_based", None)
    # The offered levels are still listed, for the screen to show once LLM is chosen again.
    assert [level["name"] for level in response.json()["effort_levels"]] == [
        "standard",
        "careful",
    ]
    assert stored(session_id) == ("rule_based", None, "group")
    assert (await save(session_id, "llm")).json()["effort_level"] == "standard"
    assert stored(session_id) == ("llm", "standard", "group")


async def test_with_no_default_model_nothing_is_offered_and_llm_is_refused(klass):
    body = await create(klass)
    assert (body["llm_unavailable"], body["effort_level"], body["effort_levels"]) == (
        "no_default_model",
        None,
        [],
    )
    refused = await save(body["id"], "llm", effort_level="standard")
    assert refusal(refused)[:2] == (409, "llm_unavailable")
    assert stored(body["id"]) == ("rule_based", None, "group")


async def test_a_rule_based_session_takes_the_new_default_and_its_level(klass):
    session_id = (await create(klass))["id"]
    await seed.ensure_zero_config()
    offered = (await read(session_id))["effort_levels"]
    assert [(level["name"], level["label"]) for level in offered] == [("standard", "Standard")]
    assert offered[0]["effect"] == seed.MOCK_SPEC["effort_levels"][0]["effect"]
    response = await save(session_id, "llm")
    assert (response.status_code, response.json()["effort_level"]) == (200, "standard")


async def test_the_debrief_mode_is_stored_and_kept_when_left_out(klass):
    session_id = (await create(klass))["id"]
    response = await save(session_id, "rule_based", debrief_mode="personal")
    assert (response.status_code, response.json()["debrief_mode"]) == (200, "personal")
    assert (await save(session_id, "rule_based")).json()["debrief_mode"] == "personal"
    assert stored(session_id) == ("rule_based", None, "personal")
    refused = await save(session_id, "rule_based", debrief_mode="solo")
    assert refusal(refused)[:2] == (422, "invalid_request")


async def test_once_locked_no_choice_changes_but_the_same_values_save(
    klass, two_levels, monkeypatch
):
    session_id = (await create(klass))["id"]
    assert (await save(session_id, "llm", dates=iso(PLAN))).status_code == 200
    at(monkeypatch, START + DAY)
    for body, field in (
        ({"ai_mode": "rule_based"}, "ai_mode"),
        ({"ai_mode": "llm", "effort_level": "careful"}, "effort_level"),
        ({"ai_mode": "llm", "debrief_mode": "personal"}, "debrief_mode"),
    ):
        refused = await call(LECTURER, "PUT", f"/api/class-sessions/{session_id}", json=body)
        assert refusal(refused) == (409, "session_locked", {field: "locked"})
    refused = await save(session_id, "rule_based", debrief_mode="personal")
    assert refusal(refused) == (
        409,
        "session_locked",
        {"ai_mode": "locked", "debrief_mode": "locked"},
    )
    assert stored(session_id) == ("llm", "standard", "group")
    response = await save(session_id, "llm", effort_level="standard", debrief_mode="group")
    assert response.status_code == 200


async def test_an_llm_row_stored_before_the_level_reads_and_saves_the_default(
    klass, two_levels, monkeypatch
):
    session_id = (await create(klass))["id"]
    assert (await save(session_id, "llm", dates=iso(PLAN))).status_code == 200
    execute("UPDATE class_sessions SET effort_level = NULL WHERE id = %s", session_id)
    assert (await read(session_id))["effort_level"] == "standard"
    at(monkeypatch, START + DAY)
    # Once locked, the default it reads is no change.
    response = await save(session_id, "llm", effort_level="standard")
    assert (response.status_code, response.json()["effort_level"]) == (200, "standard")


async def test_the_database_keeps_a_level_off_rule_based_rows(klass):
    session_id = (await create(klass))["id"]
    with pytest.raises(psycopg.errors.CheckViolation):
        execute("UPDATE class_sessions SET effort_level = 'standard' WHERE id = %s", session_id)


async def test_a_session_whose_provider_offers_nothing_here_is_flagged(
    klass, two_levels, monkeypatch
):
    session_id = (await create(klass))["id"]
    assert (await read(session_id))["provider_unavailable"] is False
    # In production the mock config offers no level: the stand-in for a provider with no key.
    enter_production(monkeypatch)
    body = await read(session_id)
    assert (body["provider_unavailable"], body["effort_levels"]) == (True, [])
    assert body["effort_level"] == "standard"
    # A Rule-based session is never flagged.
    assert (await save(session_id, "rule_based")).json()["provider_unavailable"] is False


async def test_measured_figures_come_with_the_level(klass):
    data = {
        **seed.MOCK_SPEC,
        "name": "real",
        "provider": "openai_compatible",
        "endpoint": "https://example.invalid/v1",
        "credential_env": "NO_SUCH_KEY",
    }
    row = await config.add(config.parse(data))
    await config.approve_effort(row.id, "standard", uuid.uuid4(), figures(str(row.id)))
    await config.pin(row.id)
    (level,) = (await create(klass))["effort_levels"]
    assert (level["time_per_order_median_s"], level["cost_per_game_usd"]) == ("1.2", "0.04")


async def test_the_descriptions_are_the_players_modules(klass):
    body = await create(klass)
    assert body["ai_descriptions"] == {
        "llm": players.describe("llm").text,
        "rule_based": players.describe("rule_based").text,
    }
