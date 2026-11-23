"""The only writer of the Debrief tables (Stories 9.2, 9.3, 9.6 to 9.11, AD-21, AD-8).

Each command on a Debrief session locks its row and emits `debrief:<id>` (`platform/events`
registry: `debrief.open`, `debrief.join`, `debrief.save_explanation`, `debrief.complete_step`,
`debrief.move_on`, `debrief.leave`, `debrief.open_personal_fallback`, `debrief.record_facts`,
`debrief.finish`, `debrief.submit_quiz`). Story 9.11:
a Group debrief's session is shared; its joined Students share the step pointer over steps 1 to 3
(`save_explanation` and `complete_step` move it once all have finished, `move_on` lets the opener
move it after the minimum wait). Story 9.12: `leave` lets a Student go on as a Personal debrief
(also the sweep's dropout after two silent minutes), `touch` records presence on each SSE heartbeat
(no lock, no event), `open_personal_fallback` is the sweep's 48-hour fallback, and every command
that evaluates the joined set settles it first (dropouts, the opener's hand-over). `release` writes
the Class session's release once and tells each Student who holds a Seat through
`platform/notify` (`debrief.release`). `set_quiz_exclusions` (Story 9.10) locks the Class
session row instead, records the change through `platform/audit`, emits `session:<id>` and tells
each Student whose last attempt it covers (`debrief.set_quiz_exclusions`). `store_ai_text`
(Story 9.14) stores a facts set's narration or quiz line once, from the `llm-batch` job: no lock
and no event, since no reader's text changes (it is fixed at the first view). Story 9.15:
`store_follow_up` stores a Student's answered or declined follow-up question once (no lock, no
event: the asking page has the answer), and `close_follow_up` closes the Student's follow-up in a
Class session once (the entry point Epic 11 calls when their Individual test opens), emitting
`user:<id>` so an open Debrief page shows it closed. Arguments are ids and the Student's text
only."""

import uuid
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import delete, func, literal, select, update
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.debrief.models import (
    DROPOUT_AFTER,
    FALLBACK_AFTER,
    INDIVIDUAL_STEP,
    debrief_ai_texts,
    debrief_alone,
    debrief_explanations,
    debrief_fact_sets,
    debrief_follow_up_closures,
    debrief_follow_ups,
    debrief_members,
    debrief_reflection_answers,
    debrief_releases,
    debrief_sessions,
    debrief_step_marks,
    debrief_summaries,
    quiz_attempts,
    quiz_exclusions,
)
from app.modules.debrief.rules import all_class_games_finished, last_attempts
from app.modules.games import service as games
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

GROUP_OPENED_NOTICE = "group_debrief_opened"
"""The notice each other Student of the Class game gets when a Group debrief of it opens (Story
9.11, immediate)."""

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
    shared: bool = False
    """Story 9.11: a Group debrief's session, whose joined Students share the step pointer."""
    opener_id: uuid.UUID | None = None
    step_opened_at: datetime | None = None
    fallback_at: datetime | None = None
    """Story 9.12: when the 48-hour fallback made it a Personal debrief for everyone not
    finished."""
    alone: bool = False
    """Story 9.12, set by `debrief.service` for the reading Student only: they go on as a Personal
    debrief in this shared session (`debrief_alone`)."""


def row_of(row) -> DebriefRow:
    return DebriefRow(
        id=row["id"],
        game_id=row["game_id"],
        class_session_id=row["class_session_id"],
        step=row["step"],
        shared=row["shared"],
        opener_id=row["opener_id"],
        step_opened_at=row["step_opened_at"],
        fallback_at=row["fallback_at"],
    )


def effective_opener(opener_id: uuid.UUID | None, joined: Sequence[uuid.UUID]) -> uuid.UUID | None:
    """Who may move a shared step on (Story 9.12): the opener while they are joined, else the
    earliest-joined Student who is (`joined` in joining order), else nobody."""
    if opener_id is not None and opener_id in joined:
        return opener_id
    return joined[0] if joined else None


async def _locked(session: AsyncSession, game_id: uuid.UUID) -> DebriefRow:
    found = await session.execute(
        select(debrief_sessions).where(debrief_sessions.c.game_id == game_id).with_for_update()
    )
    return row_of(found.mappings().one())


