"""`scripts/deploy-overlap` (Story 15.9): its parsing and verdict, without Docker. The script
itself is run against the Compose stack; its result is in `docs/ops/connection-budget.md`."""

import importlib.machinery
import importlib.util
from pathlib import Path

from app.modules.ops import connection_budget

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "deploy-overlap"


def load_script():
    loader = importlib.machinery.SourceFileLoader("deploy_overlap", str(SCRIPT))
    spec = importlib.util.spec_from_loader("deploy_overlap", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


overlap = load_script()


def test_the_limit_is_the_overlap_budget():
    assert overlap.OVERLAP_LIMIT == connection_budget.overlap_total()
    assert set(overlap.SERVICES) == set(connection_budget.BUDGET)


def test_activity_is_counted_per_service_and_the_peak_is_of_the_services_together():
    peaks = overlap.Peaks()
    peaks.add(overlap.parse_activity("olspillet-backend|3\nolspillet-worker-ai|2\n|4\n"))
    peaks.add(
        overlap.parse_activity(
            "olspillet-backend|6\nolspillet-worker-batch|2\nolspillet-sim|5\npsql|1\nnoise\n"
        )
    )
    assert peaks.per_service == {"backend": 6, "worker-ai": 2, "worker-batch": 2}
    assert (peaks.services, peaks.sim, peaks.samples) == (8, 5, 2)


def test_log_problems_finds_pool_timeouts_and_refused_connections():
    logs = "\n".join(
        [
            'backend-1 | {"event": "request", "status": 200}',
            "backend-2 | sqlalchemy.exc.TimeoutError: QueuePool limit of size 10 overflow 0",
            "worker-ai-1 | FATAL:  sorry, too many clients already",
            'worker-ai-1 | {"event": "llm_attempt", "exc_type": "TimeoutError"}',
            "worker-batch-1 | psycopg_pool.PoolTimeout: couldn't get a connection after 30 sec",
        ]
    )
    assert len(overlap.log_problems(logs)) == 3


def _verdict(**changes):
    peaks = overlap.Peaks()
    peaks.add({"olspillet-backend": 12, "olspillet-worker-ai": 4, "olspillet-worker-batch": 6})
    values = {
        "started": {"backend": 2, "worker-ai": 2, "worker-batch": 2},
        "sim_exit": 0,
        "requests": 500,
        "failed_requests": 0,
        "peaks": peaks,
        "limit": 50,
        "problems": [],
    }
    values.update(changes)
    return overlap.verdict(**values)


def test_every_line_passes_on_a_clean_overlap():
    lines = _verdict()
    assert all(passed for passed, _ in lines)
    assert "peak connections 22 <= 50" in lines[3][1]


def test_each_failure_fails_its_own_line():
    assert [p for p, _ in _verdict(started={"backend": 2})] == [False, True, True, True, True]
    assert [p for p, _ in _verdict(sim_exit=1)] == [True, False, True, True, True]
    assert [p for p, _ in _verdict(failed_requests=1)] == [True, True, False, True, True]
    assert [p for p, _ in _verdict(requests=0)] == [True, True, False, True, True]
    assert [p for p, _ in _verdict(limit=21)] == [True, True, True, False, True]
    assert [p for p, _ in _verdict(peaks=overlap.Peaks())] == [True, True, True, False, True]
    assert [p for p, _ in _verdict(problems=["x"])] == [True, True, True, True, False]
