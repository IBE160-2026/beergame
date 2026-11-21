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
