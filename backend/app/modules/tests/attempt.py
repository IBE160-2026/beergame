"""The Student's Individual test as their page reads it (Story 11.3, FR-51, FR-5, AD-12, AD-16).

`read` answers the state: `statement` before the Student has accepted the own-work statement (no
item is served; in one timed sitting it carries the Student's time limit, Story 11.12), `open` with
the items of their attempt in its frozen order, `closed` when their Test deadline has passed with no
attempt. `open_` accepts the statement through `commands.open_attempt`. Each open item carries a
choice item's option ids, a table item's value table (a drawn item's with its graph's axis, Story
11.14) or a number item's column (Story 11.5; a Starting task item's from the Class session's pinned
Starting task), an Adapted item's frozen text (Story 11.7) and the Student's saved answer; `save`
autosaves one answer through `commands.save_answer` (Story 11.4). Only the Student's own locked
Class session is reached; every other caller gets None (the route's 403 `forbidden`), whether or not
an attempt exists."""

import math
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from app.modules.content import service as content
from app.modules.content.schemas import TABLE_TYPES, QuestionSet, QuestionSetItem, StartingTask
from app.modules.progress import service as progress
from app.modules.sessions import service as sessions
from app.modules.tests import commands, rules, sitting
from app.modules.tests.adapted import ADAPTED
from app.modules.tests.models import AttemptStatus, test_answers
from app.modules.tests.schemas import (
    AxisOut,
    ColumnOut,
    ColumnRowOut,
    IndividualItemOut,
    MyTestOut,
    SavedAnswerOut,
    StoredAnswerOut,
    TableColumnOut,
    TableOut,
    WordingOut,
)
from app.platform import authz
from app.platform.db import get_sessionmaker

