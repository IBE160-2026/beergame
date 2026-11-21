"""The only writer of the Debrief tables (Stories 9.2, 9.3, 9.6, AD-21, AD-8).

Each command on a Debrief session locks its row and emits `debrief:<id>` (`platform/events`
registry: `debrief.open`, `debrief.save_explanation`, `debrief.complete_step`). `release` writes
the Class session's release once and tells each Student who holds a Seat through
`platform/notify` (`debrief.release`). Arguments are ids and the Student's text only."""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

import structlog
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.debrief.models import (
    debrief_explanations,
    debrief_reflection_answers,
    debrief_releases,
    debrief_sessions,
)
from app.modules.debrief.rules import all_class_games_finished
from app.modules.progress import service as progress
from app.platform import events, notify
from app.platform.db import get_sessionmaker

log = structlog.get_logger(__name__)

RELEASED_NOTICE = "debrief_released"
"""The notice each seated Student gets when a held Class session's Debriefs open (digest)."""


class ExplanationExists(Exception):
    """The Student has sent their Explanation in this Class session already (409
    `explanation_exists`): it is stored once and never changed (FR-41)."""


class AnswerOutOfOrder(Exception):
    """A reflection answer to a question that is not the Student's next one (409
    `reflection_out_of_order`): the questions are answered one at a time, in order (FR-45)."""


@dataclass(frozen=True)
class ExplanationRow:
    text: str
    length: int
    saved_at: datetime


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


async def save_explanation(
    game_id: uuid.UUID, class_session_id: uuid.UUID, user_id: uuid.UUID, text: str
) -> ExplanationRow:
    """«Send Forklaring» (Story 9.3, FR-41, AD-14, AD-16): store the Student's Explanation once,
    as typed, with its length in characters and the database time, and record the `explanation`
    step in the same transaction. The Debrief row of the Game is locked; the save emits
    `debrief:<id>` (and `progress` its `user` and `session`). The caller has judged availability
    and the text. Raises `ExplanationExists` when one is stored already, which stays unchanged."""
    async with get_sessionmaker().begin() as session:
        debrief = await _locked(session, game_id)
        stored = (
            (
                await session.execute(
                    insert(debrief_explanations)
                    .values(
                        user_id=user_id,
                        class_session_id=class_session_id,
                        game_id=game_id,
                        text=text,
                        length=len(text),
                        saved_at=func.now(),
                    )
                    .on_conflict_do_nothing(
                        index_elements=[
                            debrief_explanations.c.user_id,
                            debrief_explanations.c.class_session_id,
                        ]
                    )
                    .returning(
                        debrief_explanations.c.text,
                        debrief_explanations.c.length,
                        debrief_explanations.c.saved_at,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        if stored is None:
            raise ExplanationExists
        await progress.record_step(
            user_id, class_session_id, progress.Step.EXPLANATION, stored["saved_at"], within=session
        )
        await events.emit(session, "debrief", str(debrief.id))
    log.info("explanation_saved", debrief_id=str(debrief.id), length=stored["length"])
    return ExplanationRow(stored["text"], stored["length"], stored["saved_at"])


@dataclass(frozen=True)
class AnswerRow:
    question_id: str
    text: str
    length: int
    saved_at: datetime


async def complete_step(
    game_id: uuid.UUID,
    class_session_id: uuid.UUID,
    user_id: uuid.UUID,
    questions_version: int,
    question_ids: Sequence[str],
    question_id: str,
    text: str,
) -> AnswerRow:
    """«Fortsett» on a reflection question (Story 9.6, FR-45, AD-14, AD-21): store the Student's
    answer to `question_id`, as typed, with its length and the database time. The Debrief row of
    the Game is locked, so the order is judged against what is stored; a new answer emits
    `debrief:<id>`. `question_ids` are the pinned version's questions in the order asked, and the
    caller has judged that `question_id` is one of them and the text. An answered question
    returns the stored answer unchanged and emits nothing (a retry, a second device); any other
    question than the first unanswered one raises `AnswerOutOfOrder`."""
    async with get_sessionmaker().begin() as session:
        debrief = await _locked(session, game_id)
        stored = {
            row["question_id"]: AnswerRow(
                row["question_id"], row["text"], row["length"], row["saved_at"]
            )
            for row in (
                await session.execute(
                    select(debrief_reflection_answers).where(
                        debrief_reflection_answers.c.user_id == user_id,
                        debrief_reflection_answers.c.class_session_id == class_session_id,
                    )
                )
            ).mappings()
        }
        if question_id in stored:
            return stored[question_id]
        following = next((each for each in question_ids if each not in stored), None)
        if question_id != following:
            raise AnswerOutOfOrder
        saved_at = await session.scalar(
            insert(debrief_reflection_answers)
            .values(
                user_id=user_id,
                class_session_id=class_session_id,
                question_id=question_id,
                game_id=game_id,
                questions_version=questions_version,
                text=text,
                length=len(text),
                saved_at=func.now(),
            )
            .returning(debrief_reflection_answers.c.saved_at)
        )
        await events.emit(session, "debrief", str(debrief.id))
    log.info("reflection_answered", debrief_id=str(debrief.id), question_id=question_id)
    return AnswerRow(question_id, text, len(text), saved_at)
