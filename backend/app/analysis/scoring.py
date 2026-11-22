"""Computed scoring rules for answers (FR-85, FR-52, FR-80, AD-1, AD-9).

Pure: no I/O, no clock, no LLM (stdlib and pydantic only). Story 6.3 adds the Starting task's
rule, `score_sum`; Epic 11 extends this file (multiple choice, Interactive items) and never writes
a second copy. The Interactive rule's shape (`InteractiveRule`) lives here, as the Detected
patterns' does in `analysis.patterns`: `modules/content` validates the question set against it."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


@dataclass(frozen=True)
class SumScore:
    """The scored answer to a sum item: the right answer and whether `answer` equals it."""

    expected: int
    correct: bool


def score_sum(terms: Iterable[tuple[int, int]], answer: int) -> SumScore:
    """Score `answer` against the signed sum of `terms`, each `(sign, value)` with sign ±1:
    «Posisjon» is `(+1, Lager), (−1, Restordre), (+1, På vei)`."""
    expected = 0
    for sign, value in terms:
        if sign not in (1, -1):
            raise ValueError("a sign is +1 or -1")
        expected += sign * value
    return SumScore(expected=expected, correct=answer == expected)


@dataclass(frozen=True)
class ChoiceScore:
    """The scored answer to a multiple-choice item (Story 11.4, FR-52): whether it was answered,
    whether the chosen option is the answer key, and the credit as a share of the item's weight
    (1.0 or 0.0; partial credit is for Interactive items)."""

    answered: bool
    correct: bool
    credit: float


def score_choice(answer: str | None, key: str) -> ChoiceScore:
    """Score the chosen option id `answer` (None: not answered) against the item's answer key."""
    if answer is None:
        return ChoiceScore(answered=False, correct=False, credit=0.0)
    correct = answer == key
    return ChoiceScore(answered=True, correct=correct, credit=1.0 if correct else 0.0)


# Interactive items (Story 11.5, FR-80): table and number answers, scored per coded criterion.

ANSWER = "answer"
"""In a `balance` check, the Student's own values (every other name is a given column)."""

INTERACTIVE_LIMIT = 1_000_000
"""The largest value, either way, a cell or a number answer takes (the api's limit)."""

_RULE = ConfigDict(frozen=True, extra="forbid")
_Name = Annotated[str, Field(pattern=r"^[a-z][a-z0-9-]{0,39}$")]
_Value = Annotated[int, Field(strict=True, ge=-INTERACTIVE_LIMIT, le=INTERACTIVE_LIMIT)]
_Label = Annotated[str, Field(min_length=1, max_length=500)]


class CellCheck(BaseModel):
    """A quantity: the answer in row `row` (from 0) is `value`."""

    model_config = _RULE

    kind: Literal["cell"]
    row: Annotated[int, Field(strict=True, ge=0, le=35)]
    value: _Value


class BalanceCheck(BaseModel):
    """Units added equal units missing: the sum of `added` equals the sum of `missing`, one side
    the Student's values (`answer`), the other a given column."""

    model_config = _RULE

    kind: Literal["balance"]
    added: _Name
    missing: _Name


class FlowCheck(BaseModel):
    """The stock agrees with its flows: in every row the answer is the row above's answer (the
    first row: `start`) plus `inflow` minus `outflow`. Each row is checked against the Student's
    own row above, so one slip fails this criterion once and is not carried as a wrong level."""

    model_config = _RULE

    kind: Literal["flow"]
    inflow: _Name
    outflow: _Name
    start: _Value


class Criterion(BaseModel):
    """One coded criterion of an Interactive item: its code, its weight in whole percent of the
    item and its check. None looks at the shape of the answer's curve (no oscillation rule)."""

    model_config = _RULE

    code: Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9]{0,9}$")]
    weight: Annotated[int, Field(strict=True, ge=1, le=100)]
    check: Annotated[CellCheck | BalanceCheck | FlowCheck, Field(discriminator="kind")]


