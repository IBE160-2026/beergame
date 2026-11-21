"""The Start-date lock of a Class session (Story 5.11, FR-12, FR-13, FR-15, FR-78, AD-4, AD-8,
AD-9, AD-14, AD-17, AD-23): the sweep's `sessions.lock` freezes the snapshot once, a pin provider's
value lands in it, `lock` also locks early, and a missing provider key refuses the lock and tells
the owners and the Admins once. The api's clock is fixed and the sweep is handed its `now`; the
database clock is never read."""

import uuid
from datetime import timedelta

import pytest

from app.ai import config
from app.engine import RULES_VERSION, GameSettings
from app.engine.settings import demand_series
from app.modules.games.commands import default_runtime
from app.modules.games.schemas import SessionRuntime
from app.modules.identity.schemas import AccountRole
from app.modules.messaging import delivery
from app.modules.ops import sweep
from app.modules.sessions import service
from app.platform.db import get_sessionmaker
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_staff import ASSISTANT, call, put_staff
from tests.classes.test_student_registration import emitted
from tests.conftest import enter_production
from tests.messaging.helpers import mails, rows
from tests.sessions.test_ai_mode import two_levels
from tests.sessions.test_dates import PLAN, START, iso, new_session, refusal, save, student_of
from tests.sessions.test_lab_hours import sweep_at

__all__ = ["clock", "emitted", "klass", "two_levels"]

MINUTE = timedelta(minutes=1)
ADMIN = "admin@x.no"


@pytest.fixture(autouse=True)
def _empty(ai_db, mail_db, games_db):
    """No model config unless a test pins one, no notices and no Games."""


def locked(session_id: str) -> tuple:
    return rows("SELECT locked_at, snapshot FROM class_sessions WHERE id = %s", session_id)[0]


def notices() -> list[str]:
    return [key for (key,) in rows("SELECT dedupe_key FROM notices ORDER BY dedupe_key")]


async def dated(class_id: str, ai_mode: str = "rule_based") -> str:
    session_id = await new_session(class_id)
    assert (await save(session_id, PLAN, ai_mode)).status_code == 200
    return session_id


async def test_two_sweeps_over_a_due_session_lock_it_once(klass, emitted):
    session_id = await dated(klass)
    stored = rows("SELECT game_settings FROM class_sessions WHERE id = %s", session_id)[0][0]
    # Not due before the Start date; a session with no Start date never is.
    await new_session(klass)
    assert (await sweep.run(START - MINUTE))["sessions.lock"] == 0
    emitted.clear()
    first = await sweep.run(START + MINUTE)
    assert first["sessions.lock"] == 1
    assert (await sweep.run(START + 2 * MINUTE))["sessions.lock"] == 0
    assert emitted == [("session", session_id)]
    locked_at, snapshot = locked(session_id)
    assert locked_at == START + MINUTE
    settings = GameSettings.model_validate(stored)
    assert snapshot["settings"] == stored
    assert snapshot["settings"]["schema_version"] == settings.schema_version
    assert snapshot["demand_series"] == list(demand_series(settings))
    assert (snapshot["demand_seed"], snapshot["rules_version"]) == (
        settings.demand_seed,
        RULES_VERSION,
    )
    runtime = snapshot["session_runtime"]
    assert (runtime["ai_mode"], runtime["model_config_id"], runtime["effort_level"]) == (
        "rule_based",
        None,
        None,
    )
    assert (runtime["inactivity_limit_hours"], runtime["prompt_versions"], runtime["pins"]) == (
        24,
        None,
        {"starting_task": {"version": 1}},  # Story 6.3: the Starting task's pin
    )
    assert runtime["rule_based_params"] and runtime["play_guard_params"]
    body = (await call(LECTURER, "GET", f"/api/class-sessions/{session_id}")).json()
    assert body["locked"] is True
    assert body["locked_at"].startswith((START + MINUTE).isoformat()[:16])


async def test_the_sweeps_lock_judges_the_start_date_again_under_the_row_lock(klass):
    """Follow-up review: a Start date moved later after the finder listed the session (a worker
    clock ahead of the api's) is not locked at the old date; `lock` itself still locks early."""
    session_id = await dated(klass)
    assert await service.lock_due(uuid.UUID(session_id), START - MINUTE) is False
    assert locked(session_id) == (None, None)
    assert await service.lock_due(uuid.UUID(session_id), START + MINUTE) is True
    assert locked(session_id)[0] == START + MINUTE


