"""The Individual test's write path (Story 11.3, FR-51, AD-9, AD-10, AD-23): the only writer of
`test_attempts` and `test_answers`.

The decision (the Deferred item "Test attempt write path"):

- The commands are `open_attempt` (Story 11.3), `save_answer` (Story 11.4), `submit` (Story 11.10),
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

- `save_answer` keeps the highest revision per answer (AD-10): the row is upserted only when the
  sent revision is above the stored one, and the stored answer is returned either way, so a late
  or repeated save from a second device is no error.

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

from app.analysis.scoring import INTERACTIVE_LIMIT
from app.modules.content import service as content
from app.modules.content.schemas import QuestionSet, QuestionSetItem
from app.modules.debrief import service as debrief
from app.modules.progress import service as progress
from app.modules.sessions import service as sessions
from app.modules.tests import adapted
from app.modules.tests import selection as selections
from app.modules.tests.models import (
    AttemptStatus,
    test_answers,
    test_attempts,
    test_prepared_items,
)
from app.platform import authz, events
from app.platform.db import get_sessionmaker

__all__ = [
    "AttemptSubmitted",
    "DeadlinePassed",
    "InvalidAnswer",
    "LONG_ANSWER_MAX",
    "Opened",
    "ReplayRequired",
    "attempt_of",
    "move_deadline",
    "open_attempt",
    "save_answer",
    "selection_of",
    "UnknownItem",
]

log = structlog.get_logger(__name__)

LONG_ANSWER_MAX = 20_000
"""The longest long answer, in characters (Story 11.6): room for an argument built over several
evenings; the page's field stops there too."""


class ReplayRequired(Exception):
    """The Student has not completed the Replay (403 `replay_required`, FR-51, AD-16)."""


class DeadlinePassed(Exception):
    """The Student's Test deadline has passed (409 `test_deadline_passed`)."""


class AttemptSubmitted(Exception):
    """The attempt is handed in; its answers no longer change (409 `attempt_submitted`)."""


class UnknownItem(Exception):
    """The attempt's frozen item list has no such item (422 `unknown_item`)."""


class InvalidAnswer(Exception):
    """The value is no answer to the item (422 `invalid_answer`): for a choice item, not one of
    its option ids; for a table or number item, not whole numbers in its shape (Story 11.5); for a
    long-answer or Adapted item, not text within `LONG_ANSWER_MAX` (Stories 11.6, 11.7)."""


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


async def selection_of(
    s: AsyncSession, class_session_id: uuid.UUID, pins: Any
) -> tuple[selections.Selection, QuestionSet]:
    """The selection an attempt opens on (the lock's pin; the selection in force for a session
    locked before the pin existed) and its question set version, read in `s`."""
    pinned = selections.pinned_selection(pins)
    if pinned is not None:
        _, question_set = await content.question_set(pinned.version)
        return pinned, question_set
    chosen, question_set, _ = await selections.effective(s, class_session_id)
    return chosen, question_set


async def _prepared(
    s: AsyncSession, user_id: uuid.UUID, class_session_id: uuid.UUID, chosen: selections.Selection
) -> list[dict[str, Any]] | None:
    """The Student's prepared Adapted items (Story 11.8), when the job stored them for this
    selection's question set version and Adapted total weight; None otherwise, and None for
    replacement items prepared for a reason that may have passed (`adapted.PASSING_REASONS`)."""
    found = (
        await s.execute(
            select(test_prepared_items.c["items"]).where(
                test_prepared_items.c.user_id == user_id,
                test_prepared_items.c.class_session_id == class_session_id,
                test_prepared_items.c.question_set_version == chosen.version,
                test_prepared_items.c.adapted_weight == chosen.adapted_weight,
            )
        )
    ).scalar_one_or_none()
    if found is None or any(item.get("replaces") in adapted.PASSING_REASONS for item in found):
        return None
    return list(found)