async def open(
    game_id: uuid.UUID,
    class_session_id: uuid.UUID,
    opener_id: uuid.UUID | None = None,
    shared: bool = False,
    tell: Sequence[uuid.UUID] = (),
    held: bool = False,
) -> DebriefRow:
    """The Debrief session of the Game, created with its step pointer at step 1 if none exists
    (FR-42). The caller has judged availability (`debrief.rules`) and, for a Group debrief
    (Story 9.11, FR-43), that it is `shared`: then the row names `opener_id` as its opener, who
    is joined at once, and each other Student in `tell` gets a `group_debrief_opened` notice
    (which emits `user:<id>`, so their Hjem offers to join). Whether a session is shared is fixed
    at its creation. The row is locked; a new row emits `debrief:<id>`, an existing one is
    returned as it stands and emits nothing. Story 9.12: a shared row stores when it falls back
    to a Personal debrief, `FALLBACK_AFTER` after the Game's finish time (database time), or, in a
    `held` Class session (Story 9.2), after this first open, which follows the release, so a
    Debrief released late does not fall back at once (Epic 9 close-out); and a
    Student who opens an existing one whose group has finished the shared steps without them goes
    on alone at once (`missed`), which emits `debrief:<id>`."""
    shared = shared and opener_id is not None
    async with get_sessionmaker().begin() as session:
        fallback_due_at = None
        if shared:
            finished = await games.finished_at(session, game_id)
            now = await games.database_now(session)
            start = now if held or finished is None else min(finished, now)
            fallback_due_at = start + FALLBACK_AFTER
        created = await session.scalar(
            insert(debrief_sessions)
            .values(
                id=uuid.uuid7(),
                game_id=game_id,
                class_session_id=class_session_id,
                step=1,
                opened_at=func.now(),
                shared=shared,
                opener_id=opener_id if shared else None,
                step_opened_at=func.now(),
                fallback_due_at=fallback_due_at,
            )
            .on_conflict_do_nothing(constraint="uq_debrief_sessions_game")
            .returning(debrief_sessions.c.id)
        )
        found = await _locked(session, game_id)
        if created is not None:
            if found.shared and opener_id is not None:
                await session.execute(
                    insert(debrief_members).values(
                        debrief_id=found.id, user_id=opener_id, joined_at=func.now()
                    )
                )
                for user_id in tell:
                    if user_id != opener_id:
                        await notify.enqueue(
                            session,
                            user_id,
                            GROUP_OPENED_NOTICE,
                            f"{GROUP_OPENED_NOTICE}:{found.id}:{user_id}",
                            ref=class_session_id,
                        )
            await events.emit(session, "debrief", str(found.id))
            log.info(
                "debrief_opened", debrief_id=str(found.id), game_id=str(game_id), shared=shared
            )
        elif opener_id is not None and await _missed(session, found, opener_id):
            # Story 9.12: the group has finished its shared steps without this Student, who
            # goes on as a Personal debrief at once, without waiting for the fallback.
            await _go_alone(session, found, opener_id, "missed", 1)
            await events.emit(session, "debrief", str(found.id))
    return found


async def _missed(session: AsyncSession, debrief: DebriefRow, user_id: uuid.UUID) -> bool:
    """Whether the Student missed the Group debrief (Story 9.12, FR-43): its joined Students have
    finished the shared steps (the pointer is at `INDIVIDUAL_STEP`, no fallback) and the Student
    never joined it nor goes alone already."""
    if not debrief.shared or debrief.fallback_at is not None:
        return False
    if debrief.step < INDIVIDUAL_STEP:
        return False
    joined = await session.scalar(
        select(debrief_members.c.user_id).where(
            debrief_members.c.debrief_id == debrief.id, debrief_members.c.user_id == user_id
        )
    )
    return joined is None and not await _is_alone(session, debrief.id, user_id)


class NotGroup(Exception):
    """A Group debrief action on a Personal debrief (409 `not_group`)."""


class NotJoined(Exception):
    """A shared step's «finished» by a Student who has not joined, or the move-on by anyone but
    the opener (403 `forbidden`)."""


