"""The test results of a Class session's Students, for the Klasserapport's learning part (Story
14.2, FR-64, FR-55, FR-61, AD-1, AD-10, AD-13).

`class_results(s, class_session_id, students)` reads, in a fixed number of queries whatever the
number of Students and never writing:

- the selection in force (the Start-date lock's pin, else the selection in force) and its question
  set, so the report lists the questions in the set's order with the ones taken out;
- each Student's Starting task answers (item and whether it was right) and whether they finished
  it (the final question's row);
- each Student's attempt: its status, the frozen items with their weights, the computed credit
  `tests` stored at the hand-in for each answered computed item (never recomputed), which items
  hold content (the rule of `service.parts_with_content`, in SQL so no answer text is read), and
  their effective Test deadline (`sessions.effective_test_deadlines`, an extension included);
- their AI assessment total and Core-only subscore, only when the assessment reads as ready exactly
  as the Student's own «KI-vurdering» reads it (`assessed._view`): the switch on, the attempt
  closed, the assessment `ready` and every long-answer and Adapted item scored. The total comes
  from `analysis.total_score` and the subscore from `analysis.core_total_score` (Adapted and
  replacement items left out), both in percent of their weights.

The result is keyed by Student for the caller to aggregate; the caller sends no identifier on."""

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Boolean, case, func, literal_column, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.total import core_total_score
from app.modules.assessment import service as assessment
from app.modules.content.schemas import QuestionSet
from app.modules.sessions import service as sessions
from app.modules.tests import commands
from app.modules.tests.adapted import ADAPTED
from app.modules.tests.models import (
    PLAYED_BEFORE,
    AttemptStatus,
    starting_task_answers,
    test_answers,
    test_attempts,
)
from app.modules.tests.selection import Selection

__all__ = ["AI_TYPES", "ClassResults", "FrozenItem", "StudentResult", "class_results"]

AI_TYPES = frozenset({"long", ADAPTED})
"""The item types the AI assesses against the Scoring guide (as `assessed.AI_TYPES`)."""


@dataclass(frozen=True)
class FrozenItem:
    """An item frozen on an attempt: its id, type and weight, and whether it is a replacement item
    standing in for the Adapted items (Story 11.7)."""

    id: str
    type: str
    weight: int
    replacement: bool


@dataclass(frozen=True)
class StudentResult:
    """One Student's results in the Class session (Story 14.2)."""

    starting: Mapping[str, bool]
    """Each answered Starting task item by its id, and whether the answer was right."""
    starting_done: bool
    """The Student answered the Starting task's final question (finished it)."""
    status: str | None
    """The attempt's status (`open`, `submitted`, `auto_submitted`); None without one."""
    items: tuple[FrozenItem, ...]
    credits: Mapping[str, float]
    """The stored credit (0 to 1) of each answered computed item."""
    answered: frozenset[str]
    """The frozen items whose saved answer holds content."""
    deadline: datetime | None
    """The Student's effective Test deadline (None while the Class session has none)."""
    total: float | None
    """The AI assessment total in percent of the frozen weights; None unless it reads as ready."""
    core: float | None
    """The Core-only subscore in percent; None unless the total is there."""

    @property
    def handed_in(self) -> bool:
        return self.status in (AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED)


@dataclass(frozen=True)
class ClassResults:
    """The Class session's question set and selection in force, whether the «KI-vurdering» is
    switched on, and each asked Student's results."""

    question_set: QuestionSet
    selection: Selection
    ai_enabled: bool
    students: Mapping[uuid.UUID, StudentResult]


def _has_content():
    """Whether a saved answer holds content, as `service._has_content` judges it: not cleared, not
    blank text, not a table whose every cell is empty."""
    value = test_answers.c.value
    return case(
        (func.jsonb_typeof(value) == "null", False),
        (
            func.jsonb_typeof(value) == "string",
            func.regexp_replace(value.op("#>>")(literal_column("'{}'")), r"\s", "", "g") != "",
        ),
        (
            func.jsonb_typeof(value) == "array",
            func.jsonb_path_exists(value, literal_column("'$[*] ? (@ != null)'::jsonpath")),
        ),
        else_=true(),
    ).cast(Boolean)


def _frozen(items: Sequence[Mapping]) -> tuple[FrozenItem, ...]:
    return tuple(
        FrozenItem(
            id=str(item["id"]),
            type=str(item["type"]),
            weight=int(item["weight"]),
            replacement=bool(item.get("replaces")),
        )
        for item in items
    )


