"""The Student's Individual test as their page reads it (Story 11.3, FR-51, FR-5, AD-12, AD-16).

`read` answers the state: `statement` before the Student has accepted the own-work statement (no
item is served), `open` with the items of their attempt in its frozen order, `closed` when their
Test deadline has passed with no attempt. `open_` accepts the statement through
`commands.open_attempt`. Each open item carries a choice item's option ids, a table item's value
table or a number item's column (Story 11.5; a Starting task item's from the Class session's
pinned Starting task) and the Student's saved answer; `save` autosaves one answer through
`commands.save_answer` (Story 11.4). Only the Student's own locked Class session is reached;
every other caller gets None (the route's 403 `forbidden`), whether or not an attempt exists."""

import uuid
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sqlalchemy import select

from app.modules.content import service as content
from app.modules.content.schemas import QuestionSet, QuestionSetItem, StartingTask
from app.modules.progress import service as progress
from app.modules.sessions import service as sessions
from app.modules.tests import commands
from app.modules.tests.models import test_answers
from app.modules.tests.schemas import (
    ColumnOut,
    ColumnRowOut,
    IndividualItemOut,
    MyTestOut,
    SavedAnswerOut,
    StoredAnswerOut,
    TableColumnOut,
    TableOut,
)
from app.platform import authz
from app.platform.db import get_sessionmaker

__all__ = ["read", "open_", "save"]


async def _answers(attempt_id: uuid.UUID) -> dict[str, StoredAnswerOut]:
    async with get_sessionmaker()() as s:
        result = await s.execute(
            select(
                test_answers.c.item_id,
                test_answers.c.value,
                test_answers.c.revision,
                test_answers.c.saved_at,
            ).where(test_answers.c.attempt_id == attempt_id)
        )
        return {
            row["item_id"]: StoredAnswerOut(
                value=row["value"], revision=row["revision"], saved_at=row["saved_at"]
            )
            for row in result.mappings()
        }


def _table(item: QuestionSetItem) -> TableOut | None:
    spec = item.interactive
    if item.type != "table" or spec is None:
        return None
    return TableOut(
        prompt=spec.prompt,
        hint=spec.hint,
        caption=spec.caption,
        rows=list(spec.rows),
        columns=[TableColumnOut(label=c.label, values=list(c.values)) for c in spec.given],
        asked_label=spec.asked,
        negative=spec.negative,
    )


def _column(item: QuestionSetItem, task: StartingTask) -> ColumnOut | None:
    """A number item's column: a Starting task item's from the Starting task (its text is never
    copied into the question set, FR-52), or the item's own."""
    if item.type != "number":
        return None
    if item.starting_task_item is not None:
        found = next((t for t in task.items if t.id == item.starting_task_item), None)
        if found is None:
            return None
        return ColumnOut(
            prompt=found.prompt,
            hint=found.hint,
            caption=found.column,
            rows=[ColumnRowOut(label=row.label, value=row.value) for row in found.rows],
            asked_label=found.asked_label,
            negative=True,
            starting_task=True,
        )
    spec = item.interactive
    if spec is None or not spec.given:
        return None
    values = spec.given[0].values  # one value per row (the content's rule)
    return ColumnOut(
        prompt=spec.prompt,
        hint=spec.hint,
        caption=spec.caption,
        rows=[ColumnRowOut(label=r, value=v) for r, v in zip(spec.rows, values, strict=True)],
        asked_label=spec.asked,
        negative=spec.negative,
        starting_task=False,
    )


async def _items(attempt: Mapping[str, Any], pins: Any) -> list[IndividualItemOut]:
    question_set: QuestionSet = await content.get(
        content.Kind.QUESTION_SET, attempt["question_set_version"]
    )
    by_id = {item.id: item for item in (*question_set.items, *question_set.replacements)}
    # The Class session's pinned Starting task, the one its Students answered (Story 6.3).
    _, task = await content.starting_task(content.pinned_version(pins))
    answers = await _answers(attempt["id"])
    return [
        IndividualItemOut(
            id=item["id"],
            number=number,
            type=item["type"],
            title=by_id[item["id"]].title,
            options=list(by_id[item["id"]].options),
            table=_table(by_id[item["id"]]),
            column=_column(by_id[item["id"]], task),
            answer=answers.get(item["id"]),
        )
        for number, item in enumerate(attempt["items"], start=1)
    ]


async def _open(attempt: Mapping[str, Any], pins: Any) -> MyTestOut:
    return MyTestOut(
        state="open",
        test_deadline=attempt["effective_deadline"],
        opened_at=attempt["statement_accepted_at"],
        items=await _items(attempt, pins),
    )


async def read(
    user: authz.Principal, class_session_id: uuid.UUID, now: datetime
) -> MyTestOut | None:
    """The Student's Individual test; None for every caller but the Student of the Class session
    (FR-5). Raises `commands.ReplayRequired` before the `replay` step (AD-16)."""
    async with get_sessionmaker()() as s:
        found = await sessions.individual_test_session_of(s, user, class_session_id)
        if found is None:
            return None
        attempt = await commands.attempt_of(s, user.id, class_session_id)
    if attempt is not None:
        return await _open(attempt, found.pins)
    if not await progress.has_step(user.id, class_session_id, progress.Step.REPLAY):
        raise commands.ReplayRequired
    deadline = sessions.effective_test_deadline(user, found.row)
    passed = deadline is not None and deadline <= now
    return MyTestOut(
        state="closed" if passed else "statement", test_deadline=deadline, opened_at=None, items=[]
    )


async def open_(
    user: authz.Principal, class_session_id: uuid.UUID, now: datetime
) -> tuple[MyTestOut, bool] | None:
    """Accept the own-work statement: (the open test, whether this call made the attempt); None
    for every caller but the Student (FR-5). Raises `commands.ReplayRequired` and
    `commands.DeadlinePassed`."""
    opened = await commands.open_attempt(user, class_session_id, now)
    if opened is None:
        return None
    async with get_sessionmaker()() as s:
        found = await sessions.individual_test_session_of(s, user, class_session_id)
    if found is None:  # no longer theirs a moment later: the same refusal as before
        return None
    return await _open(opened.attempt, found.pins), opened.created


async def save(
    user: authz.Principal,
    class_session_id: uuid.UUID,
    item_id: str,
    value: Any,
    revision: int,
    now: datetime,
) -> SavedAnswerOut | None:
    """Autosave one answer (Story 11.4, AD-10): the answer stored after the save; None for every
    caller but the Student with an open attempt (FR-5). Raises `commands.AttemptSubmitted`,
    `commands.DeadlinePassed`, `commands.UnknownItem` and `commands.InvalidAnswer`."""
    stored = await commands.save_answer(user, class_session_id, item_id, value, revision, now)
    return None if stored is None else SavedAnswerOut(**stored)
