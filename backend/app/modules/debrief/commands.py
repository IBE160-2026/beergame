"""The only writer of the Debrief tables (Story 9.2, AD-21, AD-8).

Each command on a Debrief session locks its row and emits `debrief:<id>` (`platform/events`
registry: `debrief.open`). `release` writes the Class session's release once and tells each
Student who holds a Seat through `platform/notify` (`debrief.release`). Arguments are ids only."""

import uuid
from dataclasses import dataclass
from datetime import datetime

import structlog
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.debrief.models import debrief_releases, debrief_sessions
from app.modules.debrief.rules import all_class_games_finished
from app.modules.progress import service as progress
from app.platform import events, notify
from app.platform.db import get_sessionmaker

log = structlog.get_logger(__name__)

RELEASED_NOTICE = "debrief_released"
"""The notice each seated Student gets when a held Class session's Debriefs open (digest)."""


@dataclass(frozen=True)
class DebriefRow:
    id: uuid.UUID
    game_id: uuid.UUID
    class_session_id: uuid.UUID
    step: int


def row_of(row) -> DebriefRow:
    return DebriefRow(
        id=row["id"],
        game_id=row["game_id"],
        class_session_id=row["class_session_id"],
        step=row["step"],
    )


async def _locked(session: AsyncSession, game_id: uuid.UUID) -> DebriefRow:
    found = await session.execute(
        select(debrief_sessions).where(debrief_sessions.c.game_id == game_id).with_for_update()
    )
    return row_of(found.mappings().one())


async def open(game_id: uuid.UUID, class_session_id: uuid.UUID) -> DebriefRow:
    """The Debrief session of the Game, created with its step pointer at step 1 if none exists
    (FR-42). The caller has judged availability (`debrief.rules`). The row is locked; a new row
    emits `debrief:<id>`, an existing one is returned as it stands and emits nothing."""
    async with get_sessionmaker().begin() as session:
        created = await session.scalar(
            insert(debrief_sessions)
            .values(
                id=uuid.uuid7(),
                game_id=game_id,
                class_session_id=class_session_id,
                step=1,
                opened_at=func.now(),
            )
            .on_conflict_do_nothing(constraint="uq_debrief_sessions_game")
            .returning(debrief_sessions.c.id)
        )
        found = await _locked(session, game_id)
        if created is not None:
            await events.emit(session, "debrief", str(found.id))
            log.info("debrief_opened", debrief_id=str(found.id), game_id=str(game_id))
    return found


async def release(class_session_id: uuid.UUID, now: datetime) -> bool:
    """Mark a held Class session's Debriefs released, once, when every Class game has finished
    (AD-9): one notice per Student whose Class game it was (`progress` `class_game`, recorded at
    the end for every Student a Game ever seated, so one whose Seat an AI player took over is told
    too), each emitting `user:<id>` so Hjem updates.
    True when this call released it; False when it was released already or is not due."""
    async with get_sessionmaker().begin() as session:
        if not await all_class_games_finished(session, class_session_id):
            return False
        stored = await session.scalar(
            insert(debrief_releases)
            .values(class_session_id=class_session_id, released_at=now)
            .on_conflict_do_nothing(index_elements=[debrief_releases.c.class_session_id])
            .returning(debrief_releases.c.class_session_id)
        )
        if stored is None:
            return False
        students = await progress.users_with_step(
            session, class_session_id, progress.Step.CLASS_GAME
        )
        for user_id in students:
            await notify.enqueue(
                session,
                user_id,
                RELEASED_NOTICE,
                f"{RELEASED_NOTICE}:{class_session_id}:{user_id}",
                ref=class_session_id,
            )
    log.info("debriefs_released", class_session_id=str(class_session_id), students=len(students))
    return True