def _scores(
    items: tuple[FrozenItem, ...], credits: Mapping[str, float], steps: Mapping[str, int]
) -> tuple[float | None, float | None]:
    """The total and the Core-only subscore in percent, or (None, None) while an AI item has no
    step. A computed item with no stored credit counts 0, as in the Student's view."""
    weights = {item.id: item.weight for item in items}
    computed = {item.id: credits.get(item.id, 0.0) for item in items if item.type not in AI_TYPES}
    ai_items = {
        item.id: steps[item.id] for item in items if item.type in AI_TYPES and item.id in steps
    }
    if len(ai_items) < sum(1 for item in items if item.type in AI_TYPES):
        return None, None
    # The total in percent of the frozen weights: rescaled exactly, rounded once (as the subscore).
    total = core_total_score(computed, ai_items, weights, weights)
    if total is None:
        return None, None
    core = [item.id for item in items if item.type != ADAPTED and not item.replacement]
    return total, core_total_score(computed, ai_items, weights, core)


async def class_results(
    s: AsyncSession, class_session_id: uuid.UUID, students: Sequence[uuid.UUID]
) -> ClassResults:
    """The results of `students` in the Class session, read in `s` (see the module docstring).
    The caller has judged access and chosen the Students (`reports.scope`)."""
    pins = await sessions.locked_pins(s, class_session_id)
    selection, question_set = await commands.selection_of(s, class_session_id, pins)
    switch = await assessment.switch_of(s, class_session_id)
    asked = list(dict.fromkeys(students))
    starting: dict[uuid.UUID, dict[str, bool]] = {}
    done: set[uuid.UUID] = set()
    attempts: dict[uuid.UUID, Mapping] = {}
    if asked:
        for row in await s.execute(
            select(
                starting_task_answers.c.user_id,
                starting_task_answers.c.item_id,
                starting_task_answers.c.correct,
            ).where(
                starting_task_answers.c.class_session_id == class_session_id,
                starting_task_answers.c.user_id.in_(asked),
            )
        ):
            if row.item_id == PLAYED_BEFORE:
                done.add(row.user_id)
            else:
                starting.setdefault(row.user_id, {})[row.item_id] = bool(row.correct)
        found = await s.execute(
            select(
                test_attempts.c.id,
                test_attempts.c.user_id,
                test_attempts.c.status,
                test_attempts.c["items"],
                test_attempts.c.closed_at,
            ).where(
                test_attempts.c.class_session_id == class_session_id,
                test_attempts.c.user_id.in_(asked),
            )
        )
        attempts = {row.user_id: row._mapping for row in found}
    credits: dict[uuid.UUID, dict[str, float]] = {}
    answered: dict[uuid.UUID, set[str]] = {}
    if attempts:
        ids = [attempt["id"] for attempt in attempts.values()]
        for row in await s.execute(
            select(
                test_answers.c.attempt_id,
                test_answers.c.item_id,
                test_answers.c.score,
                _has_content().label("has_content"),
            ).where(test_answers.c.attempt_id.in_(ids))
        ):
            if row.has_content:
                answered.setdefault(row.attempt_id, set()).add(row.item_id)
            score = row.score
            if isinstance(score, Mapping) and score.get("answered"):
                credits.setdefault(row.attempt_id, {})[row.item_id] = float(
                    score.get("credit") or 0.0
                )
    summaries = await assessment.summaries_for_session(s, class_session_id) if attempts else {}
    steps = await assessment.item_scores_for_session(s, class_session_id) if attempts else {}
    deadlines = await sessions.effective_test_deadlines(s, class_session_id, asked) if asked else {}
    results: dict[uuid.UUID, StudentResult] = {}
    for user_id in asked:
        attempt = attempts.get(user_id)
        items = _frozen(attempt["items"]) if attempt is not None else ()
        attempt_id = attempt["id"] if attempt is not None else None
        own_credits = credits.get(attempt_id, {}) if attempt_id is not None else {}
        total = core = None
        summary = summaries.get(user_id)
        if (
            attempt is not None
            and switch.enabled
            and attempt["closed_at"] is not None
            and summary is not None
            and summary.attempt_id == attempt_id
            and summary.status == "ready"
        ):
            total, core = _scores(items, own_credits, steps.get(attempt_id, {}))
        results[user_id] = StudentResult(
            starting=starting.get(user_id, {}),
            starting_done=user_id in done,
            status=attempt["status"] if attempt is not None else None,
            items=items,
            credits=own_credits,
            answered=frozenset(answered.get(attempt_id, set())) if attempt_id else frozenset(),
            deadline=deadlines.get(user_id),
            total=total,
            core=core,
        )
    return ClassResults(
        question_set=question_set,
        selection=selection,
        ai_enabled=switch.enabled,
        students=results,
    )
