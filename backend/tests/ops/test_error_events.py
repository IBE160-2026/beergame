"""The Admin sees errors, fallback and response times per Class session (Story 15.8, NFR-8,
FR-29, FR-79, NFR-9, AD-12, AD-14, AD-15).

`error_events` is written only through `ops.service.record_error`, from three sources: the
sweep's finished-game check (a Class game, a played-out one, a Replay), a job that fails for good
(the worker middleware), and an api answer of 5xx (the request log middleware). A failure to count
never fails the caller. «Drift» reads the counts with the fallback, the response times, the Play
guard share and the AI cost of one Class session, counts and timings only. Times are passed in;
the database clock is never compared with them."""

import uuid
from datetime import timedelta

import httpx
import pytest
from fastapi import FastAPI
from structlog.testing import capture_logs

from app.ai import config, seed
from app.main import create_app
from app.modules.identity.personal_data import REGISTRY
from app.modules.identity.schemas import AccountRole
from app.modules.ops import service, sweep
from app.platform import jobs
from app.platform.db import get_sessionmaker
from app.platform.logging import RequestLogMiddleware
from tests.classes.test_classes import LECTURER, as_user, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.conftest import TEST_DATABASE_URL, empty
from tests.games.helpers import classic_game, tamper
from tests.identity.helpers import CSRF, client
from tests.messaging.helpers import rows
from tests.sessions.test_dates import new_session, save

__all__ = ["clock", "klass"]

ADMIN = "admin158@example.com"
BOOM_TASK = "tests.ops.boom"


@jobs.app.task(name=BOOM_TASK, queue=jobs.LLM_BATCH)
async def boom(game_id: str) -> None:
    raise RuntimeError(f"failed for {game_id}")  # a message no row may keep


@pytest.fixture(autouse=True)
def _empty(games_db, ai_db, test_database):
    empty(test_database, "error_events")


def events() -> list[tuple]:
    return rows(
        "SELECT source, code, class_session_id, request_id FROM error_events ORDER BY occurred_at"
    )


async def test_record_error_stores_ids_and_codes_and_never_raises(monkeypatch):
    session_id = uuid.uuid7()
    assert await service.record_error("api_error", "http_500", session_id, "req-1", at=NOW)
    assert events() == [("api_error", "http_500", session_id, "req-1")]
    with capture_logs() as logs:
        assert not await service.record_error("other", "http_500")  # not a source
        assert not await service.record_error("api_error", "Ola Nordmann failed")  # free text

        def down():
            raise ConnectionError("database down")

        monkeypatch.setattr(service, "get_sessionmaker", down)
        assert not await service.record_error("api_error", "http_500", session_id)
    assert len(events()) == 1
    assert [(e["event"], e["exc_type"]) for e in logs] == [
        ("error_record_failed", "ValueError"),
        ("error_record_failed", "ValueError"),
        ("error_record_failed", "ConnectionError"),
    ]


async def _violating_game(session_id: uuid.UUID, purpose: str, played_out: bool = False) -> str:
    """A finished Game of `purpose` in the Class session whose stored Week 10 was changed after
    the fact, so its check fails."""
    game_id = await classic_game(TEST_DATABASE_URL)
    tamper(
        TEST_DATABASE_URL,
        "UPDATE games SET purpose = %s, class_session_id = %s, "
        "played_out_at = CASE WHEN %s THEN created_at END WHERE id = %s",
        (purpose, session_id, played_out, game_id),
    )
    tamper(
        TEST_DATABASE_URL,
        "UPDATE game_weeks SET state = jsonb_set(state, '{seats,0,inventory}', "
        "to_jsonb((state #>> '{seats,0,inventory}')::int + 1)) "
        "WHERE game_id = %s AND week = 10 AND NOT finished",
        (game_id,),
    )
    return game_id


async def test_a_violation_counts_once_under_its_class_session_for_each_kind_of_game():
    session_id = uuid.uuid7()
    made = [
        await _violating_game(session_id, "class"),
        await _violating_game(session_id, "class", played_out=True),
        await _violating_game(session_id, "replay"),
    ]
    clean = await classic_game(TEST_DATABASE_URL)
    for game_id in [*made, clean]:
        await sweep._verify_finished(game_id, NOW)
    assert events() == [("conservation_check", "game_check_failed", session_id, None)] * 3
    # The sweep finds each Game once; called again the stored check counts nothing new.
    assert (await sweep.run(NOW + timedelta(minutes=1)))["games.verify_finished"] == 0
    assert len(events()) == 3


