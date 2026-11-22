"""Worker entry point (`python -m app.worker --queues ai-orders`, AD-9, AD-24).

`worker-ai` runs `--queues ai-orders` and `worker-batch` `--queues llm-batch,mail --sweeper`,
both from the backend image. `--sweeper` makes the worker defer the per-minute `ops.sweep` and
run its `sweep` queue (Story 3.5); exactly one process runs with it. A worker with `ai-orders`
also runs the rescue loop every 5 seconds (Story 2.6), which places the fallback Order of an LLM
player past its deadline. A worker needs no provider key: with none set, the AI mock answers in
`local`, `test` and `ci` (AD-17). Queues are given comma-separated or with `--queues` repeated.
"""

import argparse
import asyncio
import sys
from collections.abc import Sequence

from app.platform import error_reporting, jobs
from app.platform.config import get_settings
from app.platform.logging import configure_logging


def queues(values: Sequence[str]) -> list[str]:
    """The queues named in `--queues` values, in order and without repeats."""
    found: list[str] = []
    for value in values:
        for name in (part.strip() for part in value.split(",")):
            if name and name not in found:
                found.append(name)
    return found


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.worker", description=__doc__)
    parser.add_argument(
        "--queues",
        action="append",
        required=True,
        help=f"queue(s) to run, comma-separated or repeated: {', '.join(jobs.QUEUES)}",
    )
    parser.add_argument("--concurrency", type=int, default=1, help="jobs run at once (1)")
    parser.add_argument(
        "--sweeper",
        action="store_true",
        help="also defer and run the per-minute ops.sweep (one process only)",
    )
    return parser


async def serve(names: Sequence[str], *, concurrency: int) -> None:
    """Run the worker on `names`; with `ai-orders` among them, also the rescue loop
    (`players.rescue`, AD-5), which stops when the worker stops. A job that fails for good is
    counted under its Class session through `ops.service` (Story 15.8)."""
    from app.modules.ops import service as ops_service

    on_failure = ops_service.record_job_failure
    if jobs.AI_ORDERS not in names:
        await jobs.run_worker(names, concurrency=concurrency, on_failure=on_failure)
        return
    from app.modules.players import rescue

    stop = asyncio.Event()
    loop = asyncio.create_task(rescue.run(stop=stop))
    try:
        await jobs.run_worker(names, concurrency=concurrency, on_failure=on_failure)
    finally:
        stop.set()
        await loop


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    names = queues(args.queues)
    if not names:
        parser.error(f"no queue given; use {', '.join(jobs.QUEUES)}")
    if args.sweeper and jobs.SWEEP not in names:
        names.append(jobs.SWEEP)
    unknown = [name for name in names if name not in jobs.QUEUES]
    if unknown:
        parser.error(f"unknown queue(s) {', '.join(unknown)}; use {', '.join(jobs.QUEUES)}")
    if args.concurrency < 1:
        parser.error("--concurrency must be at least 1")
    configure_logging(get_settings().log_level)
    if args.sweeper:
        from app.modules.ops import jobs as ops_jobs

        ops_jobs.schedule()
    # psycopg's async mode cannot run on Windows' default Proactor loop.
    factory = asyncio.SelectorEventLoop if sys.platform == "win32" else asyncio.new_event_loop
    asyncio.run(_start(names, concurrency=args.concurrency), loop_factory=factory)
    return 0


async def _start(names: Sequence[str], *, concurrency: int) -> None:
    """Seed the zero-config default where allowed (AD-17), log and record the connections this
    worker holds against the written budget (Story 15.9), then serve."""
    from app.ai import seed
    from app.modules.ops import service as ops_service

    await seed.ensure_zero_config_logged()
    error_reporting.log_start(get_settings())  # Story 15.11: the tracker, or that none is set
    await ops_service.report_connections(
        ops_service.worker_process(list(names)), get_settings(), concurrency=concurrency
    )
    await serve(names, concurrency=concurrency)


if __name__ == "__main__":
    raise SystemExit(main())
