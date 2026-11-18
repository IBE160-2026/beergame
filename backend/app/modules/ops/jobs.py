"""`ops.sweep`: the one `procrastinate` periodic task, every minute (AD-9).

The task is known to every worker, but only `worker-batch` started with `--sweeper` calls
`schedule()`, which registers it as periodic and makes that worker run the `sweep` queue. The
queueing lock keeps at most one sweep waiting, so a slow sweep is never stacked.
"""

from datetime import UTC, datetime

from app.modules.ops import sweep as sweeper
from app.platform import jobs

__all__ = ["CRON", "SWEEP_TASK", "schedule", "sweep"]

SWEEP_TASK = "ops.sweep"
CRON = "* * * * *"


@jobs.app.task(name=SWEEP_TASK, queue=jobs.SWEEP, queueing_lock=SWEEP_TASK)
async def sweep(timestamp: int) -> None:
    """One sweep. `timestamp` is the minute procrastinate scheduled; the sweep uses this
    process's clock."""
    await sweeper.run(datetime.now(UTC))


def schedule() -> None:
    """Register `ops.sweep` as periodic in this process (idempotent)."""
    registry = jobs.app.periodic_registry
    if (SWEEP_TASK, "") in registry.periodic_tasks:
        return
    registry.register_task(
        task=sweep,
        cron=CRON,
        periodic_id="",
        configure_kwargs={"queueing_lock": SWEEP_TASK},
    )
