"""The Indicative letter of an AI assessment's total (Story 12.6, FR-56, AD-1).

`indicative_letter(total, thresholds)` is the only place a letter is made. `thresholds` holds a
lower bound for each letter A to E in whole percent of the total's maximum, strictly falling; F
has the bound 0, so every total gets a letter. A total exactly on a bound gets that bound's
letter. The bounds are a Lecturer setting with placeholder defaults from configuration
(`indicative_letter_thresholds`); `judge_thresholds` is the rule a stored set must meet.

The letter is an AI-generated indication, never a grade: it is no input to Completion or any
requirement (C-2). Pure (AD-1)."""

import re
from collections.abc import Mapping, Sequence
from fractions import Fraction
from typing import Literal

__all__ = [
    "BOUNDED",
    "LETTERS",
    "Letter",
    "indicative_letter",
    "judge_thresholds",
    "parse_thresholds",
]

Letter = Literal["A", "B", "C", "D", "E", "F"]

LETTERS: tuple[Letter, ...] = ("A", "B", "C", "D", "E", "F")
"""Best first. F is what is left under E's bound."""

BOUNDED: tuple[Letter, ...] = LETTERS[:-1]
"""The letters with a bound a Lecturer sets (A to E); F's bound is always 0."""


def judge_thresholds(thresholds: Mapping[str, object]) -> str | None:
    """None when `thresholds` holds exactly A to E, each a whole number from 1 to 100, strictly
    falling from A to E; else the reason: `out_of_range` (a missing, extra, non-integer or out of
    range bound) or `out_of_order`."""
    if set(thresholds) != set(BOUNDED):
        return "out_of_range"
    bounds = [thresholds[letter] for letter in BOUNDED]
    for bound in bounds:
        if isinstance(bound, bool) or not isinstance(bound, int) or not 1 <= bound <= 100:
            return "out_of_range"
    if any(higher <= lower for higher, lower in zip(bounds, bounds[1:], strict=False)):  # type: ignore[operator]
        return "out_of_order"
    return None


_WHOLE = re.compile(r"[0-9]{1,3}")
"""A bound as the configuration writes it: ASCII digits only (no sign, `_` or other digits)."""


def parse_thresholds(text: str) -> dict[str, int]:
    """`"90,80,60,50,40"` as the bounds of A to E (the configuration's form). Raises ValueError
    when the text does not give five bounds `judge_thresholds` accepts."""
    parts: Sequence[str] = [part.strip() for part in text.split(",")]
    if len(parts) != len(BOUNDED) or not all(_WHOLE.fullmatch(part) for part in parts):
        raise ValueError("five whole bounds, A to E")
    thresholds = {letter: int(part) for letter, part in zip(BOUNDED, parts, strict=True)}
    reason = judge_thresholds(thresholds)
    if reason is not None:
        raise ValueError(reason)
    return thresholds


def indicative_letter(total: float, thresholds: Mapping[str, int], out_of: int = 100) -> Letter:
    """The letter of `total` points out of `out_of`: the best letter whose bound (percent of
    `out_of`) the total reaches, else F. Raises ValueError for bounds `judge_thresholds` refuses,
    a non-positive `out_of` or a total outside 0 to `out_of`."""
    reason = judge_thresholds(thresholds)
    if reason is not None:
        raise ValueError(reason)
    if out_of <= 0:
        raise ValueError("out_of must be positive")
    # The total as written in decimal (`str` of a float is its shortest exact round trip), so a
    # total just under a bound never rounds up onto it; a non-finite total raises ValueError.
    points = Fraction(str(total))
    if not 0 <= points <= out_of:
        raise ValueError("total is outside 0 to out_of")
    for letter in BOUNDED:
        # Exact: total / out_of >= bound / 100, with no float rounding at a bound.
        if points * 100 >= thresholds[letter] * out_of:
            return letter
    return "F"
