"""The Starting task as the Student reads and answers it (Story 6.3, FR-85, UX-DR63)."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.tests.models import Choice

_IN = ConfigDict(extra="forbid")


class GivenRowOut(BaseModel):
    label: str
    value: int


class SumTermOut(BaseModel):
    """One part of the sum the result shows: «0 − 13 + 16» is (+1, 0), (−1, 13), (+1, 16)."""

    sign: Literal[1, -1]
    value: int


class ItemResultOut(BaseModel):
    """The stored answer and its score. Only for an answered item: the answer key is never sent
    before."""

    answer: int
    correct: bool
    expected: int
    terms: list[SumTermOut]


class StartingTaskItemOut(BaseModel):
    id: str
    prompt: str
    hint: str | None
    column: str
    rows: list[GivenRowOut]
    asked_label: str
    result: ItemResultOut | None


class StartingTaskOut(BaseModel):
    """The Student's Starting task: the pinned content version, the items in order (answered
    ones with their result), the final question's choice and whether the task is done. The web
    app resumes at the first item without a result."""

    version: int
    items: list[StartingTaskItemOut]
    played_before: Choice | None
    done: bool


class AnswerIn(BaseModel):
    model_config = _IN

    item_id: Annotated[str, Field(min_length=1, max_length=40)]
    answer: Annotated[int, Field(strict=True, ge=-1_000_000, le=1_000_000)]


class FinalIn(BaseModel):
    model_config = _IN

    choice: Choice
