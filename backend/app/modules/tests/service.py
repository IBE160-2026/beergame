"""The Starting task (Story 6.3, FR-85, AD-1, AD-16, AD-23).

The items come from `content` at the version the Class session's lock pinned (the latest for a
session locked before the pin, and whatever version the Student's first answer was stored with).
Each answer is scored by `analysis.scoring` (computed rules, no LLM) and stored once per Student,
Class session and item: a repeat keeps the first. The final question finishes the task and
records `progress` `starting_task` in the same transaction. The game's status is not asked, so a
finished game with no Orders still offers the task.

`parts_with_content` (Story 11.11, FR-17, AD-16) tells Completion (Epic 13) which parts of a
Student's Individual test attempt hold content, so the minimum for an auto-submitted test is
applied without another module reading the answers.

The Individual test's one timed sitting (Story 11.12, FR-51) is stored with the Class session
through this module: `tests.sitting` keeps it, registered here with `sessions` for «Lagre
Klasseøkt» and «Lag kopi» (FR-66)."""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.scoring import score_sum
from app.modules.content import service as content
from app.modules.content.schemas import StartingTask, StartingTaskItem
from app.modules.progress import service as progress
from app.modules.sessions import service as sessions
from app.modules.tests import sitting
from app.modules.tests.adapted import ADAPTED
from app.modules.tests.attempt import ReportItem, ReportTest, report_test
from app.modules.tests.models import (
    PLAYED_BEFORE,
    Choice,
    starting_task_answers,
    test_answers,
    test_attempts,
)
from app.modules.tests.schemas import (
    ColumnOut,
    GivenRowOut,
    ItemResultOut,
    StartingTaskItemOut,
    StartingTaskOut,
    SumTermOut,
    TableOut,
)
from app.platform import authz
from app.platform.db import get_sessionmaker

__all__ = [
    "PARTS",
    "ItemsOpen",
    "UnknownItem",
    "AttemptSummary",
    "ColumnOut",
    "TableOut",
    "ReportItem",
    "ReportTest",
    "answer",
    "attempt_status",
    "attempt_summary",
    "finish",
    "parts_with_content",
    "read",
    "report_test",
]

Stored = Mapping[str, Mapping[str, Any]]


class UnknownItem(Exception):
    """The item id names no item of the Student's Starting task (422 `unknown_item`)."""


class ItemsOpen(Exception):
    """The final question comes after every item is answered (409 `items_open`)."""


def _terms(item: StartingTaskItem) -> list[tuple[int, int]]:
    values = {row.key: row.value for row in item.rows}
    return [(term.sign, values[term.row]) for term in item.terms]


async def _stored(s: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID) -> Stored:
    result = await s.execute(
        select(starting_task_answers).where(
            starting_task_answers.c.user_id == user_id,
            starting_task_answers.c.class_session_id == session_id,
        )
    )
    return {row["item_id"]: row for row in result.mappings()}


async def _task(
    s: AsyncSession, user_id: uuid.UUID, own: sessions.OwnGameSession
) -> tuple[int, StartingTask, Stored]:
    stored = await _stored(s, user_id, own.class_session_id)
    # The version the Student began with wins, so one Student never mixes two versions.
    begun = next(iter(stored.values()), None)
    version = begun["content_version"] if begun is not None else own.starting_task_version
    version, task = await content.starting_task(version)
    return version, task, stored


def _out(version: int, task: StartingTask, stored: Stored) -> StartingTaskOut:
    items = []
    for item in task.items:
        row = stored.get(item.id)
        result = None
        if row is not None:
            terms = _terms(item)
            result = ItemResultOut(
                answer=row["answer"],
                correct=row["correct"],
                expected=score_sum(terms, row["answer"]).expected,
                terms=[SumTermOut(sign=sign, value=value) for sign, value in terms],
            )
        items.append(
            StartingTaskItemOut(
                id=item.id,
                prompt=item.prompt,
                hint=item.hint,
                column=item.column,
                rows=[GivenRowOut(label=r.label, value=r.value) for r in item.rows],
                asked_label=item.asked_label,
                result=result,
            )
        )
    final = stored.get(PLAYED_BEFORE)
    return StartingTaskOut(
        version=version,
        items=items,
        played_before=Choice(final["choice"]) if final is not None else None,
        done=final is not None,
    )


async def _own(user: authz.Principal, game_id: str) -> sessions.OwnGameSession:
    own = await sessions.own_game_session(user, game_id)
    if own is None:
        raise authz.Forbidden
    return own


async def read(user: authz.Principal, game_id: str) -> StartingTaskOut:
    """The Student's Starting task in their own game; `authz.Forbidden` for any other id."""
    own = await _own(user, game_id)
    async with get_sessionmaker()() as s:
        return _out(*await _task(s, user.id, own))


async def answer(
    user: authz.Principal, game_id: str, item_id: str, given: int, now: datetime
) -> StartingTaskOut:
    """Score and store the answer to one item, once: an item answered before keeps its first
    answer and the state is returned unchanged."""
    own = await _own(user, game_id)
    async with get_sessionmaker().begin() as s:
        version, task, stored = await _task(s, user.id, own)
        item = next((one for one in task.items if one.id == item_id), None)
        if item is None:
            raise UnknownItem(item_id)
        if item_id not in stored:
            scored = score_sum(_terms(item), given)
            await s.execute(
                insert(starting_task_answers)
                .values(
                    id=uuid.uuid7(),
                    user_id=user.id,
                    class_session_id=own.class_session_id,
                    content_version=version,
                    item_id=item_id,
                    answer=given,
                    correct=scored.correct,
                    answered_at=now,
                )
                .on_conflict_do_nothing(constraint="uq_starting_task_answers_item")
            )
            stored = await _stored(s, user.id, own.class_session_id)
    return _out(version, task, stored)


