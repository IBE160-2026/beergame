"""Background jobs on Postgres with procrastinate (AD-9, AD-24).

One procrastinate `App` per process. A pool is opened only where jobs run (`python -m
app.worker`, `run_until_idle`, each with a worker app of its own); deferring needs no pool,
because a job is always deferred on the caller's own database connection inside its
transaction (`defer`): the job row commits with the caller's rows or not at all, and no worker
can see it earlier. Job arguments are ids and
whole numbers only. Tasks are never retried by procrastinate: a task that must not stall a Game
handles its own failures.

Queues: `ai-orders` (`worker-ai`, the LLM players' Orders), `llm-batch` and `mail`
(`worker-batch`, Story 3.5), and `sweep`, which only the `--sweeper` worker runs: it holds the
per-minute `ops.sweep` (AD-9). Later epics add theirs. Alembic owns the procrastinate schema
(revision 0008).
"""

import importlib
from collections.abc import Iterable, Sequence
from datetime import datetime

import procrastinate
import structlog
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.config import get_settings

__all__ = [
    "AI_ORDERS",
    "LLM_BATCH",
    "MAIL",
    "QUEUES",
    "SWEEP",
    "TASK_MODULES",
    "app",
    "conninfo",
    "defer",
    "defer_many",
    "live_locks",
    "load_tasks",
    "run_until_idle",
]

log = structlog.get_logger(__name__)

AI_ORDERS = "ai-orders"
LLM_BATCH = "llm-batch"
MAIL = "mail"
SWEEP = "sweep"
QUEUES = (AI_ORDERS, LLM_BATCH, MAIL, SWEEP)

TASK_MODULES = (
    "app.modules.players.jobs",
    "app.modules.messaging.jobs",
    "app.modules.ops.jobs",
    "app.modules.debrief.jobs",
    "app.modules.replay.jobs",  # no task yet: its finish hook (Story 10.5)
    "app.modules.tests.jobs",
    "app.modules.assessment.jobs",
    "app.modules.reports.class_report_jobs",  # the Klasserapport's facts sets (Story 14.1)
)
"""The modules that register tasks on `app`; a worker imports them before it runs."""

app = procrastinate.App(connector=procrastinate.PsycopgConnector())
"""Tasks register here (`@app.task(name=..., queue=...)`); `defer` and the worker use it."""


def load_tasks() -> None:
    """Import every task module, so the worker knows each task by name."""
    for module in TASK_MODULES:
        importlib.import_module(module)


def conninfo(database_url: str | None = None) -> str:
    """The libpq connection string of `DATABASE_URL` (procrastinate speaks psycopg directly)."""
    url = make_url(database_url or get_settings().database_url)
    return url.set(drivername="postgresql").render_as_string(hide_password=False)


async def defer(
    session: AsyncSession,
    task: str,
    *,
    queue: str,
    queueing_lock: str,
    schedule_at: datetime | None = None,
    **kwargs: str | int,
) -> bool:
    """Defer one job of `task` on `session`'s connection, inside its transaction.

    `queueing_lock` is the job's natural key: while a job with the same key waits (`todo`), a
    second one is not deferred and False is returned. The attempt runs in a savepoint, so that
    refusal leaves the caller's transaction usable. `schedule_at` (Story 12.2: a later run after
    a back-off) keeps the job from running before then."""
    for name, value in kwargs.items():
        if not isinstance(value, str | int) or isinstance(value, bool):
            raise TypeError(f"job argument {name!r} must be an id or a whole number")
    savepoint = await session.begin_nested()
    # The SAVEPOINT is sent when the session hands out its connection, so it is asked for
    # after `begin_nested`: the job's query runs on that connection, past SQLAlchemy.
    connection = await session.connection()
    raw = (await connection.get_raw_connection()).driver_connection
    deferrer = app.configure_task(
        name=task,
        queue=queue,
        queueing_lock=queueing_lock,
        connection=raw,
        schedule_at=schedule_at,
    )
    try:
        job_id = await deferrer.defer_async(**kwargs)
    except procrastinate.exceptions.AlreadyEnqueued:
        await savepoint.rollback()
        log.info("job_already_enqueued", task=task, queueing_lock=queueing_lock)
        return False
    await savepoint.commit()
    log.debug("job_deferred", task=task, queue=queue, job_id=job_id)
    return True


