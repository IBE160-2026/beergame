"""Story 3.5: `ops.sweep` is the one periodic task. It only finds due work and calls the owner,
one item per transaction; a sweep that runs twice over one due notice gives one mail (AD-9)."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.modules.messaging import service as messaging
from app.modules.ops import jobs as ops_jobs
from app.modules.ops import sweep
from app.platform import jobs, ratelimit
from app.platform.db import get_sessionmaker
from tests.messaging.helpers import deliveries, drain, enqueue, mails, oslo, rows, user

APP = Path(__file__).parents[2] / "app"


async def test_two_sweeps_over_one_due_notice_give_one_mail(mail_db):
    user_id = await user()
    await enqueue(user_id, "test_immediate")
    rows("DELETE FROM procrastinate_jobs RETURNING id")  # the claim job was lost
    now = datetime.now(UTC)
    assert (await sweep.run(now))["messaging.mail"] == 1
    assert (await sweep.run(now))["messaging.mail"] == 0
    await drain()
    await sweep.run(now)
    await drain()
    assert len(mails()) == 1
    assert deliveries() == [("immediate", 1, True, None, 1)]


async def test_a_lost_mail_job_is_deferred_again_by_the_sweep(mail_db):
    user_id = await user()
    await enqueue(user_id, "test_immediate")
    [(notice_id,)] = rows("SELECT id FROM notices")
    now = datetime.now(UTC)
    await messaging.claim_notice(notice_id, now)
    rows("DELETE FROM procrastinate_jobs RETURNING id")  # the claim and `mail` jobs were lost
    assert (await sweep.run(now + timedelta(minutes=1)))["messaging.mail"] == 0
    assert (await sweep.run(now + messaging.RETRY_AFTER))["messaging.mail"] == 1
    await drain()
    assert len(mails()) == 1
    assert deliveries() == [("immediate", 1, True, None, 1)]


async def test_a_failing_item_is_logged_and_the_sweep_goes_on(mail_db, monkeypatch):
    calls = []

    async def find(now):
        return ["bad", "good"]

    async def act(item, now):
        calls.append(item)
        if item == "bad":
            raise RuntimeError("boom")

    async def broken(now):
        raise RuntimeError("find failed")

    monkeypatch.setattr(
        sweep,
        "DUE_ACTIONS",
        (sweep.DueAction("broken", broken, act), sweep.DueAction("test", find, act)),
    )
    assert await sweep.run(oslo(12, 9)) == {"broken": 0, "test": 1}
    assert calls == ["bad", "good"]


async def test_the_sweep_purges_old_rate_limit_windows(mail_db):
    now = datetime(2027, 1, 12, 9, tzinfo=UTC)
    async with get_sessionmaker().begin() as session:
        await ratelimit.hit(
            session, "b", "old", window=timedelta(minutes=15), now=now - timedelta(days=2)
        )
        await ratelimit.hit(session, "b", "new", window=timedelta(minutes=15), now=now)
    assert (await sweep.run(now))["ratelimit.purge"] == 1
    assert rows("SELECT count(*) FROM rate_limit_counters WHERE bucket = 'b'") == [(1,)]


@pytest.fixture
def clean_registry():
    registry = jobs.app.periodic_registry.periodic_tasks
    saved = dict(registry)
    registry.clear()
    yield registry
    registry.clear()
    registry.update(saved)


def test_schedule_registers_the_sweep_every_minute_once(clean_registry):
    ops_jobs.schedule()
    ops_jobs.schedule()
    [periodic] = clean_registry.values()
    assert periodic.task.name == "ops.sweep" and periodic.cron == "* * * * *"
    assert periodic.task.queue == jobs.SWEEP
    assert periodic.configure_kwargs["queueing_lock"] == "ops.sweep"


def test_nothing_else_is_periodic():
    """There is no other cron: only `ops/jobs.py` registers a periodic task."""
    for path in sorted(APP.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        if ".periodic(" in source or "register_task(" in source:
            assert path == APP / "modules" / "ops" / "jobs.py", path


async def test_the_sweep_task_runs_one_sweep(mail_db, monkeypatch):
    seen = []

    async def run(now):
        seen.append(now)
        return {}

    monkeypatch.setattr(sweep, "run", run)
    await ops_jobs.sweep(timestamp=0)
    assert len(seen) == 1 and seen[0].tzinfo is not None


async def test_the_sweeper_worker_can_defer_the_periodic_sweep(
    mail_db, clean_registry, monkeypatch
):
    """The periodic deferrer defers through the task's own app, so `run_worker` must open that
    app, not a copy (found on the local stack: `AppNotOpen`)."""
    from procrastinate import periodic

    ops_jobs.schedule()
    [task] = clean_registry.values()

    async def run_worker_async(**kwargs):
        deferrer = periodic.PeriodicDeferrer(registry=jobs.app.periodic_registry)
        await deferrer.defer_jobs([(task, 1_800_000_000)])

    monkeypatch.setattr(jobs.app, "run_worker_async", run_worker_async)
    await jobs.run_worker([jobs.SWEEP], wait=False, install_signal_handlers=False)
    assert rows("SELECT queue_name, task_name FROM procrastinate_jobs") == [("sweep", "ops.sweep")]
