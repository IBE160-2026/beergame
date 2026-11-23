"""Background jobs on Postgres with procrastinate (AD-9, AD-24).

One procrastinate `App` per process. A pool is opened only where jobs run (`python -m
app.worker`, `run_until_idle`, each with a worker app of its own); deferring needs no pool,
because a job is always deferred on the caller's own database connection inside its
transaction (`defer`): the job row commits with the caller's rows or not at all, and no worker
can see it earlier. Job arguments are ids and
whole numbers only. Tasks are never retried by procrastinate: a task that must not stall a Game
handles its own failures.

Queues: `ai-orders` (`worker-ai`, the LLM players' Orders), `llm-batch` and `mail`
(`worker-batch`, Story 3.5), `reports-single` (`worker-batch`, Story 13.7: one Student report,
with `REPORTS_SINGLE_RESERVED` slots no other queue takes, so a report meets its 30 seconds while
the worker's other queues are busy), `reports-bulk` (`worker-batch`, Story 13.12: the long report
jobs, the ZIP of Story 13.13, beside which a single report keeps its slots; beside other queues
it runs in a worker of its own, so a long ZIP never holds the sweep or the mail), and `sweep`, which
only the `--sweeper` worker runs: it holds the per-minute `ops.sweep` (AD-9). Later epics add
theirs. Alembic owns the procrastinate schema
(revision 0008).
"""

import asyncio
import importlib
import uuid
from collections.abc import Awaitable, Callable, Iterable, Mapping, Sequence
from datetime import datetime, timedelta

import procrastinate
import structlog
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform import error_reporting
from app.platform.config import get_settings

__all__ = [
    "AI_ORDERS",
    "LLM_BATCH",
    "MAIL",
    "QUEUES",
    "REPORTS_BULK",
    "REPORTS_SINGLE",
    "SWEEP",
    "TASK_MODULES",
    "app",
    "conninfo",
    "defer",
    "defer_many",
    "failed_counts",
    "failure_middleware",
    "JobFailureHook",
    "live_locks",
    "load_tasks",
    "procrastinate_pool_size",
    "run_until_idle",
    "worker_sides",
]

log = structlog.get_logger(__name__)

AI_ORDERS = "ai-orders"
LLM_BATCH = "llm-batch"
MAIL = "mail"
REPORTS_BULK = "reports-bulk"
REPORTS_SINGLE = "reports-single"
SWEEP = "sweep"
QUEUES = (AI_ORDERS, LLM_BATCH, MAIL, REPORTS_BULK, REPORTS_SINGLE, SWEEP)

TASK_MODULES = (
    "app.modules.players.jobs",
    "app.modules.messaging.jobs",
    "app.modules.ops.jobs",
    "app.modules.debrief.jobs",
    "app.modules.replay.jobs",  # no task yet: its finish hook (Story 10.5)
    "app.modules.tests.jobs",
    # No task: it registers the Completion assembler and the lookup of a Student's
    # Oppfølgingsspill with `sessions` (Stories 13.1, 13.4), which the `makeup_given` mail reads.
    "app.modules.reports.service",
    "app.modules.reports.render",  # the Student report (Story 13.7)
    "app.modules.reports.bundle",  # the ZIP of all Student reports (Story 13.13)
    "app.modules.assessment.jobs",
    "app.modules.reports.class_report_jobs",  # the Klasserapport's facts sets (Story 14.1)
    "app.modules.reports.aggregates",  # the stored aggregates of Story 14.3
)
"""The modules that register tasks on `app`; a worker imports them before it runs."""

FAILURE_WINDOW = timedelta(hours=24)
"""How far back `failed_counts` counts a job's failures by default."""

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


async def failed_counts(
    session: AsyncSession, locks: Iterable[str], within: timedelta = FAILURE_WINDOW
) -> dict[str, int]:
    """Of `locks`, how many jobs under each queueing lock failed in the last `within` (database
    time, by procrastinate's `failed` event): a sweep that defers a lost job again stops after a
    few recent failures, so a job that always fails is not deferred every minute, and tries again
    once they age out, so a failure a deploy fixed blocks nothing for good (close-out of Epic 14).
    A lock with none is left out."""
    wanted = sorted(set(locks))
    if not wanted:
        return {}
    result = await session.execute(
        text(
            "SELECT j.queueing_lock, count(DISTINCT j.id) FROM procrastinate_jobs AS j "
            "JOIN procrastinate_events AS e ON e.job_id = j.id AND e.type = 'failed' "
            "WHERE j.queueing_lock = ANY(:locks) AND j.status = 'failed' "
            "AND e.at > now() - :within GROUP BY j.queueing_lock"
        ),
        {"locks": wanted, "within": within},
    )
    return {str(lock): int(count) for lock, count in result}


def worker_sides(queues: Sequence[str]) -> dict[str, int]:
    """The queues a worker runs beside its others, on slots of their own, with their slots.

    Story 13.7: `reports-single` beside other queues runs in a worker of its own with
    `REPORTS_SINGLE_RESERVED` slots, so no other queue's job takes them (AD-9). The close-out of
    Epic 13: `reports-bulk` beside other queues runs in a worker of its own too (one slot), so a
    ZIP of many minutes never holds the sweep, the mail or the LLM batches behind it."""
    sides: dict[str, int] = {}
    if len(queues) > 1:
        if REPORTS_SINGLE in queues:
            sides[REPORTS_SINGLE] = get_settings().reports_single_reserved
        if REPORTS_BULK in queues and len(queues) > len(sides) + 1:
            sides[REPORTS_BULK] = 1
    return sides


