"""The Admin pins and freezes a model for Class sessions (Story 15.5, FR-68, FR-78, FR-3, AD-4,
AD-6, AD-17). Through the api: «KI-kostnad» lists the model configs with their measurements as
stored, a pin before the Start date replaces a Class session's config and the Lecturer's
«Innsatsnivå» follows it, the lock freezes it, and a study freeze holds one config for the chosen
Class sessions and new ones until it is lifted. The api's clock is fixed; the database clock is
never compared with it."""

import uuid
from datetime import timedelta

import pytest

from app.ai import config, seed
from app.modules.identity.schemas import AccountRole
from app.modules.sessions import service
from tests.classes.test_classes import LECTURER, as_user, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import clock, klass
from tests.identity.helpers import CSRF, client
from tests.messaging.helpers import rows
from tests.sessions.test_ai_mode import two_levels
from tests.sessions.test_dates import START, at, new_session
from tests.sessions.test_lock import dated

__all__ = ["clock", "klass", "two_levels"]

ADMIN = "admin155@example.com"
BASE = "/api/admin/ai"
LEVEL = {"provider_params": {}, "attempt_timeout_s": 4, "order_time_budget_s": 8}


@pytest.fixture(autouse=True)
def _empty(ai_db, mail_db, games_db):
    """No model config unless a test adds one, no notices and no Games."""


@pytest.fixture
async def admin(klass) -> uuid.UUID:
    return await make(ADMIN, roles=(AccountRole.admin,))


async def call(method: str, path: str, who: str = ADMIN, **kwargs):
    async with client() as c:
        await as_user(c, who)
        return await c.request(method, f"{BASE}{path}", headers=CSRF, **kwargs)


async def stored(name: str, levels: list[str], measured: list[str]) -> uuid.UUID:
    """A mock config with these levels, the `measured` ones with a mock measurement."""
    row = await config.add(
        config.parse(
            {
                **seed.MOCK_SPEC,
                "name": name,
                "model_version": f"{name}-v1",
                "effort_levels": [{"name": level, **LEVEL} for level in levels],
            }
        )
    )
    for level in measured:
        await config.add_mock_measurement(row.id, level)
    return row.id


def measure(config_id: uuid.UUID, level: str, cost: str = "0.07250000") -> None:
    """A real measurement as Story 2.12's approval stores it; each later one is newer."""
    execute(
        "INSERT INTO effort_measurements (id, model_config_id, effort_level, batch_id, mock, "
        "games, cost_per_game_usd, time_per_order_median_s, time_per_order_p95_s, "
        "retries_per_order_mean, fallback_share, switched_share, pass_lines, approved_at) "
        "VALUES (%s, %s, %s, %s, false, 40, %s, 1.2, 3.4, 0.1, 0.0125, 0.025, '{}', "
        "clock_timestamp())",
        uuid.uuid7(),
        config_id,
        level,
        uuid.uuid7(),
        cost,
    )


async def pin(session_id: str, config_id: uuid.UUID, who: str = ADMIN):
    return await call(
        "PUT",
        f"/class-sessions/{session_id}/model-config",
        who,
        json={"model_config_id": str(config_id)},
    )


def setting(session_id: str) -> tuple:
    return rows(
        "SELECT ai_mode, model_config_id, effort_level FROM class_sessions WHERE id = %s",
        session_id,
    )[0]


def audited(action: str) -> list[tuple]:
    return rows(
        "SELECT target_ids, change FROM audit_events WHERE action = %s ORDER BY occurred_at, id",
        action,
    )


async def lecturer_levels(session_id: str) -> list[str]:
    async with client() as c:
        await as_user(c, LECTURER)
        body = (await c.get(f"/api/class-sessions/{session_id}")).json()
    return [level["name"] for level in body["effort_levels"]]


def refusal(response) -> tuple:
    return response.status_code, response.json()["error"]["code"]


