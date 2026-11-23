"""Whether a Student's Debrief is open (Story 9.2, FR-42, AD-25): the one rule every Debrief
route, Hjem's Stegene and «Spillet er ferdig» use.

- `not_open`: the Student's game (`games.service.student_game`, the one way to find it, or the
  game of a Debrief they already started, `debrief_game`, Story 13.5) has not finished.
- `held`: it has, but the Lecturer holds every Debrief until all Class games have finished, and
  one Game of `games.service.class_games` (Lecturer-overview purposes, so never a test Game) has
  not. Once all have finished the Debrief is open, also before the sweep's release.
- `open` otherwise.

Game status is read only through `games.service`. `sessions` reaches this rule through the
provider registered below, so it never imports `debrief`.

Story 9.10: `quiz_changed` is the one rule for «the quiz has changed» on Hjem's Stegene: the
Student has not passed, and every question their last attempt got wrong is now taken out of the
Class session's quiz. Registered with `sessions` the same way.

Story 9.11: `group_open` is the one rule for «a Group debrief you can join» on Hjem and in its
mail, registered the same way."""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import select, union
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.debrief.models import (
    INDIVIDUAL_STEP,
    debrief_alone,
    debrief_explanations,
    debrief_fact_sets,
    debrief_members,
    debrief_sessions,
    debrief_step_marks,
    debrief_summaries,
    quiz_attempts,
    quiz_exclusions,
)
from app.modules.games import service as games
from app.modules.sessions import service as sessions
from app.platform import authz
from app.platform.db import get_sessionmaker

State = Literal["open", "not_open", "held"]


async def all_class_games_finished(session: AsyncSession, class_session_id: uuid.UUID) -> bool:
    """Whether every Class game of the session has finished (and there is one)."""
    found = await games.class_games(session, class_session_id)
    return bool(found) and all(game.lifecycle == games.Lifecycle.FINISHED for game in found)


async def _started_on(
    session: AsyncSession, user_id: uuid.UUID, class_session_id: uuid.UUID
) -> uuid.UUID | None:
    """The Game of a Debrief the Student has already started in the Class session (Story 13.5):
    the game a stored row of theirs names (the Explanation, the facts set of step 4, the summary,
    a quiz attempt), or the Debrief session they joined, marked a shared step in or chose to go on
    alone in. The 48-hour fallback's rows are the sweep's, not the Student's, and do not count."""
    by_student = [
        select(table.c.game_id).where(
            table.c.user_id == user_id, table.c.class_session_id == class_session_id
        )
        for table in (debrief_explanations, debrief_fact_sets, debrief_summaries, quiz_attempts)
    ]
    in_session = [
        select(debrief_sessions.c.game_id)
        .join(table, table.c.debrief_id == debrief_sessions.c.id)
        .where(
            table.c.user_id == user_id,
            debrief_sessions.c.class_session_id == class_session_id,
            *extra,
        )
        for table, extra in (
            (debrief_members, ()),
            (debrief_step_marks, ()),
            (debrief_alone, (debrief_alone.c.reason != "fallback",)),
        )
    ]
    found = await session.scalars(union(*by_student, *in_session).limit(1))
    return found.first()


async def debrief_game(
    session: AsyncSession, user_id: uuid.UUID, class_session_id: uuid.UUID
) -> games.StudentGame | None:
    """The game the Student's Debrief runs on (Stories 9.2, 13.5): the one they already started a
    Debrief on, which it keeps once a finished Oppfølgingsspill becomes their game (nothing stored
    is redone); else their game, `games.service.student_game`. Read in the caller's `session`."""
    started = await _started_on(session, user_id, class_session_id)
    if started is not None:
        found = await games.own_game(session, user_id, started)
        if found is not None:
            return found
    return await games.student_game(session, user_id, class_session_id)


async def state(
    session: AsyncSession, user_id: uuid.UUID, class_session_id: uuid.UUID, hold: bool
) -> State | None:
    """The Student's Debrief state in the Class session, read in the caller's `session`; None
    when they have no game there (`debrief_game`)."""
    found = await debrief_game(session, user_id, class_session_id)
    if found is None:
        return None
    if (await games.play_status(session, found.game_id)).status != "finished":
        return "not_open"
    if hold and not await all_class_games_finished(session, class_session_id):
        return "held"
    return "open"


