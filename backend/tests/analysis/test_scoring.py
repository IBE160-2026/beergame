"""`analysis.scoring.score_sum` (Story 6.3, FR-85, AD-1): the Starting task's computed rule."""

import pytest

from app.analysis.scoring import SumScore, score_sum

POSITION = [(1, 0), (-1, 13), (1, 16)]  # Lager 0 − Restordre 13 + På vei 16


def test_a_right_and_a_wrong_answer_to_the_position():
    assert score_sum(POSITION, 3) == SumScore(expected=3, correct=True)
    assert score_sum(POSITION, 29) == SumScore(expected=3, correct=False)


def test_a_negative_sum_and_a_bad_sign():
    assert score_sum([(1, 0), (-1, 13)], -13).correct
    with pytest.raises(ValueError):
        score_sum([(2, 1)], 2)
