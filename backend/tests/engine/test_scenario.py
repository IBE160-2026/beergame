"""Story 10.1: the Replay scenario template, its default and its one resolver (FR-49, FR-12,
FR-13, AD-1, AD-4). Pure: no database."""

from decimal import Decimal

import pytest

from app.engine import (
    SEED_MAX,
    GameSettings,
    IntRange,
    ReplayFixed,
    ReplayRandom,
    ReplayStep,
    ReplayTemplate,
    default_replay_template,
    demand_series,
    replay_settings,
    replay_template_admits,
    validate,
    validate_template,
)

CLASSIC = default_replay_template(GameSettings())
SEEDS = range(0, 500 * 7919, 7919)


def test_the_classic_default_keeps_the_levels_and_ranges_the_hidden_values():
    assert CLASSIC.demand == ReplayStep(
        kind="step", start=4, new_level=8, change_week=IntRange(minimum=5, maximum=12), spread=2
    )
    assert CLASSIC.weeks == IntRange(minimum=30, maximum=40)
    assert CLASSIC.guided_weeks == 0
    # Every other setting is the Class session's.
    classic = GameSettings()
    for field in (
        "roles",
        "starting_inventory",
        "starting_backlog",
        "supply_line",
        "order_delay",
        "shipping_delay",
        "production_delay",
        "holding_cost",
        "backorder_cost",
        "max_order",
        "capacity",
        "info_visibility",
    ):
        assert getattr(CLASSIC, field) == getattr(classic, field), field
    assert CLASSIC.schema_version == 1


def test_the_default_follows_the_class_sessions_other_settings():
    own = GameSettings(starting_inventory=20, shipping_delay=3, backorder_cost=Decimal("2.00"))
    template = default_replay_template(own)
    assert (template.starting_inventory, template.shipping_delay, template.backorder_cost) == (
        20,
        3,
        Decimal("2.00"),
    )


@pytest.mark.parametrize(
    ("demand", "wanted"),
    [
        # A step keeps its own levels; the spread is 2.
        (
            {"kind": "step", "start": 6, "new_level": 10, "change_week": 20},
            ReplayStep(
                kind="step",
                start=6,
                new_level=10,
                change_week=IntRange(minimum=5, maximum=12),
                spread=2,
            ),
        ),
        # A step plus noise keeps its own spread where that is larger, and 2 where it is not.
        (
            {"kind": "step+noise", "start": 6, "new_level": 10, "change_week": 8, "spread": 3},
            ReplayStep(
                kind="step",
                start=6,
                new_level=10,
                change_week=IntRange(minimum=5, maximum=12),
                spread=3,
            ),
        ),
        (
            {"kind": "step+noise", "start": 6, "new_level": 10, "change_week": 8, "spread": 1},
            ReplayStep(
                kind="step",
                start=6,
                new_level=10,
                change_week=IntRange(minimum=5, maximum=12),
                spread=2,
            ),
        ),
        # Random demand keeps its mean, with no step Week.
        ({"kind": "random", "mean": 5, "spread": 1}, ReplayRandom(kind="random", mean=5, spread=2)),
        ({"kind": "random", "mean": 5, "spread": 4}, ReplayRandom(kind="random", mean=5, spread=4)),
    ],
)
def test_one_rule_per_demand_pattern_kind(demand, wanted):
    template = default_replay_template(GameSettings(demand=demand, demand_seed=1))
    assert template.demand == wanted
    assert (template.weeks, template.guided_weeks) == (IntRange(minimum=30, maximum=40), 0)
    assert validate_template(template) == ()


def test_a_fixed_series_keeps_each_weeks_value_and_holds_the_last():
    values = (4, 4, 4) + (9,) * 33
    template = default_replay_template(GameSettings(demand={"kind": "fixed", "values": values}))
    assert template.demand == ReplayFixed(kind="fixed", values=values, spread=2)
    assert validate_template(template) == ()
    settings = replay_settings(template, 7)
    # Golden: 33 Weeks, the first three around 4, then around 9 (held past nothing here).
    assert settings.weeks == 33
    assert settings.demand.values == (
        3, 5, 3, 11, 8, 8, 7, 9, 9, 8, 9, 10, 11, 10, 9, 8, 8, 8, 9, 8, 10, 8, 10, 10, 7, 9, 7,
        10, 11, 8, 7, 8, 8,
    )  # fmt: skip
    # A short series: Weeks beyond it hold the last value as the level.
    short = default_replay_template(
        GameSettings(weeks=3, guided_weeks=0, demand={"kind": "fixed", "values": (4, 6, 9)})
    )
    for seed in range(40):
        resolved = replay_settings(short, seed)
        assert len(resolved.demand.values) == resolved.weeks
        assert all(7 <= value <= 11 for value in resolved.demand.values[3:])
        assert replay_template_admits(short, resolved)
        assert validate(resolved) == ()


