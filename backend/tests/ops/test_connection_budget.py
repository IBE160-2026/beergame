"""The database connection budget is written and checked (Story 15.9, NFR-3, NFR-4, AD-24).

`docs/ops/connection-budget.md` and `ops.connection_budget.BUDGET` hold the same numbers. Each
process logs and records at start the connections its settings give it; «Drift» sums the latest
report per process against the budget, and `check_connection_budget` compares `DB_POOLER_SIZE`
with twice the budget plus the migration's connection, unset being "not checked". Times are passed
in; the database clock is never compared with them."""

import re
from datetime import timedelta
from pathlib import Path

import pytest
from structlog.testing import capture_logs

from app.modules.identity.personal_data import REGISTRY
from app.modules.identity.schemas import AccountRole
from app.modules.ops import connection_budget as budget
from app.modules.ops import service
from app.platform.config import Settings
from tests.classes.test_classes import LECTURER, as_user, make
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.conftest import empty
from tests.identity.helpers import CSRF, client
from tests.messaging.helpers import rows
from tests.test_logging import lines, log_stream

__all__ = ["clock", "klass", "log_stream"]

DOC = Path(__file__).resolve().parents[3] / "docs" / "ops" / "connection-budget.md"
ADMIN = "admin159@example.com"


@pytest.fixture(autouse=True)
def _empty(test_database):
    empty(test_database, "db_connection_reports")


def settings(**values) -> Settings:
    return Settings(app_env="test", **values)


def test_the_document_and_the_code_hold_the_same_budget():
    text = DOC.read_text(encoding="utf-8")
    for process, line in budget.BUDGET.items():
        [row] = [r for r in text.splitlines() if r.startswith(f"| `{process}` |")]
        _, _, pool, jobs, listen, total, _ = (cell.strip() for cell in row.split("|"))
        assert pool.startswith(f"`DB_POOL_SIZE` = {line.sqlalchemy_pool},"), row
        # «0: jobs are deferred …» or «`max(2, concurrency + 1)` = 2 …»
        assert re.match(
            rf"({line.procrastinate_pool}:|.*= {line.procrastinate_pool}(?![0-9]))", jobs
        ), row
        # «1, reserved for the SSE listener» or, for a worker, inside the procrastinate pool
        assert listen.startswith(f"{line.listen},") or (
            line.listen == 0 and listen == "inside the procrastinate pool"
        ), row
        assert total == f"**{line.total}**", row
    assert budget.budget_total() == 28
    assert budget.overlap_total() == 56
    assert budget.pooler_required() == 57
    assert f"= **{budget.budget_total()}**" in text
    assert f"× 2 = **{budget.overlap_total()}**" in text
    assert f"| **{budget.pooler_required()}** |" in text
    assert f"at least {budget.pooler_required()}" in text
    assert "issue #28" in text


@pytest.mark.parametrize(
    ("pooler", "status"), [(None, "not_checked"), (15, "failed"), (56, "failed"), (57, "passed")]
)
def test_the_pooler_check_compares_the_copied_size_with_the_overlap_need(pooler, status):
    check = service.check_connection_budget(settings(db_pooler_size=pooler))
    assert (check.status, check.pooler_size, check.required, check.budget_total) == (
        status,
        pooler,
        57,
        28,
    )
    message = check.message()
    assert "57" in message
    if status == "failed":
        assert str(pooler) in message
    if status == "not_checked":
        assert "not checked" in message and "passed" not in message


def test_each_process_counts_its_pool_procrastinate_and_listen():
    tuned = settings(db_pool_size=5)
    assert budget.configured("backend", settings()) == budget.Connections(10, 0, 1)
    assert budget.configured("worker-ai", tuned) == budget.Connections(5, 2, 0)
    assert budget.configured("worker-batch", tuned, concurrency=4) == budget.Connections(5, 5, 0)
    # Story 13.7 and the close-out of Epic 13: `reports-single` (2) and `reports-bulk` (1) beside
    # the other queues hold slots of their own, as the compose and Railway worker-batch runs.
    batch = ["llm-batch", "mail", "reports-bulk", "reports-single"]
    assert budget.configured("worker-batch", tuned, queues=batch) == budget.BUDGET["worker-batch"]
    assert budget.worker_process(["ai-orders"]) == "worker-ai"
    assert budget.worker_process(["llm-batch", "mail", "sweep"]) == "worker-batch"


async def test_a_start_logs_and_records_its_connections_against_the_budget(log_stream):
    """Through the real JSON logging: every number passes the field allowlist (AD-14)."""
    assert await service.report_connections("worker-ai", settings(db_pool_size=5), concurrency=1)
    assert await service.report_connections("backend", settings(db_pool_size=20))
    logged = [e for e in lines(log_stream) if e["event"] == "db_connections_configured"]
    assert [
        (
            e["process"],
            e["sqlalchemy_pool"],
            e["procrastinate_pool"],
            e["db_listen"],
            e["db_total"],
            e["db_budget"],
            e["within_budget"],
        )
        for e in logged
    ] == [("worker-ai", 5, 2, 0, 7, 7, True), ("backend", 20, 0, 1, 21, 11, False)]
    assert sorted(
        rows("SELECT process, sqlalchemy_pool, job_pool, listen FROM db_connection_reports")
    ) == [("backend", 20, 0, 1), ("worker-ai", 5, 2, 0)]


