"""The weighted total of an Individual test (Story 12.2, FR-54, AD-1, AD-9).

`total_score(computed, ai_items, weights)` is the only place a total is made: the Student's
«KI-vurdering» and every later reader (the Indicative letter, staff views) call it with the Item
weights the attempt froze. Each item adds its weight times its share:

- a computed item (answer key, Starting task or Interactive item): its credit, 0 to 1, as `tests`
  stored it (an item with no saved answer has credit 0);
- a long-answer or Adapted item: its overall step on the Scoring guide's five-step scale over 4.

The weights are the frozen ones: an item the Lecturer took out is not among them and counts for
nothing, and the Adapted items carry the session's Adapted total between them. There is no partial
total: when an item of `weights` has no share the answer is None.

Story 14.2 (FR-64, AD-1): `core_total_score` is the Core-only subscore of the Klasserapport: the
same weighting over the Core items only, with the Adapted items (and the replacement items that
stand in for them) left out and the remaining weights rescaled to 100, so Students whose Adapted
items differ compare on the same questions.

Pure (AD-1)."""

from collections.abc import Collection, Mapping
from fractions import Fraction

__all__ = ["SCALE_TOP", "core_total_score", "total_score"]

SCALE_TOP = 4
"""The top step of the Scoring guide's five-step scale (0 to 4)."""


def _points(
    computed: Mapping[str, float],
    ai_items: Mapping[str, int],
    weights: Mapping[str, int],
) -> Fraction | None:
    """The exact weighted sum of `weights`' items; None when one has neither share."""
    total = Fraction(0)
    for item_id, weight in weights.items():
        if item_id in ai_items:
            step = ai_items[item_id]
            if not 0 <= step <= SCALE_TOP:
                raise ValueError(f"step {step} of {item_id!r} is off the scale")
            share = Fraction(step, SCALE_TOP)
        elif item_id in computed:
            credit = Fraction(computed[item_id]).limit_denominator(10_000)
            if not 0 <= credit <= 1:
                raise ValueError(f"credit of {item_id!r} is outside 0 to 1")
            share = credit
        else:
            return None
        total += weight * share
    return total


def total_score(
    computed: Mapping[str, float],
    ai_items: Mapping[str, int],
    weights: Mapping[str, int],
) -> float | None:
    """The weighted total in points of the weights' sum (100 for a saved selection), to two
    decimals; None when an item of `weights` has neither a computed credit nor an AI step.
    Shares outside `weights` are ignored."""
    total = _points(computed, ai_items, weights)
    return None if total is None else round(float(total), 2)


def core_total_score(
    computed: Mapping[str, float],
    ai_items: Mapping[str, int],
    weights: Mapping[str, int],
    core: Collection[str],
) -> float | None:
    """The Core-only subscore (Story 14.2) in points of 100, to two decimals: `total_score` over
    the items of `weights` that `core` names, their weights rescaled to sum to 100. None when no
    Core item carries weight, or when a Core item has neither share; a share of an item outside
    `core` (an Adapted or replacement item) never counts."""
    kept = {item_id: weight for item_id, weight in weights.items() if item_id in core}
    whole = sum(kept.values())
    if whole <= 0:
        return None
    total = _points(computed, ai_items, kept)
    return None if total is None else round(float(total * 100 / whole), 2)
