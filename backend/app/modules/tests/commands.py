"""The Individual test's write path (Story 11.3, FR-51, AD-9, AD-10, AD-23): the only writer of
`test_attempts` and `test_answers`.

The decision (the Deferred item "Test attempt write path"):

- The commands are `open_attempt` (here), `save_answer` (Story 11.4), `submit` (Story 11.10),
  `close_attempt` (Story 11.11), `extend_deadline` (Story 11.13) and `end_sitting` (Story 11.12).
  No other code inserts or updates an attempt or an answer.
- Every command that acts on an existing attempt takes `SELECT … FOR UPDATE` on the attempt row
  and runs in one transaction. `save_answer` and `submit` on an attempt that is not `open` fail
  with `attempt_submitted`; on an open attempt after its `effective_deadline` with
  `test_deadline_passed`.
- Where no attempt row exists yet, the lock is named: `open_attempt` relies on the unique key on
  User and Class session (`uq_test_attempts_user_session`) and returns the existing attempt on a
  conflict; `extend_deadline` locks the Student's extension row in `modules/sessions`, and the
  attempt row too when there is one.
- `effective_deadline` is the Student's `sessions.effective_test_deadline` when the attempt is
  opened; a change of the Class session's Test deadline moves it for every open attempt in the
  save's transaction (`move_deadline`, registered with `sessions`). Story 11.13 must leave a
  Student with their own extension out.

No answer text is ever logged."""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.content import service as content
from app.modules.debrief import service as debrief
from app.modules.progress import service as progress
from app.modules.sessions import service as sessions
from app.modules.tests import selection as selections
from app.modules.tests.models import AttemptStatus, test_attempts
from app.platform import authz, events
from app.platform.db import get_sessionmaker

__all__ = [
    "DeadlinePassed",
    "Opened",
    "ReplayRequired",
    "attempt_of",
    "move_deadline",
    "open_attempt",
]

log = structlog.get_logger(__name__)


class ReplayRequired(Exception):
    """The Student has not completed the Replay (403 `replay_required`, FR-51, AD-16)."""


class DeadlinePassed(Exception):
    """The Student's Test deadline has passed (409 `test_deadline_passed`)."""


@dataclass(frozen=True)
class Opened:
    """The Student's attempt and whether this call made it."""

    attempt: Mapping[str, Any]
    created: bool


async def attempt_of(
    s: AsyncSession, user_id: uuid.UUID, class_session_id: uuid.UUID
) -> Mapping[str, Any] | None:
    """The Student's attempt in the Class session, read in `s`; None before they open it."""
    result = await s.execute(
        select(test_attempts).where(
            test_attempts.c.user_id == user_id,
            test_attempts.c.class_session_id == class_session_id,
        )
    )
    return result.mappings().one_or_none()


async def _frozen(
    s: AsyncSession, class_session_id: uuid.UUID, pins: Any
) -> tuple[selections.Selection, list[dict[str, Any]]]:
    """The selection the attempt opens on (the lock's pin; the selection in force for a session
    locked before the pin existed) and its ordered item list: the Core items left in, in the
    question set's order, each with its type and weight (AD-23). Adapted items join it in 11.7."""
    pinned = selections.pinned_selection(pins)
    if pinned is not None:
        _, question_set = await content.question_set(pinned.version)
        chosen = pinned
    else:
        chosen, question_set, _ = await selections.effective(s, class_session_id)
    items = [
        {"id": item.id, "type": item.type, "weight": chosen.weights.get(item.id, item.weight)}
        for item in question_set.items
        if item.id not in chosen.excluded
    ]
    return chosen, items


async def open_attempt(
    user: authz.Principal, class_session_id: uuid.UUID, now: datetime
) -> Opened | None:
    """The Student accepts the own-work statement (Story 11.3, FR-51): their one attempt in the
    Class session, made now or the one they have. None when the session is not one of their own
    locked Class sessions (the route's 403, FR-5). Raises `ReplayRequired` without the `replay`
    step (read only through `progress.has_step`, AD-16) and `DeadlinePassed` when no attempt
    exists and their effective Test deadline has passed.

    One transaction, the Class session row share-locked so its Test deadline and pins hold: the
    row is inserted with `ON CONFLICT DO NOTHING` on the unique key, and on a conflict the
    existing attempt is returned (two opens at once make one). The Student's Debrief follow-up
    questions close in the same transaction (FR-45, `debrief.service.close_follow_up`), and
    `user:<id>` is emitted so their other devices read the test again."""
    if not await progress.has_step(user.id, class_session_id, progress.Step.REPLAY):
        async with get_sessionmaker()() as s:
            found = await sessions.individual_test_session_of(s, user, class_session_id)
        if found is None:
            return None
        raise ReplayRequired
    async with get_sessionmaker().begin() as s:
        found = await sessions.individual_test_session_of(s, user, class_session_id)
        if found is None:
            return None
        existing = await attempt_of(s, user.id, class_session_id)
        if existing is not None:
            return Opened(existing, created=False)
        deadline = sessions.effective_test_deadline(user, found.row)
        if deadline is not None and deadline <= now:
            raise DeadlinePassed
        chosen, items = await _frozen(s, class_session_id, found.pins)
        made = await s.scalar(
            insert(test_attempts)
            .values(
                id=uuid.uuid7(),
                user_id=user.id,
                class_session_id=class_session_id,
                question_set_version=chosen.version,
                selection=chosen.as_json(),
                items=items,
                statement_accepted_at=now,
                effective_deadline=deadline,
                status=AttemptStatus.OPEN.value,
            )
            .on_conflict_do_nothing(constraint="uq_test_attempts_user_session")
            .returning(test_attempts.c.id)
        )
        attempt = await attempt_of(s, user.id, class_session_id)
        assert attempt is not None
        if made is None:  # another open committed first: theirs is the attempt
            return Opened(attempt, created=False)
        # The closure emits `user:<id>` itself; when it was closed already, the open does.
        closed = await debrief.close_follow_up(user.id, class_session_id, within=s)
        if not closed:
            await events.emit(s, "user", str(user.id))
    log.info(
        "test_attempt_opened",
        class_session_id=str(class_session_id),
        attempt_id=str(attempt["id"]),
        items=len(items),
        follow_up_closed=closed,
    )
    return Opened(attempt, created=True)


async def move_deadline(
    s: AsyncSession, class_session_id: uuid.UUID, deadline: datetime | None
) -> None:
    """`sessions.save`'s Test-deadline mover (Story 11.3, AD-9): every open attempt of the Class
    session takes the new Test deadline, in the save's transaction under the Class session's row
    lock. Story 11.13 must leave Students with their own extension out."""
    await s.execute(
        update(test_attempts)
        .where(
            test_attempts.c.class_session_id == class_session_id,
            test_attempts.c.status == AttemptStatus.OPEN.value,
        )
        .values(effective_deadline=deadline)
    )


sessions.register_test_deadline_mover(move_deadline)