__all__ = ["ReportItem", "ReportTest", "read", "open_", "report_test", "save", "submit"]


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
    """A table item's value table; a drawn item's too, with its graph's axis (Story 11.14)."""
    spec = item.interactive
    if item.type not in TABLE_TYPES or spec is None:
        return None
    return TableOut(
        prompt=spec.prompt,
        hint=spec.hint,
        caption=spec.caption,
        rows=list(spec.rows),
        columns=[TableColumnOut(label=c.label, values=list(c.values)) for c in spec.given],
        asked_label=spec.asked,
        negative=spec.negative,
        axis=None if spec.axis is None else AxisOut(min=spec.axis.min, max=spec.axis.max),
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


def _adapted(frozen: Mapping[str, Any], number: int, answer: Any) -> IndividualItemOut:
    """An Adapted item as frozen on the attempt (Story 11.7): its text never changes."""
    wording = WordingOut.model_validate(frozen["text"])
    return IndividualItemOut(
        id=frozen["id"],
        number=number,
        type=ADAPTED,
        title=wording.text,
        options=[],
        table=None,
        column=None,
        wording=wording,
        answer=answer,
    )


async def _items(attempt: Mapping[str, Any], pins: Any) -> list[IndividualItemOut]:
    question_set: QuestionSet = await content.get(
        content.Kind.QUESTION_SET, attempt["question_set_version"]
    )
    by_id = {item.id: item for item in (*question_set.items, *question_set.replacements)}
    # The Class session's pinned Starting task, the one its Students answered (Story 6.3).
    _, task = await content.starting_task(content.pinned_version(pins))
    answers = await _answers(attempt["id"])
    out = []
    for number, frozen in enumerate(attempt["items"], start=1):
        if frozen["type"] == ADAPTED:
            out.append(_adapted(frozen, number, answers.get(frozen["id"])))
            continue
        item = by_id[frozen["id"]]
        out.append(
            IndividualItemOut(
                id=frozen["id"],
                number=number,
                type=frozen["type"],
                title=item.title,
                options=list(item.options),
                table=_table(item),
                column=_column(item, task),
                wording=None,
                answer=answers.get(frozen["id"]),
            )
        )
    return out


async def _open(attempt: Mapping[str, Any], pins: Any, now: datetime) -> MyTestOut:
    """The Student's attempt: `open`, or handed in (`submitted`, `auto_submitted`, Story 11.10)
    with its time; the items and saved answers either way. A timed one (Story 11.12) carries its
    sitting's end, when answering ends, the API's clock, and whether the sweep handed it in at the
    sitting's end (`commands.end_sitting` stores `submitted_at = sitting_ends_at`)."""
    state = attempt["status"]
    ends = attempt["sitting_ends_at"]
    # The limit the sitting was opened with, the Student's time factor applied.
    limit = (
        math.ceil((ends - attempt["statement_accepted_at"]).total_seconds() / 60)
        if ends is not None
        else None
    )
    return MyTestOut(
        state="open" if state == AttemptStatus.OPEN.value else state,
        test_deadline=attempt["effective_deadline"],
        opened_at=attempt["statement_accepted_at"],
        submitted_at=attempt["submitted_at"],
        items=await _items(attempt, pins),
        time_limit_minutes=limit,
        sitting_ends_at=ends,
        answering_ends_at=rules.answering_ends_at(attempt),
        server_now=now,
        sitting_ended=(
            state == AttemptStatus.AUTO_SUBMITTED.value
            and ends is not None
            and attempt["submitted_at"] == ends
            and (attempt["effective_deadline"] is None or ends < attempt["effective_deadline"])
        ),
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
        minutes = await sitting.minutes_of(s, class_session_id) if attempt is None else None
        factor = (
            await sitting.time_factor(s, class_session_id, user.id) if minutes is not None else None
        )
    if attempt is not None:
        return await _open(attempt, found.pins, now)
    if not await progress.has_step(user.id, class_session_id, progress.Step.REPLAY):
        raise commands.ReplayRequired
    deadline = sessions.effective_test_deadline(user, found.row)
    passed = deadline is not None and deadline <= now
    return MyTestOut(
        state="closed" if passed else "statement",
        test_deadline=deadline,
        opened_at=None,
        submitted_at=None,
        items=[],
        # Story 11.12: the statement names the Student's own limit before the test is opened.
        time_limit_minutes=(
            rules.limit_minutes(minutes, factor)
            if minutes is not None and factor is not None
            else None
        ),
        server_now=now,
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
    return await _open(opened.attempt, found.pins, now), opened.created


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


async def submit(
    user: authz.Principal, class_session_id: uuid.UUID, now: datetime
) -> MyTestOut | None:
    """«Lever testen» (Story 11.10, FR-51): the test as handed in; None for every caller but the
    Student with an opened test (FR-5). Raises `commands.AttemptSubmitted` when it was handed in
    already (nothing changes) and `commands.DeadlinePassed` past the Student's Test deadline."""
    done = await commands.submit(user, class_session_id, now)
    if done is None:
        return None
    if not done.submitted:
        raise commands.AttemptSubmitted
    # Handed in: answered with what was committed, read with the pins the command read.
    return await _open(done.attempt, done.pins, now)


@dataclass(frozen=True)
class ReportItem:
    """One item of a Student's test for the Student report (Story 13.10, FR-58): the item as the
    Student's page shows it (its saved answer with it), its frozen weight, and the stored computed
    score as points of that weight (credit × weight, two decimals) with whether it was answered;
    `points` None for an item no computed rule scores (a long answer, an Adapted item: the Scoring
    guide's, Epic 12) or not scored yet (an attempt still open). Never a criterion, an explanation
    or an AI score (FR-54, C-2)."""

    item: IndividualItemOut
    weight: int
    points: Decimal | None


@dataclass(frozen=True)
class ReportTest:
    """The Student's attempt: `open`, `submitted` or `auto_submitted`, when it was handed in,
    and every item in its frozen order."""

    state: str
    submitted_at: datetime | None
    items: list[ReportItem]


COMPUTED = frozenset({"choice", "table", "number", "drawn"})
"""The item types a computed rule scores (`tests.scoring.score_answer`)."""


def _points(score: Any, weight: int) -> Decimal | None:
    credit = score.get("credit") if isinstance(score, Mapping) else None
    if isinstance(credit, bool) or not isinstance(credit, int | float):
        return None
    return (Decimal(str(credit)) * weight).quantize(Decimal("0.01"))


async def report_test(user_id: uuid.UUID, class_session_id: uuid.UUID) -> ReportTest | None:
    """The Student's Individual test for their Student report, or None before they opened it.
    Takes ids only: the `reports-single` job calls it after the api's policy allowed the
    download (AD-12, AD-18). The items are read as the Student's page reads them (`_items`, with
    the pins the Class session's lock stored), the scores as `commands.score_answers` stored
    them at the hand-in."""
    async with get_sessionmaker()() as s:
        attempt = await commands.attempt_of(s, user_id, class_session_id)
        if attempt is None:
            return None
        pins = await sessions.locked_pins(s, class_session_id)
        scores = {
            row["item_id"]: row["score"]
            for row in (
                await s.execute(
                    select(test_answers.c.item_id, test_answers.c.score).where(
                        test_answers.c.attempt_id == attempt["id"]
                    )
                )
            ).mappings()
        }
    items = await _items(attempt, pins)
    weights = {frozen["id"]: int(frozen.get("weight") or 0) for frozen in attempt["items"]}
    handed_in = attempt["status"] != AttemptStatus.OPEN.value

    def points(item: IndividualItemOut) -> Decimal | None:
        weight = weights.get(item.id, 0)
        found = _points(scores.get(item.id), weight)
        # A handed-in item a computed rule scores, left unanswered: no row, so nothing stored,
        # and it scores 0 (`score_answers`).
        if found is None and handed_in and item.type in COMPUTED and item.answer is None:
            return Decimal("0.00")
        return found

    return ReportTest(
        state=attempt["status"],
        submitted_at=attempt["submitted_at"],
        items=[
            ReportItem(item=item, weight=weights.get(item.id, 0), points=points(item))
            for item in items
        ],
    )
