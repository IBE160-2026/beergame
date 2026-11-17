"""The Rule-based player (FR-33): anchoring and adjustment on the Seat's own numbers."""

import json
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.engine import (
    GameSettings,
    NeighbourNumber,
    Role,
    RuleBasedParams,
    SeatView,
    advance,
    guided_order,
    initial_state,
    seat_view,
)
from app.engine.demand import DemandStep
from app.engine.rule_based import expected_incoming_order, lead_weeks, order, parse_params

BACKEND = Path(__file__).parents[2]
PLACEHOLDER = BACKEND / "app" / "parameter_sets" / "rule_based" / "placeholder-unverified.json"
GOLDEN = Path(__file__).parent / "golden" / "rule-based-classic-step.json"
CLASSIC = GameSettings()


def shipped_params():
    return parse_params(PLACEHOLDER.read_text(encoding="utf-8"), "placeholder-unverified")


def params(**changes):
    data = {
        "id": "test",
        "version": 1,
        "verified": False,
        "source": "test values",
        "theta": Decimal("0.5"),
        "alpha_s": Decimal("0.5"),
        "beta": Decimal("0.5"),
        "desired_inventory": 12,
    }
    return RuleBasedParams(**(data | changes))


def view(**changes):
    data = {
        "role": Role.WHOLESALER,
        "inventory": 12,
        "backlog": 0,
        "incoming_orders": (4,),
        "supply_line": 12,
        "order_history": (),
    }
    return SeatView(**(data | changes))


def play_rule_based(settings, rule_params, weeks_with_guidance=True):
    """Play the Game with every Seat on the rule; Guided Weeks order the starting demand."""
    state = initial_state(settings)
    states, placed = [], []
    while not state.finished:
        states.append(state)
        if weeks_with_guidance and state.week <= settings.guided_weeks:
            orders = {role.value: guided_order(settings) for role in settings.roles}
        else:
            orders = {
                role.value: order(settings, seat_view(settings, states, placed, role), rule_params)
                for role in settings.roles
            }
        placed.append(orders)
        state = advance(settings, state, orders)
    return placed, state


def test_shipped_set_is_the_labelled_placeholder():
    shipped = shipped_params()
    assert shipped.id == "placeholder-unverified"
    assert shipped.verified is False
    assert "placeholder" in shipped.source
    assert "#8" in shipped.source and "#17" in shipped.source


@pytest.mark.parametrize("role", CLASSIC.roles)
def test_classic_week_1_is_in_balance(role):
    rule_view = seat_view(CLASSIC, [initial_state(CLASSIC)], [], role)
    assert order(CLASSIC, rule_view, shipped_params()) == 4


def test_constant_demand_keeps_every_order_at_4():
    settings = GameSettings(demand=DemandStep(kind="step", start=4, new_level=4, change_week=5))
    placed, final = play_rule_based(settings, shipped_params(), weeks_with_guidance=False)
    assert len(placed) == 36
    assert all(value == 4 for orders in placed for value in orders.values())
    assert all(seat.inventory == 12 and seat.backlog == 0 for seat in final.seats)


def test_classic_step_matches_the_stored_golden_trace():
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    shipped = shipped_params()
    # A change to the shipped set must be made visible in the golden file too.
    assert shipped.model_dump(mode="json") == golden["params"]
    settings = GameSettings.model_validate(golden["settings"])
    placed, final = play_rule_based(settings, shipped)
    assert placed == golden["orders"]
    assert {seat.role.value: str(seat.total_cost) for seat in final.seats} == golden["total_cost"]
    assert placed[4] != placed[3]  # the rule reacts to the step


def test_neighbour_numbers_do_not_change_the_order():
    seen = view(incoming_orders=(4, 8, 8), order_history=(4, 6), inventory=3, supply_line=10)
    neighbours = (
        NeighbourNumber(role=Role.DISTRIBUTOR, week=3, quantity="inventory", value=0),
        NeighbourNumber(role=Role.RETAILER, week=3, quantity="backlog", value=90),
    )
    other = (NeighbourNumber(role=Role.DISTRIBUTOR, week=3, quantity="inventory", value=500),)
    base = order(CLASSIC, seen, params())
    assert order(CLASSIC, seen.model_copy(update={"neighbour_numbers": neighbours}), params()) == (
        base
    )
    assert order(CLASSIC, seen.model_copy(update={"neighbour_numbers": other}), params()) == base