async def test_the_page_lists_each_config_with_its_measurements_as_stored(admin, two_levels):
    measured = await stored("ekte", ["fast", "deep"], [])
    measure(measured, "fast", "0.09000000")
    measure(measured, "fast")  # the newer measurement is the one shown
    response = await call("GET", "/model-configs")
    assert response.status_code == 200
    by_name = {item["name"]: item for item in response.json()["items"]}
    item = by_name["ekte"]
    assert (item["provider"], item["endpoint"], item["region"], item["model_version"]) == (
        "mock",
        "mock://local",
        "local",
        "ekte-v1",
    )
    assert (item["pinnable"], item["active_default"], item["frozen"]) == (True, False, False)
    fast, deep = item["effort_levels"]
    assert fast["offered"] and fast["measurement"]["mock"] is False
    figures = {k: fast["measurement"][k] for k in ("games", "cost_per_game_usd", "fallback_share")}
    assert figures == {"games": 40, "cost_per_game_usd": "0.0725", "fallback_share": "0.0125"}
    assert fast["measurement"]["switched_share"] == "0.025"
    assert (deep["offered"], deep["measurement"]) == (False, None)
    default = by_name["mock-two"]
    assert default["active_default"] and default["effort_levels"][0]["measurement"]["mock"]
    # Only the Admin: a Lecturer is refused on every route before anything is read.
    for method, path in (
        ("GET", "/model-configs"),
        ("GET", "/class-sessions"),
        ("GET", "/freeze"),
        ("POST", "/freezes"),
        ("PUT", f"/class-sessions/{uuid.uuid7()}/model-config"),
        ("POST", f"/freezes/{uuid.uuid7()}/lift"),
    ):
        assert (await call(method, path, LECTURER, json={})).status_code == 403
    # A freeze names 1 to 50 Class sessions.
    for ids in ([], [str(uuid.uuid7()) for _ in range(51)]):
        body = {"model_config_id": str(measured), "class_session_ids": ids}
        assert (await call("POST", "/freezes", json=body)).status_code == 422


async def test_a_pin_before_the_start_date_replaces_the_config_and_its_levels(
    admin, klass, two_levels
):
    session_id = await dated(klass, "llm")
    assert setting(session_id) == ("llm", two_levels, "standard")
    async with client() as c:
        await as_user(c, LECTURER)
        saved = await c.put(
            f"/api/class-sessions/{session_id}",
            headers=CSRF,
            json={"ai_mode": "llm", "effort_level": "careful"},
        )
        assert saved.status_code == 200, saved.text
    other = await stored("andre", ["careful", "deep"], ["careful", "deep"])
    response = await pin(session_id, other)
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["model_config_id"], body["model_name"], body["effort_level"]) == (
        str(other),
        "andre",
        "careful",
    )
    assert body["warnings"] == [] and body["locked"] is False and body["frozen"] is None
    # The Level in force stays when offered; the Lecturer's «Innsatsnivå» offers the new config's.
    assert setting(session_id) == ("llm", other, "careful")
    assert await lecturer_levels(session_id) == ["careful", "deep"]
    assert (await config.get(other)).referenced
    # A config without the level in force: its first offered level.
    third = await stored("tredje", ["slow", "fast"], ["fast"])
    assert (await pin(session_id, third)).status_code == 200
    assert setting(session_id) == ("llm", third, "fast")
    assert await lecturer_levels(session_id) == ["fast"]
    # The same config again changes nothing and audits nothing.
    assert (await pin(session_id, third)).status_code == 200
    changes = [change for _, change in audited("model_config.pinned")]
    assert changes == [
        {"model_config_id": str(other), "previous_model_config_id": str(two_levels)},
        {"model_config_id": str(third), "previous_model_config_id": str(other)},
    ]
    assert rows(
        "SELECT count(*) FROM ai_budgets WHERE scope_kind = 'class_session' AND scope_id = %s",
        session_id,
    ) == [(1,)]
    async with client() as c:
        await as_user(c, ADMIN)
        logged = (await c.get("/api/admin/audit?action=model_config.pinned")).json()
    [target] = logged["items"][0]["targets"]
    assert target["key"] == "class_session_id" and target["label"].endswith("· Klasseøkt 1")
    # A Rule-based session keeps no level, and gets its budget row with the config.
    plain = await dated(klass)
    assert (await pin(plain, other)).status_code == 200
    assert setting(plain) == ("rule_based", other, None)
    assert rows("SELECT count(*) FROM ai_budgets WHERE scope_id = %s", plain) == [(1,)]


async def test_after_the_lock_the_config_is_frozen_and_shown_read_only(
    admin, klass, two_levels, monkeypatch
):
    other = await stored("andre", ["careful"], ["careful"])
    session_id = await dated(klass, "llm")
    assert (await pin(session_id, other)).status_code == 200
    assert await service.lock(uuid.UUID(session_id))
    [(snapshot,)] = rows("SELECT snapshot FROM class_sessions WHERE id = %s", session_id)
    assert snapshot["session_runtime"]["model_config_id"] == str(other)
    response = await pin(session_id, two_levels)
    assert refusal(response) == (409, "model_config_frozen")
    assert setting(session_id) == ("llm", other, "careful")
    [item] = [
        i for i in (await call("GET", "/class-sessions")).json()["items"] if i["id"] == session_id
    ]
    assert item["locked"] is True
    assert item["frozen"] == {
        "model_config_id": str(other),
        "model_name": "andre",
        "model_version": "andre-v1",
        "endpoint": "mock://local",
        "effort_level": "careful",
        "prompt_versions": seed.MOCK_SPEC["prompts"],
    }
    # A Start date that has passed freezes it too, before the sweep has locked it.
    waiting = await dated(klass, "llm")
    at(monkeypatch, START + timedelta(minutes=1))
    assert refusal(await pin(waiting, other)) == (409, "model_config_frozen")
    assert setting(waiting)[1] == two_levels
    assert len(audited("model_config.pinned")) == 1


