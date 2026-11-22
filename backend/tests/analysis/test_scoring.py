"""`analysis.scoring` (AD-1): the Starting task's `score_sum` (Story 6.3, FR-85) and the Individual
test's `score_choice` (Story 11.4, FR-52)."""

import pytest

from app.analysis.scoring import ChoiceScore, SumScore, score_choice, score_sum

POSITION = [(1, 0), (-1, 13), (1, 16)]  # Lager 0 − Restordre 13 + På vei 16


def test_a_right_and_a_wrong_answer_to_the_position():
    assert score_sum(POSITION, 3) == SumScore(expected=3, correct=True)
    assert score_sum(POSITION, 29) == SumScore(expected=3, correct=False)


def test_a_negative_sum_and_a_bad_sign():
    assert score_sum([(1, 0), (-1, 13)], -13).correct
    with pytest.raises(ValueError):
        score_sum([(2, 1)], 2)


def test_a_right_a_wrong_and_an_unanswered_choice():
    assert score_choice("b", "b") == ChoiceScore(answered=True, correct=True, credit=1.0)
    assert score_choice("c", "b") == ChoiceScore(answered=True, correct=False, credit=0.0)
    assert score_choice(None, "b") == ChoiceScore(answered=False, correct=False, credit=0.0)
