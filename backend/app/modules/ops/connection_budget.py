"""The database connection budget, written and checked (Story 15.9, NFR-3, NFR-4, AD-24).

Production reaches Postgres through Supabase's session pooler on port 5432, where every open
client connection holds one pooler slot. `docs/ops/connection-budget.md` writes down what each
process may hold; `BUDGET` here is the same table, and a test keeps the two equal. The values are
PLACEHOLDERS, to be tuned under load (issue #28).

What the system checks, since the pooler's own pool size cannot be read over the pooler:
- each process logs at start the connections its settings give it, and records them
  (`report_start`); «Drift» sums the latest report per process against `BUDGET`;
- `check_connection_budget` compares `DB_POOLER_SIZE`, which the founder copies from Supabase,
  with what a deploy overlap needs: twice the budget total, plus the one connection of the
  `backend` pre-deploy migration. Unset is "not checked", never "passed".
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

import structlog
from sqlalchemy import delete, func, select

from app.modules.ops.models import PROCESSES, db_connection_reports
from app.modules.ops.operations_schemas import (
    ConnectionBudgetOut,
    ConnectionCountsOut,
    PoolerCheckOut,
    ProcessConnectionsOut,
)
from app.platform import jobs
from app.platform.config import Settings, get_settings
from app.platform.db import get_sessionmaker

__all__ = [
    "BUDGET",
    "BudgetCheck",
    "Connections",
    "KEEP_PER_PROCESS",
    "MIGRATION_CONNECTIONS",
    "budget_total",
    "check_connection_budget",
    "configured",
    "latest_reports",
    "overlap_total",
    "pooler_required",
    "read_budget",
    "report_start",
    "worker_process",
]

log = structlog.get_logger(__name__)

Process = Literal["backend", "worker-ai", "worker-batch"]


@dataclass(frozen=True)
class Connections:
    """The connections one process may hold: its SQLAlchemy pool (`max_overflow=0`), its
    procrastinate pool and its own LISTEN connection."""

    sqlalchemy_pool: int
    procrastinate_pool: int
    listen: int

    @property
    def total(self) -> int:
        return self.sqlalchemy_pool + self.procrastinate_pool + self.listen


BUDGET: dict[str, Connections] = {
    # `DB_POOL_SIZE` 10; jobs are deferred on the request's own connection, so no procrastinate
    # pool; one LISTEN connection for the event stream (AD-8, `platform/events/hub.py`).
    "backend": Connections(sqlalchemy_pool=10, procrastinate_pool=0, listen=1),
    # `DB_POOL_SIZE` 5; procrastinate's pool at `--concurrency 1` (its LISTEN is inside it).
    "worker-ai": Connections(sqlalchemy_pool=5, procrastinate_pool=2, listen=0),
    # Story 13.7 and the close-out of Epic 13: plus `reports-single`'s 2 slots and `reports-bulk`'s
    # 1, which it runs beside its other queues (`jobs.worker_sides`).
    "worker-batch": Connections(sqlalchemy_pool=5, procrastinate_pool=5, listen=0),
}
"""The written budget per process, PLACEHOLDERS to be tuned under load (issue #28). Equal to the
table in `docs/ops/connection-budget.md` (checked by a test)."""

MIGRATION_CONNECTIONS = 1
"""The `backend` pre-deploy `alembic upgrade head`: one connection (NullPool) while it runs, which
can overlap the old processes and a worker's new one."""

KEEP_PER_PROCESS = 10
"""Start reports kept per process; older ones are deleted when a process reports."""


def budget_total() -> int:
    """What one deploy of every service may hold."""
    return sum(item.total for item in BUDGET.values())


def overlap_total() -> int:
    """What a deploy overlap may hold: the old and the new deploy side by side."""
    return 2 * budget_total()


def pooler_required() -> int:
    """The pooler pool size a deploy overlap needs, the migration included."""
    return overlap_total() + MIGRATION_CONNECTIONS


def configured(
    process: str,
    settings: Settings,
    *,
    concurrency: int = 1,
    queues: Sequence[str] = (),
) -> Connections:
    """The connections `process` holds with `settings`: its `DB_POOL_SIZE`, and for a worker the
    procrastinate pool of its concurrency and `queues`, for `backend` its LISTEN connection."""
    if process == "backend":
        return Connections(settings.db_pool_size, 0, 1)
    return Connections(settings.db_pool_size, jobs.procrastinate_pool_size(concurrency, queues), 0)


def worker_process(queues: list[str] | tuple[str, ...]) -> Process:
    """The service a worker runs as: `worker-ai` when it runs the AI Orders, else `worker-batch`
    (`railway/<service>/railway.toml`)."""
    return "worker-ai" if jobs.AI_ORDERS in queues else "worker-batch"


async def report_start(
    process: str,
    connections: Connections,
    *,
    at: datetime | None = None,
) -> bool:
    """Log the connections `process` is configured to hold against its budget line, and record
    them for «Drift». A failure to record is logged by type and never stops the process."""
    line = BUDGET.get(process)
    if line is None:
        log.warning("db_connections_report_failed", process=process, exc_type="UnknownProcess")
        return False
    log.info(
        "db_connections_configured",
        process=process,
        sqlalchemy_pool=connections.sqlalchemy_pool,
        procrastinate_pool=connections.procrastinate_pool,
        db_listen=connections.listen,
        db_total=connections.total,
        db_budget=line.total,
        within_budget=connections.total <= line.total,
    )
    try:
        async with get_sessionmaker().begin() as session:
            await session.execute(
                db_connection_reports.insert().values(
                    id=uuid.uuid7(),
                    process=process,
                    sqlalchemy_pool=connections.sqlalchemy_pool,
                    job_pool=connections.procrastinate_pool,
                    listen=connections.listen,
                    reported_at=at or datetime.now(UTC),
                )
            )
            newest = (
                select(db_connection_reports.c.id)
                .where(db_connection_reports.c.process == process)
                .order_by(db_connection_reports.c.id.desc())
                .limit(KEEP_PER_PROCESS)
            )
            await session.execute(
                delete(db_connection_reports).where(
                    db_connection_reports.c.process == process,
                    db_connection_reports.c.id.not_in(newest.scalar_subquery()),
                )
            )
    except Exception as exc:  # the type only
        log.warning("db_connections_report_failed", process=process, exc_type=type(exc).__name__)
        return False
    return True


@dataclass(frozen=True)
class Report:
    connections: Connections
    reported_at: datetime


async def latest_reports() -> dict[str, Report]:
    """The latest start report of each process that has reported (by UUIDv7 id)."""
    newest = (
        select(
            db_connection_reports,
            func.row_number()
            .over(
                partition_by=db_connection_reports.c.process,
                order_by=db_connection_reports.c.id.desc(),
            )
            .label("rank"),
        )
    ).subquery()
    async with get_sessionmaker()() as session:
        rows = (await session.execute(select(newest).where(newest.c.rank == 1))).mappings().all()
    return {
        row["process"]: Report(
            Connections(row["sqlalchemy_pool"], row["job_pool"], row["listen"]),
            row["reported_at"],
        )
        for row in rows
    }


@dataclass(frozen=True)
class BudgetCheck:
    """The pooler check: `passed`, `failed` (the pool is smaller than `required`) or
    `not_checked` (`DB_POOLER_SIZE` is not set)."""

    status: Literal["passed", "failed", "not_checked"]
    pooler_size: int | None
    required: int
    budget_total: int

    def message(self) -> str:
        if self.status == "not_checked":
            return f"not checked: DB_POOLER_SIZE is not set (needed {self.required})"
        if self.status == "failed":
            return f"failed: DB_POOLER_SIZE {self.pooler_size} < {self.required} needed"
        return f"passed: DB_POOLER_SIZE {self.pooler_size} >= {self.required} needed"


def check_connection_budget(settings: Settings | None = None) -> BudgetCheck:
    """Compare `DB_POOLER_SIZE` with twice the budget total plus the migration's connection. No
    database: the pooler's size cannot be read over the session pooler."""
    settings = settings or get_settings()
    required = pooler_required()
    size = settings.db_pooler_size
    if size is None:
        status: Literal["passed", "failed", "not_checked"] = "not_checked"
    elif size < required:
        status = "failed"
    else:
        status = "passed"
    return BudgetCheck(status, size, required, budget_total())


def _counts(item: Connections) -> ConnectionCountsOut:
    return ConnectionCountsOut(
        sqlalchemy_pool=item.sqlalchemy_pool,
        procrastinate_pool=item.procrastinate_pool,
        listen=item.listen,
        total=item.total,
    )


async def read_budget(now: datetime, settings: Settings | None = None) -> ConnectionBudgetOut:
    """The budget per process against its latest start report, the sums and the pooler check,
    for «Drift» (Story 15.9)."""
    reports = await latest_reports()
    processes: list[ProcessConnectionsOut] = []
    for process in PROCESSES:
        line = BUDGET[process]
        report = reports.get(process)
        processes.append(
            ProcessConnectionsOut(
                process=process,
                budget=_counts(line),
                configured=_counts(report.connections) if report else None,
                reported_at=report.reported_at if report else None,
                over_budget=bool(report and report.connections.total > line.total),
            )
        )
    configured_total = sum(report.connections.total for report in reports.values())
    if configured_total > budget_total() or any(item.over_budget for item in processes):
        running = "over"
    elif any(item.configured is None for item in processes):
        running = "incomplete"
    else:
        running = "within"
    check = check_connection_budget(settings)
    return ConnectionBudgetOut(
        read_at=now,
        processes=processes,
        budget_total=budget_total(),
        overlap_total=overlap_total(),
        configured_total=configured_total,
        running=running,
        pooler=PoolerCheckOut(
            status=check.status, pooler_size=check.pooler_size, required=check.required
        ),
    )