async def test_llm_players_freeze_the_model_config_its_level_and_prompt_versions(klass, two_levels):
    session_id = await dated(klass, "llm")
    assert (await sweep.run(START + MINUTE))["sessions.lock"] == 1
    runtime = locked(session_id)[1]["session_runtime"]
    found = await config.get(two_levels)
    assert found is not None and found.referenced
    assert (runtime["ai_mode"], runtime["model_config_id"], runtime["effort_level"]) == (
        "llm",
        str(two_levels),
        "standard",
    )
    assert runtime["prompt_versions"] == dict(found.spec.prompts)


async def test_a_pin_provider_lands_in_the_snapshot_and_lock_also_locks_early(
    klass, monkeypatch, emitted
):
    seen: list[str] = []

    async def dummy(session, class_session):
        seen.append(str(class_session["id"]))
        return {"version": 3}

    monkeypatch.setattr(service, "_pin_providers", {})
    service.register_pin_provider("dummy", dummy)
    service.register_pin_provider("dummy", dummy)  # the same provider again changes nothing

    async def other(session, class_session):
        return None

    with pytest.raises(ValueError):
        service.register_pin_provider("dummy", other)
    session_id = await dated(klass)
    emitted.clear()
    # Before the Start date, as Epic 8's early start will.
    assert await service.lock(uuid.UUID(session_id), now=NOW) is True
    assert await service.lock(uuid.UUID(session_id), now=NOW + MINUTE) is False
    assert emitted == [("session", session_id)]
    assert seen == [session_id]
    locked_at, snapshot = locked(session_id)
    assert locked_at == NOW
    assert snapshot["session_runtime"]["pins"] == {"dummy": {"version": 3}}
    # Locked though the Start date is ahead: the frozen fields refuse, deadlines still move.
    response = await call(
        LECTURER,
        "PUT",
        f"/api/class-sessions/{session_id}",
        json={"ai_mode": "rule_based", "inactivity_limit_hours": 30},
    )
    assert refusal(response) == (409, "session_locked", {"inactivity_limit_hours": "locked"})
    later = {**PLAN, "test_deadline": PLAN["test_deadline"] + timedelta(days=1)}
    response = await call(
        LECTURER,
        "PUT",
        f"/api/class-sessions/{session_id}",
        json={"ai_mode": "rule_based", "dates": iso(later)},
    )
    assert response.status_code == 200
    assert response.json()["locked"] is True
    # The Startdato of a session locked before it does not move either.
    moved = {**PLAN, "start_at": PLAN["start_at"] + timedelta(days=1)}
    response = await call(
        LECTURER,
        "PUT",
        f"/api/class-sessions/{session_id}",
        json={"ai_mode": "rule_based", "dates": iso(moved)},
    )
    assert refusal(response) == (409, "session_locked", {"start_at": "locked"})
    assert (await sweep.run(START + MINUTE))["sessions.lock"] == 0


async def test_an_early_lock_ends_the_lecturer_homes_wait_for_an_allocation(klass):
    await student_of(klass)
    session_id = await dated(klass)

    async def waiting() -> list:
        body = (await call(LECTURER, "GET", "/api/lecturer-home/class-sessions")).json()
        return [s for c in body["waiting"] for s in c["sessions"]]

    assert await waiting() == [{"id": session_id, "number": 1, "lacks": ["allocation"]}]
    assert await service.lock(uuid.UUID(session_id), now=NOW) is True
    assert await waiting() == []


def test_the_snapshot_runtime_has_the_shape_of_a_games_runtime():
    """`build_snapshot` and a Game that freezes at creation share `games.SessionRuntime`."""
    runtime = default_runtime(model_config_id=None, effort_level=None)
    assert set(runtime.model_dump(mode="json")) == set(SessionRuntime.model_fields)