@dataclass(frozen=True)
class Availability:
    """`available`'s answer: the state and, when the Student has one, their game."""

    state: State
    game: games.StudentGame
    group_mode: bool = False
    """Story 9.11: the Class session's Debrief mode is Group debrief."""
    hold: bool = False
    """Story 9.2: the Class session holds every Debrief until all Class games have finished."""


async def available(user: authz.Principal, class_session_id: uuid.UUID) -> Availability | None:
    """The User's Debrief in the Class session: None when the session is not one of their own
    locked sessions or they have no Class game in it (the routes answer `forbidden`)."""
    async with get_sessionmaker()() as s:
        found = await sessions.debrief_session_of(s, user, class_session_id)
        if found is None:
            return None
        game = await debrief_game(s, user.id, class_session_id)
        if game is None:
            return None
        judged = await state(s, user.id, class_session_id, found.hold)
    if judged is None:
        return None
    return Availability(judged, game, found.group, found.hold)


async def excluded_questions(session: AsyncSession, class_session_id: uuid.UUID) -> set[str]:
    """The ids of the Debrief quiz questions taken out of the Class session's quiz (Story 9.10)."""
    return set(
        (
            await session.scalars(
                select(quiz_exclusions.c.question_id).where(
                    quiz_exclusions.c.class_session_id == class_session_id
                )
            )
        ).all()
    )


async def last_attempts(
    session: AsyncSession, class_session_id: uuid.UUID, user_id: uuid.UUID | None = None
) -> dict[uuid.UUID, Mapping[str, Any]]:
    """Each Student's latest Debrief quiz attempt in the Class session (or only `user_id`'s), by
    User id: `answers` and `passed`."""
    query = (
        select(quiz_attempts.c.user_id, quiz_attempts.c.answers, quiz_attempts.c.passed)
        .where(quiz_attempts.c.class_session_id == class_session_id)
        .order_by(quiz_attempts.c.user_id, quiz_attempts.c.number.desc())
        .ext(distinct_on(quiz_attempts.c.user_id))
    )
    if user_id is not None:
        query = query.where(quiz_attempts.c.user_id == user_id)
    return {row["user_id"]: row for row in (await session.execute(query)).mappings()}


async def quiz_changed(
    session: AsyncSession, user_id: uuid.UUID, class_session_id: uuid.UUID
) -> bool:
    """Whether Hjem says the Debrief quiz has changed for the Student: not passed, and every
    question their last attempt got wrong is now taken out. The next attempt ends it."""
    last = (await last_attempts(session, class_session_id, user_id)).get(user_id)
    if last is None or last["passed"]:
        return False
    wrong = {a["question_id"] for a in last["answers"] if not a["correct"]}
    return bool(wrong) and wrong <= await excluded_questions(session, class_session_id)


async def group_open(
    session: AsyncSession, user_id: uuid.UUID, class_session_id: uuid.UUID
) -> bool:
    """Story 9.11: whether a Group debrief of the Student's game is under way that they have not
    joined, so Hjem offers to join and the `group_debrief_opened` mail still goes out."""
    found = await debrief_game(session, user_id, class_session_id)
    if found is None:
        return False
    joined = (
        select(debrief_members.c.user_id)
        .where(
            debrief_members.c.debrief_id == debrief_sessions.c.id,
            debrief_members.c.user_id == user_id,
        )
        .exists()
    )
    # Story 9.12: nor once they go alone, after the 48-hour fallback, or once the group has
    # finished its shared steps (they open it as a Personal debrief then).
    alone = (
        select(debrief_alone.c.user_id)
        .where(
            debrief_alone.c.debrief_id == debrief_sessions.c.id,
            debrief_alone.c.user_id == user_id,
        )
        .exists()
    )
    waiting = await session.scalar(
        select(debrief_sessions.c.id).where(
            debrief_sessions.c.game_id == found.game_id,
            debrief_sessions.c.shared,
            debrief_sessions.c.fallback_at.is_(None),
            debrief_sessions.c.step < INDIVIDUAL_STEP,
            ~joined,
            ~alone,
        )
    )
    return waiting is not None


sessions.register_debrief_state(state)
sessions.register_quiz_changed(quiz_changed)
sessions.register_group_open(group_open)
