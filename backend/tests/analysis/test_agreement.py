"""`analysis.agreement` (Story 12.10, FR-82, AD-1, AD-27): golden cases worked by hand."""

import pytest

from app.analysis.agreement import agreement


def _words(*answers: str, count: int = 10) -> dict[str, int]:
    return dict.fromkeys(answers, count)


def test_a_constant_offset_agrees_within_one_step_but_never_exactly():
    """Human 0, 1, 2, 3 and AI 1, 2, 3, 4: every difference is +1. Exact 0/4, within one 4/4,
    offset (1+1+1+1)/4 = 1, and both spreads are the same (SD of 0..3 = SD of 1..4), so 1."""
    human = [("a", 0), ("b", 1), ("c", 2), ("d", 3)]
    ai = {"a": 1, "b": 2, "c": 3, "d": 4}
    found = agreement(human, ai, words=_words("a", "b", "c", "d"))
    assert found.pairs == 4
    assert found.exact == 0.0
    assert found.within_one == 1.0
    assert found.offset == 1.0
    assert found.compression == 1.0


def test_a_compressed_scale_shows_as_a_spread_under_one():
    """Human 0..4 and AI 1, 2, 2, 2, 3. Exact: only c (2 = 2), 1/5 = 0.2. Within one: every
    difference is −1, +1, 0, −1 or −1, so 5/5. Offset (1+1+0−1−1)/5 = 0. Human variance: mean 2,
    (4+1+0+1+4)/5 = 2. AI variance: mean 2, (1+0+0+0+1)/5 = 0.4. Compression √(0.4/2) = √0.2 =
    0.44721… → 0.4472."""
    human = [("a", 0), ("b", 1), ("c", 2), ("d", 3), ("e", 4)]
    ai = {"a": 1, "b": 2, "c": 2, "d": 2, "e": 3}
    found = agreement(human, ai, words=_words(*"abcde"))
    assert found.exact == 0.2
    assert found.within_one == 1.0
    assert found.offset == 0.0
    assert found.compression == 0.4472


def test_flat_human_steps_have_no_compression_to_compare():
    """Human 2 and 2 (no spread), AI 1 and 3: exact 0, within one 1, offset (−1+1)/2 = 0, and
    compression None (division by a zero spread)."""
    found = agreement([("a", 2), ("b", 2)], {"a": 1, "b": 3}, words=_words("a", "b"))
    assert (found.exact, found.within_one, found.offset, found.compression) == (0.0, 1.0, 0.0, None)


def test_two_scorers_on_one_answer_are_two_pairs_and_an_answer_without_ai_pairs_with_nothing():
    """Scorers 1 and 2 give answer a steps 3 and 1, the AI 3: pairs (3,3) and (1,3). Answer b has
    a human 4 but no AI step: left out. Exact 1/2, within one 1/2 (|1−3| = 2), offset (0+2)/2 = 1.
    Human variance: mean 2, (1+1)/2 = 1; AI variance 0: compression 0."""
    human = [("a", 3), ("a", 1), ("b", 4)]
    found = agreement(human, {"a": 3}, words=_words("a"))
    assert found.pairs == 2
    assert (found.exact, found.within_one, found.offset, found.compression) == (0.5, 0.5, 1.0, 0.0)


def test_agreement_by_answer_length_splits_at_50_and_150_words():
    """s (49 words): human 2, AI 2, exact. m1 (50 words): human 0, AI 2, apart by 2. m2 (149):
    human 3, AI 4, within one. l (150): human 1, AI 1, exact.
    short: 1 pair, exact 1, within 1; medium: 2 pairs, exact 0/2, within one 1/2; long: 1 pair,
    exact 1, within 1. Overall exact 2/4, within one 3/4, offset (0+2+1+0)/4 = 0.75. Shares of a
    third round to four decimals."""
    human = [("s", 2), ("m1", 0), ("m2", 3), ("l", 1)]
    ai = {"s": 2, "m1": 2, "m2": 4, "l": 1}
    found = agreement(human, ai, words={"s": 49, "m1": 50, "m2": 149, "l": 150})
    assert (found.exact, found.within_one, found.offset) == (0.5, 0.75, 0.75)
    short, medium, long = found.by_length
    assert (short.band, short.min_words, short.max_words) == ("short", 0, 49)
    assert (short.pairs, short.exact, short.within_one) == (1, 1.0, 1.0)
    assert (medium.band, medium.min_words, medium.max_words) == ("medium", 50, 149)
    assert (medium.pairs, medium.exact, medium.within_one) == (2, 0.0, 0.5)
    assert (long.band, long.min_words, long.max_words) == ("long", 150, None)
    assert (long.pairs, long.exact, long.within_one) == (1, 1.0, 1.0)
    thirds = agreement(
        [("a", 0), ("b", 1), ("c", 4)], {"a": 0, "b": 3, "c": 0}, words=_words("a", "b", "c")
    )
    assert thirds.exact == 0.3333  # 1/3
    assert thirds.offset == -0.6667  # (0 + 2 − 4)/3


def test_no_pairs_give_no_measures():
    found = agreement([("a", 2)], {}, words={})
    assert found.pairs == 0
    assert (found.exact, found.within_one, found.offset, found.compression) == (None,) * 4
    assert all(band.pairs == 0 and band.exact is None for band in found.by_length)


@pytest.mark.parametrize(
    ("human", "ai"),
    [([("a", 5)], {"a": 1}), ([("a", -1)], {"a": 1}), ([("a", 1)], {"a": 7})],
)
def test_a_step_off_the_scale_is_refused(human, ai):
    with pytest.raises(ValueError, match="off the five-step scale"):
        agreement(human, ai, words={"a": 1})
