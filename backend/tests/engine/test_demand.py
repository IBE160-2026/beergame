"""Story 1.4: the demand series from a Demand pattern and a seed (FR-13, AD-1)."""

import json
from collections import Counter
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from app.engine import (
    SEED_MAX,
    DemandFixed,
    DemandPattern,
    DemandRandom,
    DemandStep,
    DemandStepNoise,
    GameSettings,
    Role,
    advance,
    demand_series,
    initial_state,
)
from app.engine.demand import new_seed, series

GOLDEN = Path(__file__).parent / "golden" / "demand-series.json"
PATTERN = TypeAdapter(DemandPattern)
CLASSIC = DemandStep(kind="step", start=4, new_level=8, change_week=5)
RANDOM = DemandRandom(kind="random", mean=4, spread=2)
NOISY = DemandStepNoise(kind="step+noise", start=4, new_level=8, change_week=5, spread=2)
SEEDS = range(200)


def test_fixed_series_is_returned_as_given():
    assert series(DemandFixed(kind="fixed", values=(4, 4, 9)), 3) == (4, 4, 9)


def test_step_series_ignores_the_seed():
    expected = (4, 4, 4, 4, 8, 8, 8)
    assert series(CLASSIC, 7) == expected
    assert series(CLASSIC, 7, 42) == expected


def test_one_whole_number_per_week():
    for pattern in (CLASSIC, RANDOM, NOISY):
        values = series(pattern, 36, 42)
        assert len(values) == 36
        assert all(type(value) is int and value >= 0 for value in values)


@pytest.mark.parametrize("seed", SEEDS)
def test_random_values_stay_within_mean_plus_minus_spread(seed):
    assert set(series(RANDOM, 36, seed)) <= {2, 3, 4, 5, 6}


@pytest.mark.parametrize("seed", SEEDS)
def test_step_plus_noise_follows_the_stepped_mean(seed):
    values = series(NOISY, 36, seed)
    assert set(values[:4]) <= {2, 3, 4, 5, 6}
    assert set(values[4:]) <= {6, 7, 8, 9, 10}
    # Same noise per Week as the random pattern with the same seed and spread.
    shift = [n - r for n, r in zip(values, series(RANDOM, 36, seed), strict=True)]
    assert shift == [0] * 4 + [4] * 32


def test_draws_are_discrete_uniform():
    counts = Counter(value for seed in SEEDS for value in series(RANDOM, 36, seed))
    total = len(SEEDS) * 36
    assert set(counts) == {2, 3, 4, 5, 6}
    for value in counts:
        assert abs(counts[value] / total - 1 / 5) < 0.02
    assert abs(sum(v * c for v, c in counts.items()) / total - 4) < 0.05


def test_draws_below_zero_become_zero():
    pattern = DemandRandom(kind="random", mean=1, spread=3)
    counts = Counter(value for seed in SEEDS for value in series(pattern, 36, seed))
    total = len(SEEDS) * 36
    assert set(counts) == {0, 1, 2, 3, 4}
    # -2, -1 and 0 all land on 0: about 3 in 7.
    assert abs(counts[0] / total - 3 / 7) < 0.03


def test_spread_zero_is_the_level():
    assert series(DemandRandom(kind="random", mean=4, spread=0), 5, 9) == (4,) * 5


def test_same_pattern_and_seed_give_the_same_series():
    assert series(NOISY, 36, 42) == series(NOISY.model_copy(), 36, 42)


def test_a_longer_game_extends_the_series():
    assert series(RANDOM, 36, 42)[:20] == series(RANDOM, 20, 42)


def test_seeds_give_different_series():
    assert len({series(RANDOM, 36, seed) for seed in SEEDS}) == len(SEEDS)


@pytest.mark.parametrize(
    ("pattern", "weeks", "seed", "message"),
    [
        (RANDOM, 36, None, "needs a seed"),
        (NOISY, 36, None, "needs a seed"),
        (RANDOM, 36, -1, "needs a seed"),
        (RANDOM, 36, SEED_MAX + 1, "needs a seed"),
        (RANDOM, 36, True, "needs a seed"),
        (RANDOM, 36, 4.0, "needs a seed"),
        (DemandFixed(kind="fixed", values=(4, 4, 9)), 36, None, "has 3 Weeks, not 36"),
        (DemandRandom(kind="random", mean=4, spread=-1), 36, 1, "spread cannot be negative"),
        (CLASSIC, 0, None, "whole number of Weeks"),
        (CLASSIC, True, None, "whole number of Weeks"),
    ],
)
def test_bad_inputs_raise(pattern, weeks, seed, message):
    with pytest.raises(ValueError, match=message):
        series(pattern, weeks, seed)


def test_golden_series_match_an_independent_implementation():
    """`demand-series.json` was computed by a separate reviewer from the Design Notes rule,
    with their own code, never by this engine."""
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert len(golden["series"]) == 5
    for case in golden["series"]:
        pattern = PATTERN.validate_python(case["pattern"])
        assert series(pattern, case["weeks"], case["seed"]) == tuple(case["series"])
    entropy = bytes.fromhex(golden["new_seed"]["entropy_hex"])
    assert new_seed(entropy) == golden["new_seed"]["seed"]


def test_new_seed_is_a_whole_number_from_the_entropy_passed_in():
    seed = new_seed(b"0123456789abcdef")
    assert type(seed) is int and 0 <= seed <= SEED_MAX
    assert new_seed(b"0123456789abcdef") == seed
    assert new_seed(b"0123456789abcdeg") != seed
    assert int(str(seed)) == seed
    assert new_seed(b"12345678") >= 0


@pytest.mark.parametrize(
    ("entropy", "error"),
    [("0123456789abcdef", TypeError), (bytearray(16), TypeError), (b"1234567", ValueError)],
)
def test_new_seed_rejects_bad_entropy(entropy, error):
    with pytest.raises(error):
        new_seed(entropy)


@pytest.mark.parametrize(
    "data",
    [
        {"kind": "fixed", "values": [4, 4, 9]},
        {"kind": "step", "start": 4, "new_level": 8, "change_week": 5},
        {"kind": "random", "mean": 4, "spread": 2},
        {"kind": "step+noise", "start": 4, "new_level": 8, "change_week": 5, "spread": 2},
    ],
)
def test_every_pattern_round_trips_through_settings_json(data):
    settings = GameSettings.model_validate({"demand": data, "demand_seed": 42})
    assert settings.model_dump(mode="json")["demand"] == data
    assert GameSettings.model_validate_json(settings.model_dump_json()) == settings


def test_the_retailer_meets_the_series_week_by_week():
    settings = GameSettings(demand=NOISY, demand_seed=42, weeks=12)
    expected = series(NOISY, 12, 42)
    assert demand_series(settings) == expected
    state = initial_state(settings)
    seen = []
    while not state.finished:
        seen.append(state.seat(Role.RETAILER).incoming_order)
        state = advance(settings, state, {s.role: s.incoming_order for s in state.seats})
    assert tuple(seen) == expected


def test_a_fixed_series_game():
    values = (4, 6, 0, 9, 4)
    settings = GameSettings(demand=DemandFixed(kind="fixed", values=values), weeks=5)
    state = initial_state(settings)
    seen = []
    while not state.finished:
        seen.append(state.seat(Role.RETAILER).incoming_order)
        state = advance(settings, state, {s.role: 4 for s in state.seats})
    assert tuple(seen) == values
