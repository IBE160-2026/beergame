"""What a worker loads of `replay` (Stories 10.5 and 10.7): its finish hooks and its task.

A Replay's last Order may be an AI player's, placed by the `ai-orders` worker, so the worker must
have `replay.service`'s and `replay.walkthrough`'s hooks registered
(`games.service.on_game_finished`) for the Replay's `replay` step to be recorded and its
walkthrough line deferred in that finish. `platform.jobs.TASK_MODULES` names this module, so
every worker imports it before it runs.

Story 10.7: `replay.narrate_walkthrough(game_id)` on `llm-batch` words a finished Replay's
walkthrough line through the AI gateway and stores it once, falling back to its code text; it
never retries a call. Delivered twice, it stores nothing new."""

import structlog

from app.modules.replay import service, walkthrough
from app.platform import jobs

__all__ = ["narrate_walkthrough", "service", "walkthrough"]

log = structlog.get_logger(__name__)


@jobs.app.task(name=walkthrough.NARRATE_TASK, queue=jobs.LLM_BATCH)
async def narrate_walkthrough(game_id: str) -> None:
    try:
        stored = await walkthrough.narrate(game_id)
    except Exception as exc:  # the type only: an exception's text may hold personal data
        log.error("replay_walkthrough_failed", game_id=game_id, exc_type=type(exc).__name__)
        raise
    log.info("replay_walkthrough_done", game_id=game_id, stored=stored)
