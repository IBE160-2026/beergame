"""The Klasserapport's learning part (Story 14.2, FR-64, FR-55, FR-56, FR-61, FR-63, AD-1, AD-10,
AD-13): what the class learned, for the Lecturers of the Class (`class_report.READ`).

`class_learning(user, class_session_id, now)` is the one assembler. It reads `tests` through its
`service.py` (`tests.class_results`, one bulk read with the computed scores `tests` stored and the
AI totals made by `analysis.total_score` and `analysis.core_total_score`) and computes every
figure here, never in the web app (AD-10):

- the Students: the reporting Students of the Class session, the Class's registered Students less
  test students and none for a Control test Class session. Until Epic 13's `reports.scope` is on
  this branch, `_reporting_students` stands in for `scope.reporting_students(session, id)`; the
  merge replaces it with that call (AD-13);
- handed in (`submitted`, `auto_submitted`) and still to submit (an open test, or none yet while
  the Student's own Test deadline, an extension included, is unset or ahead);
- the Starting task beside the matching test items, over the Students who did both;
- results per question of the selection in force, a question taken out listed as such and left out
  of every figure;
- the AI assessment totals and Core-only subscores as distributions and bands, or the state that
  stands in for them (switched off, not ready). Never an Indicative letter (FR-56).

Small groups (Story 14.2's decision, FR-63): the live report shows figures at any group size, each
with its count, since the Class's own staff may read every answer; the threshold of 10 belongs to
the stored aggregates (Story 14.3) and the cross-Institution views. Nothing in the answer names a
Student: no name, `user_id`, attempt id or per-Student row, and the score values go out sorted.

A fixed number of queries whatever the number of Students (NFR-3), and no write."""

import uuid
from collections.abc import Iterable, Sequence
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.classes import service as classes
from app.modules.identity import service as identity
from app.modules.reports.class_report import READ, distribution, percent
from app.modules.reports.class_report_learning_schemas import (
    AdaptedPartOut,
    ClassLearningOut,
    LearningAiOut,
    LearningStartingItemOut,
    LearningStartingTaskOut,
    QuestionResultOut,
    ScoreBandOut,
)
from app.modules.sessions import service as sessions
from app.modules.tests import service as tests
from app.platform import authz
from app.platform.db import get_sessionmaker

__all__ = ["BANDS", "bands", "class_learning", "mean_percent"]

_TENTH = Decimal("0.1")
ADAPTED = "adapted"
AI_SCORED = frozenset({"long"})
"""The Core question types the AI assesses; every other Core type is computed."""

BANDS = tuple((low, low + 10) for low in range(0, 100, 10))
"""The 10-point bands of the score table: 0–10, …, 90–100."""


def mean_percent(credits: Sequence[float]) -> Decimal | None:
    """The mean of credits 0 to 1 in percent to one decimal (half up); None for none."""
    if not credits:
        return None
    total = sum((Decimal(str(credit)) for credit in credits), Decimal(0))
    return (total * 100 / len(credits)).quantize(_TENTH, ROUND_HALF_UP)


