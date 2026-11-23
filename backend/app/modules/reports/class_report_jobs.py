"""The Klasserapport's facts sets (Story 14.1, AD-7, AD-9, AD-25).

Forsterkning and «Mønstre» read the stored facts sets of a finished Class game's Seats, and the
report never builds one: building runs the «Simulert, samme kunder» part, a replay of the Game.
So the finish of every Class game defers `reports.store_class_facts(game_id, class_session_id)`
on `llm-batch` (the finish hook `reports.class_facts`, inside the finishing transaction, ids
only, one job per game by its queueing lock). The task stores the four Seats' sets through
`games.service.fact_set` (built once, never rebuilt; a set the Debrief stored already is kept)
and emits `session:<id>`, so an open Klasserapport refetches. Delivered twice, it stores nothing
new and announces again, which only refetches.

`platform.jobs.TASK_MODULES` names this module, so every worker registers the hook (an AI
player's Order may finish a Class game in `worker-ai`); `app.main` imports it for the api."""

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.settings import ROLES
from app.modules.games import service as games
from app.modules.games.service import Purpose
from app.modules.reports import scope
from app.platform import events, jobs
from app.platform.db import get_sessionmaker

__all__ = ["FINISH_HOOK", "STORE_TASK", "facts_key", "store_class_facts"]

log = structlog.get_logger(__name__)

STORE_TASK = "reports.store_class_facts"
FINISH_HOOK = "reports.class_facts"


def facts_key(game_id: object) -> str:
    return f"class-facts:{game_id}"


async def _defer_on_finish(session: AsyncSession, finished: games.FinishedGame) -> None:
    """The finish hook: one job per finished Class game of a Class session. A Replay, a make-up
    game, a Lecturer's test Game, a simulation and a Control test's game are never in the
    Klasserapport (AD-13, AD-27)."""
    if finished.class_session_id is None or finished.purpose != Purpose.CLASS:
        return
    # A Control test Class session is in no report (AD-27): its games need no facts sets here.
    if not await scope.is_reporting_session(session, finished.class_session_id):
        return
    await jobs.defer(
        session,
        STORE_TASK,
        queue=jobs.LLM_BATCH,
        queueing_lock=facts_key(finished.game_id),
        game_id=str(finished.game_id),
        class_session_id=str(finished.class_session_id),
    )


games.on_game_finished(FINISH_HOOK, _defer_on_finish)


async def store(game_id: str, class_session_id: str) -> None:
    """Store the facts set of every Seat of the finished Class game, then announce its Class
    session. Raises as `games.service.fact_set` does (`ViewError`)."""
    for role in ROLES:
        await games.fact_set(game_id, str(role))
    async with get_sessionmaker().begin() as s:
        await events.emit(s, "session", str(uuid.UUID(class_session_id)))


@jobs.app.task(name=STORE_TASK, queue=jobs.LLM_BATCH)
async def store_class_facts(game_id: str, class_session_id: str) -> None:
    try:
        await store(game_id, class_session_id)
    except Exception as exc:  # the type only: an exception's text may hold personal data
        log.error("class_facts_failed", game_id=game_id, exc_type=type(exc).__name__)
        raise
    log.info("class_facts_stored", game_id=game_id)
