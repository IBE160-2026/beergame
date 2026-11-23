"""How well the AI's scores agree with human scores of a Control test (Story 12.10, FR-82, AD-1,
AD-27).

`agreement(human_scores, ai_scores, words=...)` is the only source of the five FR-82 measures.
Every human score of an answer that has an AI step is one pair (an answer two scorers scored gives
two pairs); a human score of an answer without an AI step pairs with nothing. Over the pairs:

- `exact`: the share where the human and the AI chose the same step;
- `within_one`: the share where they are at most one step apart;
- `offset`: the mean of AI step minus human step; positive when the AI scores higher;
- `compression`: the spread of the AI steps over the spread of the human steps (population
  standard deviations of the paired steps); under 1 when the AI uses less of the scale, None when
  the human steps do not vary (no spread to compare with);
- `by_length`: `exact` and `within_one` again for short (under 50 words), medium (50 to 149) and
  long (150 or more) answers, by the answer's word count.

Shares and means are rounded to four decimals; with no pair each is None. A step off the
five-step scale raises `ValueError`.

Pure (AD-1)."""

import math
from collections.abc import Hashable, Iterable, Mapping
from dataclasses import dataclass
from fractions import Fraction

from app.analysis.total import SCALE_TOP

__all__ = ["LENGTH_BANDS", "Agreement", "LengthBand", "agreement"]

LENGTH_BANDS: tuple[tuple[str, int, int | None], ...] = (
    ("short", 0, 49),
    ("medium", 50, 149),
    ("long", 150, None),
)
"""The answer-length bands by word count: name, first and last word count (None: no upper end)."""


@dataclass(frozen=True)
class LengthBand:
    """The agreement over the pairs of one answer-length band."""

    band: str
    min_words: int
    max_words: int | None
    pairs: int
    exact: float | None
    within_one: float | None


@dataclass(frozen=True)
class Agreement:
    """The FR-82 measures over every pair of a human and an AI score of the same answer."""

    pairs: int
    exact: float | None
    within_one: float | None
    offset: float | None
    compression: float | None
    by_length: tuple[LengthBand, ...]


def _step(value: int, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= SCALE_TOP:
        raise ValueError(f"{what} {value!r} is off the five-step scale")
    return value


def _share(count: int, total: int) -> float | None:
    return None if total == 0 else round(float(Fraction(count, total)), 4)


def _variance(values: list[int]) -> Fraction:
    mean = Fraction(sum(values), len(values))
    return sum(((value - mean) ** 2 for value in values), Fraction(0)) / len(values)


def _band(words: int) -> str:
    for name, low, high in LENGTH_BANDS:
        if words >= low and (high is None or words <= high):
            return name
    raise ValueError(f"word count {words!r} is negative")  # pragma: no cover - checked below


def agreement(
    human_scores: Iterable[tuple[Hashable, int]],
    ai_scores: Mapping[Hashable, int],
    *,
    words: Mapping[Hashable, int],
) -> Agreement:
    """The measures over the pairs of `human_scores` (answer, step) with the AI's step of the same
    answer in `ai_scores`; `words` holds each paired answer's word count (a paired answer missing
    from it raises `KeyError`)."""
    pairs: list[tuple[int, int, str]] = []
    for answer, human in human_scores:
        _step(human, "human score")
        if answer not in ai_scores:
            continue
        ai = _step(ai_scores[answer], "AI score")
        count = words[answer]
        if count < 0:
            raise ValueError(f"word count {count!r} is negative")
        pairs.append((human, ai, _band(count)))
    total = len(pairs)
    exact = sum(1 for h, a, _ in pairs if h == a)
    within = sum(1 for h, a, _ in pairs if abs(h - a) <= 1)
    offset = (
        None if total == 0 else round(float(Fraction(sum(a - h for h, a, _ in pairs), total)), 4)
    )
    compression: float | None = None
    if total:
        spread = _variance([h for h, _, _ in pairs])
        if spread != 0:
            compression = round(math.sqrt(_variance([a for _, a, _ in pairs]) / spread), 4)
    bands = []
    for name, low, high in LENGTH_BANDS:
        inside = [(h, a) for h, a, band in pairs if band == name]
        bands.append(
            LengthBand(
                band=name,
                min_words=low,
                max_words=high,
                pairs=len(inside),
                exact=_share(sum(1 for h, a in inside if h == a), len(inside)),
                within_one=_share(sum(1 for h, a in inside if abs(h - a) <= 1), len(inside)),
            )
        )
    return Agreement(
        pairs=total,
        exact=_share(exact, total),
        within_one=_share(within, total),
        offset=offset,
        compression=compression,
        by_length=tuple(bands),
    )
