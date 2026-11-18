"""Story 2.3: the mock provider's fixed answer fits the output schema (AD-17)."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from app.ai import mock


class Kind(StrEnum):
    UP = "up"
    DOWN = "down"


class Inner(BaseModel):
    note: str = Field(min_length=3)
    flag: bool


class Wide(BaseModel):
    order: int = Field(ge=4, le=999)
    above: int = Field(gt=2)
    share: float = Field(ge=0.5)
    kind: Kind
    tag: Literal["fixed"]
    items: list[int] = Field(min_length=2)
    inner: Inner
    maybe: int | None
    optional: str = "default"


def test_the_fixed_answer_validates_against_its_schema_and_never_changes():
    answer = mock.fixed_answer(Wide)
    assert Wide.model_validate(answer) == Wide(
        order=4,
        above=3,
        share=0.5,
        kind=Kind.UP,
        tag="fixed",
        items=[0, 0],
        inner=Inner(note="xxx", flag=False),
        maybe=0,
    )
    assert mock.fixed_answer(Wide) == answer
    assert "optional" not in answer