def procrastinate_pool_size(concurrency: int, queues: Sequence[str] = ()) -> int:
    """The connections a worker's procrastinate pool may hold: one per job run at once, the
    slots of the queues it runs on their own (`worker_sides`), and one for its LISTEN for new
    jobs, at least two (docs/ops/connection-budget.md)."""
    return max(2, concurrency + sum(worker_sides(queues).values()) + 1)


def _connector(database_url: str | None, size: int) -> procrastinate.PsycopgConnector:
    return procrastinate.PsycopgConnector(
        conninfo=conninfo(database_url),
        min_size=1,
        max_size=size,
        kwargs={"connect_timeout": 5},
    )


HOOK_TIMEOUT_S = 5.0
"""The longest the failure hook may hold a failed job's status."""

JobFailureHook = Callable[[str, Mapping[str, object], object], Awaitable[object]]
"""`(task name, task arguments, job id)`: told when a job failed for good (Story 15.8)."""


def _job_ids(kwargs: Mapping[str, object]) -> dict[str, str]:
    """A job's Class session and Game, when its arguments name them as UUIDs."""
    found = {}
    for name in ("class_session_id", "game_id"):
        try:
            found[name] = str(uuid.UUID(str(kwargs[name])))
        except KeyError, ValueError, TypeError:
            continue
    return found


def failure_middleware(on_failure: JobFailureHook):
    """A procrastinate worker middleware that tells `on_failure` about a job that raised and that
    its task will not retry, then lets the job fail as before. A failing hook is logged by type
    and never changes the job's outcome (NFR-9). `platform` imports no module, so the hook comes
    from `worker.py` (Story 15.8)."""

    async def middleware(call_next, context, worker):
        try:
            return await call_next()
        except BaseException as exc:
            if not isinstance(exc, Exception) or isinstance(
                exc, procrastinate.exceptions.JobAborted
            ):
                raise
            job = context.job
            task = worker.app.tasks.get(job.task_name)
            retry = task.get_retry_exception(exception=exc, job=job) if task else None
            if retry is None:
                # The error tracker gets its class, stack and ids, never its text (Story 15.11).
                error_reporting.capture(
                    exc, job_id=job.id, task=job.task_name, **_job_ids(job.task_kwargs)
                )
                try:
                    await asyncio.wait_for(
                        on_failure(job.task_name, dict(job.task_kwargs), job.id), HOOK_TIMEOUT_S
                    )
                except Exception as hook_exc:
                    log.warning(
                        "job_failure_hook_failed",
                        job_id=job.id,
                        exc_type=type(hook_exc).__name__,
                    )
            raise

    return middleware


async def run_worker(
    queues: Sequence[str],
    *,
    wait: bool = True,
    concurrency: int = 1,
    database_url: str | None = None,
    install_signal_handlers: bool = True,
    on_failure: JobFailureHook | None = None,
) -> None:
    """Run a worker on `queues` until it is stopped, or, with `wait=False`, until no job of
    those queues is left (jobs deferred by the jobs it runs included). `on_failure` is told of
    each job that fails for good (Story 15.8)."""
    if not queues:
        raise ValueError("no queue given")  # procrastinate would run every queue
    unknown = [queue for queue in queues if queue not in QUEUES]
    if unknown:
        raise ValueError(f"unknown queue(s): {', '.join(unknown)}")
    load_tasks()
    sides = worker_sides(queues)
    others = [queue for queue in queues if queue not in sides]
    # The app gets a pool that lives as long as this worker. It is the app itself, not a copy
    # (`with_connector`): the periodic deferrer of `ops.sweep` defers through the task's own app,
    # which must be the open one (Story 3.5).
    with app.replace_connector(
        _connector(database_url, procrastinate_pool_size(concurrency, queues))
    ) as worker_app:
        async with worker_app.open_async():
            main = worker_app.run_worker_async(
                queues=others,
                wait=wait,
                concurrency=concurrency,
                listen_notify=wait,
                install_signal_handlers=install_signal_handlers,
                delete_jobs="successful",
                worker_middleware=[failure_middleware(on_failure)] if on_failure else None,
            )
            if not sides:
                await main
                return
            side = [
                asyncio.ensure_future(
                    worker_app.run_worker_async(
                        queues=[queue],
                        name=queue,
                        wait=wait,
                        concurrency=slots,
                        listen_notify=wait,
                        install_signal_handlers=False,
                        delete_jobs="successful",
                    )
                )
                for queue, slots in sides.items()
            ]
            first = asyncio.ensure_future(main)
            every = [first, *side]
            try:
                if not wait:
                    await asyncio.gather(*every)  # run until idle: the reports too
                    return
                await asyncio.wait(every, return_when=asyncio.FIRST_COMPLETED)
                stopped = [task for task in side if task.done()]
                if stopped and not first.done():
                    # A reports worker stopped on its own: the process stops, so it restarts.
                    log.error("reports_worker_stopped")
                    stopped[0].result()
                    raise RuntimeError("a reports worker stopped")
                await first
            finally:
                # On a stop, a render in flight is cancelled; its request ends `failed` and the
                # Student presses again.
                for task in every:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*every, return_exceptions=True)


async def run_until_idle(
    queues: Iterable[str],
    *,
    database_url: str | None = None,
    on_failure: JobFailureHook | None = None,
) -> None:
    """Run every job waiting on `queues`, and the jobs they defer, in this process; returns
    when none is left. Tests and the simulation runner drive jobs with it, never with a
    clock."""
    await run_worker(
        list(queues),
        wait=False,
        database_url=database_url,
        install_signal_handlers=False,
        on_failure=on_failure,
    )
