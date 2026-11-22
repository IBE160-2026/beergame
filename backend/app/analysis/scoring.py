"""Computed scoring rules for answers (FR-85, FR-52, AD-1, AD-9).

Pure: no I/O, no clock, no LLM. Story 6.3 adds the Starting task's rule, `score_sum`; Epic 11
extends this file (multiple choice, Interactive items) and never writes a second copy."""

from collections.abc import Iterable
from dataclasses import dataclass


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