async def defer_many(
    session: AsyncSession,
    task: str,
    *,
    queue: str,
    jobs: Sequence[tuple[str, dict[str, str | int]]],
) -> int:
    """Defer one job of `task` per `(queueing_lock, kwargs)` in one statement, on `session`'s
    connection inside its transaction (`defer` for many at once, Story 4.4). For jobs whose
    locks are new, such as one per freshly created row: a lock already waiting fails the whole
    batch (procrastinate's `AlreadyEnqueued`), and the caller's transaction with it."""
    if not jobs:
        return 0
    for _, kwargs in jobs:
        for name, value in kwargs.items():
            if not isinstance(value, str | int) or isinstance(value, bool):
                raise TypeError(f"job argument {name!r} must be an id or a whole number")
    connection = await session.connection()
    raw = (await connection.get_raw_connection()).driver_connection
    template = app.configure_task(name=task, queue=queue, connection=raw).job
    deferred = await app.job_manager.batch_defer_jobs_async(
        jobs=[template.evolve(queueing_lock=lock, task_kwargs=dict(kw)) for lock, kw in jobs],
        connection=raw,
    )
    log.debug("jobs_deferred", task=task, queue=queue, count=len(deferred))
    return len(deferred)


async def live_locks(session: AsyncSession, locks: Iterable[str]) -> set[str]:
    """Of `locks`, the queueing locks of a job that waits (`todo`) or runs (`doing`) now: a job
    for that key is alive, so it must not be deferred again (Story 8.14)."""
    wanted = sorted(set(locks))
    if not wanted:
        return set()
    result = await session.execute(
        text(
            "SELECT DISTINCT queueing_lock FROM procrastinate_jobs "
            "WHERE queueing_lock = ANY(:locks) AND status IN ('todo', 'doing')"
        ),
        {"locks": wanted},
    )
    return {str(lock) for lock in result.scalars()}


def _connector(database_url: str | None, size: int) -> procrastinate.PsycopgConnector:
    return procrastinate.PsycopgConnector(
        conninfo=conninfo(database_url),
        min_size=1,
        max_size=size,
        kwargs={"connect_timeout": 5},
    )


async def run_worker(
    queues: Sequence[str],
    *,
    wait: bool = True,
    concurrency: int = 1,
    database_url: str | None = None,
    install_signal_handlers: bool = True,
) -> None:
    """Run a worker on `queues` until it is stopped, or, with `wait=False`, until no job of
    those queues is left (jobs deferred by the jobs it runs included)."""
    if not queues:
        raise ValueError("no queue given")  # procrastinate would run every queue
    unknown = [queue for queue in queues if queue not in QUEUES]
    if unknown:
        raise ValueError(f"unknown queue(s): {', '.join(unknown)}")
    load_tasks()
    # The app gets a pool that lives as long as this worker. It is the app itself, not a copy
    # (`with_connector`): the periodic deferrer of `ops.sweep` defers through the task's own app,
    # which must be the open one (Story 3.5).
    with app.replace_connector(_connector(database_url, max(2, concurrency + 1))) as worker_app:
        async with worker_app.open_async():
            await worker_app.run_worker_async(
                queues=list(queues),
                wait=wait,
                concurrency=concurrency,
                listen_notify=wait,
                install_signal_handlers=install_signal_handlers,
                delete_jobs="successful",
            )


async def run_until_idle(queues: Iterable[str], *, database_url: str | None = None) -> None:
    """Run every job waiting on `queues`, and the jobs they defer, in this process; returns
    when none is left. Tests and the simulation runner drive jobs with it, never with a
    clock."""
    await run_worker(
        list(queues), wait=False, database_url=database_url, install_signal_handlers=False
    )
