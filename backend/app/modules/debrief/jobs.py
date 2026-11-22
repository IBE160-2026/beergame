"""The Debrief's `llm-batch` task (Story 9.14, AD-9): `debrief.narrate(game_id, seat_id)`.

Deferred by the finish hook of `debrief.narration` (and again by the sweep when lost), with ids
only. It words the Seat's narration and quiz lines through the AI gateway and stores them, each
falling back to its code text; it never retries a call. Delivered twice, it stores nothing new."""

import structlog

from app.modules.debrief import narration
from app.platform import jobs

__all__ = ["narrate_seat"]

log = structlog.get_logger(__name__)


@jobs.app.task(name=narration.NARRATE_TASK, queue=jobs.LLM_BATCH)
async def narrate_seat(game_id: str, seat_id: str) -> None:
    try:
        stored = await narration.narrate(game_id, seat_id)
    except Exception as exc:  # the type only: an exception's text may hold personal data
        log.error("debrief_narration_failed", game_id=game_id, exc_type=type(exc).__name__)
        raise
    log.info("debrief_narration_done", game_id=game_id, stored=stored)
