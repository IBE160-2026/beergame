"""The bookkeeping check (Story 1.5): correct games pass, every altered number is named."""

from decimal import Decimal

import pytest

from app.engine import (
    ROLES,
    DemandRandom,
    DemandStep,
    GameSettings,
    Role,
    SeatState,
    Violation,
    WeekState,
    advance,
    initial_state,
)
from app.engine.check import conservation, starting_units

CLASSIC = GameSettings()
FOURS = {role: 4 for role in ROLES}


def play(settings, orders):
    states = [initial_state(settings)]
    for placed in orders:
        states.append(advance(settings, states[-1], placed))
    return states


def classic_game():
    orders = [FOURS] * CLASSIC.weeks
    return play(CLASSIC, orders), orders


def with_seat(states, s, role, **update):
    """A copy of `states` where one Seat of state `s` has the given fields changed."""
    state = states[s]
    seats = tuple(
        seat.model_copy(update=update) if seat.role == role else seat for seat in state.seats
    )
    changed = list(states)
    changed[s] = state.model_copy(update={"seats": seats})
    return changed


def rules(violations):
    return {(v.rule, v.week, v.role) for v in violations}


def test_classic_game_keeps_its_books():
    states, orders = classic_game()
    assert len(states) == 37 and states[-1].finished
    assert conservation(CLASSIC, states, orders) == ()


def test_classic_chain_starts_with_80_units():
    first = initial_state(CLASSIC)
    assert starting_units(CLASSIC) == 80
    on_hand_and_in_transit = sum(s.inventory + sum(s.goods_slots) for s in first.seats)
    entered = first.seat(Role.FACTORY).goods_slots[-1]
    delivered = first.seat(Role.RETAILER).shipped
    assert on_hand_and_in_transit - entered + delivered == 80


def test_a_game_in_progress_keeps_its_books():
    states, orders = classic_game()
    assert conservation(CLASSIC, states[:10], orders[:9]) == ()
    assert conservation(CLASSIC, states[:1], []) == ()


def test_units_left_in_slots_at_the_end_are_counted_and_carry_no_cost():
    states, orders = classic_game()
    end = states[-1]
    in_slots = sum(sum(seat.goods_slots) for seat in end.seats)
    assert in_slots > 0
    assert conservation(CLASSIC, states, orders) == ()
    retailer = end.seat(Role.RETAILER)
    slot_cost = CLASSIC.holding_cost * sum(retailer.goods_slots)
    found = conservation(
        CLASSIC,
        with_seat(states, 36, Role.RETAILER, total_cost=retailer.total_cost + slot_cost),
        orders,
    )
    assert rules(found) == {
        ("total_cost", 36, Role.RETAILER),
        ("chain_total_cost", 36, None),
    }


def test_one_unit_altered_names_the_rule_week_and_role():
    states, orders = classic_game()
    seat = states[6].seat(Role.WHOLESALER)
    found = conservation(
        CLASSIC, with_seat(states, 6, Role.WHOLESALER, inventory=seat.inventory + 1), orders
    )
    assert ("inventory_balance", 7, Role.WHOLESALER) in rules(found)
    assert ("units_conserved", 7, None) in rules(found)
    (first,) = [v for v in found if v.rule == "inventory_balance" and v.week == 7]
    assert (first.expected, first.actual) == (str(seat.inventory), str(seat.inventory + 1))
    assert "inventory" in first.message


def test_one_cost_altered():
    states, orders = classic_game()
    seat = states[2].seat(Role.FACTORY)
    found = conservation(
        CLASSIC, with_seat(states, 2, Role.FACTORY, cost=seat.cost + Decimal("0.50")), orders
    )
    assert ("cost", 3, Role.FACTORY) in rules(found)


