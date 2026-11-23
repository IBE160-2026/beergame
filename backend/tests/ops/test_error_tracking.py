"""Errors reach the error tracker without personal data, and are counted in `error_events` too
(Story 15.11, NFR-4, NFR-8, AD-14, AD-17).

An api route and a job raise while a name, an e-mail and an Explanation are in their local
variables, in the request body and in the exception's message. The bytes the tracker's transport
would have sent hold none of them, and hold the error's type, its stack and the ids; the same
error is a row in `error_events` (Story 15.8). The Admin's deliberate test error does both for a
Class session. No test reaches a tracker: the DSN reporter gets a fake transport."""

import json
import uuid

import httpx
import pytest

from app.modules.identity.schemas import AccountRole
from app.modules.ops import service
from app.platform import jobs
from app.platform.db import get_sessionmaker
from app.platform.error_reporting import DsnReporter, use_reporter
from tests.classes.test_classes import LECTURER, as_user, make
from tests.classes.test_roster_upload import clock, klass
from tests.conftest import empty
from tests.identity.helpers import CSRF, app
from tests.messaging.helpers import rows
from tests.platform.test_error_reporting import (
    DSN,
    EMAIL,
    EXPLANATION,
    NAME,
    FakeTransport,
    assert_no_personal_data,
)
from tests.sessions.test_dates import new_session

__all__ = ["clock", "klass"]

ADMIN = "admin1511@example.com"
PERSONAL_TASK = "tests.ops.personal_boom"


@jobs.app.task(name=PERSONAL_TASK, queue=jobs.LLM_BATCH)
async def personal_boom(class_session_id: str, game_id: str) -> None:
    name, email, explanation = NAME, EMAIL, EXPLANATION  # noqa: F841 - locals in scope
    raise RuntimeError(f"{name} <{email}>: {explanation} in {class_session_id}")


@pytest.fixture(autouse=True)
def _empty(games_db, test_database):
    empty(test_database, "error_events")


@pytest.fixture
def tracker():
    transport = FakeTransport()
    reporter = DsnReporter(DSN, transport)
    with use_reporter(reporter):
        yield reporter, transport


def events() -> list[tuple]:
    return rows(
        "SELECT source, code, class_session_id, request_id FROM error_events ORDER BY occurred_at"
    )


def sent_events(reporter: DsnReporter, transport: FakeTransport) -> list[dict]:
    assert reporter.flush(5)
    for _, _, body in transport.sent:
        assert_no_personal_data(body)
    return [json.loads(body.split(b"\n")[2]) for _, _, body in transport.sent]


def _client() -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app(), raise_app_exceptions=False)
    return httpx.AsyncClient(transport=transport, base_url="https://t")


_PATH = "/api/test-only/class-sessions/{class_session_id}/explanation"
_SESSION_PATH = "/api/test-only/sessions/{session_id}/explanation"


def _route_with_personal_data():
    """A route on the real app (its middleware included) that fails with personal data in
    scope: in its locals, in the request body it read, and in the exception's message."""
    the_app = app()

    async def fail(class_session_id: uuid.UUID, body: dict) -> None:
        name, email, explanation = body["name"], body["email"], body["explanation"]
        raise ValueError(f"could not store {explanation!r} for {name} <{email}>")

    async def fail_by_session(session_id: uuid.UUID, body: dict) -> None:
        raise ValueError(f"could not store {body['explanation']!r} for {body['email']}")

    the_app.router.add_api_route(_PATH, fail, methods=["POST"])
    the_app.router.add_api_route(_SESSION_PATH, fail_by_session, methods=["POST"])
    return the_app


@pytest.fixture
def personal_routes():
    the_app = _route_with_personal_data()
    yield
    the_app.router.routes[:] = [
        route
        for route in the_app.router.routes
        if getattr(route, "path", None) not in (_PATH, _SESSION_PATH)
    ]


