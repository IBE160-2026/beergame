"""The computed score of one stored answer (Story 11.5, FR-52, FR-80, FR-85, AD-1): which pure rule
of `analysis.scoring` scores which item. Epic 12's assessment reads it; nothing here is sent to
the Student (FR-54).

- A multiple-choice item: `score_choice` against its answer key.
- A Starting task item: `score_sum` over the Starting task item's terms, the same rule the
  Startoppgave scores with (FR-85).
- A table or number Interactive item: `score_interactive` over the values alone (FR-80), so how
  they were entered never counts.

Long answers and Adapted items are scored against the Scoring guide (Epic 12), not here."""

from dataclasses import dataclass
from typing import Any

from app.analysis.scoring import (
    CriterionScore,
    score_choice,
    score_interactive,
    score_sum,
)
from app.modules.content.schemas import QuestionSetItem, StartingTask

__all__ = ["ItemScore", "score_answer"]


@dataclass(frozen=True)
class ItemScore:
    """One answer scored: whether it was answered, the credit as a share of the item's weight and,
    for an Interactive item, each criterion with its explanation."""

    answered: bool
    credit: float
    criteria: tuple[CriterionScore, ...] = ()


def _whole(value: Any) -> int | None:
    return value if type(value) is int else None


def score_answer(item: QuestionSetItem, value: Any, task: StartingTask) -> ItemScore | None:
    """The computed score of `value` (a stored answer's value, None when not answered) to `item`;
    None for an item no computed rule scores (a long answer, an item without its table). `task` is
    the Starting task the Class session pinned."""
    if item.type == "choice" and item.answer_key is not None:
        chosen = score_choice(value if isinstance(value, str) else None, item.answer_key)
        return ItemScore(answered=chosen.answered, credit=chosen.credit)
    if item.type == "number" and item.starting_task_item is not None:
        found = next((t for t in task.items if t.id == item.starting_task_item), None)
        if found is None:
            return None
        answer = _whole(value)
        if answer is None:
            return ItemScore(answered=False, credit=0.0)
        rows = {row.key: row.value for row in found.rows}
        summed = score_sum(((t.sign, rows[t.row]) for t in found.terms), answer)
        return ItemScore(answered=True, credit=1.0 if summed.correct else 0.0)
    spec = item.interactive
    if spec is None or item.type not in ("table", "number"):
        return None
    rule = spec.rule(item.type)
    if item.type == "number":
        values: list[int | None] = [_whole(value)]
    elif isinstance(value, list) and len(value) == len(rule.labels):
        values = [_whole(v) for v in value]
    else:
        values = [None] * len(rule.labels)
    scored = score_interactive(values, rule)
    return ItemScore(answered=scored.answered, credit=scored.credit, criteria=scored.criteria)
