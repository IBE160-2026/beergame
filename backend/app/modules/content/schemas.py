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
from app.analysis.scoring import ANSWER, Criterion, FlowCheck, InteractiveRule
from app.analysis.sentences import MomentTemplates, SentenceTemplates

__all__ = [
    "CRITERIA_MAX",
    "CRITERIA_MIN",
    "ColumnRow",
    "DebriefQuiz",
    "GUIDE_TEXT_MAX",
    "GivenColumn",
    "InteractiveSpec",
    "MomentTemplates",
    "NarrationTemplates",
    "REFLECTION_KINDS",
    "ITEM_TAGS",
    "ITEM_TYPES",
    "PatternSet",
    "QuestionSet",
    "QuestionSetItem",
    "ReflectionQuestion",
    "ReflectionQuestions",
    "SCALE_STEPS",
    "ScoringGuide",
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


ITEM_TYPES = ("choice", "table", "number", "long")
"""The Core item types of the Individual test (Story 11.1, FR-52): multiple choice, a table and a
number Interactive item, and a long answer. No diagram item in v1; a drawn graph (Story 11.14)
adds its type here."""

INTERACTIVE_TYPES = frozenset({"table", "number"})

_BEER = re.compile(r"\bøl\b", re.IGNORECASE)
"""Interactive items say «enheter», never «øl» (FR-80)."""


class GivenColumn(BaseModel):
    """A given column of an Interactive item: its name (what a criterion refers to), its heading
    and one whole number per row."""

    model_config = _FROZEN

    key: _Key
    label: _Text
    values: Annotated[
        tuple[Annotated[int, Field(strict=True, ge=-80_000, le=80_000)], ...],
        Field(min_length=1, max_length=36),
    ]


class InteractiveSpec(BaseModel):
    """What a table or number Interactive item shows and how it is scored (Story 11.5, FR-80):
    its prompt, an optional hint, the table's caption, the row labels (a table: one per Uke, a
    number item: its given rows), the given columns, the asked column's (a table) or row's (a
    number item) label, whether a value may be negative, and the coded criteria of its computed
    rule (`analysis.scoring`). A table item is answered by one value per row; a number item by one
    value, under exactly one given column."""

    model_config = _FROZEN

    prompt: _Text
    hint: _Text | None = None
    caption: _Text
    rows: Annotated[tuple[_Text, ...], Field(min_length=1, max_length=36)]
    given: Annotated[tuple[GivenColumn, ...], Field(max_length=4)] = ()
    asked: _Text
    negative: Annotated[bool, Field(strict=True)] = False
    criteria: Annotated[tuple[Criterion, ...], Field(min_length=1, max_length=8)]

    @model_validator(mode="after")
    def _columns_fit(self) -> InteractiveSpec:
        keys = [column.key for column in self.given]
        if len(set(keys)) != len(keys) or ANSWER in keys:
            raise ValueError(f"given column names repeat or use {ANSWER!r}")
        if any(len(column.values) != len(self.rows) for column in self.given):
            raise ValueError("a given column has one value per row")
        texts = [self.prompt, self.hint or "", self.caption, self.asked, *self.rows]
        texts += [column.label for column in self.given]
        for text in texts:
            if "!" in text or _BEER.search(text):
                raise ValueError(f"an Interactive item may not say {text!r}")
        return self

    def rule(self, item_type: str) -> InteractiveRule:
        """The computed rule for an item of `item_type`: a table's values are its rows, a number
        item's is its one asked value."""
        labels = self.rows if item_type == "table" else (self.asked,)
        return InteractiveRule(
            labels=labels,
            columns={column.key: column.values for column in self.given},
            criteria=self.criteria,
        )


ITEM_TAGS = ("quantity", "explanation-wording", "unseen-demand", "other-business")
"""The closed set of question tags (FR-52, FR-53, FR-80): an item that measures quantities, the one
item using the Explanation's wording, an unseen Demand pattern, and an Interactive item set in a
business other than the beer chain."""


class QuestionSetItem(BaseModel):
    """One Core item of the question set (Story 11.1): its type, its default Item weight in whole
    percent, its answer key (a choice item: the right option's id) or the id of the computed
    scoring rule or Scoring guide entry (every other type), and its tags. An item that is a
    Starting task item names it by id (`starting_task_item`) and takes its text from the Starting
    task record; nothing is copied (FR-52)."""

    model_config = _FROZEN

    id: _Key
    type: Literal["choice", "table", "number", "long"]
    title: _Text
    weight: Annotated[int, Field(strict=True, ge=0, le=100)]
    options: Annotated[tuple[_Key, ...], Field(max_length=8)] = ()
    answer_key: _Key | None = None
    scoring_rule: _Key | None = None
    tags: Annotated[
        tuple[Literal["quantity", "explanation-wording", "unseen-demand", "other-business"], ...],
        Field(max_length=4),
    ] = ()
    starting_task_item: _Key | None = None
    interactive: InteractiveSpec | None = None
    """A table item's or a non-Starting-task number item's table and rule (Story 11.5). Optional
    so version 1 still reads; the content load requires it (`interactive_missing`)."""

    @model_validator(mode="after")
    def _key_or_rule(self) -> QuestionSetItem:
        if self.type == "choice":
            if len(self.options) < 2 or self.answer_key not in self.options:
                raise ValueError(f"choice item {self.id!r} needs options and its answer among them")
            if self.scoring_rule is not None:
                raise ValueError(f"choice item {self.id!r} is scored by its answer key")
        elif self.scoring_rule is None or self.answer_key is not None or self.options:
            raise ValueError(f"{self.type} item {self.id!r} names a scoring rule and no answer key")
        if len(set(self.options)) != len(self.options):
            raise ValueError(f"item {self.id!r} repeats an option")
        if self.starting_task_item is not None and self.type != "number":
            raise ValueError(f"item {self.id!r} names a Starting task item, a number item")
        if len(set(self.tags)) != len(self.tags):
            raise ValueError(f"item {self.id!r} repeats a tag")
        if "!" in self.title:
            raise ValueError(f"an item may not say {self.title!r}")
        if self.interactive is not None:
            if self.type not in INTERACTIVE_TYPES or self.starting_task_item is not None:
                raise ValueError(f"item {self.id!r} is no Interactive item with its own table")
            if self.type == "number" and len(self.interactive.given) != 1:
                raise ValueError(f"number item {self.id!r} has one given column")
            flows = [c for c in self.interactive.criteria if isinstance(c.check, FlowCheck)]
            if self.type == "number" and flows:
                raise ValueError(f"number item {self.id!r} has no flow criterion")
            try:
                self.interactive.rule(self.type)
            except ValueError as invalid:
                raise ValueError(f"item {self.id!r}: {invalid}") from invalid
        return self

    def needs_interactive(self) -> bool:
        """Whether the item is answered on its own table (Story 11.5): a table item, or a number
        item that is not a Starting task item."""
        return self.type in INTERACTIVE_TYPES and self.starting_task_item is None


class QuestionSet(BaseModel):
    """The Individual test's question set (Story 11.1, FR-52, FR-53, FR-80, AD-23): its Core items
    with default weights, the default total weight of the Adapted items, and the replacement Core
    items a Student with fewer than 10 own Orders gets in their place, whose weights add up to that
    total. `draft` until the founder approves the real questions (issue #16); in production a Class
    session cannot lock on a draft (`tests.selection`). The rule that every Starting task item is
    referenced needs the stored Starting task: `content.service.publish` checks it.

    The replacement items' weights are given at the default Adapted total; when a Class session
    sets another total, the reader that serves them (Story 11.7) scales them to it, so they always
    carry the session's Adapted total (FR-53)."""

    model_config = _FROZEN

    status: Literal["draft", "approved"]
    adapted_weight: Annotated[int, Field(strict=True, ge=0, le=100)]
    items: Annotated[tuple[QuestionSetItem, ...], Field(min_length=1, max_length=60)]
    replacements: Annotated[tuple[QuestionSetItem, ...], Field(min_length=1, max_length=20)]

    @model_validator(mode="after")
    def _ids_unique(self) -> QuestionSet:
        ids = [item.id for item in (*self.items, *self.replacements)]
        if len(set(ids)) != len(ids):
            raise ValueError("item ids repeat")
        refs = [item.starting_task_item for item in self.items if item.starting_task_item]
        if len(set(refs)) != len(refs):
            raise ValueError("a Starting task item is referenced twice")
        if any(item.starting_task_item for item in self.replacements):
            raise ValueError("a replacement item may not be a Starting task item")
        return self

    @model_validator(mode="after")
    def _the_set_is_complete(self) -> QuestionSet:
        """What every set must hold (FR-52, FR-53, FR-80)."""

        def tagged(tag: str) -> list[QuestionSetItem]:
            return [item for item in self.items if tag in item.tags]

        if len(tagged("explanation-wording")) != 1:
            raise ValueError("exactly one item uses the Explanation's wording")
        if not tagged("unseen-demand"):
            raise ValueError("one item has an unseen Demand pattern")
        if not tagged("quantity"):
            raise ValueError("at least one item measures quantities")
        other = tagged("other-business")
        if not 2 <= len(other) <= 3 or any(i.type not in INTERACTIVE_TYPES for i in other):
            raise ValueError("two or three Interactive items are set in another business")
        if sum(item.weight for item in self.items) + self.adapted_weight != 100:
            raise ValueError("the default weights and the Adapted total weight sum to 100")
        if sum(item.weight for item in self.replacements) != self.adapted_weight:
            raise ValueError("the replacement items carry the Adapted total weight")
        return self


CRITERIA_MIN, CRITERIA_MAX = 5, 8
"""How many coded criteria each question of the Scoring guide has (FR-81)."""

SCALE_STEPS = 5
"""The one fixed scale of the Scoring guide, shared by every question: steps 0 to 4 (FR-81)."""

_Code = Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9]{0,9}$")]
GUIDE_TEXT_MAX = 4000
"""The longest guide text of one Scoring guide question (Story 11.2)."""

