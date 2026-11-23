"""The Klasserapport's learning part (Story 14.2, FR-64, FR-55, FR-56, FR-61, AD-10, AD-14).

Every number is the api's: counts, percents, medians and quartiles are computed in
`class_report_learning.py` and sent as decimal strings, so the web app only formats them (AD-10).
Question ids, titles and counts only: never a name, a `user_id`, an attempt id, an answer or a
per-Student row; the AI scores go out as a sorted list of values (AD-14). No Indicative letter is
ever part of it (FR-56)."""

import uuid
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from app.modules.reports.class_report_schemas import DistributionOut

__all__ = [
    "AdaptedPartOut",
    "ClassLearningOut",
    "LearningAiOut",
    "QuestionResultOut",
    "ScoreBandOut",
    "LearningStartingItemOut",
    "LearningStartingTaskOut",
]


class LearningStartingItemOut(BaseModel):
    """One Starting task item beside the matching Individual test item, over the Students who
    finished the Starting task and handed in a test holding that item (`students`): how many
    answered it right in the Starting task, and how many got the test item fully right with their
    mean credit in percent (an unanswered test item counts 0)."""

    number: int
    """The test item's number in the test."""
    title: str
    students: int
    start_correct: int
    start_percent: Decimal | None
    test_right: int
    test_percent: Decimal | None


class LearningStartingTaskOut(BaseModel):
    """The Starting task beside the test: `students` is how many finished the Starting task and
    handed in the test."""

    students: int
    items: list[LearningStartingItemOut]


class QuestionResultOut(BaseModel):
    """One Core question of the selection in force, in the set's order. A question taken out
    (`excluded`) has no number, no weight and no figures, and counts in no total. Over the handed-in
    tests holding it (`students`): a computed question has right, partly, wrong and not answered
    with the mean credit in percent; a long-answer question (`scoring = ai`) only how many answered
    it, its scores being the AI assessment's."""

    number: int | None
    id: str
    title: str
    type: Literal["choice", "table", "number", "long", "drawn"]
    weight: int | None
    excluded: bool
    scoring: Literal["computed", "ai", "excluded"]
    students: int
    answered: int
    right: int
    partly: int
    wrong: int
    not_answered: int
    percent: Decimal | None


class AdaptedPartOut(BaseModel):
    """The Adapted part, which differs between Students: its total weight in the selection, how many
    handed-in tests had Adapted items and how many had the replacement items instead."""

    weight: int
    adapted: int
    replaced: int


class ScoreBandOut(BaseModel):
    """How many ready AI assessments have their total, and their Core-only subscore, in `low` to
    `high` points of 100 (each band holds its lower bound; the last also holds 100)."""

    low: int
    high: int
    total: int
    core: int


class LearningAiOut(BaseModel):
    """The AI assessment totals (FR-55: AI-generated and not a grade): `switched_off` when the
    «KI-vurdering» is off for the Class session, `not_ready` while no assessment of a handed-in test
    is ready, else `ready` with how many are (`ready` of `submitted`). The totals and the Core-only
    subscores in points of 100, as distributions and bands; null without a ready assessment."""

    state: Literal["switched_off", "not_ready", "ready"]
    ready: int
    submitted: int
    total: DistributionOut | None
    core: DistributionOut | None
    bands: list[ScoreBandOut]


class ClassLearningOut(BaseModel):
    """The Klasserapport's learning part (Story 14.2) over the Class session's reporting Students
    (`students`): how many handed in the Individual test and how many may still hand it in (an open
    test, or none yet before their own Test deadline, an extension included)."""

    class_session_id: uuid.UUID
    students: int
    submitted: int
    still_to_submit: int
    starting_task: LearningStartingTaskOut
    questions: list[QuestionResultOut]
    adapted: AdaptedPartOut
    ai: LearningAiOut
