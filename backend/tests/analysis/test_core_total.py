"""Golden cases for `analysis.core_total_score` (Story 14.2, FR-64, AD-1): the Core-only subscore of
the Klasserapport, the same weighting as `total_score` over the Core items only, Adapted and
replacement items left out and the remaining Item weights rescaled to 100."""

import pytest

from app.analysis.total import core_total_score, total_score
from tests.analysis.test_total_score import COMPUTED, WEIGHTS

ADAPTED = ("tilpasset-eget-spill", "tilpasset-replay")
CORE = [item for item in WEIGHTS if item not in ADAPTED]
AI = {"langsvar-forsinkelse": 3, "langsvar-informasjon": 2, "tilpasset-eget-spill": 4}


def test_the_core_items_are_weighted_as_in_the_total_and_rescaled_to_100():
    ai = AI | {"tilpasset-replay": 1}
    # Core points: 3 + 0 + 4 + 5 + 0 + 6 + 3.5 + computed tall + 7.5 + 5, over the Core weights 70.
    core_points = total_score(COMPUTED, ai, {item: WEIGHTS[item] for item in CORE})
    assert core_points is not None
    assert core_total_score(COMPUTED, ai, WEIGHTS, CORE) == round(core_points * 100 / 70, 2)


def test_adapted_scores_never_move_the_core_subscore():
    low = core_total_score(COMPUTED, AI | {"tilpasset-replay": 0}, WEIGHTS, CORE)
    high = core_total_score(
        COMPUTED, AI | {"tilpasset-eget-spill": 0, "tilpasset-replay": 4}, WEIGHTS, CORE
    )
    assert low == high


def test_a_full_core_and_an_empty_adapted_part_read_60_and_100():
    weights = {"a": 40, "b": 20, "tilpasset": 40}
    computed = {"a": 1.0, "b": 1.0}
    assert total_score(computed, {"tilpasset": 0}, weights) == 60.0
    assert core_total_score(computed, {"tilpasset": 0}, weights, ["a", "b"]) == 100.0


def test_a_replacement_item_is_left_out_when_the_caller_leaves_it_out_of_core():
    weights = {"a": 70, "erstatning": 30}
    assert core_total_score({"a": 0.5, "erstatning": 1.0}, {}, weights, ["a"]) == 50.0


def test_rounds_to_two_decimals():
    weights = {"a": 1, "b": 1, "c": 1}
    assert core_total_score({"a": 1.0, "b": 0.0, "c": 0.0}, {}, weights, ["a", "b", "c"]) == 33.33


@pytest.mark.parametrize(
    ("computed", "ai", "weights", "core"),
    [
        ({"a": 1.0}, {}, {"a": 10, "b": 10}, ["a", "b"]),  # b has no share
        ({"a": 1.0}, {}, {"a": 0, "t": 100}, ["a"]),  # no Core weight
        ({}, {}, {"t": 100}, []),  # no Core item at all
    ],
)
def test_none_without_a_share_or_without_core_weight(computed, ai, weights, core):
    assert core_total_score(computed, ai, weights, core) is None


def test_an_off_scale_step_is_refused():
    with pytest.raises(ValueError):
        core_total_score({}, {"a": 5}, {"a": 100}, ["a"])