@pytest.mark.parametrize(
    ("s", "role", "field", "delta", "rule"),
    [
        (4, Role.RETAILER, "backlog", 1, "backlog_balance"),
        (4, Role.DISTRIBUTOR, "shipped", 1, "inventory_balance"),
        (4, Role.DISTRIBUTOR, "shipped", -1, "shipment"),
        (4, Role.WHOLESALER, "incoming_delivery", -1, "in_transit"),
        (0, Role.RETAILER, "incoming_order", 1, "incoming_order"),
        (8, Role.FACTORY, "incoming_order", 1, "incoming_order"),
        (9, Role.WHOLESALER, "total_cost", 1, "total_cost"),
        (0, Role.WHOLESALER, "total_cost", 1, "total_cost"),
        (0, Role.DISTRIBUTOR, "inventory", 1, "inventory_balance"),
        (0, Role.RETAILER, "backlog", 1, "backlog_balance"),
        (0, Role.FACTORY, "incoming_delivery", 1, "in_transit"),
        (0, Role.WHOLESALER, "shipped", 1, "shipment"),
        (36, Role.FACTORY, "shipped", 1, "inventory_balance"),
        (36, Role.FACTORY, "incoming_delivery", 1, "in_transit"),
        (36, Role.RETAILER, "incoming_order", 1, "incoming_order"),
        (36, Role.DISTRIBUTOR, "backlog", 1, "backlog_balance"),
        (36, Role.DISTRIBUTOR, "cost", 1, "cost"),
        (36, Role.WHOLESALER, "inventory", 1, "inventory_balance"),
    ],
)
def test_each_altered_number_is_named(s, role, field, delta, rule):
    states, orders = classic_game()
    value = getattr(states[s].seat(role), field)
    found = conservation(CLASSIC, with_seat(states, s, role, **{field: value + delta}), orders)
    assert (rule, states[s].week, role) in rules(found)


@pytest.mark.parametrize(
    ("s", "role", "field", "rule"),
    [
        (3, Role.RETAILER, "goods_slots", "in_transit"),
        (3, Role.FACTORY, "goods_slots", "in_transit"),
        (36, Role.WHOLESALER, "goods_slots", "in_transit"),
        (5, Role.DISTRIBUTOR, "incoming_orders", "order_slots"),
        (36, Role.WHOLESALER, "incoming_orders", "order_slots"),
        (5, Role.FACTORY, "production_orders", "order_slots"),
    ],
)
def test_each_altered_slot_is_named(s, role, field, rule):
    states, orders = classic_game()
    slots = getattr(states[s].seat(role), field)
    altered = (slots[0] + 1,) + slots[1:]
    found = conservation(CLASSIC, with_seat(states, s, role, **{field: altered}), orders)
    assert (rule, states[s].week, role) in rules(found)


def test_an_altered_order_is_seen_in_the_slots():
    states, orders = classic_game()
    changed = list(orders)
    changed[3] = FOURS | {Role.FACTORY: 5}
    found = conservation(CLASSIC, states, changed)
    assert ("order_slots", 5, Role.FACTORY) in rules(found)
    assert ("units_conserved", 6, None) in rules(found)
    assert ("in_transit", 6, Role.FACTORY) in rules(found)


def test_inventory_and_backlog_both_positive():
    states, orders = classic_game()
    states, orders = states[:5], orders[:4]
    seat = states[4].seat(Role.RETAILER)
    assert seat.inventory > 0 and seat.backlog == 0
    found = conservation(
        CLASSIC,
        with_seat(
            states,
            4,
            Role.RETAILER,
            shipped=seat.shipped - 1,
            inventory=seat.inventory + 1,
            backlog=1,
            cost=seat.cost + CLASSIC.holding_cost + CLASSIC.backorder_cost,
        ),
        orders,
    )
    assert rules(found) == {
        ("shipment", 5, Role.RETAILER),
        ("inventory_and_backlog", 5, Role.RETAILER),
    }
    (both,) = [v for v in found if v.rule == "inventory_and_backlog"]
    assert both == (
        Violation(
            rule="inventory_and_backlog",
            week=5,
            role=Role.RETAILER,
            actual=f"inventory {seat.inventory + 1}, backlog 1",
            message="an uncapped Seat holds inventory and backlog at once",
        )
    )


