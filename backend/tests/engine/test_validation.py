from decimal import Decimal

import pytest

from app.engine import (
    RANGES,
    DemandStep,
    GameSettings,
    Range,
    Role,
    SettingsError,
    SettingsWarning,
    advance,
    demand_change_reaches_retailer,
    initial_state,
    validate,
    warnings,
)

FLAT = DemandStep(kind="step", start=4, new_level=4, change_week=5)


def codes(issues):
    return [(issue.code, issue.field) for issue in issues]


def test_classic_has_no_errors_and_no_warnings():
    assert validate(GameSettings()) == ()
    assert warnings(GameSettings()) == ()


def test_ranges_cover_every_checked_field_in_a_fixed_order():
    assert list(RANGES) == [
        "starting_inventory",
        "starting_backlog",
        "supply_line",
        "order_delay",
        "shipping_delay",
        "production_delay",
        "holding_cost",
        "backorder_cost",
        "weeks",
        "guided_weeks",
        "max_order",
    ]
    assert all(field in GameSettings.model_fields for field in RANGES)


def test_only_delays_are_confirmed():
    for field, allowed in RANGES.items():
        assert allowed.placeholder is (
            field not in {"order_delay", "shipping_delay", "production_delay"}
        )
    assert RANGES["order_delay"] == Range(minimum=1, maximum=3, placeholder=False)


def test_ranges_are_read_only():
    with pytest.raises(TypeError):
        RANGES["weeks"] = Range(minimum=1, maximum=2, placeholder=True)  # type: ignore[index]


def _settings(field, value):
    """Settings that break nothing except, perhaps, `field`."""
    return GameSettings(
        **{"guided_weeks": 0, "starting_inventory": 0, "demand": FLAT} | {field: value}
    )


def _constructible(field, value):
    try:
        _settings(field, value)
    except ValueError:
        return False
    return True


def _edges():
    for field, allowed in RANGES.items():
        step = Decimal("0.01") if allowed.decimal_places is not None else 1
        yield field, allowed.minimum, True
        yield field, allowed.maximum, True
        yield field, allowed.maximum + step, False
        # Just below the minimum only when the pydantic type does not already reject it.
        if _constructible(field, allowed.minimum - step):
            yield field, allowed.minimum - step, False


EDGES = list(_edges())


def test_only_max_order_has_a_below_minimum_value_the_type_allows():
    below = [
        (field, value) for field, value, ok in EDGES if not ok and value < RANGES[field].minimum
    ]
    assert below == [("max_order", 0)]


@pytest.mark.parametrize(("field", "value", "ok"), EDGES)
def test_range_edges(field, value, ok):
    errors = validate(_settings(field, value))
    if ok:
        assert errors == ()
    else:
        allowed = RANGES[field]
        assert errors == (
            SettingsError(
                code="out_of_range",
                field=field,
                message=errors[0].message,
                minimum=allowed.minimum,
                maximum=allowed.maximum,
                placeholder=allowed.placeholder,
            ),
        )
        assert str(value) in errors[0].message


def test_delay_out_of_range():
    (error,) = validate(GameSettings(order_delay=4))
    assert (error.code, error.field, error.minimum, error.maximum, error.placeholder) == (
        "out_of_range",
        "order_delay",
        1,
        3,
        False,
    )


def test_several_bad_fields_give_one_error_each():
    assert codes(validate(GameSettings(weeks=500, max_order=0))) == [
        ("out_of_range", "weeks"),
        ("out_of_range", "max_order"),
    ]


@pytest.mark.parametrize("field", ["holding_cost", "backorder_cost"])
def test_too_many_decimal_places(field):
    (error,) = validate(GameSettings(**{field: Decimal("0.505")}))
    assert (error.code, error.field) == ("too_many_decimal_places", field)
    assert (error.minimum, error.maximum, error.placeholder) == (
        Decimal("0.00"),
        Decimal("100.00"),
        True,
    )


@pytest.mark.parametrize("value", ["0.5", "0.500", "1", "1E+1", "100.00"])
def test_trailing_zeros_are_not_extra_precision(value):
    assert validate(GameSettings(holding_cost=Decimal(value), backorder_cost=Decimal("100"))) == ()


def test_out_of_range_beats_precision():
    (error,) = validate(GameSettings(holding_cost=Decimal("100.001")))
    assert error.code == "out_of_range"


def test_guided_weeks_must_end_before_the_demand_change():
    (error,) = validate(GameSettings(guided_weeks=5))
    assert (error.code, error.field) == ("guided_weeks_not_before_demand_change", "guided_weeks")
    assert error.minimum is None and error.maximum is None and error.placeholder is None
    assert validate(GameSettings(guided_weeks=4)) == ()


def test_guided_weeks_must_leave_weeks_to_play():
    settings = GameSettings(weeks=4, guided_weeks=4, demand=FLAT)
    assert codes(validate(settings)) == [("guided_weeks_leave_no_weeks_to_play", "guided_weeks")]
    assert validate(GameSettings(weeks=5, guided_weeks=4, demand=FLAT)) == ()
    # Also with a demand step, when Guided Weeks end before the change but fill the Game.
    assert codes(validate(GameSettings(weeks=4, guided_weeks=4))) == [
        ("guided_weeks_leave_no_weeks_to_play", "guided_weeks")
    ]


def test_when_both_guided_rules_fail_only_the_first_is_reported():
    settings = GameSettings(weeks=4, guided_weeks=5)
    assert codes(validate(settings)) == [("guided_weeks_not_before_demand_change", "guided_weeks")]


def test_flat_demand_has_no_change_week_rule_and_no_arrival_warning():
    assert FLAT.first_change_week is None
    settings = GameSettings(demand=FLAT, guided_weeks=10, weeks=11)
    assert validate(settings) == ()
    assert demand_change_reaches_retailer(settings) is None
    assert warnings(settings) == ()