async def test_a_job_that_fails_for_good_counts_under_the_session_of_its_game():
    session_id = uuid.uuid7()
    game_id = await classic_game(TEST_DATABASE_URL)
    tamper(
        TEST_DATABASE_URL,
        "UPDATE games SET class_session_id = %s WHERE id = %s",
        (session_id, game_id),
    )
    async with get_sessionmaker().begin() as s:
        await jobs.defer(s, BOOM_TASK, queue=jobs.LLM_BATCH, queueing_lock="b1", game_id=game_id)
        await jobs.defer(
            s, BOOM_TASK, queue=jobs.LLM_BATCH, queueing_lock="b2", game_id=str(uuid.uuid7())
        )
    await jobs.run_until_idle([jobs.LLM_BATCH], on_failure=service.record_job_failure)
    found = rows(
        "SELECT source, code, class_session_id FROM error_events ORDER BY class_session_id"
    )
    assert sorted(found, key=str) == sorted(
        [("job_failed", BOOM_TASK, session_id), ("job_failed", BOOM_TASK, None)], key=str
    )
    job_ids = {r for (r,) in rows("SELECT request_id FROM error_events")}
    failed = {str(j) for (j,) in rows("SELECT id FROM procrastinate_jobs WHERE status = 'failed'")}
    assert job_ids == failed and len(failed) == 2  # the jobs still failed
    assert "failed for" not in str(rows("SELECT * FROM error_events"))


async def test_a_failing_hook_leaves_the_job_failed():
    async def broken(*args):
        raise RuntimeError("hook down")

    async with get_sessionmaker().begin() as s:
        await jobs.defer(
            s, BOOM_TASK, queue=jobs.LLM_BATCH, queueing_lock="b3", game_id=str(uuid.uuid7())
        )
    with capture_logs() as logs:
        await jobs.run_until_idle([jobs.LLM_BATCH], on_failure=broken)
    assert [e["exc_type"] for e in logs if e["event"] == "job_failure_hook_failed"] == [
        "RuntimeError"
    ]
    assert rows("SELECT status FROM procrastinate_jobs") == [("failed",)]


def _boom_app(hook) -> FastAPI:
    app = FastAPI()

    @app.get("/x/class-sessions/{class_session_id}")
    async def fail(class_session_id: str):
        raise RuntimeError("boom")

    @app.get("/x/sessions/{session_id}")
    async def fail_session(session_id: str):
        raise RuntimeError("boom")

    @app.get("/x/games/{game_id}")
    async def fail_game(game_id: str):
        raise RuntimeError("boom")

    @app.get("/x/ok")
    async def ok():
        return {}

    app.add_middleware(RequestLogMiddleware, on_server_error=hook)
    return app


async def test_a_5xx_answer_counts_under_the_session_its_path_names():
    session_id, other = uuid.uuid7(), uuid.uuid7()
    game_id = await classic_game(TEST_DATABASE_URL)
    tamper(
        TEST_DATABASE_URL,
        "UPDATE games SET class_session_id = %s WHERE id = %s",
        (other, game_id),
    )
    app = _boom_app(service.record_api_error)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        failed = await c.get(f"/x/class-sessions/{session_id}")
        no_uuid = await c.get("/x/class-sessions/not-a-uuid")
        by_name = await c.get(f"/x/sessions/{session_id}")
        by_game = await c.get(f"/x/games/{game_id}")
        fine = await c.get("/x/ok")
    assert [r.status_code for r in (failed, no_uuid, by_name, by_game, fine)] == [500] * 4 + [200]
    found = events()
    assert [(s, code, sid) for s, code, sid, _ in found] == [
        ("api_error", "http_500", session_id),
        ("api_error", "http_500", None),
        ("api_error", "http_500", session_id),
        ("api_error", "http_500", other),
    ]
    assert all(uuid.UUID(request_id) for *_, request_id in found)  # the request log's id


async def test_a_failing_5xx_hook_changes_nothing_and_the_app_counts_through_ops():
    async def broken(*args):
        raise RuntimeError("hook down")

    transport = httpx.ASGITransport(app=_boom_app(broken), raise_app_exceptions=False)
    with capture_logs() as logs:
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
            assert (await c.get(f"/x/class-sessions/{uuid.uuid7()}")).status_code == 500
    # Beside the error tracker's mock line (Story 15.11), the hook's failure by type only.
    assert [e["event"] for e in logs if e.get("exc_type") == "RuntimeError"] == [
        "[errors:mock]",
        "server_error_hook_failed",
    ]
    # The app factory hands the request log the hook of `ops.service` (platform imports no module).
    [middleware] = [m for m in create_app().user_middleware if m.cls is RequestLogMiddleware]
    assert middleware.kwargs == {"on_server_error": service.record_api_error}


