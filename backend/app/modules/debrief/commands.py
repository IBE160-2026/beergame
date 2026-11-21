"""The only writer of the Debrief tables (Stories 9.2, 9.3, 9.6 to 9.10, AD-21, AD-8).

Each command on a Debrief session locks its row and emits `debrief:<id>` (`platform/events`
registry: `debrief.open`, `debrief.save_explanation`, `debrief.complete_step`,
`debrief.record_facts`, `debrief.finish`, `debrief.submit_quiz`). `release` writes
the Class session's release once and tells each Student who holds a Seat through
`platform/notify` (`debrief.release`). `set_quiz_exclusions` (Story 9.10) locks the Class
session row instead, records the change through `platform/audit`, emits `session:<id>` and tells
each Student whose last attempt it covers (`debrief.set_quiz_exclusions`). Arguments are ids and
the Student's text only."""

import uuid
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.debrief.models import (
    debrief_explanations,
    debrief_fact_sets,
    debrief_reflection_answers,
    debrief_releases,
    debrief_sessions,
    debrief_summaries,
    quiz_attempts,
    quiz_exclusions,
)
from app.modules.debrief.rules import all_class_games_finished, last_attempts
from app.modules.progress import service as progress
from app.modules.sessions import service as sessions
from app.platform import audit, events, notify
from app.platform.db import get_sessionmaker

log = structlog.get_logger(__name__)

RELEASED_NOTICE = "debrief_released"
"""The notice each seated Student gets when a held Class session's Debriefs open (digest)."""

QUIZ_CHANGED_NOTICE = "quiz_changed"
"""The notice a Student gets when the Lecturer takes out every question their last Debrief quiz
attempt got wrong (Story 9.10, digest)."""

EXCLUSIONS_CHANGED = "debrief_quiz.exclusions_changed"
"""The audit action of a change to a Class session's Debrief quiz exclusions (Story 9.10)."""


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


async def record_facts(
    game_id: uuid.UUID, class_session_id: uuid.UUID, user_id: uuid.UUID, fact_set_id: uuid.UUID
) -> uuid.UUID:
    """The Student's first view of step 4 (Story 9.7, AD-7): store the id of the facts set their
    own moments are rendered from, once. The Debrief row of the Game is locked; a new row emits
    `debrief:<id>`. Returns the stored id, which a later call (a reload, a second device) keeps
    whatever it is given, and which emits nothing."""
    async with get_sessionmaker().begin() as session:
        debrief = await _locked(session, game_id)
        created = await session.scalar(
            insert(debrief_fact_sets)
            .values(
                user_id=user_id,
                class_session_id=class_session_id,
                game_id=game_id,
                fact_set_id=fact_set_id,
                recorded_at=func.now(),
            )
            .on_conflict_do_nothing(
                index_elements=[debrief_fact_sets.c.user_id, debrief_fact_sets.c.class_session_id]
            )
            .returning(debrief_fact_sets.c.fact_set_id)
        )
        if created is not None:
            await events.emit(session, "debrief", str(debrief.id))
            log.info("moments_facts_recorded", debrief_id=str(debrief.id))
            return created
        stored = await session.scalar(
            select(debrief_fact_sets.c.fact_set_id).where(
                debrief_fact_sets.c.user_id == user_id,
                debrief_fact_sets.c.class_session_id == class_session_id,
            )
        )
    assert stored is not None
    return stored


class DebriefIncomplete(Exception):
    """«Fullfør Debriefen» before every reflection question is answered or before step 4 was seen
    (409 `debrief_incomplete`)."""


class TestDeadlinePassed(Exception):
    """«Fullfør Debriefen» after the Student's Test deadline (409 `test_deadline_passed`): the
    Debrief stays open until then (FR-18)."""


@dataclass(frozen=True)
class SummaryRow:
    game_id: uuid.UUID
    fact_set_id: uuid.UUID
    moment_ids: tuple[str, ...]
    reflection: tuple[dict[str, Any], ...]
    finished_at: datetime


def summary_of(row) -> SummaryRow:
    return SummaryRow(
        game_id=row["game_id"],
        fact_set_id=row["fact_set_id"],
        moment_ids=tuple(row["moment_ids"]),
        reflection=tuple(row["reflection"]),
        finished_at=row["finished_at"],
    )


