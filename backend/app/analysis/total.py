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

Pure (AD-1)."""

from collections.abc import Mapping
from fractions import Fraction

__all__ = ["SCALE_TOP", "total_score"]

SCALE_TOP = 4
"""The top step of the Scoring guide's five-step scale (0 to 4)."""


def total_score(
    computed: Mapping[str, float],
    ai_items: Mapping[str, int],
    weights: Mapping[str, int],
) -> float | None:
    """The weighted total in points of the weights' sum (100 for a saved selection), to two
    decimals; None when an item of `weights` has neither a computed credit nor an AI step.
    Shares outside `weights` are ignored."""
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
    return round(float(total), 2)