def test_starting_inventory_and_backlog_cannot_both_be_positive():
    (error,) = validate(GameSettings(starting_inventory=12, starting_backlog=4))
    assert (error.code, error.field) == ("starting_inventory_and_backlog", "starting_backlog")
    assert validate(GameSettings(starting_inventory=0, starting_backlog=4)) == ()


def test_a_range_error_suppresses_the_same_fields_cross_field_error():
    assert codes(validate(GameSettings(starting_inventory=12, starting_backlog=101))) == [
        ("out_of_range", "starting_backlog")
    ]
    assert codes(validate(GameSettings(guided_weeks=21, weeks=10))) == [
        ("out_of_range", "guided_weeks")
    ]


def test_range_errors_come_before_cross_field_errors():
    settings = GameSettings(starting_inventory=12, starting_backlog=4, guided_weeks=5, max_order=0)
    assert codes(validate(settings)) == [
        ("out_of_range", "max_order"),
        ("starting_inventory_and_backlog", "starting_backlog"),
        ("guided_weeks_not_before_demand_change", "guided_weeks"),
    ]


def test_warnings_with_their_numbers():
    settings = GameSettings(supply_line=5, backorder_cost=Decimal("0.50"), max_order=50, weeks=20)
    assert validate(settings) == ()
    found = warnings(settings)
    assert all(isinstance(w, SettingsWarning) for w in found)
    assert [(w.code, w.field, w.values) for w in found] == [
        (
            "supply_line_differs_from_demand",
            "supply_line",
            {"supply_line": "5", "starting_demand": "4"},
        ),
        (
            "backorder_not_above_holding",
            "backorder_cost",
            {"backorder_cost": "0.50", "holding_cost": "0.50"},
        ),
        (
            "max_order_may_bind",
            "max_order",
            {"max_order": "50", "peak_demand": "8", "threshold": "80"},
        ),
        ("too_few_weeks_for_demand_change", "weeks", {"arrival_week": "21", "weeks": "20"}),
    ]
    assert all(w.message for w in found)


@pytest.mark.parametrize(
    ("override", "code"),
    [
        ({"supply_line": 3}, "supply_line_differs_from_demand"),
        ({"backorder_cost": Decimal("0.49")}, "backorder_not_above_holding"),
        ({"max_order": 79}, "max_order_may_bind"),
        ({"weeks": 20}, "too_few_weeks_for_demand_change"),
    ],
)
def test_warning_fires_just_past_the_threshold(override, code):
    assert [w.code for w in warnings(GameSettings(**override))] == [code]


@pytest.mark.parametrize(
    "override",
    [
        {"supply_line": 4},
        {"backorder_cost": Decimal("0.51")},
        {"max_order": 80},
        {"weeks": 21},
    ],
)
def test_no_warning_just_inside_the_threshold(override):
    assert warnings(GameSettings(**override)) == ()


def test_peak_demand_uses_the_higher_level():
    falling = DemandStep(kind="step", start=8, new_level=4, change_week=5)
    (warning,) = warnings(GameSettings(demand=falling, supply_line=8, max_order=79))
    assert warning.values["peak_demand"] == "8"


@pytest.mark.parametrize(("delay", "week"), [(1, 13), (2, 21), (3, 29)])
def test_demand_change_reaches_retailer(delay, week):
    settings = GameSettings(order_delay=delay, shipping_delay=delay, production_delay=delay)
    assert demand_change_reaches_retailer(settings) == week


@pytest.mark.parametrize("delays", [(1, 1, 1), (2, 2, 2), (3, 3, 3), (1, 2, 3), (3, 1, 2)])
def test_arrival_week_matches_the_engine(delays):
    """With no starting inventory every Seat ships only what it receives, so the first Week the
    Retailer receives more than 4 is when units the Factory made for the step arrive."""
    order, shipping, production = delays
    settings = GameSettings(
        order_delay=order,
        shipping_delay=shipping,
        production_delay=production,
        starting_inventory=0,
        weeks=60,
    )
    state = initial_state(settings)
    while state.seat(Role.RETAILER).incoming_delivery == 4:
        state = advance(settings, state, {s.role: s.incoming_order for s in state.seats})
    assert state.week == demand_change_reaches_retailer(settings)


def test_arrival_counts_roles_and_each_delay_separately():
    settings = GameSettings(
        roles=(Role.RETAILER, Role.FACTORY), order_delay=1, shipping_delay=2, production_delay=3
    )
    assert demand_change_reaches_retailer(settings) == 5 + 2 * 1 + 3 + 1 * 2


@pytest.mark.parametrize(
    "settings",
    [
        GameSettings(),
        GameSettings(
            starting_inventory=0,
            starting_backlog=0,
            supply_line=0,
            demand=DemandStep(kind="step", start=0, new_level=0, change_week=1),
            holding_cost=Decimal(0),
            backorder_cost=Decimal(0),
            weeks=1,
            guided_weeks=0,
            max_order=0,
        ),
        GameSettings(
            starting_inventory=10**9,
            starting_backlog=10**9,
            supply_line=10**9,
            order_delay=10**6,
            shipping_delay=10**6,
            production_delay=10**6,
            demand=DemandStep(kind="step", start=10**9, new_level=0, change_week=10**9),
            holding_cost=Decimal("1E+30"),
            backorder_cost=Decimal("1E-30"),
            weeks=10**9,
            guided_weeks=10**9,
            max_order=10**9,
        ),
    ],
)
def test_never_raises_and_returns_tuples(settings):
    assert isinstance(validate(settings), tuple)
    assert isinstance(warnings(settings), tuple)