_GuideText = Annotated[str, Field(min_length=1, max_length=GUIDE_TEXT_MAX)]


class ScaleStep(BaseModel):
    """One step of the Scoring guide's five-step scale: its number and what it means."""

    model_config = _FROZEN

    step: Annotated[int, Field(strict=True, ge=0, le=SCALE_STEPS - 1)]
    label: _Text


class GuideCriterion(BaseModel):
    """One coded criterion of a question (FR-81): its code, what it looks for and its weight in
    whole percent of the question."""

    model_config = _FROZEN

    code: _Code
    text: _Text
    weight: Annotated[int, Field(strict=True, ge=1, le=100)]


class GuideQuestion(BaseModel):
    """The Scoring guide of one long-answer question (`long`, its id the item's `scoring_rule`) or
    one Adapted item template (`adapted`, Story 11.7): its title, the descriptive guide text a
    Lecturer may edit (what is asked for, what strong and weak answers look like) and its 5 to 8
    coded criteria, whose weights sum to 100. The criteria are never edited in v1."""

    model_config = _FROZEN

    id: _Key
    kind: Literal["long", "adapted"]
    title: _Text
    guide: _GuideText
    criteria: Annotated[
        tuple[GuideCriterion, ...], Field(min_length=CRITERIA_MIN, max_length=CRITERIA_MAX)
    ]

    @model_validator(mode="after")
    def _criteria_coded(self) -> GuideQuestion:
        codes = [criterion.code for criterion in self.criteria]
        if len(set(codes)) != len(codes):
            raise ValueError(f"question {self.id!r} repeats a criterion code")
        if sum(criterion.weight for criterion in self.criteria) != 100:
            raise ValueError(f"the criteria of question {self.id!r} weigh 100 together")
        if not self.guide.strip():
            raise ValueError(f"question {self.id!r} has no guide text")
        if "\x00" in self.guide:  # a JSONB value cannot hold it
            raise ValueError(f"the guide text of question {self.id!r} holds a NUL character")
        return self


class ScoringGuide(BaseModel):
    """The Scoring guide (Story 11.2, FR-81, AD-23): one fixed five-step scale (0 to 4) shared by
    every question, and per long-answer question and Adapted item template its guide. `draft`
    until the founder approves the real text (issue #16). A default is published by the content
    load; a Lecturer's edit is a new version made for one Class session (`tests.guide`)."""

    model_config = _FROZEN

    status: Literal["draft", "approved"]
    scale: Annotated[tuple[ScaleStep, ...], Field(min_length=SCALE_STEPS, max_length=SCALE_STEPS)]
    questions: Annotated[tuple[GuideQuestion, ...], Field(min_length=1, max_length=40)]

    @model_validator(mode="after")
    def _fixed_scale_and_unique_ids(self) -> ScoringGuide:
        if [step.step for step in self.scale] != list(range(SCALE_STEPS)):
            raise ValueError("the scale has the steps 0 to 4 in order")
        ids = [question.id for question in self.questions]
        if len(set(ids)) != len(ids):
            raise ValueError("question ids repeat")
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