async def test_an_api_error_with_personal_data_in_scope_reaches_the_tracker_without_it(
    tracker, personal_routes
):
    session_id = uuid.uuid7()
    body = {"name": NAME, "email": EMAIL, "explanation": EXPLANATION}
    async with _client() as c:
        answer = await c.post(_PATH.format(class_session_id=session_id), json=body, headers=CSRF)
        by_name = await c.post(_SESSION_PATH.format(session_id=session_id), json=body, headers=CSRF)
    assert answer.status_code == by_name.status_code == 500
    assert EMAIL not in answer.text
    event, named = sent_events(*tracker)
    (source, code, counted_session, request_id), second = events()
    # A Class session named `session_id` in the path is the same Class session to both.
    assert named["tags"]["class_session_id"] == str(second[2]) == str(session_id)
    assert (source, code, counted_session) == ("api_error", "http_500", session_id)
    assert event["tags"] == {
        "request_id": request_id,  # the same error: one id joins the report and the row
        "class_session_id": str(session_id),
        "status": "500",
    }
    [error] = event["exception"]["values"]
    assert error["type"] == "ValueError" and error["module"] == "builtins"
    assert error["stacktrace"]["frames"][-1]["function"] == "fail"


async def test_a_failed_job_with_personal_data_in_scope_reaches_the_tracker_without_it(tracker):
    session_id, game_id = uuid.uuid7(), uuid.uuid7()
    async with get_sessionmaker().begin() as s:
        await jobs.defer(
            s,
            PERSONAL_TASK,
            queue=jobs.LLM_BATCH,
            queueing_lock="pb1",
            class_session_id=str(session_id),
            game_id=str(game_id),
        )
    await jobs.run_until_idle([jobs.LLM_BATCH], on_failure=service.record_job_failure)
    [event] = sent_events(*tracker)
    [(source, code, counted_session, job_id)] = events()
    assert (source, code, counted_session) == ("job_failed", PERSONAL_TASK, session_id)
    assert event["tags"] == {
        "job_id": job_id,
        "task": PERSONAL_TASK,
        "class_session_id": str(session_id),
        "game_id": str(game_id),
    }
    [error] = event["exception"]["values"]
    assert error["type"] == "RuntimeError"
    assert error["stacktrace"]["frames"][-1]["function"] == "personal_boom"
    assert rows("SELECT status FROM procrastinate_jobs") == [("failed",)]  # still failed


@pytest.fixture
async def admin(klass) -> uuid.UUID:
    return await make(ADMIN, roles=(AccountRole.admin,))


async def _test_error(session_id: object, who: str) -> httpx.Response:
    async with _client() as c:
        await as_user(c, who)
        return await c.post(
            f"/api/admin/operations/class-sessions/{session_id}/test-error", headers=CSRF
        )


async def test_the_admins_deliberate_error_reaches_the_tracker_and_drift(admin, klass, tracker):
    session_id = await new_session(klass)
    answer = await _test_error(session_id, ADMIN)
    assert answer.status_code == 500
    [event] = sent_events(*tracker)
    [(source, code, counted_session, request_id)] = events()
    assert (source, code, str(counted_session)) == ("api_error", "http_500", session_id)
    assert event["tags"]["request_id"] == request_id
    [error] = event["exception"]["values"]
    assert (error["type"], error["module"]) == (
        "DeliberateTestError",
        "app.modules.ops.operations_routes",
    )
    async with _client() as c:
        await as_user(c, ADMIN)
        view = await c.get(f"/api/admin/operations/class-sessions/{session_id}", headers=CSRF)
    assert view.json()["totals"]["api_error"] == 1  # «Drift» shows it


async def test_the_deliberate_error_is_404_for_an_unknown_session_and_admin_only(admin, klass):
    unknown = await _test_error(uuid.uuid7(), ADMIN)
    assert (unknown.status_code, unknown.json()["error"]["code"]) == (404, "not_found")
    session_id = await new_session(klass)
    assert (await _test_error(session_id, LECTURER)).status_code == 403
    assert events() == []