def test_error_events_are_kept_at_retention_and_hold_no_personal_data():
    entry = REGISTRY["error_events"]
    assert entry.handling == "none" and "Kept at retention" in entry.note


@pytest.fixture
async def admin(klass) -> uuid.UUID:
    return await make(ADMIN, roles=(AccountRole.admin,))


async def get(path: str, who: str = ADMIN):
    async with client() as c:
        await as_user(c, who)
        return await c.get(path, headers=CSRF)


def _call(scope, purpose, level, latency, usd, model) -> None:
    execute(
        "INSERT INTO llm_call (id, purpose, scope_kind, scope_id, caller_ref, model_config_id, "
        "provider, endpoint, model_version, quantisation, effort_level, prompt_version, attempt, "
        "input_tokens, output_tokens, reasoning_tokens, cost_usd, latency_ms, outcome, request, "
        "started_at) VALUES (%s, %s, 'class_session', %s, '{}', %s, 'mock', 'mock', 'mock-v1', "
        "'none', %s, 1, 1, 10, 5, 0, %s, %s, 'ok', '{}', %s)",
        uuid.uuid7(),
        purpose,
        str(scope),
        model,
        level,
        usd,
        latency,
        NOW,
    )


async def _llm_game(session_id: str, purpose: str) -> str:
    """A finished Game in the session whose Fabrikk and Distributør were LLM players from the
    start: the Detaljist's Orders of Weeks 1–9 by the LLM, two replaced on a timeout and one on a
    provider error; the Play guard switched the Detaljist (Week 10), and a guard row on a Seat that
    was never an LLM player's counts for nothing."""
    game_id = await classic_game(TEST_DATABASE_URL)
    seats = dict(
        rows("SELECT role, id FROM seats WHERE game_id = %s", game_id)  # role -> seat id
    )
    sql = [
        (
            "UPDATE games SET purpose = %s, class_session_id = %s WHERE id = %s",
            (purpose, session_id, game_id),
        ),
        (
            "UPDATE seat_occupancy SET occupant_kind = 'llm' WHERE seat_id = ANY(%s)",
            ([seats["retailer"], seats["wholesaler"]],),
        ),
        (
            "UPDATE seat_weeks SET occupant_kind = 'llm', decided_by = 'llm' "
            "WHERE seat_id = %s AND week <= 9",
            (seats["retailer"],),
        ),
        (
            "UPDATE seat_weeks SET fallback = 'timeout', decided_by = 'rule_based' "
            "WHERE seat_id = %s AND week IN (2, 3)",
            (seats["retailer"],),
        ),
        (
            "UPDATE seat_weeks SET fallback = 'provider_error', decided_by = 'rule_based' "
            "WHERE seat_id = %s AND week = 4",
            (seats["retailer"],),
        ),
    ]
    for statement, params in sql:
        tamper(TEST_DATABASE_URL, statement, params)
    for role in ("retailer", "distributor"):
        tamper(
            TEST_DATABASE_URL,
            "INSERT INTO seat_occupancy (id, seat_id, from_week, occupant_kind, policy_id, reason) "
            "VALUES (%s, %s, 10, 'rule_based', 'sterman', 'guard_switch')",
            (uuid.uuid7(), seats[role]),
        )
    return game_id


