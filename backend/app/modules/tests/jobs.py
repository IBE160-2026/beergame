"""The Individual test's `llm-batch` task (Story 11.8, AD-9): `tests.prepare_adapted(user_id,
class_session_id)`.

Deferred by the sweep (`tests.prepare.due_prepares`), with ids only. It builds the Student's
Adapted items, words them through the AI gateway where the templates allow it, falling back to the
code text, and stores one prepared set; it never retries a call. Delivered twice, or after the
Student opened the test, it stores nothing new."""

import structlog

from app.modules.tests import prepare
from app.platform import jobs

__all__ = ["prepare_adapted"]

log = structlog.get_logger(__name__)


@jobs.app.task(name=prepare.PREPARE_TASK, queue=jobs.LLM_BATCH)
async def prepare_adapted(user_id: str, class_session_id: str) -> None:
    try:
        stored = await prepare.prepare(user_id, class_session_id)
    except Exception as exc:  # the type only: an exception's text may hold personal data
        log.error(
            "adapted_items_prepare_failed",
            class_session_id=class_session_id,
            exc_type=type(exc).__name__,
        )
        raise
    log.info("adapted_items_prepare_done", class_session_id=class_session_id, stored=stored)
