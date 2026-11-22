"""Story 2.10: the Play guard statistics as a pure function (FR-79, AD-1)."""

import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.analysis import play_guard
from app.analysis.play_guard import GuardDecision, GuardRow, evaluate, is_calibrated
from app.engine import GameSettings, default_replay_template, replay_settings
from app.modules.games import commands
from app.platform.parameter_sets import read_parameter_set
from tests.engine.test_purity import FORBIDDEN_STDLIB, imported_roots

ANALYSIS = Path(__file__).parents[2] / "app" / "analysis"
SET_ID = "placeholder-0"


def shipped() -> play_guard.PlayGuardParams:
    return play_guard.parse_params(read_parameter_set("play_guard", SET_ID), SET_ID)


PARAMS = shipped()


def rows(orders, rb=8, no=8, by="llm", first=1):
    """One row per Order from Week `first`; `rb`/`no` are the references in every Week."""
    return [
        GuardRow(
            week=first + i,
            order=order,
            decided_by=by,
            rule_based_reference_order=rb,
            near_optimal_reference_order=no,
        )
        for i, order in enumerate(orders)
    ]


def test_the_shipped_set_is_a_marked_placeholder():
    assert PARAMS.verified is False
    assert "issue #20" in PARAMS.source
    assert (PARAMS.window_weeks, PARAMS.minimum_weeks) == (8, 8)
    assert (PARAMS.lower_distance, PARAMS.lower_share) == (4, Decimal("0.95"))
    assert (PARAMS.upper_margin, PARAMS.large_distance) == (Decimal("0.05"), 16)
    assert PARAMS.distance == "absolute_units"
    assert list(PARAMS.calibrated_profiles) == ["classic"]
    assert PARAMS.calibrated_profiles["classic"] == GameSettings()


def test_too_few_llm_orders_never_switch():
    result = evaluate(rows([40] * 7), PARAMS)
    assert result.decision is GuardDecision.WITHIN_BAND
    assert (result.statistic, result.llm_weeks, result.lower_share) == (None, 7, None)


def test_only_llm_rows_count():
    others = [
        *rows([40] * 5, by="guided"),
        *rows([40] * 5, by="rule_based", first=6),
        *rows([40] * 5, by="scripted", first=11),
        *rows([40] * 5, by="student", first=16),
    ]
    result = evaluate([*others, *rows([8] * 7, first=21)], PARAMS)
    assert (result.decision, result.llm_weeks) == (GuardDecision.WITHIN_BAND, 7)


def test_orders_far_above_the_reference_switch_on_the_lower_limit():
    result = evaluate(rows([28] * 8), PARAMS)
    assert result.decision is GuardDecision.SWITCH
    assert (result.statistic, result.value) == ("lower_share", Decimal(0))


def test_one_outlier_in_the_window_switches():
    result = evaluate(rows([8] * 7 + [13]), PARAMS)
    assert (result.decision, result.statistic) == (GuardDecision.SWITCH, "lower_share")
    assert result.value == Decimal("0.875")


def test_the_window_rolls_past_old_outliers():
    result = evaluate(rows([40] * 5 + [9] * 8), PARAMS)
    assert result.decision is GuardDecision.WITHIN_BAND
    assert (result.llm_weeks, result.lower_share) == (13, Decimal(1))


def test_a_player_at_the_near_optimal_reference_switches_on_the_upper_limit():
    result = evaluate(rows([11] * 8, rb=8, no=11), PARAMS)
    assert (result.decision, result.statistic) == (GuardDecision.SWITCH, "upper_closeness")
    assert result.value == Decimal(0) == result.upper_closeness
    assert result.lower_share == Decimal(1)


def test_weeks_where_the_references_coincide_do_not_count_against_the_upper_limit():
    result = evaluate(rows([8] * 8, rb=8, no=8), PARAMS)
    assert result.decision is GuardDecision.WITHIN_BAND
    assert result.upper_closeness is None
    mixed = [*rows([8] * 7, rb=8, no=8), *rows([8], rb=8, no=12, first=8)]
    assert evaluate(mixed, PARAMS).upper_closeness == Decimal(1)
    missing = rows([8] * 8, rb=8, no=None)  # turns opened before Story 2.9
    assert evaluate(missing, PARAMS).upper_closeness is None


def test_a_player_at_the_rule_based_reference_stays_in_the_band():
    result = evaluate(rows([8] * 8, rb=8, no=12), PARAMS)
    assert result.decision is GuardDecision.WITHIN_BAND
    assert result.upper_closeness == Decimal(1)


def test_the_upper_limit_is_a_mean_over_the_differing_weeks():
    # RB 12, NO 16: an Order of 15 is 0.25 of the gap from NO, an Order of 16 is 0.
    near = [*rows([15] * 4, rb=12, no=16), *rows([16] * 4, rb=12, no=16, first=5)]
    result = evaluate(near, PARAMS)
    assert result.upper_closeness == Decimal("0.125")
    assert result.decision is GuardDecision.WITHIN_BAND
    closer = [*rows([16] * 7, rb=12, no=16), *rows([15], rb=12, no=16, first=8)]
    result = evaluate(closer, PARAMS)
    assert result.decision is GuardDecision.SWITCH
    assert result.value == Decimal("0.03125")