def test_shipping_more_than_on_hand_is_caught_even_when_the_books_balance():
    states, orders = classic_game()
    states, orders = states[:2], orders[:1]
    seat = states[1].seat(Role.RETAILER)
    shipped, inventory, backlog = seat.shipped + 20, seat.inventory - 20, seat.backlog - 20
    found = conservation(
        CLASSIC,
        with_seat(
            states,
            1,
            Role.RETAILER,
            shipped=shipped,
            inventory=inventory,
            backlog=backlog,
            cost=CLASSIC.holding_cost * inventory + CLASSIC.backorder_cost * backlog,
        ),
        orders,
    )
    assert rules(found) == {("shipment", 2, Role.RETAILER)}
    assert (found[0].expected, found[0].actual) == (str(seat.shipped), str(shipped))


@pytest.mark.parametrize(
    "settings",
    [
        GameSettings(
            order_delay=1,
            shipping_delay=1,
            production_delay=1,
            starting_inventory=0,
            starting_backlog=5,
        ),
        GameSettings(
            order_delay=3,
            shipping_delay=3,
            production_delay=3,
            starting_inventory=0,
            starting_backlog=7,
        ),
        GameSettings(roles=(Role.RETAILER,), weeks=12),
        GameSettings(
            demand=DemandRandom(kind="random", mean=6, spread=4),
            demand_seed=42,
            supply_line=0,
            weeks=20,
        ),
    ],
)
def test_other_chains_keep_their_books(settings):
    orders = [
        {role: (week * 7 + i * 3) % 13 for i, role in enumerate(settings.roles)}
        for week in range(settings.weeks)
    ]
    states = play(settings, orders)
    assert conservation(settings, states, orders) == ()


def test_orders_keyed_by_role_name_or_role():
    states, orders = classic_game()
    named = [{role.value: value for role, value in placed.items()} for placed in orders]
    assert conservation(CLASSIC, states, named) == ()


# Malformed data: shape violations only, never an exception.


def shape(found):
    return [(v.rule, v.week, v.role) for v in found]


def test_no_states():
    assert shape(conservation(CLASSIC, [], [])) == [("states_shape", None, None)]


def test_an_item_that_is_not_a_week_state():
    states, orders = classic_game()
    found = conservation(CLASSIC, states[:2] + [None], orders[:2])
    assert shape(found) == [("states_shape", None, None)]
    assert "NoneType" in found[0].message


@pytest.mark.parametrize(
    ("s", "update"),
    [
        (2, {"week": 5}),
        (2, {"week": "3"}),
        (2, {"finished": "no"}),
        (2, {"finished": True}),
        (36, {"finished": False}),
        (36, {"week": 35}),
    ],
)
def test_weeks_out_of_sequence(s, update):
    states, orders = classic_game()
    states[s] = states[s].model_copy(update=update)
    found = conservation(CLASSIC, states, orders)
    assert [v.rule for v in found] == ["week_sequence"]


def test_a_week_beyond_the_game():
    settings = GameSettings(weeks=3)
    orders = [FOURS] * 3
    states = play(settings, orders)
    extra = states[2].model_copy(update={"week": 4})
    found = conservation(settings, states[:3] + [extra], orders)
    assert [v.rule for v in found] == ["week_sequence"]


def test_a_finished_state_first():
    settings = GameSettings(weeks=1)
    states = play(settings, [FOURS])
    found = conservation(settings, [states[1]], [])
    assert shape(found) == [("week_sequence", 1, None)]


def test_seats_missing_or_out_of_order():
    states, orders = classic_game()
    broken = list(states)
    broken[1] = states[1].model_copy(update={"seats": states[1].seats[::-1]})
    broken[2] = states[2].model_copy(update={"seats": states[2].seats[:3]})
    broken[3] = WeekState.model_construct(week=4, finished=False)
    broken[4] = states[4].model_copy(update={"seats": (None,) + states[4].seats[1:]})
    found = shape(conservation(CLASSIC, broken, orders))
    assert found == [
        ("seat_shape", 2, Role.RETAILER),
        ("seat_shape", 2, Role.WHOLESALER),
        ("seat_shape", 2, Role.DISTRIBUTOR),
        ("seat_shape", 2, Role.FACTORY),
        ("seat_shape", 3, None),
        ("seat_shape", 4, None),
        ("seat_shape", 5, Role.RETAILER),
    ]