def test_the_same_template_and_seed_give_the_same_settings_and_series():
    first, second = replay_settings(CLASSIC, 424242), replay_settings(CLASSIC, 424242)
    assert first == second
    assert demand_series(first) == demand_series(second)


@pytest.mark.parametrize(
    ("seed", "weeks", "change_week", "series"),
    [
        (1, 33, 6, [2, 4, 5, 3, 3, 9, 8, 6, 9, 6, 8, 10, 6, 6, 10, 6, 8, 10, 6, 10, 10, 7, 10, 10, 8, 8, 7, 9, 6, 10, 7, 7, 8]),  # noqa: E501
        (2, 37, 10, [5, 3, 4, 4, 4, 4, 5, 6, 4, 8, 10, 10, 6, 9, 10, 8, 7, 9, 8, 8, 10, 9, 10, 6, 10, 10, 10, 6, 8, 6, 10, 10, 7, 7, 8, 8, 8]),  # noqa: E501
        (3, 36, 12, [4, 5, 5, 6, 2, 4, 2, 2, 3, 2, 6, 7, 7, 9, 10, 6, 6, 9, 8, 8, 8, 7, 6, 10, 9, 8, 8, 10, 8, 10, 10, 6, 8, 10, 6, 8]),  # noqa: E501
    ],
)  # fmt: skip
def test_golden_draws_of_the_classic_default(seed, weeks, change_week, series):
    settings = replay_settings(CLASSIC, seed)
    assert (settings.weeks, settings.demand.change_week, settings.demand_seed) == (
        weeks,
        change_week,
        seed,
    )
    assert (settings.demand.kind, settings.demand.spread, settings.guided_weeks) == (
        "step+noise",
        2,
        0,
    )
    assert list(demand_series(settings)) == series


def test_every_draw_of_the_classic_default_stays_inside_its_ranges():
    changes, lengths = set(), set()
    for seed in SEEDS:
        settings = replay_settings(CLASSIC, seed)
        change = settings.demand.change_week
        changes.add(change)
        lengths.add(settings.weeks)
        assert 5 <= change <= 12
        assert 30 <= settings.weeks <= 40
        assert settings.guided_weeks == 0
        for week, value in enumerate(demand_series(settings), start=1):
            level = 8 if week >= change else 4
            assert type(value) is int and value >= 0
            assert abs(value - level) <= 2
        assert validate(settings) == ()
        assert replay_template_admits(CLASSIC, settings)
    # The draws reach every value of both ranges.
    assert changes == set(range(5, 13))
    assert lengths == set(range(30, 41))


@pytest.mark.parametrize("seed", [-1, SEED_MAX + 1, True, 1.0, "1", None])
def test_a_bad_seed_is_refused(seed):
    with pytest.raises(ValueError, match="Replay seed"):
        replay_settings(CLASSIC, seed)


def _with(**changes) -> ReplayTemplate:
    return ReplayTemplate.model_validate({**CLASSIC.model_dump(), **changes})


def _step(**changes) -> dict:
    return {**CLASSIC.demand.model_dump(), **changes}


def test_a_change_week_that_can_fall_after_the_game_is_refused_with_its_range():
    template = _with(demand=_step(change_week={"minimum": 5, "maximum": 40}))
    [error] = validate_template(template)
    assert (error.code, error.field, error.minimum, error.maximum) == (
        "demand_change_week_outside_game",
        "demand.change_week",
        1,
        30,
    )


def test_an_inverted_range_is_refused_and_cannot_be_resolved():
    template = _with(weeks={"minimum": 40, "maximum": 30})
    [error] = validate_template(template)
    assert (error.code, error.field, error.minimum, error.maximum) == (
        "range_inverted",
        "weeks",
        40,
        30,
    )
    with pytest.raises(ValueError, match="inverted"):
        replay_settings(template, 1)


@pytest.mark.parametrize(
    ("changes", "code", "field", "allowed"),
    [
        ({"order_delay": {"minimum": 1, "maximum": 4}}, "out_of_range", "order_delay", (1, 3)),
        ({"shipping_delay": 0}, "out_of_range", "shipping_delay", (1, 3)),
        ({"weeks": {"minimum": 30, "maximum": 101}}, "out_of_range", "weeks", (1, 100)),
        (
            {"guided_weeks": {"minimum": 0, "maximum": 6}},
            "guided_weeks_not_before_demand_change",
            "guided_weeks",
            (0, 4),
        ),
        (
            {"starting_backlog": {"minimum": 0, "maximum": 3}},
            "starting_inventory_and_backlog",
            "starting_backlog",
            (None, None),
        ),
        (
            {"demand": _step(change_week={"minimum": 0, "maximum": 12})},
            "out_of_range",
            "demand.change_week",
            (1, 30),
        ),
    ],
)
def test_template_validation_uses_the_game_settings_rules(changes, code, field, allowed):
    errors = validate_template(_with(**changes))
    assert [(e.code, e.field, (e.minimum, e.maximum)) for e in errors] == [(code, field, allowed)]


