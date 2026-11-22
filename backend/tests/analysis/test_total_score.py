"""Golden cases for `analysis.total_score` (Story 12.2, FR-54, AD-1, AD-9): the weighted total of
an Individual test from computed credits, AI steps and the frozen Item weights."""

import pytest

from app.analysis.total import total_score

# The shipped question set's defaults: ten Core items and the Adapted total of 30 split 15/15.
WEIGHTS = {
    "startoppgave-sende": 3,
    "startoppgave-restordre": 3,
    "startoppgave-posisjon": 4,
    "flervalg-forklaring": 5,
    "flervalg-arsaker": 5,
    "tabell-nytt-monster": 10,
    "tabell-annen-bransje": 10,
    "tall-annen-bransje": 10,
    "langsvar-forsinkelse": 10,
    "langsvar-informasjon": 10,
    "tilpasset-eget-spill": 15,
    "tilpasset-replay": 15,
}
COMPUTED = {
    "startoppgave-sende": 1.0,
    "startoppgave-restordre": 0.0,
    "startoppgave-posisjon": 1.0,
    "flervalg-forklaring": 1.0,
    "flervalg-arsaker": 0.0,
    "tabell-nytt-monster": 0.6,
    "tabell-annen-bransje": 0.35,
    "tall-annen-bransje": 1.0,
}
AI = {
    "langsvar-forsinkelse": 3,
    "langsvar-informasjon": 0,
    "tilpasset-eget-spill": 4,
    "tilpasset-replay": 1,
}


def test_a_full_attempt_adds_each_weight_times_its_share():
    # 3 + 0 + 4 + 5 + 0 + 6 + 3.5 + 10 = 31.5 computed; 7.5 + 0 + 15 + 3.75 = 26.25 AI.
    assert total_score(COMPUTED, AI, WEIGHTS) == 57.75


def test_every_share_at_the_top_gives_the_weights_sum():
    computed = dict.fromkeys(COMPUTED, 1.0)
    ai = dict.fromkeys(AI, 4)
    assert total_score(computed, ai, WEIGHTS) == 100.0
    assert total_score(dict.fromkeys(COMPUTED, 0.0), dict.fromkeys(AI, 0), WEIGHTS) == 0.0


def test_an_excluded_question_counts_for_nothing_even_with_a_share():
    # The Lecturer took «flervalg-arsaker» out and gave its 5 to «flervalg-forklaring».
    weights = {k: v for k, v in WEIGHTS.items() if k != "flervalg-arsaker"}
    weights["flervalg-forklaring"] = 10
    computed = {**COMPUTED, "flervalg-arsaker": 1.0}
    assert total_score(computed, AI, weights) == 62.75


def test_the_fixed_adapted_weight_is_split_between_the_adapted_items():
    # An Adapted total of 25 split 13/12 (`apportion`), each at step 2: half of 25.
    weights = {"a": 75, "tilpasset-eget-spill": 13, "tilpasset-replay": 12}
    assert (
        total_score({"a": 0.0}, {"tilpasset-eget-spill": 2, "tilpasset-replay": 2}, weights) == 12.5
    )


def test_replacement_items_carry_the_adapted_total_as_core_items():
    weights = {"a": 70, "erstatning-tabell": 15, "erstatning-langsvar": 15}
    assert (
        total_score({"a": 1.0, "erstatning-tabell": 0.5}, {"erstatning-langsvar": 3}, weights)
        == 88.75
    )


def test_a_missing_item_gives_no_partial_total():
    ai = {k: v for k, v in AI.items() if k != "tilpasset-replay"}
    assert total_score(COMPUTED, ai, WEIGHTS) is None
    assert total_score({}, {}, {}) == 0.0


@pytest.mark.parametrize(("computed", "ai"), [({"a": 1.5}, {}), ({}, {"a": 5}), ({}, {"a": -1})])
def test_a_share_off_the_scale_is_refused(computed, ai):
    with pytest.raises(ValueError):
        total_score(computed, ai, {"a": 10})