@pytest.mark.parametrize(
    "update",
    [
        {"inventory": "x"},
        {"backlog": None},
        {"shipped": True},
        {"cost": Decimal("NaN")},
        {"total_cost": 6.0},
        {"goods_slots": (4,)},
        {"goods_slots": [4, 4]},
        {"goods_slots": (4, "4")},
        {"incoming_orders": (4, 4)},
    ],
)
def test_seat_fields_of_the_wrong_kind(update):
    states, orders = classic_game()
    found = conservation(CLASSIC, with_seat(states, 1, Role.RETAILER, **update), orders)
    assert shape(found) == [("seat_shape", 2, Role.RETAILER)]


def test_a_seat_with_no_fields():
    states, orders = classic_game()
    seats = (SeatState.model_construct(role=Role.RETAILER),) + states[1].seats[1:]
    broken = list(states)
    broken[1] = states[1].model_copy(update={"seats": seats})
    found = conservation(CLASSIC, broken, orders)
    assert len(found) == 10
    assert {(v.rule, v.week, v.role) for v in found} == {("seat_shape", 2, Role.RETAILER)}


def test_a_week_state_with_no_fields():
    found = conservation(CLASSIC, [WeekState.model_construct()], [])
    assert shape(found) == [("week_sequence", None, None), ("seat_shape", None, None)]


@pytest.mark.parametrize(
    ("orders", "expected"),
    [
        ([FOURS] * 2, [("orders_shape", None, None)]),
        ([FOURS, None, FOURS], [("orders_shape", 2, None)]),
        ([FOURS, FOURS | {"brewer": 4}, FOURS], [("orders_shape", 2, None)]),
        (
            [FOURS, {Role.RETAILER: 4, Role.WHOLESALER: 4, Role.DISTRIBUTOR: 4}, FOURS],
            [("orders_shape", 2, Role.FACTORY)],
        ),
        ([FOURS, FOURS | {Role.RETAILER: "4"}, FOURS], [("orders_shape", 2, Role.RETAILER)]),
        ([FOURS, FOURS | {Role.RETAILER: 4.0}, FOURS], [("orders_shape", 2, Role.RETAILER)]),
        ([FOURS, FOURS | {Role.FACTORY: -1}, FOURS], [("orders_shape", 2, Role.FACTORY)]),
        ([FOURS, FOURS | {Role.FACTORY: 1000}, FOURS], [("orders_shape", 2, Role.FACTORY)]),
    ],
)
def test_bad_orders(orders, expected):
    states, _ = classic_game()
    assert shape(conservation(CLASSIC, states[:4], orders)) == expected


def test_a_demand_series_that_cannot_be_built():
    settings = GameSettings(demand=DemandRandom(kind="random", mean=4, spread=2), demand_seed=1)
    states = play(settings, [FOURS] * 3)
    unseeded = settings.model_copy(update={"demand_seed": None})
    found = conservation(unseeded, states, [FOURS] * 3)
    assert shape(found) == [("demand_series", None, None)]
    assert "seed" in found[0].message


def test_the_check_reads_but_never_changes_its_input():
    states, orders = classic_game()
    before = [state.model_dump() for state in states], [dict(placed) for placed in orders]
    conservation(CLASSIC, states, orders)
    assert ([state.model_dump() for state in states], [dict(p) for p in orders]) == before


def test_a_violation_is_a_frozen_value():
    violation = Violation(rule="cost", week=1, role=Role.RETAILER, message="x")
    assert violation.model_dump(mode="json") == {
        "rule": "cost",
        "week": 1,
        "role": "retailer",
        "expected": None,
        "actual": None,
        "message": "x",
    }
    with pytest.raises(ValueError):
        violation.week = 2


def test_constant_demand_keeps_every_seat_at_12():
    flat = GameSettings(demand=DemandStep(kind="step", start=4, new_level=4, change_week=5))
    orders = [FOURS] * flat.weeks
    states = play(flat, orders)
    assert conservation(flat, states, orders) == ()
    assert all(seat.inventory == 12 for state in states for seat in state.seats)