async def finish(
    user: authz.Principal, game_id: str, choice: Choice, now: datetime
) -> StartingTaskOut:
    """Store the final question's answer («Hopp over» is `skipped`) once every item is answered,
    and record `progress` `starting_task` in the same transaction (AD-16). A repeat changes
    nothing."""
    own = await _own(user, game_id)
    async with get_sessionmaker().begin() as s:
        version, task, stored = await _task(s, user.id, own)
        if any(item.id not in stored for item in task.items):
            raise ItemsOpen
        if PLAYED_BEFORE not in stored:
            await s.execute(
                insert(starting_task_answers)
                .values(
                    id=uuid.uuid7(),
                    user_id=user.id,
                    class_session_id=own.class_session_id,
                    content_version=version,
                    item_id=PLAYED_BEFORE,
                    choice=Choice(choice).value,
                    answered_at=now,
                )
                .on_conflict_do_nothing(constraint="uq_starting_task_answers_item")
            )
            await progress.record_step(
                user.id, own.class_session_id, progress.Step.STARTING_TASK, now, within=s
            )
            stored = await _stored(s, user.id, own.class_session_id)
    return _out(version, task, stored)


PARTS: dict[str, str] = {
    "choice": "choice",
    "table": "interactive",
    "number": "interactive",
    "drawn": "interactive",
    "long": "long",
    ADAPTED: "adapted",
}
"""The parts of the Individual test by item type (Story 11.11, FR-17) [ASSUMPTION: the parts
Completion's minimum counts]: multiple choice, Interactive items (table, number and drawn), long
answers and Adapted items."""


def _has_content(value: Any) -> bool:
    """Whether a saved answer holds content: not cleared, not blank text, not a table whose every
    cell is empty (the same rule as the page's unanswered items, Story 11.10)."""
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, list):
        return any(cell is not None for cell in value)
    return True


async def parts_with_content(
    user_id: uuid.UUID, class_session_id: uuid.UUID
) -> dict[str, bool] | None:
    """Which parts of the Student's Individual test attempt hold content (Story 11.11, FR-17,
    AD-16): for each part among its frozen items (`PARTS`), whether any of those items has a saved
    answer with content. None when the Student has no attempt. Reads no answer out of `tests`:
    the caller learns only the flags."""
    async with get_sessionmaker()() as s:
        attempt = (
            (
                await s.execute(
                    select(test_attempts.c.id, test_attempts.c["items"]).where(
                        test_attempts.c.user_id == user_id,
                        test_attempts.c.class_session_id == class_session_id,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        if attempt is None:
            return None
        saved = await s.execute(
            select(test_answers.c.item_id, test_answers.c.value).where(
                test_answers.c.attempt_id == attempt["id"]
            )
        )
        answered = {row.item_id for row in saved if _has_content(row.value)}
    parts: dict[str, bool] = {}
    for item in attempt["items"]:
        part = PARTS.get(item["type"])
        if part is not None:
            parts[part] = parts.get(part, False) or item["id"] in answered
    return parts


async def attempt_status(user_id: uuid.UUID, class_session_id: uuid.UUID) -> str | None:
    """The status of the Student's Individual test attempt (`open`, `submitted` or
    `auto_submitted`), None without one (Story 13.1: Completion checks the parts of an
    auto-submitted attempt only, FR-17)."""
    async with get_sessionmaker()() as s:
        return await s.scalar(
            select(test_attempts.c.status).where(
                test_attempts.c.user_id == user_id,
                test_attempts.c.class_session_id == class_session_id,
            )
        )


@dataclass(frozen=True)
class AttemptSummary:
    """The Student's Individual test attempt as the Studentside shows it (Story 13.2, FR-63): its
    status (`open`, `submitted`, `auto_submitted`), when it was handed in (None while open) and
    which parts hold content (`parts_with_content`). Never an answer."""

    status: str
    submitted_at: datetime | None
    parts: dict[str, bool]


async def attempt_summary(user_id: uuid.UUID, class_session_id: uuid.UUID) -> AttemptSummary | None:
    """The `AttemptSummary` of the Student's attempt in the Class session, None without one."""
    async with get_sessionmaker()() as s:
        found = (
            await s.execute(
                select(test_attempts.c.status, test_attempts.c.submitted_at).where(
                    test_attempts.c.user_id == user_id,
                    test_attempts.c.class_session_id == class_session_id,
                )
            )
        ).first()
    if found is None:
        return None
    parts = await parts_with_content(user_id, class_session_id)
    return AttemptSummary(status=found.status, submitted_at=found.submitted_at, parts=parts or {})


# «Lagre Klasseøkt» stores the timed sitting here (Story 11.12), and «Lag kopi» copies it (FR-66).
sessions.register_test_sitting(sitting.minutes_of, sitting.write)
sessions.register_copier(sitting.copy_sitting)
