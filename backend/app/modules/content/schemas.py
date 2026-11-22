"""The shapes of the content records (Story 6.3, AD-23), validated on every publish and read.

The Detected pattern definitions (Story 9.1) are `analysis.patterns.PatternSet`: the pure layer
that applies the thresholds owns their shape; so are the sentence templates (Story 9.4,
`analysis.sentences.SentenceTemplates`) and the own moments' templates (Story 9.7,
`analysis.sentences.MomentTemplates`) and the Debrief quiz (Story 9.9,
`analysis.quiz.DebriefQuiz`, whose scoring and own-game sentences are pure) and the narration
templates (Story 9.14, `analysis.narration.NarrationTemplates`). The reflection
questions (Story 9.6) are shaped here."""

import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.analysis.narration import NarrationTemplates
from app.analysis.patterns import PatternSet
from app.analysis.quiz import DebriefQuiz
from app.analysis.sentences import MomentTemplates, SentenceTemplates

__all__ = [
    "ColumnRow",
    "DebriefQuiz",
    "MomentTemplates",
    "NarrationTemplates",
    "REFLECTION_KINDS",
    "PatternSet",
    "ReflectionQuestion",
    "ReflectionQuestions",
    "SentenceTemplates",
    "StartingTask",
    "StartingTaskItem",
    "SumTerm",
]

_FROZEN = ConfigDict(frozen=True, extra="forbid")
_FORBIDDEN = re.compile(r"beer\s*game|bullwhip", re.IGNORECASE)
_Text = Annotated[str, Field(min_length=1, max_length=500)]
_Key = Annotated[str, Field(pattern=r"^[a-z][a-z0-9-]{0,39}$")]
"""No underscore, so an item id never meets the final question's `played_before`."""


class ColumnRow(BaseModel):
    """A given cell of the item's column: a row of the week table and its number."""

    model_config = _FROZEN

    key: _Key
    label: _Text
    # At most 12 terms of 80 000: every right answer stays inside what the api takes (±1 000 000).
    value: Annotated[int, Field(strict=True, ge=-80_000, le=80_000)]


class SumTerm(BaseModel):
    """One part of the computed rule: a row of the column, added or taken away."""

    model_config = _FROZEN

    row: _Key
    sign: Literal[1, -1]


class StartingTaskItem(BaseModel):
    """One item of the Starting task (FR-85): a column of the week table with given rows and one
    asked row, answered by a whole number. The answer is the signed sum of `terms` over the
    given rows (`analysis.scoring.score_sum`), so new items need no code."""

    model_config = _FROZEN

    id: _Key
    prompt: _Text
    hint: _Text | None = None
    column: _Text
    """The column's heading, e.g. «Uke 11»."""
    rows: Annotated[tuple[ColumnRow, ...], Field(min_length=1, max_length=12)]
    asked_label: _Text
    terms: Annotated[tuple[SumTerm, ...], Field(min_length=1, max_length=12)]

    @model_validator(mode="after")
    def _pre_debrief_copy(self) -> StartingTaskItem:
        """The Startoppgave comes before the Debrief: no name of the exercise, no exclamation
        mark (FR-84, AD-19, UX-DR78), as `check-copy.mjs` holds the web app's copy."""
        texts = [self.prompt, self.hint or "", self.column, self.asked_label]
        texts += [row.label for row in self.rows]
        for text in texts:
            if "!" in text or _FORBIDDEN.search(text):
                raise ValueError(f"pre-Debrief content may not say {text!r}")
        return self

    @model_validator(mode="after")
    def _terms_name_rows(self) -> StartingTaskItem:
        keys = [row.key for row in self.rows]
        if len(set(keys)) != len(keys):
            raise ValueError("row keys repeat")
        if any(term.row not in keys for term in self.terms):
            raise ValueError("a term names no row of the column")
        return self


REFLECTION_KINDS = ("feelings", "evidence", "structure")
"""The reflection questions' kinds, in the order they are asked (FR-45)."""


class ReflectionQuestion(BaseModel):
    """One reflection question of the Debrief (Story 9.6): asked after the whole chain, answered
    in the Student's own words."""

    model_config = _FROZEN

    id: _Key
    kind: Literal["feelings", "evidence", "structure"]
    prompt: _Text
    hint: _Text | None = None


class ReflectionQuestions(BaseModel):
    """The reflection questions (Story 9.6, FR-45, UX-DR74): feelings, then evidence, then
    structure, each kind at least once. Shown after the reveal, so the exercise may be named, but
    the copy rules hold: no exclamation mark."""

    model_config = _FROZEN

    questions: Annotated[tuple[ReflectionQuestion, ...], Field(min_length=1, max_length=12)]

    @model_validator(mode="after")
    def _ids_unique(self) -> ReflectionQuestions:
        ids = [question.id for question in self.questions]
        if len(set(ids)) != len(ids):
            raise ValueError("question ids repeat")
        return self

    @model_validator(mode="after")
    def _feelings_evidence_structure(self) -> ReflectionQuestions:
        order = [REFLECTION_KINDS.index(question.kind) for question in self.questions]
        if order != sorted(order) or set(order) != set(range(len(REFLECTION_KINDS))):
            raise ValueError("questions run feelings, evidence, structure, each at least once")
        return self

    @model_validator(mode="after")
    def _no_exclamation(self) -> ReflectionQuestions:
        for question in self.questions:
            if "!" in question.prompt or "!" in (question.hint or ""):
                raise ValueError(f"a reflection question may not say {question.prompt!r}")
        return self


class StartingTask(BaseModel):
    """The Starting task content (Story 6.3): its items in order. The final played-before
    question is fixed product copy, not content."""

    model_config = _FROZEN

    items: Annotated[tuple[StartingTaskItem, ...], Field(min_length=1, max_length=20)]

    @model_validator(mode="after")
    def _ids_unique(self) -> StartingTask:
        ids = [item.id for item in self.items]
        if len(set(ids)) != len(ids):
            raise ValueError("item ids repeat")
        return self