def test_worked_example_after_the_step():
    # E = 0.5*8 + 0.5*4 = 6; S = 8; SL* = 6*3 = 18; O* = 6 + 0.5*((12-8) + 0.5*(18-12)) = 9.5
    seen = view(role=Role.RETAILER, incoming_orders=(4, 8), order_history=(4,), inventory=8)
    assert order(CLASSIC, seen, params()) == 10


def test_half_rounds_up_and_below_half_rounds_down():
    # O* = 4 + 0.5*(1 + 0) = 4.5 -> 5; O* = 4 + 0.25*1 = 4.25 -> 4
    assert order(CLASSIC, view(inventory=11), params()) == 5
    assert order(CLASSIC, view(inventory=11), params(alpha_s=Decimal("0.25"))) == 4


def test_big_shortfall_is_capped_at_the_maximum_order():
    shortfall = view(inventory=0, backlog=5000, supply_line=0)
    assert order(CLASSIC, shortfall, params()) == CLASSIC.max_order
    assert order(GameSettings(max_order=20), shortfall, params()) == 20


def test_big_surplus_orders_nothing():
    assert order(CLASSIC, view(inventory=500), params()) == 0


def test_each_parameter_moves_the_order_the_documented_way():
    short = view(inventory=4, supply_line=8, incoming_orders=(4, 8), order_history=(4,))
    low, high = Decimal("0.2"), Decimal("0.8")
    # more weight on the newest (higher) incoming order -> higher expectation -> larger Order
    assert order(CLASSIC, short, params(theta=high)) > order(CLASSIC, short, params(theta=low))
    # a stock and supply-line shortfall: correcting more of it orders more
    assert order(CLASSIC, short, params(alpha_s=high)) > order(CLASSIC, short, params(alpha_s=low))
    # supply line below desired: weighing it more orders more
    assert order(CLASSIC, short, params(beta=high)) > order(CLASSIC, short, params(beta=low))
    # a higher stock target orders more
    assert order(CLASSIC, short, params(desired_inventory=20)) > order(CLASSIC, short, params())


def test_beta_zero_ignores_the_supply_line():
    rule_params = params(beta=Decimal(0))
    assert order(CLASSIC, view(supply_line=0), rule_params) == order(
        CLASSIC, view(supply_line=90), rule_params
    )


def test_the_rule_uses_the_delays_in_force():
    slow = GameSettings(order_delay=3, shipping_delay=3, production_delay=1)
    assert lead_weeks(CLASSIC, view()) == 3
    assert lead_weeks(slow, view(role=Role.WHOLESALER)) == 5
    assert lead_weeks(slow, view(role=Role.FACTORY)) == 3
    # the same Seat wants a longer supply line under longer delays
    assert order(slow, view(), params()) > order(CLASSIC, view(), params())


def test_expected_incoming_order_smooths_from_the_first():
    assert expected_incoming_order((4,), Decimal("0.5")) == 4
    assert expected_incoming_order((4, 8, 8), Decimal("0.5")) == 7
    assert expected_incoming_order((4, 8, 8), Decimal(1)) == 8
    assert expected_incoming_order((4, 8, 8), Decimal(0)) == 4


def test_role_not_in_the_game_raises():
    settings = GameSettings(roles=(Role.RETAILER, Role.FACTORY))
    with pytest.raises(ValueError, match="not a Role"):
        order(settings, view(role=Role.WHOLESALER), params())


def test_the_order_is_a_plain_int():
    assert type(order(CLASSIC, view(), params())) is int


@pytest.mark.parametrize(
    "changes",
    [
        {"theta": Decimal("1.01")},
        {"alpha_s": Decimal("-0.1")},
        {"beta": Decimal("NaN")},
        {"desired_inventory": -1},
        {"version": 0},
        {"source": ""},
        {"id": "../escape"},
        {"id": "Upper"},
        {"extra": 1},
    ],
)
def test_bad_params_are_rejected(changes):
    with pytest.raises(ValidationError):
        params(**changes)


def test_parse_params_reads_json_and_checks_the_id():
    text = params(id="my-set").model_dump_json()
    assert parse_params(text, "my-set").id == "my-set"
    with pytest.raises(ValueError, match="holds set"):
        parse_params(text, "other-set")
    with pytest.raises(ValidationError):
        parse_params('{"id": "my-set"}', "my-set")