class InteractiveRule(BaseModel):
    """The computed rule of one Interactive item: the label of each answer value (a table: one per
    Uke; a number item: its one asked label), the given columns by name, and the criteria, whose
    weights sum to 100."""

    model_config = _RULE

    labels: Annotated[tuple[_Label, ...], Field(min_length=1, max_length=36)]
    columns: dict[_Name, tuple[_Value, ...]] = {}
    criteria: Annotated[tuple[Criterion, ...], Field(min_length=1, max_length=8)]

    @model_validator(mode="after")
    def _consistent(self) -> InteractiveRule:
        codes = [criterion.code for criterion in self.criteria]
        if len(set(codes)) != len(codes):
            raise ValueError("criterion codes repeat")
        if sum(criterion.weight for criterion in self.criteria) != 100:
            raise ValueError("the criteria weigh 100 together")
        if ANSWER in self.columns:
            raise ValueError(f"a given column may not be named {ANSWER!r}")
        names = {ANSWER, *self.columns}
        for criterion in self.criteria:
            check = criterion.check
            if isinstance(check, CellCheck) and check.row >= len(self.labels):
                raise ValueError(f"criterion {criterion.code} names a row past the answer")
            if isinstance(check, BalanceCheck):
                if not {check.added, check.missing} <= names:
                    raise ValueError(f"criterion {criterion.code} names an unknown column")
                # A balance of given columns alone would score every answer the same.
                if (check.added == ANSWER) == (check.missing == ANSWER):
                    raise ValueError(f"criterion {criterion.code} weighs the answer on one side")
            if isinstance(check, FlowCheck):
                flows = (check.inflow, check.outflow)
                if any(name not in self.columns for name in flows):
                    raise ValueError(f"criterion {criterion.code} names an unknown column")
                if any(len(self.columns[name]) != len(self.labels) for name in flows):
                    raise ValueError(f"criterion {criterion.code}: a flow has one value per row")
        return self


@dataclass(frozen=True)
class CriterionScore:
    """One criterion scored: met or not, and the computed reason in words (for the assessment, not
    the Student)."""

    code: str
    weight: int
    met: bool
    explanation: str


@dataclass(frozen=True)
class InteractiveScore:
    """A scored Interactive answer (FR-80): whether any value was given, the credit as a share of
    the item's weight (the met criteria's weights over 100) and each criterion."""

    answered: bool
    credit: float
    criteria: tuple[CriterionScore, ...]


def _n(value: int) -> str:
    return f"−{-value}" if value < 0 else str(value)


def _unanswered(labels: Sequence[str], values: Sequence[int | None]) -> str | None:
    return next(
        (f"{label} er ikke besvart." for label, v in zip(labels, values, strict=True) if v is None),
        None,
    )


def _cell(
    check: CellCheck, labels: Sequence[str], values: Sequence[int | None]
) -> tuple[bool, str]:
    label, value = labels[check.row], values[check.row]
    if value is None:
        return False, f"{label} er ikke besvart."
    if value == check.value:
        return True, f"{label}: {_n(value)}, som regelen gir."
    return False, f"{label}: {_n(value)}, regelen gir {_n(check.value)}."


def _balance(
    check: BalanceCheck, rule: InteractiveRule, values: Sequence[int | None]
) -> tuple[bool, str]:
    missing = _unanswered(rule.labels, values)
    if missing:
        return False, missing

    def total(name: str) -> int:
        if name == ANSWER:
            return sum(v for v in values if v is not None)
        return sum(rule.columns[name])

    added, short = total(check.added), total(check.missing)
    if added == short:
        return True, f"Lagt til {_n(added)} enheter, mangler {_n(short)} enheter: like mange."
    return False, f"Lagt til {_n(added)} enheter, mangler {_n(short)} enheter: ikke like mange."


def _flow(
    check: FlowCheck, rule: InteractiveRule, values: Sequence[int | None]
) -> tuple[bool, str]:
    missing = _unanswered(rule.labels, values)
    if missing:
        return False, missing
    before = check.start
    for row, label in enumerate(rule.labels):
        value = values[row]
        assert value is not None
        inflow, outflow = rule.columns[check.inflow][row], rule.columns[check.outflow][row]
        expected = before + inflow - outflow
        if value != expected:
            return False, (
                f"{label}: {_n(before)} + {_n(inflow)} − {_n(outflow)} = {_n(expected)}, "
                f"svaret er {_n(value)}."
            )
        before = value
    return True, "Hver rad stemmer med raden over, pluss inn og minus ut."


def score_interactive(values: Sequence[int | None], rule: InteractiveRule) -> InteractiveScore:
    """Score an Interactive answer (Story 11.5, FR-80, AD-1): `values` has one entry per label of
    `rule` (None: not answered). Partial credit per coded criterion, each met or not, with the
    computed explanation; a criterion that needs an unanswered value is not met. The score reads
    the values only, never how they were entered or the shape of their curve."""
    if len(values) != len(rule.labels):
        raise ValueError("one value per label of the rule")
    scored: list[CriterionScore] = []
    for criterion in rule.criteria:
        check = criterion.check
        if isinstance(check, CellCheck):
            met, why = _cell(check, rule.labels, values)
        elif isinstance(check, BalanceCheck):
            met, why = _balance(check, rule, values)
        else:
            met, why = _flow(check, rule, values)
        scored.append(CriterionScore(criterion.code, criterion.weight, met, why))
    credit = sum(c.weight for c in scored if c.met) / 100
    return InteractiveScore(
        answered=any(v is not None for v in values), credit=credit, criteria=tuple(scored)
    )