async def finish(
    game_id: uuid.UUID,
    class_session_id: uuid.UUID,
    user_id: uuid.UUID,
    question_ids: Sequence[str],
    moment_ids_of: Callable[[uuid.UUID], Awaitable[Sequence[str]]],
    test_deadline: datetime | None,
) -> tuple[SummaryRow, bool]:
    """«Fullfør Debriefen» (Story 9.8, FR-47, AD-7, AD-16): store the Student's Debrief summary
    once (the key moments by fact id, the reflection answers in the order asked, the facts set
    their moments cite and the database time) and record the `debrief` step at that time in the
    same transaction. The Debrief row of the Game is locked; a new summary emits `debrief:<id>`
    (and `progress` its `user` and `session`). `question_ids` are the pinned reflection questions
    in the order asked; `moment_ids_of(fact_set_id)` gives the cited set's moment ids.

    A stored summary is returned unchanged with False, and emits nothing (a retry, a second
    device). Raises `DebriefIncomplete` while a question is unanswered or the facts set is not
    recorded (step 4 not seen), and `TestDeadlinePassed` once the database time is past
    `test_deadline`."""
    async with get_sessionmaker().begin() as session:
        debrief = await _locked(session, game_id)
        mine = (
            debrief_summaries.c.user_id == user_id,
            debrief_summaries.c.class_session_id == class_session_id,
        )
        stored = (
            (await session.execute(select(debrief_summaries).where(*mine))).mappings().one_or_none()
        )
        if stored is not None:
            return summary_of(stored), False
        if test_deadline is not None and await session.scalar(select(func.now() > test_deadline)):
            raise TestDeadlinePassed
        cited = await session.scalar(
            select(debrief_fact_sets.c.fact_set_id).where(
                debrief_fact_sets.c.user_id == user_id,
                debrief_fact_sets.c.class_session_id == class_session_id,
            )
        )
        answered = {
            row["question_id"]: row
            for row in (
                await session.execute(
                    select(debrief_reflection_answers).where(
                        debrief_reflection_answers.c.user_id == user_id,
                        debrief_reflection_answers.c.class_session_id == class_session_id,
                    )
                )
            ).mappings()
        }
        if cited is None or not question_ids or any(q not in answered for q in question_ids):
            raise DebriefIncomplete
        reflection = [
            {
                "question_id": q,
                "questions_version": answered[q]["questions_version"],
                "text": answered[q]["text"],
            }
            for q in question_ids
        ]
        saved = (
            (
                await session.execute(
                    insert(debrief_summaries)
                    .values(
                        user_id=user_id,
                        class_session_id=class_session_id,
                        game_id=game_id,
                        fact_set_id=cited,
                        moment_ids=list(await moment_ids_of(cited)),
                        reflection=reflection,
                        finished_at=func.now(),
                    )
                    .returning(*debrief_summaries.c)
                )
            )
            .mappings()
            .one()
        )
        await progress.record_step(
            user_id, class_session_id, progress.Step.DEBRIEF, saved["finished_at"], within=session
        )
        await events.emit(session, "debrief", str(debrief.id))
    log.info("debrief_finished", debrief_id=str(debrief.id))
    return summary_of(saved), True


class QuizPassed(Exception):
    """An attempt after the Student has passed the Debrief quiz (409 `quiz_passed`): the passing
    attempt stays the last."""


@dataclass(frozen=True)
class AttemptRow:
    number: int
    quiz_version: int
    answers: tuple[dict[str, Any], ...]
    passed: bool
    submitted_at: datetime


def attempt_of(row) -> AttemptRow:
    return AttemptRow(
        number=row["number"],
        quiz_version=row["quiz_version"],
        answers=tuple(row["answers"]),
        passed=row["passed"],
        submitted_at=row["submitted_at"],
    )


async def submit_quiz(
    game_id: uuid.UUID,
    class_session_id: uuid.UUID,
    user_id: uuid.UUID,
    quiz_version: int,
    answers: Sequence[dict[str, Any]],
    test_deadline: datetime | None,
) -> AttemptRow:
    """A scored attempt at the Debrief quiz (Story 9.9, FR-46, AD-16, AD-23): store it once as the
    Student's next attempt (numbered from 1), with the quiz version, the answers in the order
    shown (`{question_id, choice_id, correct}`, scored by the caller with the answer key) and the
    database time. It passes when every answer is correct; a passing attempt records the
    `quiz_passed` step at that time in the same transaction. The Debrief row of the Game is
    locked; every attempt emits `debrief:<id>` (and a passing one, through `progress`, its `user`
    and `session`).

    Raises `QuizPassed` once an attempt has passed, and `TestDeadlinePassed` once the database
    time is past `test_deadline`; nothing is stored then."""
    passed = bool(answers) and all(each["correct"] for each in answers)
    async with get_sessionmaker().begin() as session:
        debrief = await _locked(session, game_id)
        mine = (
            quiz_attempts.c.user_id == user_id,
            quiz_attempts.c.class_session_id == class_session_id,
        )
        done, count = (
            await session.execute(
                select(func.bool_or(quiz_attempts.c.passed), func.count()).where(*mine)
            )
        ).one()
        if done:
            raise QuizPassed
        if test_deadline is not None and await session.scalar(select(func.now() > test_deadline)):
            raise TestDeadlinePassed
        saved = (
            (
                await session.execute(
                    insert(quiz_attempts)
                    .values(
                        id=uuid.uuid7(),
                        user_id=user_id,
                        class_session_id=class_session_id,
                        game_id=game_id,
                        number=count + 1,
                        quiz_version=quiz_version,
                        answers=list(answers),
                        passed=passed,
                        submitted_at=func.now(),
                    )
                    .returning(*quiz_attempts.c)
                )
            )
            .mappings()
            .one()
        )
        if passed:
            await progress.record_step(
                user_id,
                class_session_id,
                progress.Step.QUIZ_PASSED,
                saved["submitted_at"],
                within=session,
            )
        await events.emit(session, "debrief", str(debrief.id))
    log.info("quiz_attempted", debrief_id=str(debrief.id), number=saved["number"], passed=passed)
    return attempt_of(saved)