async def test_the_view_shows_errors_fallback_times_guard_share_and_cost(klass, admin):
    session_id = await new_session(klass)
    other = await new_session(klass)
    await _llm_game(session_id, "class")
    await _llm_game(session_id, "lecturer_test")  # a Lecturer's test Game is left out
    timing = {"attempt_timeout_s": 4, "order_time_budget_s": 8}
    levels = [{**timing, "name": "deep", "label": "Grundig"}, {**timing, "name": "fast"}]
    spec = {**seed.MOCK_SPEC, "name": "drift", "effort_levels": levels}
    model = (await config.add(config.parse(spec))).id
    for latency in (400, 100, 300, 200):
        _call(session_id, "player_order", "fast", latency, "0.01000000", model)
    _call(session_id, "player_order", "deep", 1000, "0.10000000", model)
    _call(session_id, "debrief_narration", "fast", 9000, "0.50000000", model)
    _call(other, "player_order", "fast", 5000, "1.00000000", model)
    for source, at in (
        ("api_error", NOW - timedelta(minutes=1)),
        ("api_error", NOW - timedelta(minutes=50)),
        ("job_failed", NOW - timedelta(hours=3)),
        ("conservation_check", NOW - timedelta(hours=25)),  # outside the 24 hours
    ):
        assert await service.record_error(source, "x", session_id, at=at)
    assert await service.record_error("api_error", "x", other, at=NOW)

    response = await get(f"/api/admin/operations/class-sessions/{session_id}")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["label"] == "class-of-1994 · Klasseøkt 1"
    assert len(body["hours"]) == 24
    assert body["hours"][-1]["hour"] == "2026-11-19T09:00:00Z"
    assert body["hours"][0]["hour"] == "2026-11-18T10:00:00Z"
    assert body["hours"][-1]["api_error"] == 0  # 09:00, now
    assert body["hours"][-2]["api_error"] == 2  # 08:10 and 08:59
    assert body["hours"][-4]["job_failed"] == 1  # 06:00
    assert sum(h["conservation_check"] for h in body["hours"]) == 0
    assert body["totals"] == {"conservation_check": 1, "job_failed": 1, "api_error": 2}
    assert body["llm_orders"] == 9
    assert body["fallbacks"] == [
        {"kind": "fallback_timeout", "orders": 2, "share": "0.2222"},
        {"kind": "fallback_invalid_output", "orders": 0, "share": "0.0000"},
        {"kind": "fallback_budget_exhausted", "orders": 0, "share": "0.0000"},
        {"kind": "fallback_provider_error", "orders": 1, "share": "0.1111"},
    ]
    assert body["response_times"] == [
        # The level's label from its model config; none for a level the config does not label.
        {"effort_level": "deep", "label": "Grundig", "calls": 1, "median_ms": 1000, "p95_ms": 1000},
        {"effort_level": "fast", "label": None, "calls": 4, "median_ms": 200, "p95_ms": 400},
    ]
    assert (body["llm_seats"], body["switched_seats"], body["switched_share"]) == (2, 1, "0.5000")
    assert (body["cost_usd"], body["ai_calls"]) == ("0.64000000", 6)
    # Counts and timings only: no name, e-mail or text of anyone (FR-5, AD-12).
    assert "@" not in response.text and "Bard" not in response.text

    # The list holds the saved Class sessions, newest first.
    for saved in (session_id, other):
        assert (await save(saved, None)).status_code == 200
    listed = (await get("/api/admin/operations/class-sessions")).json()["items"]
    assert [(i["label"], i["errors_24h"]) for i in listed] == [
        ("class-of-1994 · Klasseøkt 2", 1),
        ("class-of-1994 · Klasseøkt 1", 3),  # the error 25 hours ago is not counted
    ]


async def test_an_empty_session_reads_zeros_and_nulls(klass, admin):
    session_id = await new_session(klass)
    body = (await get(f"/api/admin/operations/class-sessions/{session_id}")).json()
    assert body["totals"] == {"conservation_check": 0, "job_failed": 0, "api_error": 0}
    assert body["llm_orders"] == 0 and {f["share"] for f in body["fallbacks"]} == {None}
    assert (body["response_times"], body["switched_share"]) == ([], None)
    assert (body["cost_usd"], body["ai_calls"]) == ("0.00000000", 0)


async def test_only_the_admin_reads_and_an_unknown_session_is_404(klass, admin):
    session_id = await new_session(klass)
    for path in ("", f"/{session_id}"):
        refused = await get(f"/api/admin/operations/class-sessions{path}", who=LECTURER)
        assert (refused.status_code, refused.json()["error"]["code"]) == (403, "forbidden")
    missing = await get(f"/api/admin/operations/class-sessions/{uuid.uuid7()}")
    assert (missing.status_code, missing.json()["error"]["code"]) == (404, "not_found")


def test_no_module_but_ops_writes_error_events():
    from pathlib import Path

    app = Path(__file__).resolve().parents[2] / "app"
    writers = [
        path.relative_to(app).as_posix()
        for path in app.rglob("*.py")
        if "error_events" in path.read_text(encoding="utf-8")
    ]
    assert sorted(writers) == ["modules/identity/personal_data.py"] + sorted(
        w for w in writers if w.startswith("modules/ops/")
    )
