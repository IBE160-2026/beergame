"""Story 2.9: the near-optimal reference Order, a pure function of the whole chain (FR-79, AD-1)."""

import json
from pathlib import Path

import pytest

from app.engine import (
    GameSettings,
    Role,
    advance,
    demand_series,
    guided_order,
    initial_state,
    near_optimal,
    rule_based,
    seat_view,
)
from app.engine.demand import DemandFixed, DemandStep

BACKEND = Path(__file__).parents[2]
PLACEHOLDER = BACKEND / "app" / "parameter_sets" / "rule_based" / "placeholder-unverified.json"
GOLDEN = Path(__file__).parent / "golden" / "near-optimal-classic-step.json"
CLASSIC = GameSettings()
CONSTANT = GameSettings(demand=DemandStep(kind="step", start=4, new_level=4, change_week=5))


def shipped_params() -> rule_based.RuleBasedParams:
    return rule_based.parse_params(
        PLACEHOLDER.read_text(encoding="utf-8"), rule_based.DEFAULT_SET_ID
    )


def play(settings, orders_of=None, guided=True):
    """Play the Game (Rule-based Orders after the Guided Weeks unless `orders_of` chooses) and
    return per Week the opened state with both references of every Role."""
    params = shipped_params()
    series = demand_series(settings)
    state = initial_state(settings)
    states, placed, weeks = [], [], []
    while not state.finished:
        states.append(state)
        refs = {
            role.value: (
                rule_based.order(settings, seat_view(settings, states, placed, role), params),
                near_optimal.order(settings, state, series, state.week, role),
            )
            for role in settings.roles
        }
        weeks.append((state, refs))
        if guided and state.week <= settings.guided_weeks:
            orders = {role.value: guided_order(settings) for role in settings.roles}
        elif orders_of is not None:
            orders = orders_of(state, refs)
        else:
            orders = {role: pair[0] for role, pair in refs.items()}
        placed.append(orders)
        state = advance(settings, state, orders)
    return weeks, placed, states


def test_the_label_is_the_placeholder_and_order_dispatches_through_it():
    assert near_optimal.ALGORITHM_VERSION == "placeholder-0"
    assert near_optimal.ALGORITHM_VERSION in near_optimal.ALGORITHMS


@pytest.mark.parametrize("role", CONSTANT.roles)
def test_classic_week_1_under_constant_demand_orders_4(role):
    state = initial_state(CONSTANT)
    assert near_optimal.order(CONSTANT, state, demand_series(CONSTANT), 1, role) == 4


@pytest.mark.parametrize("role", CLASSIC.roles)
def test_classic_step_week_1_is_the_hand_worked_8(role):
    # cover 4 + 4 + 4 + 8 = 20, position 12 + 12 = 24, target 12: 12 + 20 - 24 = 8.
    state = initial_state(CLASSIC)
    value = near_optimal.order(CLASSIC, state, demand_series(CLASSIC), 1, role.value)
    assert value == 8 and type(value) is int


def test_both_references_coincide_in_every_week_under_constant_demand():
    weeks, placed, _ = play(CONSTANT, guided=False)
    assert len(weeks) == 36
    for state, refs in weeks:
        for role, (rule, near) in refs.items():
            assert rule == near == 4, (state.week, role)
    assert all(value == 4 for orders in placed for value in orders.values())


SUPPLY_LINE_CASES = [
    CLASSIC,
    GameSettings(order_delay=1, shipping_delay=1, production_delay=1, starting_backlog=3),
    GameSettings(order_delay=3, shipping_delay=3, production_delay=2, starting_inventory=2),
    GameSettings(capacity={Role.WHOLESALER: 5}, weeks=20),
    GameSettings(roles=(Role.RETAILER, Role.FACTORY), weeks=12),
    GameSettings(roles=(Role.FACTORY,), weeks=8),
]


