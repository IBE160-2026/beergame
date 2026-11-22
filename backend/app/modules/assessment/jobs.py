"""The AI assessment's `llm-batch` task (Story 12.2, AD-9): `assessment.assess(attempt_id)`.

Deferred by `tests.commands.close_attempt` through `service.schedule`, and again by its own run
while an item lacks a score, with the attempt id only. Idempotent on the attempt: a run on a
`ready` or `failed` assessment stores nothing. It never retries a call itself."""

import uuid

import structlog

from app.modules.assessment import service
from app.platform import jobs

__all__ = ["assess"]

log = structlog.get_logger(__name__)


@jobs.app.task(name=service.ASSESS_TASK, queue=jobs.LLM_BATCH)
async def assess(attempt_id: str) -> None:
    try:
        outcome = await service.assess(uuid.UUID(attempt_id))
    except Exception as exc:  # the type only: an exception's text may hold personal data
        log.error("assessment_failed", attempt_id=attempt_id, exc_type=type(exc).__name__)
        raise
    log.info("assessment_done", attempt_id=attempt_id, outcome=outcome)