async def test_an_unmeasured_or_unknown_config_or_session_is_refused(admin, klass, two_levels):
    session_id = await dated(klass, "llm")
    bare = await stored("umålt", ["standard"], [])
    assert refusal(await pin(session_id, bare)) == (409, "no_measured_level")
    assert refusal(await pin(session_id, uuid.uuid7())) == (404, "config_not_found")
    assert refusal(await pin(str(uuid.uuid7()), two_levels)) == (404, "not_found")
    assert setting(session_id)[1] == two_levels
    assert audited("model_config.pinned") == []


async def test_a_config_whose_provider_has_no_key_is_pinned_with_a_warning(
    admin, klass, two_levels, monkeypatch
):
    other = await stored("andre", ["careful"], ["careful"])
    session_id = await dated(klass, "llm")
    plain = await dated(klass)
    monkeypatch.setattr(config, "may_answer", lambda found: False)
    response = await pin(session_id, other)
    assert response.status_code == 200
    assert response.json()["warnings"] == ["provider_key_missing"]
    # Nothing is offered without the key, so the measured level is the one in force.
    assert setting(session_id) == ("llm", other, "careful")
    assert (await pin(plain, other)).json()["warnings"] == []
    listed = (await call("GET", "/model-configs")).json()["items"]
    assert {item["name"]: item["may_answer"] for item in listed} == {
        "mock-two": False,
        "andre": False,
    }


async def test_a_study_freeze_holds_one_config_until_it_is_lifted(admin, klass, two_levels):
    study = await stored("studie", ["careful"], ["careful"])
    other = await stored("andre", ["careful"], ["careful"])
    first = await dated(klass, "llm")
    second = await dated(klass)
    locked = await dated(klass, "llm")
    assert await service.lock(uuid.UUID(locked))
    draft = await new_session(klass)  # never saved: not listed, so never pinned or frozen
    listed = {i["id"] for i in (await call("GET", "/class-sessions")).json()["items"]}
    assert locked in listed and draft not in listed
    # A locked session with another config cannot join; nothing is stored.
    response = await call(
        "POST",
        "/freezes",
        json={"model_config_id": str(study), "class_session_ids": [first, locked]},
    )
    assert refusal(response) == (409, "model_config_frozen")
    assert response.json()["error"]["fields"] == {"class_session_ids": [locked]}
    assert (await call("GET", "/freeze")).json() == {"active": None}

    response = await call(
        "POST",
        "/freezes",
        json={"model_config_id": str(study), "class_session_ids": [first, second, first]},
    )
    assert response.status_code == 200, response.text
    active = response.json()["active"]
    assert (active["model_config_id"], active["class_session_ids"]) == (str(study), [first, second])
    assert setting(first) == ("llm", study, "careful")
    assert setting(second) == ("rule_based", study, None)
    [(target, change)] = audited("model_config.frozen")
    assert target == {"model_config_id": str(study)}
    assert change == {"freeze_id": active["id"], "class_session_ids": [first, second]}
    assert len(audited("model_config.pinned")) == 2
    listed = {i["id"]: i for i in (await call("GET", "/class-sessions")).json()["items"]}
    assert (listed[first]["in_freeze"], listed[locked]["in_freeze"]) == (True, False)
    assert {i["name"]: i["frozen"] for i in (await call("GET", "/model-configs")).json()["items"]}[
        "studie"
    ]

    # One freeze at a time; a study session cannot move to another config.
    again = await call(
        "POST", "/freezes", json={"model_config_id": str(other), "class_session_ids": [first]}
    )
    assert refusal(again) == (409, "freeze_active")
    assert refusal(await pin(first, other)) == (409, "study_frozen")
    assert (await pin(first, study)).status_code == 200
    # New Class sessions get the frozen config as their default.
    assert setting(await new_session(klass))[1] == study
    # An edit of the frozen config is a new row; the frozen one never changes.
    edited = await config.derive(study, prompts={"player_order": 1})
    assert edited.id != study and edited.derived_from == study
    assert (await config.get(study)).spec.name == "studie"

    lifted = await call("POST", f"/freezes/{active['id']}/lift")
    assert lifted.json() == {"active": None}
    assert [t for t, _ in audited("model_config.freeze_lifted")] == [
        {"model_config_id": str(study)}
    ]
    assert refusal(await call("POST", f"/freezes/{active['id']}/lift")) == (409, "freeze_lifted")
    assert refusal(await call("POST", f"/freezes/{uuid.uuid7()}/lift")) == (404, "not_found")
    async with client() as c:
        await as_user(c, ADMIN)
        for action in ("model_config.frozen", "model_config.freeze_lifted"):
            logged = (await c.get(f"/api/admin/audit?action={action}")).json()
            [target] = logged["items"][0]["targets"]
            assert (target["key"], target["label"]) == ("model_config_id", "studie · studie-v1")
    # After the lift: the newest pin is the default again, and study sessions keep their config.
    assert setting(await new_session(klass))[1] == two_levels
    assert setting(first)[1] == study
    assert (await pin(first, other)).status_code == 200