class StepNotOpen(Exception):
    """«Ferdig med steget» on a shared step that is not the pointer's (409 `step_not_open`)."""


class TooEarly(Exception):
    """The opener's move-on before the step has been open the minimum wait (409 `too_early`)."""

    def __init__(self, available_at: datetime) -> None:
        super().__init__(available_at.isoformat())
        self.available_at = available_at


class GroupClosed(Exception):
    """«Bli med» by a Student who goes on alone, or after the 48-hour fallback (409
    `group_closed`, Story 9.12): going alone is final."""


def _alone_ids(debrief_id: uuid.UUID):
    return select(debrief_alone.c.user_id).where(debrief_alone.c.debrief_id == debrief_id)


async def _members(session: AsyncSession, debrief_id: uuid.UUID) -> list[uuid.UUID]:
    """The joined Students of a shared Debrief session, in joining order: those who joined and
    have not gone alone (Story 9.12)."""
    return list(
        (
            await session.scalars(
                select(debrief_members.c.user_id)
                .where(
                    debrief_members.c.debrief_id == debrief_id,
                    debrief_members.c.user_id.not_in(_alone_ids(debrief_id)),
                )
                .order_by(debrief_members.c.joined_at, debrief_members.c.user_id)
            )
        ).all()
    )


async def _is_alone(session: AsyncSession, debrief_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    found = await session.scalar(
        select(debrief_alone.c.user_id).where(
            debrief_alone.c.debrief_id == debrief_id, debrief_alone.c.user_id == user_id
        )
    )
    return found is not None


async def _go_alone(
    session: AsyncSession, debrief: DebriefRow, user_id: uuid.UUID, reason: str, step: int
) -> bool:
    """Store that the Student goes on as a Personal debrief from `step` (Story 9.12); False when
    they already do."""
    stored = await session.scalar(
        insert(debrief_alone)
        .values(debrief_id=debrief.id, user_id=user_id, step=step, reason=reason, since=func.now())
        .on_conflict_do_nothing(
            index_elements=[debrief_alone.c.debrief_id, debrief_alone.c.user_id]
        )
        .returning(debrief_alone.c.user_id)
    )
    if stored is not None:
        log.info("debrief_alone", debrief_id=str(debrief.id), reason=reason, step=step)
    return stored is not None


async def _settle(
    session: AsyncSession, debrief: DebriefRow, keep: uuid.UUID | None
) -> tuple[DebriefRow, bool]:
    """In the caller's transaction, holding the row's lock, evaluate a shared session's joined set
    (Story 9.12, FR-43): the caller `keep`, whose command shows they are there, is seen now; each
    other joined Student silent longer than `DROPOUT_AFTER` (database time) drops out, as `leave`
    would; an opener no longer joined hands over to the earliest-joined Student who is; then the
    pointer moves on while every joined Student has finished its step. Returns the row and whether
    any of it changed (the caller's presence is not a change)."""
    if not debrief.shared or debrief.fallback_at is not None:
        return debrief, False
    changed = False
    if debrief.step < INDIVIDUAL_STEP:
        if keep is not None:
            await session.execute(
                update(debrief_members)
                .where(
                    debrief_members.c.debrief_id == debrief.id, debrief_members.c.user_id == keep
                )
                .values(last_seen_at=func.now())
            )
        silent = (
            await session.scalars(
                select(debrief_members.c.user_id).where(
                    debrief_members.c.debrief_id == debrief.id,
                    debrief_members.c.user_id.not_in(_alone_ids(debrief.id)),
                    debrief_members.c.last_seen_at < func.now() - DROPOUT_AFTER,
                )
            )
        ).all()
        for user_id in silent:
            if user_id != keep:
                changed |= await _go_alone(session, debrief, user_id, "dropout", debrief.step)
        opener = effective_opener(debrief.opener_id, await _members(session, debrief.id))
        if opener != debrief.opener_id:
            await session.execute(
                update(debrief_sessions)
                .where(debrief_sessions.c.id == debrief.id)
                .values(opener_id=opener)
            )
            debrief = replace(debrief, opener_id=opener)
            changed = True
            log.info("debrief_opener_handed_over", debrief_id=str(debrief.id))
    moved = await _advance(session, debrief)
    return moved, changed or moved.step != debrief.step


async def _finished(
    session: AsyncSession, debrief: DebriefRow, step: int, user_ids: Sequence[uuid.UUID]
) -> set[uuid.UUID]:
    """Those of `user_ids` who have finished shared step `step`: step 1 by their stored
    Explanation, steps 2 and 3 by their mark."""
    if not user_ids:
        return set()
    if step == 1:
        query = select(debrief_explanations.c.user_id).where(
            debrief_explanations.c.class_session_id == debrief.class_session_id,
            debrief_explanations.c.user_id.in_(list(user_ids)),
        )
    else:
        query = select(debrief_step_marks.c.user_id).where(
            debrief_step_marks.c.debrief_id == debrief.id,
            debrief_step_marks.c.step == step,
            debrief_step_marks.c.user_id.in_(list(user_ids)),
        )
    return set((await session.scalars(query)).all())


async def _move(session: AsyncSession, debrief: DebriefRow, step: int) -> DebriefRow:
    await session.execute(
        update(debrief_sessions)
        .where(debrief_sessions.c.id == debrief.id)
        .values(step=step, step_opened_at=func.now())
    )
    log.info("debrief_step_moved", debrief_id=str(debrief.id), step=step)
    return await _locked(session, debrief.game_id)


async def _advance(session: AsyncSession, debrief: DebriefRow) -> DebriefRow:
    """In the caller's transaction, holding the row's lock: move a shared pointer on while every
    joined Student has finished its step, at most to `INDIVIDUAL_STEP` (FR-43)."""
    if not debrief.shared:
        return debrief
    members = await _members(session, debrief.id)
    while members and debrief.step < INDIVIDUAL_STEP:
        if len(await _finished(session, debrief, debrief.step, members)) < len(members):
            break
        debrief = await _move(session, debrief, debrief.step + 1)
    return debrief


async def join(game_id: uuid.UUID, user_id: uuid.UUID) -> DebriefRow:
    """«Bli med» (Story 9.11, FR-43): add the Student to the joined set of the Game's shared
    Debrief session. The caller has judged that it is their game. The row is locked; a new member
    emits `debrief:<id>`, a second join changes nothing and emits nothing. Raises `NotGroup` on a
    Personal debrief, and `GroupClosed` for a Student who goes alone or after the fallback (Story
    9.12). Settles the joined set (`_settle`)."""
    async with get_sessionmaker().begin() as session:
        debrief = await _locked(session, game_id)
        if not debrief.shared:
            raise NotGroup
        if debrief.fallback_at is not None or await _is_alone(session, debrief.id, user_id):
            raise GroupClosed
        if await _missed(session, debrief, user_id):
            # The group finished its shared steps without them: alone at once, as on `open`.
            await _go_alone(session, debrief, user_id, "missed", 1)
            await events.emit(session, "debrief", str(debrief.id))
            return debrief
        added = await session.scalar(
            insert(debrief_members)
            .values(debrief_id=debrief.id, user_id=user_id, joined_at=func.now())
            .on_conflict_do_nothing(
                index_elements=[debrief_members.c.debrief_id, debrief_members.c.user_id]
            )
            .returning(debrief_members.c.user_id)
        )
        debrief, settled = await _settle(session, debrief, keep=user_id)
        if added is not None or settled:
            await events.emit(session, "debrief", str(debrief.id))
        if added is not None:
            log.info("debrief_joined", debrief_id=str(debrief.id))
    return debrief


async def move_on(game_id: uuid.UUID, user_id: uuid.UUID, wait: timedelta) -> DebriefRow:
    """«Gå videre for alle» (Story 9.11, FR-43): the opener moves the shared pointer to the next
    step although not every joined Student has finished it, once the step has been open `wait`
    (database time). The row is locked; a move emits `debrief:<id>`; at `INDIVIDUAL_STEP` nothing
    moves. Raises `NotGroup` on a Personal debrief, `NotJoined` for anyone but the opener and
    `TooEarly` with the time it becomes possible. Story 9.12: the joined set is settled first, so
    once the opener has gone the earliest-joined Student who is still there moves on, and a
    settle that moved the pointer is the move. The settle commits on its own, so a refusal after
    it keeps it."""
    async with get_sessionmaker().begin() as session:
        debrief = await _locked(session, game_id)
        if not debrief.shared:
            raise NotGroup
        before = debrief.step
        debrief, settled = await _settle(session, debrief, keep=user_id)
        if settled:
            await events.emit(session, "debrief", str(debrief.id))
    if debrief.step != before and debrief.opener_id == user_id:
        return debrief
    async with get_sessionmaker().begin() as session:
        debrief = await _locked(session, game_id)
        if debrief.opener_id != user_id or debrief.fallback_at is not None:
            raise NotJoined
        if debrief.step >= INDIVIDUAL_STEP:
            return debrief
        opened = debrief.step_opened_at
        assert opened is not None
        if await session.scalar(select(func.now() < opened + wait)):
            raise TooEarly(opened + wait)
        debrief = await _move(session, debrief, debrief.step + 1)
        await events.emit(session, "debrief", str(debrief.id))
    return debrief


async def leave(game_id: uuid.UUID, user_id: uuid.UUID, dropout: bool = False) -> DebriefRow:
    """«Forlat gruppen» / «Ta en Personlig debrief» (Story 9.12, FR-43): the Student goes on as a
    Personal debrief, from the shared step they were on (step 1 for one who never joined), with
    everything they saved kept; final. With `dropout` (the sweep), only a joined Student silent
    longer than `DROPOUT_AFTER` (database time) goes, as `dropout`. The row is locked; the joined
    set is then settled (the opener handed over, the pointer moved when the others have all
    finished) and `debrief:<id>` emitted. Once the pointer reached `INDIVIDUAL_STEP`, after the
    fallback, or for a Student already alone, nothing changes and nothing is emitted. Raises
    `NotGroup` on a Personal debrief."""
    async with get_sessionmaker().begin() as session:
        debrief = await _locked(session, game_id)
        if not debrief.shared:
            raise NotGroup
        if debrief.fallback_at is not None or debrief.step >= INDIVIDUAL_STEP:
            return debrief
        joined = user_id in await _members(session, debrief.id)
        if dropout:
            silent = await session.scalar(
                select(debrief_members.c.last_seen_at < func.now() - DROPOUT_AFTER).where(
                    debrief_members.c.debrief_id == debrief.id,
                    debrief_members.c.user_id == user_id,
                )
            )
            if not joined or not silent:
                return debrief
        reason = "dropout" if dropout else "left"
        if not await _go_alone(session, debrief, user_id, reason, debrief.step if joined else 1):
            return debrief
        debrief, _ = await _settle(session, debrief, keep=None if dropout else user_id)
        await events.emit(session, "debrief", str(debrief.id))
    return debrief


async def touch(user_id: uuid.UUID) -> None:
    """Presence (Story 9.12, FR-43, AD-21): on each SSE heartbeat of the User (`platform/events`
    `on_heartbeat`), record the database time as `last_seen_at` on each of their joined rows of a
    shared Debrief session still on its shared steps. The one command that takes no Debrief row
    lock and emits no event: a short database session of its own, so the stream holds none."""
    async with get_sessionmaker().begin() as session:
        await session.execute(
            update(debrief_members)
            .where(
                debrief_members.c.user_id == user_id,
                debrief_members.c.debrief_id.in_(
                    select(debrief_sessions.c.id).where(
                        debrief_sessions.c.shared,
                        debrief_sessions.c.step < INDIVIDUAL_STEP,
                        debrief_sessions.c.fallback_at.is_(None),
                    )
                ),
                ~select(debrief_alone.c.user_id)
                .where(
                    debrief_alone.c.debrief_id == debrief_members.c.debrief_id,
                    debrief_alone.c.user_id == debrief_members.c.user_id,
                )
                .exists(),
            )
            .values(last_seen_at=func.now())
        )


FALLBACK_NOTICE = "debrief_fallback"
"""The notice each Student a Group debrief's 48-hour fallback makes go alone gets (Story 9.12,
digest)."""


async def open_personal_fallback(debrief_id: uuid.UUID) -> bool:
    """The 48-hour fallback (Story 9.12, FR-43, AD-9), the sweep's act: a shared Debrief session
    that has not reached `INDIVIDUAL_STEP` becomes a Personal debrief for each Student of its
    Class game who has not finished the Debrief and does not go alone already, from the shared
    step they were on (step 1 for one who never joined), each told by a `debrief_fallback` notice
    (which emits `user:<id>`). Once: the row is locked and stores when it ran. Emits
    `debrief:<id>`. True when this call did it."""
    async with get_sessionmaker().begin() as session:
        found = (
            (
                await session.execute(
                    select(debrief_sessions)
                    .where(debrief_sessions.c.id == debrief_id)
                    .with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        if found is None:
            return False
        debrief = row_of(found)
        if not debrief.shared or debrief.fallback_at is not None:
            return False
        if debrief.step >= INDIVIDUAL_STEP:
            return False
        await session.execute(
            update(debrief_sessions)
            .where(debrief_sessions.c.id == debrief.id)
            .values(fallback_at=func.now())
        )
        joined = await _members(session, debrief.id)
        # The game's Students, and any joined Student no longer counted among them.
        students = [each.user_id for each in await games.game_students(session, debrief.game_id)]
        students += [each for each in joined if each not in students]
        finished = set(
            (
                await session.scalars(
                    select(debrief_summaries.c.user_id).where(
                        debrief_summaries.c.class_session_id == debrief.class_session_id,
                        debrief_summaries.c.user_id.in_(students),
                    )
                )
            ).all()
        )
        told = 0
        for user_id in students:
            if user_id in finished:
                continue
            step = debrief.step if user_id in joined else 1
            if not await _go_alone(session, debrief, user_id, "fallback", step):
                continue
            await notify.enqueue(
                session,
                user_id,
                FALLBACK_NOTICE,
                f"{FALLBACK_NOTICE}:{debrief.id}:{user_id}",
                ref=debrief.class_session_id,
            )
            told += 1
        await events.emit(session, "debrief", str(debrief.id))
    log.info("debrief_fallback_opened", debrief_id=str(debrief_id), students=told)
    return True


async def backdate_step(debrief_id: uuid.UUID, by: timedelta) -> None:
    """Local dev only (`debrief.dev`, never mounted in production): move the shared step's opening
    time back by `by`, so an end-to-end test need not wait for the move-on. Emits nothing."""
    async with get_sessionmaker().begin() as session:
        await session.execute(
            update(debrief_sessions)
            .where(debrief_sessions.c.id == debrief_id)
            .values(step_opened_at=debrief_sessions.c.step_opened_at - by)
        )


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
        # Story 9.11: in a Group debrief the last joined Student's Explanation moves the pointer
        # (Story 9.12: after the joined set is settled).
        await _settle(session, debrief, keep=user_id)
        await events.emit(session, "debrief", str(debrief.id))
    log.info("explanation_saved", debrief_id=str(debrief.id), length=stored["length"])
    return ExplanationRow(stored["text"], stored["length"], stored["saved_at"])


@dataclass(frozen=True)
class AnswerRow:
    question_id: str
    text: str
    length: int
    saved_at: datetime


@dataclass(frozen=True)
class Reflection:
    """A reflection answer to store (Story 9.6): the pinned version, its questions in the order
    asked, the question answered and the text."""

    questions_version: int
    question_ids: Sequence[str]
    question_id: str
    text: str


async def complete_step(
    game_id: uuid.UUID,
    class_session_id: uuid.UUID,
    user_id: uuid.UUID,
    step: int,
    reflection: Reflection | None = None,
) -> AnswerRow | DebriefRow:
    """A Student finishes part of the Debrief (AD-21). The Debrief row of the Game is locked.

    - With `reflection`, «Fortsett» on a reflection question (Story 9.6, FR-45, AD-14), which
      answers `_answer`'s `AnswerRow`.
    - Without, «Ferdig med steget» on shared step `step`, 2 or 3, of a Group debrief (Story 9.11,
      FR-43): the joined Student's mark is stored once, and when every joined Student has
      finished the step the pointer moves on; a new mark emits `debrief:<id>`, a second one
      nothing. Raises `NotGroup` on a Personal debrief, `NotJoined` for a Student who has not
      joined and `StepNotOpen` for any step but the pointer's. Answers the Debrief row as it
      stands."""
    if reflection is not None:
        return await _answer(game_id, class_session_id, user_id, reflection)
    async with get_sessionmaker().begin() as session:
        debrief = await _locked(session, game_id)
        if not debrief.shared:
            raise NotGroup
        if user_id not in await _members(session, debrief.id):
            raise NotJoined
        if step != debrief.step or not 2 <= step < INDIVIDUAL_STEP:
            raise StepNotOpen
        marked = await session.scalar(
            insert(debrief_step_marks)
            .values(debrief_id=debrief.id, user_id=user_id, step=step, done_at=func.now())
            .on_conflict_do_nothing(
                index_elements=[
                    debrief_step_marks.c.debrief_id,
                    debrief_step_marks.c.user_id,
                    debrief_step_marks.c.step,
                ]
            )
            .returning(debrief_step_marks.c.step)
        )
        debrief, settled = await _settle(session, debrief, keep=user_id)
        if marked is not None or settled:
            await events.emit(session, "debrief", str(debrief.id))
    return debrief


async def _answer(
    game_id: uuid.UUID, class_session_id: uuid.UUID, user_id: uuid.UUID, reflection: Reflection
) -> AnswerRow:
    """Store the Student's answer to `question_id`, as typed, with its length and the database
    time. The Debrief row of the Game is locked, so the order is judged against what is stored; a
    new answer emits `debrief:<id>`. `question_ids` are the pinned version's questions in the
    order asked, and the caller has judged that `question_id` is one of them and the text. An
    answered question returns the stored answer unchanged and emits nothing (a retry, a second
    device); any other question than the first unanswered one raises `AnswerOutOfOrder`."""
    questions_version = reflection.questions_version
    question_ids = reflection.question_ids
    question_id = reflection.question_id
    text = reflection.text
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


# Story 9.12: presence. Registered at import, which the app does at startup through the routes.
events.on_heartbeat(touch)


async def store_ai_text(
    fact_set_id: uuid.UUID,
    subject: str,
    text: str,
    *,
    ai_generated: bool,
    llm_call_id: uuid.UUID | None,
) -> bool:
    """Store a facts set's AI text once (Story 9.14, AD-7): the narration (`narration`) or a quiz
    question's line (`quiz:<question_id>`), as `{text, ai_generated, llm_call_id}`. A row already
    stored stays (a job delivered twice); returns whether this call stored it. No lock and no
    event: the text a Student reads is fixed at their first view, so no open page changes."""
    async with get_sessionmaker().begin() as session:
        stored = await session.scalar(
            insert(debrief_ai_texts)
            .values(
                fact_set_id=fact_set_id,
                subject=subject,
                text=text,
                ai_generated=ai_generated,
                llm_call_id=llm_call_id,
                # The time of the insert, not of the transaction's start, so a Student's first
                # view that comes before this row commits never counts as after it.
                created_at=func.clock_timestamp(),
            )
            .on_conflict_do_nothing(
                index_elements=[debrief_ai_texts.c.fact_set_id, debrief_ai_texts.c.subject]
            )
            .returning(debrief_ai_texts.c.subject)
        )
    if stored is not None:
        log.info("debrief_ai_text_stored", subject=subject.split(":")[0], ai_generated=ai_generated)
    return stored is not None


async def clear_ai_texts(fact_set_id: uuid.UUID) -> None:
    """Delete a facts set's AI texts: the local dev narration (`debrief.dev`) only, so an
    end-to-end test can narrate a Seat again with the mock failing. Never in production (the dev
    router is not mounted there)."""
    async with get_sessionmaker().begin() as session:
        await session.execute(
            debrief_ai_texts.delete().where(debrief_ai_texts.c.fact_set_id == fact_set_id)
        )


@dataclass(frozen=True)
class FollowUpRow:
    id: uuid.UUID
    question: str
    outcome: str
    answer: str | None
    llm_call_id: uuid.UUID
    asked_at: datetime


def follow_up_of(row) -> FollowUpRow:
    return FollowUpRow(
        id=row["id"],
        question=row["question"],
        outcome=row["outcome"],
        answer=row["answer"],
        llm_call_id=row["llm_call_id"],
        asked_at=row["asked_at"],
    )


async def store_follow_up(
    user_id: uuid.UUID,
    class_session_id: uuid.UUID,
    fact_set_id: uuid.UUID,
    question: str,
    *,
    outcome: str,
    answer: str | None,
    llm_call_id: uuid.UUID,
) -> FollowUpRow:
    """Store a Student's follow-up question with its answer once (Story 9.15, FR-45, AD-7, AD-14):
    `answered` with the hint text code rendered, or `declined`, keyed by the Student and the
    Class session with the facts set and the call it cites, at the database time. No lock and no
    event: the asking page has the answer, and no other reader sees it."""
    async with get_sessionmaker().begin() as session:
        saved = (
            (
                await session.execute(
                    insert(debrief_follow_ups)
                    .values(
                        id=uuid.uuid7(),
                        user_id=user_id,
                        class_session_id=class_session_id,
                        fact_set_id=fact_set_id,
                        question=question,
                        outcome=outcome,
                        answer=answer,
                        llm_call_id=llm_call_id,
                        asked_at=func.clock_timestamp(),
                    )
                    .returning(*debrief_follow_ups.c)
                )
            )
            .mappings()
            .one()
        )
    log.info("debrief_follow_up_stored", outcome=outcome)
    return follow_up_of(saved)


async def close_follow_up(
    user_id: uuid.UUID, class_session_id: uuid.UUID, *, within: AsyncSession | None = None
) -> bool:
    """Close the Student's follow-up questions in the Class session for good (Story 9.15, FR-45):
    Epic 11 calls it, through `debrief.service.close_follow_up`, when their Individual test opens,
    in its own transaction (`within`, Story 11.3). Idempotent: returns whether this call closed
    it. Emits `user:<id>`, so an open Debrief page replaces the field with the line that says it
    is closed."""
    if within is not None:
        return await _close_follow_up(within, user_id, class_session_id)
    async with get_sessionmaker().begin() as session:
        closed = await _close_follow_up(session, user_id, class_session_id)
    if closed:  # logged once committed; within a caller's transaction, the caller logs
        log.info("debrief_follow_up_closed", class_session_id=str(class_session_id))
    return closed


async def _close_follow_up(
    session: AsyncSession, user_id: uuid.UUID, class_session_id: uuid.UUID
) -> bool:
    closed = await session.scalar(
        insert(debrief_follow_up_closures)
        .values(user_id=user_id, class_session_id=class_session_id, closed_at=func.now())
        .on_conflict_do_nothing(
            index_elements=[
                debrief_follow_up_closures.c.user_id,
                debrief_follow_up_closures.c.class_session_id,
            ]
        )
        .returning(debrief_follow_up_closures.c.user_id)
    )
    if closed is not None:
        await events.emit(session, "user", str(user_id))
    return closed is not None


ERASED_TABLES = frozenset(
    {
        "debrief_explanations",
        "debrief_reflection_answers",
        "debrief_follow_ups",
        "debrief_summaries",
    }
)
"""The Debrief tables whose text of a Student the erasure deletes (Story 15.2)."""


async def erase_user_text(session: AsyncSession, user_id: uuid.UUID) -> None:
    """In the erasure's transaction (Story 15.2, FR-76, AD-14): delete the free text the Student
    wrote, their Forklaring, reflection answers and follow-up questions with the AI answers that
    quote them, and empty the reflection their Debrief summaries copied. Every count stays: the
    summary row, the quiz attempts and the step marks keep the anonymous User's id. Idempotent."""
    await session.execute(
        delete(debrief_explanations).where(debrief_explanations.c.user_id == user_id)
    )
    await session.execute(
        delete(debrief_reflection_answers).where(debrief_reflection_answers.c.user_id == user_id)
    )
    await session.execute(delete(debrief_follow_ups).where(debrief_follow_ups.c.user_id == user_id))
    await session.execute(
        update(debrief_summaries)
        .where(
            debrief_summaries.c.user_id == user_id,
            debrief_summaries.c.reflection != literal([], JSONB),
        )
        .values(reflection=literal([], JSONB))
    )
