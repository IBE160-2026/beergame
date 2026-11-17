"""Capacity (Story 1.12, FR-12, FR-26, FR-29): a capped Seat ships at most its capacity a Week."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.engine import (
    CAPACITY_RANGE,
    ROLES,
    DemandFixed,
    DemandStep,
    GameSettings,
    Role,
    advance,
    initial_state,
    validate,
    warnings,
)
from app.engine.check import conservation

FLAT_8 = DemandFixed(kind="fixed", values=(8,) * 36)


def play(settings, orders):
    states = [initial_state(settings)]
    for placed in orders:
        states.append(advance(settings, states[-1], placed))
    return states


def pass_through(settings, weeks):
    """Every Seat orders its own incoming order; returns the states and the Orders."""
    states = [initial_state(settings)]
    orders = []
    for _ in range(weeks):
        placed = {seat.role.value: seat.incoming_order for seat in states[-1].seats}
        orders.append(placed)
        states.append(advance(settings, states[-1], placed))
    return states, orders


def every_seat(capacity):
    return {role: capacity for role in ROLES}


def rules(violations):
    return {(v.rule, v.week, v.role) for v in violations}


# --- settings ---------------------------------------------------------------------------------


def test_capacity_is_off_by_default_and_left_out_of_the_dump():
    assert GameSettings().capacity is None
    assert "capacity" not in GameSettings().model_dump()
    assert "capacity" not in GameSettings().model_dump(mode="json")
    assert GameSettings().capacity_of(Role.RETAILER) is None


def test_capacity_round_trips_through_json():
    settings = GameSettings(capacity={"wholesaler": 6})
    assert settings.model_dump(mode="json")["capacity"] == {"wholesaler": 6}
    again = GameSettings.model_validate_json(settings.model_dump_json())
    assert again == settings
    assert again.capacity_of(Role.WHOLESALER) == 6
    assert again.capacity_of(Role.RETAILER) is None


@pytest.mark.parametrize(
    "capacity",
    [
        {"retailer": 6.5},
        {"retailer": "6"},
        {"retailer": True},
        {"retailer": None},
        {"shop": 6},
        6,
    ],
)
def test_capacity_that_is_not_a_whole_number_per_role_is_refused(capacity):
    with pytest.raises(ValidationError):
        GameSettings(capacity=capacity)


def test_an_empty_capacity_is_no_capacity():
    settings = GameSettings(capacity={})
    assert settings.capacity is None
    assert settings == GameSettings()
    assert "capacity" not in settings.model_dump()
    assert validate(settings) == ()


def test_a_bad_chain_is_reported_once_not_again_under_capacity():
    with pytest.raises(ValidationError) as caught:
        GameSettings(roles=("retailer", "retailer"), capacity={"retailer": 6})
    assert [error["loc"] for error in caught.value.errors()] == [("roles",)]


def test_capacity_for_a_role_outside_the_chain_is_refused():
    with pytest.raises(ValidationError, match="not a Role in this chain"):
        GameSettings(roles=("retailer", "wholesaler"), capacity={"factory": 6})
    assert GameSettings(roles=("retailer", "wholesaler"), capacity={"wholesaler": 6})


# --- validation and warnings ------------------------------------------------------------------


def test_capacity_is_refused_when_the_flag_is_off():
    settings = GameSettings(capacity={"retailer": 6})
    for errors in (validate(settings), validate(settings, capacity_enabled=False)):
        assert [(e.code, e.field) for e in errors] == [("capacity_disabled", "capacity")]
    assert validate(settings, capacity_enabled=True) == ()


def test_the_flag_changes_nothing_without_a_capacity():
    for settings in (GameSettings(), GameSettings(weeks=101), GameSettings(guided_weeks=5)):
        assert validate(settings) == validate(settings, capacity_enabled=True)


def test_capacity_range_is_whole_numbers_above_zero_with_a_placeholder_maximum():
    assert (CAPACITY_RANGE.minimum, CAPACITY_RANGE.maximum) == (1, 100)
    assert CAPACITY_RANGE.placeholder is True


@pytest.mark.parametrize(
    ("value", "ok"), [(-1, False), (0, False), (1, True), (100, True), (101, False)]
)
def test_capacity_range_edges(value, ok):
    errors = validate(GameSettings(capacity={"distributor": value}), capacity_enabled=True)
    if ok:
        assert errors == ()
    else:
        (error,) = errors
        assert (error.code, error.field) == ("out_of_range", "capacity.distributor")
        assert (error.minimum, error.maximum, error.placeholder) == (1, 100, True)
        assert str(value) in error.message


def test_capacity_errors_come_in_chain_order_after_demand_and_before_cross_field_rules():
    settings = GameSettings(
        capacity={"factory": 0, "retailer": 0},
        demand=DemandStep(kind="step", start=4, new_level=8, change_week=40),
        starting_backlog=1,
    )
    fields = [e.field for e in validate(settings, capacity_enabled=True)]
    assert fields == [
        "demand.change_week",
        "capacity.retailer",
        "capacity.factory",
        "starting_backlog",
    ]


def test_capacity_below_peak_demand_warns_with_its_numbers():
    settings = GameSettings(capacity={"factory": 7, "retailer": 6, "wholesaler": 8})
    found = warnings(settings)
    assert [w.code for w in found] == ["capacity_below_peak_demand"] * 2
    assert [(w.field, w.values) for w in found] == [
        ("capacity.retailer", {"role": "retailer", "capacity": "6", "peak_demand": "8"}),
        ("capacity.factory", {"role": "factory", "capacity": "7", "peak_demand": "8"}),
    ]
    assert "6" in found[0].message and "8" in found[0].message


def test_capacity_warnings_come_after_the_others():
    settings = GameSettings(supply_line=5, capacity={"retailer": 6})
    assert [w.code for w in warnings(settings)] == [
        "supply_line_differs_from_demand",
        "capacity_below_peak_demand",
    ]


def test_no_capacity_warning_at_or_above_peak():
    assert warnings(GameSettings(capacity=every_seat(8))) == ()


# --- the Week sequence ------------------------------------------------------------------------


def test_one_capped_seat_ships_at_most_its_capacity_and_keeps_the_rest_as_backlog():
    settings = GameSettings(demand=FLAT_8, capacity={"retailer": 6})
    states, orders = pass_through(settings, 12)
    retailer = [state.seat(Role.RETAILER) for state in states]
    assert all(seat.shipped <= 6 for seat in retailer)
    assert [seat.backlog for seat in retailer[:4]] == [2, 4, 6, 8]
    assert retailer[0].inventory > 0 and retailer[0].backlog > 0
    assert conservation(settings, states, orders) == ()


def test_every_seat_capped():
    settings = GameSettings(demand=FLAT_8, capacity=every_seat(6))
    states, orders = pass_through(settings, 36)
    assert states[-1].finished
    assert all(seat.shipped <= 6 for state in states for seat in state.seats)
    assert any(seat.shipped == 6 for state in states for seat in state.seats)
    assert conservation(settings, states, orders) == ()


def test_the_factory_cap_limits_shipping_not_production():
    settings = GameSettings(demand=FLAT_8, capacity={"factory": 6})
    states, orders = pass_through(settings, 20)
    factory = [state.seat(Role.FACTORY) for state in states]
    assert all(seat.shipped <= 6 for seat in factory)
    assert any(seat.goods_slots[-1] == 8 for seat in factory)
    assert conservation(settings, states, orders) == ()


def test_a_capacity_that_never_binds_changes_nothing():
    orders = [{role: 4 + (week % 5) for role in ROLES} for week in range(36)]
    uncapped = play(GameSettings(), orders)
    capped = play(GameSettings(capacity=every_seat(50)), orders)
    assert capped == uncapped


# --- the conservation check -------------------------------------------------------------------


def with_seat(states, s, role, **update):
    state = states[s]
    seats = tuple(
        seat.model_copy(update=update) if seat.role == role else seat for seat in state.seats
    )
    changed = list(states)
    changed[s] = state.model_copy(update={"seats": seats})
    return changed


def test_shipping_past_the_capacity_is_caught():
    settings = GameSettings(demand=FLAT_8, capacity={"retailer": 6})
    states, orders = pass_through(settings, 3)
    seat = states[1].seat(Role.RETAILER)
    changed = with_seat(
        states,
        1,
        Role.RETAILER,
        shipped=seat.shipped + 1,
        inventory=seat.inventory - 1,
        backlog=seat.backlog - 1,
        cost=seat.cost - settings.holding_cost - settings.backorder_cost,
    )
    found = rules(conservation(settings, changed[:2], orders[:1]))
    assert found == {("shipment", 2, Role.RETAILER)}


def test_both_positive_is_allowed_on_the_capped_seat_only():
    capped = GameSettings(demand=FLAT_8, capacity={"retailer": 6})
    states, orders = pass_through(capped, 2)
    seat = states[1].seat(Role.RETAILER)
    assert seat.inventory > 0 and seat.backlog > 0
    assert conservation(capped, states, orders) == ()
    # The same books read as an uncapped Retailer's break the rule (and the shipment).
    uncapped = GameSettings(demand=FLAT_8, capacity={"wholesaler": 6})
    found = rules(conservation(uncapped, states, orders))
    assert ("inventory_and_backlog", 2, Role.RETAILER) in found
    assert {role for rule, _, role in found if rule == "inventory_and_backlog"} == {Role.RETAILER}


def test_golden_capped_retailer_holds_both_and_keeps_its_books():
    settings = GameSettings(capacity={"retailer": 6})
    states, orders = pass_through(settings, 10)
    retailer = [state.seat(Role.RETAILER) for state in states[4:10]]
    assert [seat.backlog for seat in retailer] == [2, 4, 6, 8, 10, 12]
    assert all(seat.inventory > 0 for seat in retailer)
    assert conservation(settings, states, orders) == ()
    assert states[10].seat(Role.RETAILER).total_cost == Decimal("87.00")