def test_guided_weeks_in_a_game_without_a_change_week():
    template = ReplayTemplate.model_validate(
        {
            **CLASSIC.model_dump(),
            "demand": {"kind": "random", "mean": 4, "spread": 2},
            "weeks": {"minimum": 3, "maximum": 10},
            "guided_weeks": {"minimum": 0, "maximum": 3},
        }
    )
    [error] = validate_template(template)
    assert (error.code, error.maximum) == ("guided_weeks_leave_no_weeks_to_play", 2)


def test_switched_off_features_are_refused_as_for_game_settings():
    template = _with(capacity={"factory": 6})
    assert [e.code for e in validate_template(template)] == ["capacity_disabled"]
    assert validate_template(template, capacity_enabled=True) == ()


def test_a_template_with_fixed_values_is_one_game():
    """An own scenario may set the Class game's exact settings (Story 10.2): with spread 0 and
    single values every seed gives the same Game, its demand a plain step."""
    template = _with(weeks=36, guided_weeks=4, demand=_step(change_week=5, spread=0))
    assert validate_template(template) == ()
    settings = replay_settings(template, 99)
    assert settings == GameSettings(demand_seed=99)
    assert replay_template_admits(template, settings)


def test_admits_only_draws_of_the_template():
    settings = replay_settings(CLASSIC, 5)
    assert replay_template_admits(CLASSIC, settings)
    assert not replay_template_admits(CLASSIC, GameSettings())  # 36 Weeks fits, 4 Guided does not
    assert not replay_template_admits(CLASSIC, settings.model_copy(update={"shipping_delay": 3}))
    assert not replay_template_admits(CLASSIC, settings.model_copy(update={"weeks": 41}))
    costlier = settings.model_copy(update={"holding_cost": Decimal("0.75")})
    assert not replay_template_admits(CLASSIC, costlier)
    plain = settings.model_copy(
        update={"demand": GameSettings().demand.model_copy(update={"change_week": 6})}
    )
    assert not replay_template_admits(CLASSIC, plain)  # no variation: another scenario
    random = default_replay_template(
        GameSettings(demand={"kind": "random", "mean": 5, "spread": 2})
    )
    assert not replay_template_admits(random, settings)
    assert replay_template_admits(random, replay_settings(random, 5))


def test_a_template_round_trips_through_json():
    assert ReplayTemplate.model_validate_json(CLASSIC.model_dump_json()) == CLASSIC
    assert "capacity" not in CLASSIC.model_dump()


def _fixed(values, **changes) -> ReplayTemplate:
    demand = {"kind": "fixed", "values": values, "spread": 2}
    return ReplayTemplate.model_validate({**CLASSIC.model_dump(), "demand": demand, **changes})


def test_a_fixed_series_at_the_top_of_its_range_stays_inside_it():
    template = _fixed([100] * 5 + [98])
    assert validate_template(template) == ()
    for seed in range(60):
        settings = replay_settings(template, seed)
        assert max(settings.demand.values) <= 100
        assert validate(settings) == ()
        assert replay_template_admits(template, settings)


def test_a_fixed_series_varies_from_week_2_so_guided_weeks_end_before_it():
    [error] = validate_template(_fixed([4] * 36, guided_weeks={"minimum": 0, "maximum": 2}))
    assert (error.code, error.field, error.minimum, error.maximum) == (
        "guided_weeks_not_before_demand_change",
        "guided_weeks",
        0,
        1,
    )
    template = _fixed([4] * 36, guided_weeks=1)
    assert validate_template(template) == ()
    # With no variation the levels alone decide, as for Game settings.
    exact = ReplayTemplate.model_validate(
        {**template.model_dump(), "demand": {"kind": "fixed", "values": [4] * 36, "spread": 0}}
    )
    assert validate_template(exact.model_copy(update={"guided_weeks": 4})) == ()
    assert all(validate(replay_settings(template, seed)) == () for seed in range(40))


def test_a_fixed_series_spread_has_the_spread_range():
    template = ReplayTemplate.model_validate(
        {**CLASSIC.model_dump(), "demand": {"kind": "fixed", "values": [4], "spread": 21}}
    )
    [error] = validate_template(template)
    assert (error.code, error.field, error.maximum) == ("out_of_range", "demand.spread", 20)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"roles": []}, "at least one Role"),
        ({"roles": ["retailer", "retailer"]}, "once in the chain"),
        ({"roles": ["retailer", "factory"], "capacity": {"wholesaler": 4}}, "not a Role"),
    ],
)
def test_a_template_chain_follows_the_game_settings_rules(changes, message):
    with pytest.raises(ValueError, match=message):
        ReplayTemplate.model_validate({**CLASSIC.model_dump(), **changes})
