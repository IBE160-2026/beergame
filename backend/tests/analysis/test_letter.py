"""The Indicative letter (Story 12.6, FR-56, AD-1): `analysis.indicative_letter`, golden cases at
every bound, and the rule a set of bounds must meet."""

import pytest
from pydantic import ValidationError

from app.analysis.letter import indicative_letter, judge_thresholds, parse_thresholds
from app.platform.config import Settings

BOUNDS = {"A": 90, "B": 80, "C": 60, "D": 50, "E": 40}


@pytest.mark.parametrize(
    ("total", "letter"),
    [
        (100, "A"),
        (90, "A"),
        (89.99, "B"),
        (80, "B"),
        (79.99, "C"),
        (60, "C"),
        (59.99, "D"),
        (50, "D"),
        (49.99, "E"),
        (40, "E"),
        (39.99, "F"),
        (0, "F"),
    ],
)
def test_each_bound_belongs_to_its_letter(total, letter):
    assert indicative_letter(total, BOUNDS) == letter


def test_the_bounds_are_percent_of_the_maximum():
    # 45 of 50 points is 90 %: an A; 44.99 is just under.
    assert indicative_letter(45, BOUNDS, out_of=50) == "A"
    assert indicative_letter(44.99, BOUNDS, out_of=50) == "B"
    # 2 of 3 points is 66.67 %: a C, exactly, with no float rounding at a bound.
    assert indicative_letter(2, {"A": 90, "B": 80, "C": 66, "D": 50, "E": 40}, out_of=3) == "C"
    assert indicative_letter(19.8, BOUNDS, out_of=22) == "A"  # 90 % exactly


def test_other_bounds_move_the_letters():
    tight = {"A": 99, "B": 98, "C": 97, "D": 96, "E": 1}
    assert indicative_letter(98.5, tight) == "B"
    assert indicative_letter(1, tight) == "E"
    assert indicative_letter(0.99, tight) == "F"


@pytest.mark.parametrize(
    ("bounds", "reason"),
    [
        (BOUNDS, None),
        ({"A": 100, "B": 4, "C": 3, "D": 2, "E": 1}, None),
        ({"A": 90, "B": 90, "C": 60, "D": 50, "E": 40}, "out_of_order"),
        ({"A": 80, "B": 90, "C": 60, "D": 50, "E": 40}, "out_of_order"),
        ({"A": 101, "B": 80, "C": 60, "D": 50, "E": 40}, "out_of_range"),
        ({"A": 90, "B": 80, "C": 60, "D": 50, "E": 0}, "out_of_range"),
        ({"A": 90, "B": 80, "C": 60, "D": 50}, "out_of_range"),
        ({"A": 90, "B": 80, "C": 60, "D": 50, "E": 40, "F": 0}, "out_of_range"),
        ({"A": 90.5, "B": 80, "C": 60, "D": 50, "E": 40}, "out_of_range"),
        ({"A": True, "B": 80, "C": 60, "D": 50, "E": 40}, "out_of_range"),
    ],
)
def test_the_bounds_must_be_whole_in_range_and_strictly_falling(bounds, reason):
    assert judge_thresholds(bounds) == reason


def test_refused_inputs_raise():
    with pytest.raises(ValueError):
        indicative_letter(50, {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5})
    with pytest.raises(ValueError):
        indicative_letter(101, BOUNDS)
    with pytest.raises(ValueError):
        indicative_letter(-1, BOUNDS)
    with pytest.raises(ValueError):
        indicative_letter(1, BOUNDS, out_of=0)


def test_the_configuration_form_parses():
    assert parse_thresholds(" 90, 80,60,50 ,40") == BOUNDS
    for bad in (
        "90,80,60,50",
        "90,80,60,50,40,30",
        "a,b,c,d,e",
        "40,50,60,80,90",
        "+90,80,60,50,40",
        "9_0,80,60,50,40",
        "٩٠,80,60,50,40",
    ):
        with pytest.raises(ValueError):
            parse_thresholds(bad)


def test_the_configuration_refuses_bad_bounds_at_load():
    with pytest.raises(ValidationError, match="indicative_letter_thresholds"):
        Settings(indicative_letter_thresholds="40,50,60,80,90")
    assert Settings(indicative_letter_thresholds="95,85,75,65,55").indicative_letter_thresholds


def test_a_total_just_under_a_bound_stays_under_it():
    assert indicative_letter(89.99996, BOUNDS) == "B"
    assert indicative_letter(89.999999999, BOUNDS) == "B"
    with pytest.raises(ValueError):
        indicative_letter(float("inf"), BOUNDS)