async def test_only_the_newest_ten_reports_per_process_are_kept():
    for i in range(12):
        await budget.report_start("worker-batch", budget.Connections(i, 2, 0), at=NOW)
    await budget.report_start("backend", budget.Connections(10, 0, 1), at=NOW)
    kept = rows(
        "SELECT sqlalchemy_pool FROM db_connection_reports WHERE process = 'worker-batch' "
        "ORDER BY sqlalchemy_pool"
    )
    assert [n for (n,) in kept] == list(range(2, 12))
    assert (await budget.latest_reports())["worker-batch"].connections.sqlalchemy_pool == 11


async def test_an_unknown_process_is_logged_not_raised():
    with capture_logs() as logs:
        assert not await budget.report_start("frontend", budget.Connections(1, 0, 0))
    assert [(e["event"], e["exc_type"]) for e in logs] == [
        ("db_connections_report_failed", "UnknownProcess")
    ]
    assert rows("SELECT count(*) FROM db_connection_reports") == [(0,)]


async def test_a_report_that_cannot_be_stored_is_logged_and_the_start_goes_on(monkeypatch):
    def down():
        raise ConnectionError("database down")

    monkeypatch.setattr(budget, "get_sessionmaker", down)
    with capture_logs() as logs:
        assert not await service.report_connections("backend", settings())
    assert [(e["event"], e.get("exc_type")) for e in logs] == [
        ("db_connections_configured", None),
        ("db_connections_report_failed", "ConnectionError"),
    ]


async def test_the_api_reports_its_connections_and_the_pooler_check_at_start(log_stream):
    from app import main

    async with main.lifespan(main.app):
        pass
    events = {e["event"]: e for e in lines(log_stream)}
    assert events["db_connections_configured"]["process"] == "backend"
    assert events["db_pooler_check"]["status"] == "not_checked"
    assert events["db_pooler_check"]["pooler_required"] == 57
    assert rows("SELECT process FROM db_connection_reports") == [("backend",)]


def test_the_reports_hold_no_personal_data():
    entry = REGISTRY["db_connection_reports"]
    assert entry.handling == "none" and "no User" in entry.note


@pytest.fixture
async def admin(klass):
    return await make(ADMIN, roles=(AccountRole.admin,))


async def get(who: str = ADMIN):
    async with client() as c:
        await as_user(c, who)
        return await c.get("/api/admin/operations/connections", headers=CSRF)


async def test_drift_reads_no_report_as_incomplete_and_not_checked(admin):
    answer = await get()
    assert answer.status_code == 200
    body = answer.json()
    assert [p["process"] for p in body["processes"]] == ["backend", "worker-ai", "worker-batch"]
    assert all(p["configured"] is None and not p["over_budget"] for p in body["processes"])
    assert body["processes"][0]["budget"] == {
        "sqlalchemy_pool": 10,
        "procrastinate_pool": 0,
        "listen": 1,
        "total": 11,
    }
    assert (body["budget_total"], body["overlap_total"], body["configured_total"]) == (28, 56, 0)
    assert body["running"] == "incomplete"
    assert body["pooler"] == {"status": "not_checked", "pooler_size": None, "required": 57}


async def test_drift_sums_the_latest_report_per_process(admin):
    old = NOW - timedelta(hours=1)
    await budget.report_start("backend", budget.Connections(30, 0, 1), at=old)  # replaced
    await budget.report_start("backend", budget.Connections(10, 0, 1), at=NOW)
    await budget.report_start("worker-ai", budget.Connections(5, 2, 0), at=NOW)
    await budget.report_start("worker-batch", budget.Connections(5, 5, 0), at=NOW)
    body = (await get()).json()
    assert [p["configured"]["total"] for p in body["processes"]] == [11, 7, 10]
    assert (body["configured_total"], body["running"]) == (28, "within")

    await budget.report_start("worker-batch", budget.Connections(10, 2, 0), at=NOW)
    body = (await get()).json()
    assert [p["over_budget"] for p in body["processes"]] == [False, False, True]
    assert (body["configured_total"], body["running"]) == (30, "over")


async def test_drift_shows_the_pooler_check_with_both_numbers(admin, monkeypatch):
    from app.platform import config

    monkeypatch.setattr(config.get_settings(), "db_pooler_size", 15)
    body = (await get()).json()
    assert body["pooler"] == {"status": "failed", "pooler_size": 15, "required": 57}


async def test_only_the_admin_reads_the_budget(admin):
    assert (await get(LECTURER)).status_code == 403


def test_no_module_but_ops_writes_the_reports():
    app = Path(__file__).resolve().parents[2] / "app"
    writers = {
        path.relative_to(app).as_posix()
        for path in app.rglob("*.py")
        if re.search(r"\bdb_connection_reports\b", path.read_text(encoding="utf-8"))
    }
    assert writers == {
        "modules/ops/models.py",
        "modules/ops/connection_budget.py",
        "modules/identity/personal_data.py",  # its registry entry
    }