def test_uncalibrated_settings_apply_no_upper_limit():
    result = evaluate(rows([11] * 8, rb=8, no=11), PARAMS, calibrated=False)
    assert result.decision is GuardDecision.WITHIN_BAND
    assert result.upper_closeness is None


def test_uncalibrated_settings_switch_only_on_a_large_deviation():
    large = evaluate(rows([28] * 8), PARAMS, calibrated=False)
    assert (large.decision, large.statistic) == (GuardDecision.SWITCH, "large_deviation")
    moderate = evaluate(rows([18] * 8), PARAMS, calibrated=False)
    assert moderate.decision is GuardDecision.WITHIN_BAND
    assert evaluate(rows([18] * 8), PARAMS).decision is GuardDecision.SWITCH


def test_rows_are_read_in_week_order():
    shuffled = list(reversed(rows([40] * 5 + [8] * 8)))
    assert evaluate(shuffled, PARAMS).decision is GuardDecision.WITHIN_BAND


def test_classic_settings_are_calibrated_whatever_the_seed():
    assert is_calibrated(GameSettings(), PARAMS)
    assert is_calibrated(GameSettings(demand_seed=99), PARAMS)
    assert not is_calibrated(GameSettings(shipping_delay=3), PARAMS)
    assert not is_calibrated(GameSettings(weeks=20), PARAMS)
    assert not is_calibrated(GameSettings(capacity={"factory": 6}), PARAMS)
    # A neighbour's numbers change what a player sees, so it is not the calibrated profile.
    assert not is_calibrated(GameSettings(info_visibility={"upstream": True}), PARAMS)


def test_the_default_set_calibrates_the_default_replay_scenario():
    """Story 10.1 (FR-79, AD-22): `placeholder-1` holds `placeholder-0`'s values plus the default
    Replay scenario of the Classic settings, and is the set new Games freeze."""
    params = play_guard.parse_params(
        read_parameter_set("play_guard", "placeholder-1"), "placeholder-1"
    )
    assert commands.DEFAULT_PLAY_GUARD_SET == "placeholder-1"
    assert params.version == 1
    template = default_replay_template(GameSettings())
    assert params.calibrated_profiles == {"classic": GameSettings(), "replay_default": template}
    assert params.model_dump(exclude={"id", "source", "calibrated_profiles"}) == PARAMS.model_dump(
        exclude={"id", "source", "calibrated_profiles"}
    )
    # Every default Replay counts; the Classic game still does.
    assert all(is_calibrated(replay_settings(template, seed), params) for seed in range(50))
    assert is_calibrated(GameSettings(demand_seed=3), params)
    assert not is_calibrated(replay_settings(template, 1), PARAMS)
    # An own scenario with other settings does not.
    own = template.model_copy(update={"shipping_delay": 3})
    assert not is_calibrated(replay_settings(own, 1), params)
    slower = default_replay_template(GameSettings(production_delay=3))
    assert not is_calibrated(replay_settings(slower, 1), params)


def test_a_new_profile_is_data_in_a_new_version_of_the_set():
    data = json.loads(read_parameter_set("play_guard", SET_ID))
    replay = GameSettings(weeks=20, guided_weeks=0).model_dump(mode="json")
    data["version"] = 2
    data["calibrated_profiles"]["replay_default"] = replay
    params = play_guard.parse_params(json.dumps(data), SET_ID)
    assert is_calibrated(GameSettings(weeks=20, guided_weeks=0, demand_seed=4), params)
    assert not is_calibrated(GameSettings(weeks=20, guided_weeks=1), params)
    assert is_calibrated(GameSettings(), params)


@pytest.mark.parametrize(
    "change",
    [
        {"calibrated_profiles": {}},
        {"lower_share": "1.5"},
        {"window_weeks": 0},
        {"distance": "squared"},
        {"extra": 1},
    ],
)
def test_invalid_sets_are_refused(change):
    data = {**json.loads(read_parameter_set("play_guard", SET_ID)), **change}
    with pytest.raises(ValidationError):
        play_guard.parse_params(json.dumps(data), SET_ID)


def test_a_set_must_hold_the_id_asked_for():
    with pytest.raises(ValueError, match="holds set"):
        play_guard.parse_params(read_parameter_set("play_guard", SET_ID), "other")


def test_analysis_imports_only_stdlib_pydantic_and_the_engine():
    files = sorted(ANALYSIS.rglob("*.py"))
    assert ANALYSIS / "play_guard.py" in files
    for path in files:
        source = path.read_text(encoding="utf-8")
        roots = imported_roots(source)
        outside = roots - {"app", "pydantic"} - set(sys.stdlib_module_names)
        assert not outside, f"{path.name} imports {outside}"
        assert not roots & FORBIDDEN_STDLIB, f"{path.name} imports {roots & FORBIDDEN_STDLIB}"
        for forbidden in ("app.modules", "app.platform", "app.ai"):
            assert forbidden not in source, path.name