def bands(totals: Iterable[float], cores: Iterable[float]) -> list[ScoreBandOut]:
    """How many totals and Core-only subscores lie in each band of `BANDS` (100 in the last)."""

    def band(value: float) -> int:
        return min(max(int(value // 10), 0), len(BANDS) - 1)

    total_counts = [0] * len(BANDS)
    core_counts = [0] * len(BANDS)
    for value in totals:
        total_counts[band(value)] += 1
    for value in cores:
        core_counts[band(value)] += 1
    return [
        ScoreBandOut(low=low, high=high, total=total_counts[i], core=core_counts[i])
        for i, (low, high) in enumerate(BANDS)
    ]


async def _reporting_students(
    s: AsyncSession, class_id: uuid.UUID, control_test: bool
) -> list[uuid.UUID]:
    """The Students the report counts: `scope.reporting_students(...)` of Epic 13 (AD-13), the
    Class's registered Students less test students, none for a Control test Class session."""
    if control_test:
        return []
    registered = await classes.registered_students(class_id)
    excluded = await identity.test_students(s, registered) if registered else set()
    return sorted((user for user in registered if user not in excluded), key=str)


def _still_to_submit(result: tests.StudentResult, now: datetime) -> bool:
    if result.status == "open":
        return True
    return result.status is None and (result.deadline is None or result.deadline > now)


def _questions(
    found: tests.ClassResults, handed: list[tests.StudentResult]
) -> list[QuestionResultOut]:
    rows = []
    number = 0
    holding = [{item.id for item in result.items} for result in handed]
    for item in found.question_set.items:
        excluded = item.id in found.selection.excluded
        if not excluded:
            number += 1
        over = (
            []
            if excluded
            else [r for r, ids in zip(handed, holding, strict=True) if item.id in ids]
        )
        computed = item.type not in AI_SCORED
        credits = [r.credits[item.id] for r in over if item.id in r.credits]
        answered = len(credits) if computed else sum(1 for r in over if item.id in r.answered)
        rows.append(
            QuestionResultOut(
                number=None if excluded else number,
                id=item.id,
                title=item.title,
                type=item.type,
                weight=None if excluded else found.selection.weights.get(item.id, item.weight),
                excluded=excluded,
                scoring="excluded" if excluded else "computed" if computed else "ai",
                students=len(over),
                answered=answered,
                right=sum(1 for c in credits if c >= 1) if computed else 0,
                partly=sum(1 for c in credits if 0 < c < 1) if computed else 0,
                wrong=sum(1 for c in credits if c <= 0) if computed else 0,
                not_answered=len(over) - answered if computed else 0,
                percent=(
                    mean_percent([r.credits.get(item.id, 0.0) for r in over]) if computed else None
                ),
            )
        )
    return rows


def _starting_task(
    found: tests.ClassResults, handed: list[tests.StudentResult]
) -> LearningStartingTaskOut:
    both = [result for result in handed if result.starting_done]
    numbers: dict[str, int] = {}
    for item in found.question_set.items:
        if item.id not in found.selection.excluded:
            numbers[item.id] = len(numbers) + 1
    items = []
    for item in found.question_set.items:
        if item.starting_task_item is None or item.id not in numbers:
            continue
        over = [r for r in both if any(frozen.id == item.id for frozen in r.items)]
        start_correct = sum(1 for r in over if r.starting.get(item.starting_task_item))
        test = [r.credits.get(item.id, 0.0) for r in over]
        items.append(
            LearningStartingItemOut(
                number=numbers[item.id],
                title=item.title,
                students=len(over),
                start_correct=start_correct,
                start_percent=percent(start_correct, len(over)),
                test_right=sum(1 for credit in test if credit >= 1),
                test_percent=mean_percent(test),
            )
        )
    return LearningStartingTaskOut(students=len(both), items=items)


def _ai(found: tests.ClassResults, handed: list[tests.StudentResult]) -> LearningAiOut:
    ready = [result for result in handed if result.total is not None]
    shown_at = lambda value: Decimal(str(value)).quantize(_TENTH, ROUND_HALF_UP)  # noqa: E731
    totals = sorted(shown_at(r.total) for r in ready)
    cores = sorted(shown_at(r.core) for r in ready if r.core is not None)
    if not found.ai_enabled:
        state = "switched_off"
    elif not ready:
        state = "not_ready"
    else:
        state = "ready"
    shown = state == "ready"
    return LearningAiOut(
        state=state,
        ready=len(ready) if found.ai_enabled else 0,
        submitted=len(handed),
        total=distribution(totals, _TENTH) if shown else None,
        core=distribution(cores, _TENTH) if shown else None,
        bands=bands(map(float, totals), map(float, cores)) if shown else [],
    )


async def class_learning(
    user: authz.Principal, class_session_id: uuid.UUID, now: datetime
) -> ClassLearningOut | None:
    """The learning part of the Klasserapport, or None when the User may not read it or the Class
    session does not exist: one answer for both (FR-5, NFR-7)."""
    staffed = await sessions.staffed_session(user, class_session_id, READ)
    if staffed is None:
        return None
    async with get_sessionmaker()() as s:
        kind = await sessions.kind_of(class_session_id, session=s)
        students = await _reporting_students(s, staffed.class_id, kind == sessions.CONTROL_TEST)
        found = await tests.class_results(s, class_session_id, students)
    results = [found.students[student] for student in students]
    handed = [result for result in results if result.handed_in]
    return ClassLearningOut(
        class_session_id=class_session_id,
        students=len(results),
        submitted=len(handed),
        still_to_submit=sum(1 for result in results if _still_to_submit(result, now)),
        starting_task=_starting_task(found, handed),
        questions=_questions(found, handed),
        adapted=AdaptedPartOut(
            weight=found.selection.adapted_weight,
            adapted=sum(1 for r in handed if any(item.type == ADAPTED for item in r.items)),
            replaced=sum(1 for r in handed if any(item.replacement for item in r.items)),
        ),
        ai=_ai(found, handed),
    )