async def test_a_missing_provider_key_refuses_the_lock_and_tells_owners_and_admins_once(
    klass, two_levels, monkeypatch
):
    admin = await make(ADMIN, roles=(AccountRole.admin,))
    gone = await make("gammel-admin@x.no", roles=(AccountRole.admin,))
    execute("UPDATE users SET is_active = false WHERE id = %s", gone)
    put_staff(klass, await make(ASSISTANT), "assistant")
    owner = rows("SELECT id FROM users WHERE email = %s", LECTURER)[0][0]
    session_id = await dated(klass, "llm")
    # The provider's key is not set: the config may not answer here.
    may_answer = config.may_answer
    monkeypatch.setattr(config, "may_answer", lambda found: False)
    for minute in (1, 2):
        await sweep_at(START + minute * MINUTE)
        assert locked(session_id) == (None, None)
        expected = sorted(
            f"{service.LOCK_REFUSED_NOTICE}:{session_id}:{user}" for user in (owner, admin)
        )
        assert [k for k in notices() if k.startswith(service.LOCK_REFUSED_NOTICE)] == expected
    # Each told once, by mail at once: the owner and the active Admin, not the Assistant.
    sent = sorted(mails(), key=lambda m: m.to)
    assert [m.to for m in sent] == sorted([ADMIN, LECTURER])
    for mail in sent:
        assert mail.subject == "Klasseøkten kan ikke starte"
        assert "Klasseøkt 1 i Klassen class-of-1994 har nådd startdatoen" in mail.text
    assert service.LOCK_REFUSED_NOTICE == delivery.LOCK_REFUSED_KIND
    assert delivery.KINDS[delivery.LOCK_REFUSED_KIND].mode == delivery.IMMEDIATE
    # The Klasseøkt tells the refusal from a lock still waiting (GitHub issue 109); the first
    # refusal's time stands.
    body = (await call(LECTURER, "GET", f"/api/class-sessions/{session_id}")).json()
    assert (body["locked_at"], body["lock_refused"]) == (None, True)
    refused_at = rows("SELECT lock_refused_at FROM class_sessions WHERE id = %s", session_id)
    assert refused_at == [(START + MINUTE,)]
    # The key is set: the next sweep locks, and the mail of a notice still waiting is left out.
    monkeypatch.setattr(config, "may_answer", may_answer)
    assert (await sweep.run(START + 3 * MINUTE))["sessions.lock"] == 1
    assert locked(session_id)[0] == START + 3 * MINUTE
    async with get_sessionmaker().begin() as s:
        assert await service.lock_refused_mail_context(s, admin, uuid.UUID(session_id), NOW) is None
    body = (await call(LECTURER, "GET", f"/api/class-sessions/{session_id}")).json()
    assert body["lock_refused"] is False


async def test_in_production_the_mock_config_may_not_answer(two_levels, monkeypatch):
    found = await config.get(two_levels)
    assert found is not None and config.may_answer(found)
    enter_production(monkeypatch)
    assert not config.may_answer(found)


async def test_a_refused_lock_in_an_archived_class_tells_nobody(klass, two_levels, monkeypatch):
    session_id = await dated(klass, "llm")
    archived = await call(LECTURER, "POST", f"/api/classes/{klass}/archive")
    assert archived.status_code == 200
    monkeypatch.setattr(config, "may_answer", lambda found: False)
    await sweep.run(START + MINUTE)
    assert locked(session_id) == (None, None)
    assert notices() == []
    # Refused once, it is not tried again each minute while the Class is archived (GitHub issue
    # 109), only once the Class is restored.
    assert await service.due_locks(START + 2 * MINUTE) == []
    execute("UPDATE classes SET archived_at = NULL WHERE id = %s", klass)
    assert await service.due_locks(START + 2 * MINUTE) == [uuid.UUID(session_id)]


async def test_the_sweep_purges_expired_roster_uploads(klass):
    owner = rows("SELECT id FROM users WHERE email = %s", LECTURER)[0][0]
    execute(
        "INSERT INTO roster_uploads (id, class_id, uploaded_by, file_name, headers, has_header, "
        "column_count, row_count, created_at, expires_at) VALUES (gen_random_uuid(), %s, %s, "
        "'r.csv', '[]', false, 1, 0, %s, %s)",
        klass,
        owner,
        NOW,
        NOW + timedelta(hours=1),
    )
    done = await sweep.run(NOW)
    assert done["identity.purge_expired_roster_uploads"] == 1
    assert rows("SELECT count(*) FROM roster_uploads") == [(1,)]
    await sweep.run(NOW + timedelta(hours=2))
    assert rows("SELECT count(*) FROM roster_uploads") == [(0,)]