class LastQuestion(Exception):
    """An exclusion that would leave the Debrief quiz with no question (409 `last_question`)."""


class UnknownQuizQuestion(Exception):
    """An exclusion of a question the Class session's quiz version does not have (422)."""


@dataclass(frozen=True)
class QuizVersion:
    """The Debrief quiz a Class session uses: its version and its question ids, in order."""

    version: int
    question_ids: tuple[str, ...]


async def set_quiz_exclusions(
    class_session_id: uuid.UUID,
    actor_id: uuid.UUID,
    wanted: Sequence[str],
    resolve: Callable[[Any], Awaitable[QuizVersion]],
) -> tuple[QuizVersion, frozenset[str]]:
    """«Lagre quizvalg» (Story 9.10, FR-46, AD-23, AD-15): make `wanted` the Class session's
    Debrief quiz exclusions, as Class session rows (never an edit of the content record). In one
    transaction holding the Class session's lock (`sessions.lock_for_quiz_exclusions`, which
    refuses an archived Class): `resolve(pins)` gives the quiz version the lock pinned (the latest
    before the lock). Raises `UnknownQuizQuestion` for an id the version does not have,
    `LastQuestion` when no question would be asked and `TestDeadlinePassed` once the database
    time is past the Class session's Test deadline; nothing is stored then. An unchanged set
    writes nothing. A change stores and deletes rows, records one audit row (ids only), emits
    `session:<id>`, and enqueues a `quiz_changed` notice for each Student who has not passed and
    whose last attempt got wrong only questions now taken out, one of them in this change. No
    Student is passed by it. Answers the version and the exclusions now."""
    wanted_set = frozenset(wanted)
    async with get_sessionmaker().begin() as session:
        pins, test_deadline = await sessions.lock_for_quiz_exclusions(session, class_session_id)
        quiz = await resolve(pins)
        if not wanted_set <= set(quiz.question_ids):
            raise UnknownQuizQuestion
        if wanted_set >= set(quiz.question_ids):
            raise LastQuestion
        if test_deadline is not None and await session.scalar(select(func.now() > test_deadline)):
            raise TestDeadlinePassed
        stored = frozenset(
            (
                await session.scalars(
                    select(quiz_exclusions.c.question_id).where(
                        quiz_exclusions.c.class_session_id == class_session_id
                    )
                )
            ).all()
        )
        # Rows of another version (taken out before a lock pinned a newer one) count as they are.
        excluded = sorted(wanted_set - stored)
        lifted = sorted((stored - wanted_set) & set(quiz.question_ids))
        if not excluded and not lifted:
            return quiz, stored & set(quiz.question_ids)
        if lifted:
            await session.execute(
                quiz_exclusions.delete().where(
                    quiz_exclusions.c.class_session_id == class_session_id,
                    quiz_exclusions.c.question_id.in_(lifted),
                )
            )
        for question_id in excluded:
            await session.execute(
                insert(quiz_exclusions).values(
                    class_session_id=class_session_id,
                    question_id=question_id,
                    quiz_version=quiz.version,
                    excluded_by=actor_id,
                    excluded_at=func.now(),
                )
            )
        now = await session.scalar(select(func.now()))
        change_id = await audit.record(
            session,
            actor_id,
            EXCLUSIONS_CHANGED,
            {"class_session_id": class_session_id},
            {"excluded": excluded, "lifted": lifted, "quiz_version": quiz.version},
            now,
        )
        told = 0
        newly = set(excluded)
        for user_id, attempt in (await last_attempts(session, class_session_id)).items():
            wrong = {a["question_id"] for a in attempt["answers"] if not a["correct"]}
            if attempt["passed"] or not wrong:
                continue
            if not wrong <= wanted_set or not wrong & newly:
                # Hjem's «quizen er endret» turned off by a lift: the Student's pages read again.
                if wrong <= stored:
                    await events.emit(session, "user", str(user_id))
                continue
            await notify.enqueue(
                session,
                user_id,
                QUIZ_CHANGED_NOTICE,
                f"{QUIZ_CHANGED_NOTICE}:{class_session_id}:{user_id}:{change_id}",
                ref=class_session_id,
            )
            told += 1
        await events.emit(session, "session", str(class_session_id))
    log.info(
        "quiz_exclusions_changed",
        class_session_id=str(class_session_id),
        excluded=excluded,
        lifted=lifted,
        told=told,
    )
    return quiz, wanted_set