async def test_a_frozen_config_that_cannot_answer_here_gives_no_default(
    admin, klass, two_levels, monkeypatch
):
    study = await stored("studie", ["careful"], ["careful"])
    first = await dated(klass)
    response = await call(
        "POST", "/freezes", json={"model_config_id": str(study), "class_session_ids": [first]}
    )
    assert response.status_code == 200
    offered = config.offered_effort_levels

    async def nothing_for_study(config_id, *, session=None):
        if str(config_id) == str(study):
            return []
        return await offered(config_id, session=session)

    monkeypatch.setattr(config, "offered_effort_levels", nothing_for_study)
    # Never another model during the study: no default, so the new session is Rule-based.
    assert await config.active_default() is None
    assert setting(await new_session(klass))[:2] == ("rule_based", None)


async def test_a_freeze_takes_a_locked_session_only_when_it_holds_the_config(
    admin, klass, two_levels, monkeypatch
):
    study = await stored("studie", ["careful"], ["careful"])
    holding = await dated(klass, "llm")
    assert (await pin(holding, study)).status_code == 200
    assert await service.lock(uuid.UUID(holding))
    waiting = await dated(klass, "llm")  # holds the default, Start date about to pass
    at(monkeypatch, START + timedelta(minutes=1))
    listed = {i["id"]: i for i in (await call("GET", "/class-sessions")).json()["items"]}
    assert (listed[holding]["locked"], listed[waiting]["locked"]) == (True, True)
    response = await call(
        "POST",
        "/freezes",
        json={"model_config_id": str(study), "class_session_ids": [holding, waiting]},
    )
    assert refusal(response) == (409, "model_config_frozen")
    assert response.json()["error"]["fields"] == {"class_session_ids": [waiting]}
    response = await call(
        "POST", "/freezes", json={"model_config_id": str(study), "class_session_ids": [holding]}
    )
    assert response.status_code == 200
    assert response.json()["active"]["class_session_ids"] == [holding]
    # Locked, so nothing was written for it: only the pin made before the lock is audited.
    assert len(audited("model_config.pinned")) == 1


async def test_a_control_test_keeps_its_config_and_is_never_pinned(admin, klass, two_levels):
    """Story 12.7 after 15.5: a Control test checks the model config it was made with (a trigger
    refuses any change), so the Admin's pin and a study freeze refuse it as frozen, not as a 500,
    and the list shows it read-only."""
    import psycopg

    from tests.conftest import TEST_DATABASE_URL, libpq_dsn

    other = await stored("andre", ["careful"], ["careful"])
    session_id = await dated(klass, "llm")
    # Made as a course session, turned into a Control test (the kind never changes in the app).
    with psycopg.connect(libpq_dsn(TEST_DATABASE_URL)) as conn:
        conn.execute("SET LOCAL session_replication_role = replica")
        conn.execute("UPDATE class_sessions SET kind = 'control_test' WHERE id = %s", (session_id,))
    assert refusal(await pin(session_id, other)) == (409, "model_config_frozen")
    frozen = await call(
        "POST", "/freezes", json={"model_config_id": str(other), "class_session_ids": [session_id]}
    )
    assert refusal(frozen) == (409, "model_config_frozen")
    assert setting(session_id)[1] == two_levels
    [item] = [
        i for i in (await call("GET", "/class-sessions")).json()["items"] if i["id"] == session_id
    ]
    assert item["locked"] is True
    assert audited("model_config.pinned") == []