@pytest.mark.parametrize("settings", SUPPLY_LINE_CASES)
def test_the_chain_supply_line_equals_the_seats_own_supply_line(settings):
    """Played with alternating near-optimal and wild Orders so pipelines and backlogs move."""

    def orders_of(state, refs):
        return {
            role: (pair[1] if state.week % 2 else (state.week * 7 + i) % 25)
            for i, (role, pair) in enumerate(refs.items())
        }

    _, placed, states = play(settings, orders_of=orders_of, guided=False)
    for week, state in enumerate(states, start=1):
        for role in settings.roles:
            own = seat_view(settings, states[:week], placed[: week - 1], role).supply_line
            assert near_optimal.supply_line(settings, state, role) == own, (week, role)


def test_a_big_shortfall_is_capped_at_the_maximum_order():
    settings = GameSettings(
        max_order=10, demand=DemandStep(kind="step", start=4, new_level=50, change_week=2)
    )
    state = initial_state(settings)
    assert near_optimal.order(settings, state, demand_series(settings), 1, "retailer") == 10


def test_a_big_surplus_orders_nothing():
    settings = GameSettings(
        starting_inventory=90, demand=DemandFixed(kind="fixed", values=[0] * 36)
    )
    state = initial_state(settings)
    # target 90 + cover 0 - position (90 + 12): below zero.
    assert near_optimal.order(settings, state, demand_series(settings), 1, "factory") == 0


def test_weeks_after_the_series_take_its_last_value():
    settings = GameSettings(weeks=2, demand=DemandFixed(kind="fixed", values=[4, 9]))
    weeks, _, _ = play(settings, guided=False)
    state, _ = weeks[-1]
    # Week 2, Retailer: cover is four Weeks past the series, all 9.
    seat = state.seat("retailer")
    position = (
        seat.inventory - seat.backlog + near_optimal.supply_line(settings, state, Role.RETAILER)
    )
    expected = settings.starting_inventory + 4 * 9 - position
    assert near_optimal.order(settings, state, demand_series(settings), 2, "retailer") == expected


def test_bad_calls_are_refused():
    state = initial_state(CLASSIC)
    series = demand_series(CLASSIC)
    two = GameSettings(roles=(Role.RETAILER, Role.FACTORY))
    with pytest.raises(ValueError, match="not a Role in this Game"):
        near_optimal.order(two, initial_state(two), series, 1, "wholesaler")
    with pytest.raises(ValueError, match="not opened Week 2"):
        near_optimal.order(CLASSIC, state, series, 2, "retailer")
    finished = state.model_copy(update={"finished": True})
    with pytest.raises(ValueError, match="not opened Week 1"):
        near_optimal.order(CLASSIC, finished, series, 1, "retailer")
    with pytest.raises(ValueError, match="no Week 1"):
        near_optimal.order(CLASSIC, state, (), 1, "retailer")
    with pytest.raises(ValueError):
        near_optimal.order(CLASSIC, state, series, 1, "nobody")


def golden_record():
    """The Classic step played as `rule-based-classic-step.json` plays it, with both references
    of every Role and Week."""
    weeks, placed, _ = play(CLASSIC)
    return {
        "rule_based": [{role: pair[0] for role, pair in refs.items()} for _, refs in weeks],
        "near_optimal": [{role: pair[1] for role, pair in refs.items()} for _, refs in weeks],
        "orders": placed,
    }


def test_classic_step_matches_the_stored_golden_trace():
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert golden["algorithm_version"] == near_optimal.ALGORITHM_VERSION
    assert golden["rule_based_params"] == shipped_params().id
    assert GameSettings.model_validate(golden["settings"]) == CLASSIC
    record = golden_record()
    assert record["orders"] == golden["orders"]
    assert record["rule_based"] == golden["rule_based"]
    assert record["near_optimal"] == golden["near_optimal"]
    assert record["near_optimal"] != record["rule_based"]  # the step separates them
