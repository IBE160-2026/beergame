"""Story 2.5: `python -m app.worker --queues …` (AD-9, AD-24). The worker loop itself is
procrastinate's; the job tests drive it with `run_until_idle`."""

import pytest

from app import worker
from app.platform import jobs


def test_queues_are_read_comma_separated_or_repeated_without_repeats():
    assert worker.queues(["ai-orders"]) == ["ai-orders"]
    assert worker.queues(["ai-orders, llm-batch", "ai-orders"]) == ["ai-orders", "llm-batch"]


@pytest.mark.parametrize("argv", [[], ["--queues", "reports"], ["--queues", ","]])
def test_a_missing_or_unknown_queue_exits_2(capsys, argv):
    with pytest.raises(SystemExit) as info:
        worker.main(argv)
    assert info.value.code == 2
    assert "queue" in capsys.readouterr().err


def test_main_runs_a_worker_on_the_named_queues(monkeypatch):
    seen = {}
    order = []

    async def run_worker(queues, *, concurrency):
        order.append("serve")
        seen.update(queues=queues, concurrency=concurrency)

    async def loop(interval_s=5.0, stop=None):
        await stop.wait()

    from app.ai import seed
    from app.modules.players import rescue

    async def seeded():
        order.append("seed")
        seen["seeded"] = True

    monkeypatch.setattr(jobs, "run_worker", run_worker)
    monkeypatch.setattr(rescue, "run", loop)
    monkeypatch.setattr(seed, "ensure_zero_config_logged", seeded)
    assert worker.main(["--queues", "ai-orders,llm-batch", "--concurrency", "3"]) == 0
    # AD-17: the worker seeds the zero-config default before it serves (Story 2.12).
    assert seen == {"seeded": True, "queues": ["ai-orders", "llm-batch"], "concurrency": 3}
    assert order == ["seed", "serve"]


def test_the_sweeper_flag_schedules_the_sweep_and_runs_its_queue(monkeypatch):
    """Story 3.5: `worker-batch` runs `--queues llm-batch,mail --sweeper`; only that process
    registers the periodic `ops.sweep`."""
    from app.ai import seed
    from app.modules.ops import jobs as ops_jobs

    seen = {}

    async def run_worker(queues, *, concurrency):
        seen["queues"] = queues

    async def seeded():
        pass

    monkeypatch.setattr(jobs, "run_worker", run_worker)
    monkeypatch.setattr(seed, "ensure_zero_config_logged", seeded)
    monkeypatch.setattr(ops_jobs, "schedule", lambda: seen.setdefault("scheduled", True))
    assert worker.main(["--queues", "llm-batch,mail", "--sweeper"]) == 0
    assert seen == {"scheduled": True, "queues": ["llm-batch", "mail", "sweep"]}
    seen.clear()
    assert worker.main(["--queues", "mail"]) == 0
    assert seen == {"queues": ["mail"]}
    with pytest.raises(SystemExit):  # the sweeper alone is not a queue list
        worker.main(["--queues", ",", "--sweeper"])


def test_the_worker_knows_the_mail_and_sweep_tasks_by_name():
    jobs.load_tasks()
    assert jobs.app.tasks["messaging.claim_notice"].queue == jobs.MAIL
    assert jobs.app.tasks["messaging.send_mail"].queue == jobs.MAIL
    assert jobs.app.tasks["ops.sweep"].queue == jobs.SWEEP


def test_the_concurrency_must_be_positive(capsys):
    with pytest.raises(SystemExit) as info:
        worker.main(["--queues", "ai-orders", "--concurrency", "0"])
    assert info.value.code == 2


async def test_run_worker_refuses_an_unknown_queue_or_none():
    with pytest.raises(ValueError, match="unknown queue"):
        await jobs.run_worker(["reports"])
    with pytest.raises(ValueError, match="no queue"):
        await jobs.run_worker([])


def test_the_worker_knows_the_llm_order_task_by_its_name():
    jobs.load_tasks()
    assert "players.place_llm_order" in jobs.app.tasks
    assert jobs.app.tasks["players.place_llm_order"].queue == jobs.AI_ORDERS


async def test_run_until_idle_returns_when_no_job_waits(games_db):
    await jobs.run_until_idle([jobs.AI_ORDERS, jobs.LLM_BATCH])


def test_conninfo_is_the_database_url_for_libpq():
    url = "postgresql+psycopg://u:p@db:5432/x"
    assert jobs.conninfo(url) == "postgresql://u:p@db:5432/x"


async def test_an_ai_orders_worker_runs_the_rescue_loop_until_the_worker_stops(monkeypatch):
    """Story 2.6: `worker-ai` runs the rescue loop beside the worker; it stops with the
    worker. A worker without `ai-orders` runs no loop."""
    import asyncio

    from app.modules.players import rescue

    seen = []

    async def run_worker(queues, *, concurrency):
        seen.append(("worker", list(queues)))
        await asyncio.sleep(0)

    async def loop(interval_s=rescue.RESCUE_INTERVAL_S, stop=None):
        seen.append(("loop", interval_s))
        await stop.wait()
        seen.append(("loop stopped", stop.is_set()))

    monkeypatch.setattr(jobs, "run_worker", run_worker)
    monkeypatch.setattr(rescue, "run", loop)
    await asyncio.wait_for(worker.serve(["ai-orders"], concurrency=1), timeout=1)
    # The loop task starts when the worker first yields.
    assert seen == [("worker", ["ai-orders"]), ("loop", 5.0), ("loop stopped", True)]
    seen.clear()
    await worker.serve(["llm-batch"], concurrency=1)
    assert seen == [("worker", ["llm-batch"])]