async def _frozen(
    s: AsyncSession, user_id: uuid.UUID, class_session_id: uuid.UUID, pins: Any
) -> tuple[selections.Selection, list[dict[str, Any]], bool]:
    """The selection the attempt opens on (`selection_of`) and its ordered item list: the Core
    items left in, in the question set's order, each with its type and weight (AD-23), then the
    Student's Adapted items or their replacement items, carrying the Adapted total weight: the
    prepared set when the job stored one for this selection (Story 11.8), else built now (Story
    11.7, `adapted.build`), so opening never waits on an LLM call. The flag says which."""
    chosen, question_set = await selection_of(s, class_session_id, pins)
    items = [
        {"id": item.id, "type": item.type, "weight": chosen.weights.get(item.id, item.weight)}
        for item in question_set.items
        if item.id not in chosen.excluded
    ]
    prepared = await _prepared(s, user_id, class_session_id, chosen)
    if prepared is not None:
        return chosen, items + prepared, True
    items += await adapted.build(
        s, user_id, class_session_id, pins, chosen.adapted_weight, question_set
    )
    return chosen, items, False


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
    `user:<id>` is emitted so their other devices read the test again. The Student's Adapted items
    are built from their stored facts sets in this transaction and frozen with the rest (Story
    11.7), or copied from the set the `tests.prepare_adapted` job prepared (Story 11.8): a second
    open returns them as first stored, whatever template version or prepared set is newer."""
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
        chosen, items, prepared = await _frozen(s, user.id, class_session_id, found.pins)
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
        prepared=prepared,
        follow_up_closed=closed,
    )
    return Opened(attempt, created=True)


def _whole(value: Any, negative: bool) -> bool:
    """A whole number the api takes (never a bool or a float), negative only where allowed."""
    return type(value) is int and abs(value) <= INTERACTIVE_LIMIT and (negative or value >= 0)


def _text(value: Any) -> bool:
    """A long answer's text as typed (Story 11.6): at most `LONG_ANSWER_MAX` characters, empty when
    the Student emptied it. A NUL character, which JSONB cannot hold, and a lone surrogate, which
    is no text, are refused rather than stored altered."""
    if not isinstance(value, str) or len(value) > LONG_ANSWER_MAX or "\x00" in value:
        return False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def _valid(item_type: str, item: QuestionSetItem | None, value: Any) -> bool:
    """Whether `value` answers an item of this type: a choice item's option id (Story 11.4); a
    table item's list of one whole number or null per row, and a number item's whole number or
    null (cleared), negative only where the item allows it (Story 11.5; a Starting task item
    always does); a long-answer item's text, stored as typed (Story 11.6), and so an Adapted
    item's, whose text is frozen on the attempt rather than in the question set (Story 11.7). An
    item with no table of its own (question set version 1) takes nothing."""
    if item_type == adapted.ADAPTED:
        return _text(value)
    if item is None:
        return False
    if item_type == "long":
        return _text(value)
    if item_type == "choice":
        return isinstance(value, str) and value in item.options
    if item_type == "number" and item.starting_task_item is not None:
        return value is None or _whole(value, negative=True)
    spec = item.interactive
    if spec is None:
        return False
    if item_type == "number":
        return value is None or _whole(value, spec.negative)
    if item_type == "table":
        return (
            isinstance(value, list)
            and len(value) == len(spec.rows)
            and all(v is None or _whole(v, spec.negative) for v in value)
        )
    return False


async def save_answer(
    user: authz.Principal,
    class_session_id: uuid.UUID,
    item_id: str,
    value: Any,
    revision: int,
    now: datetime,
) -> Mapping[str, Any] | None:
    """Autosave the Student's answer to one item (Story 11.4, FR-51, AD-10): the stored answer
    (`item_id`, `value`, `revision`, `saved_at`) after the save. It is replaced only when
    `revision` is above the stored one; otherwise the stored answer is returned unchanged, without
    an error. None when the session is not one of the Student's own locked Class sessions or they
    have not opened the test (the route's 403, FR-5).

    One transaction with the attempt row `FOR UPDATE`, so two devices saving the same item are
    serialised and the highest revision is the one kept. Raises `AttemptSubmitted` once the
    attempt is not open, `DeadlinePassed` once its `effective_deadline` has passed, `UnknownItem`
    for an item not in its frozen list and `InvalidAnswer` for a value that does not answer the
    item. Emits nothing: the saving page has the answer, and another device reads it when it
    reads the test. The value is never logged."""
    async with get_sessionmaker().begin() as s:
        found = await sessions.individual_test_session_of(s, user, class_session_id)
        if found is None:
            return None
        attempt = (
            (
                await s.execute(
                    select(test_attempts)
                    .where(
                        test_attempts.c.user_id == user.id,
                        test_attempts.c.class_session_id == class_session_id,
                    )
                    .with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        if attempt is None:
            return None
        if attempt["status"] != AttemptStatus.OPEN.value:
            raise AttemptSubmitted
        deadline = attempt["effective_deadline"]
        if deadline is not None and deadline <= now:
            raise DeadlinePassed
        frozen = next((item for item in attempt["items"] if item["id"] == item_id), None)
        if frozen is None:
            raise UnknownItem
        question_set: QuestionSet = await content.get(
            content.Kind.QUESTION_SET, attempt["question_set_version"]
        )
        found_item = next(
            (i for i in (*question_set.items, *question_set.replacements) if i.id == item_id),
            None,
        )
        if not _valid(frozen["type"], found_item, value):
            raise InvalidAnswer
        sent = insert(test_answers).values(
            id=uuid.uuid7(),
            attempt_id=attempt["id"],
            item_id=item_id,
            value=value,
            revision=revision,
            saved_at=now,
        )
        await s.execute(
            sent.on_conflict_do_update(
                constraint="uq_test_answers_item",
                set_={
                    "value": sent.excluded.value,
                    "revision": sent.excluded.revision,
                    "saved_at": sent.excluded.saved_at,
                },
                where=test_answers.c.revision < sent.excluded.revision,
            )
        )
        stored = (
            (
                await s.execute(
                    select(
                        test_answers.c.item_id,
                        test_answers.c.value,
                        test_answers.c.revision,
                        test_answers.c.saved_at,
                    ).where(
                        test_answers.c.attempt_id == attempt["id"],
                        test_answers.c.item_id == item_id,
                    )
                )
            )
            .mappings()
            .one()
        )
    return stored


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
