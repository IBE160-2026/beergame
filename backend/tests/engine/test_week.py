from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.engine import (
    ROLES,
    DemandStep,
    GameFinishedError,
    GameSettings,
    InvalidOrdersError,
    Role,
    advance,
    initial_state,
)

CONSTANT = GameSettings(demand=DemandStep(kind="step", start=4, new_level=4, change_week=5))
FOURS = {role: 4 for role in ROLES}


def units(state):
    return sum(seat.inventory + sum(seat.goods_slots) for seat in state.seats)


def test_classic_open_matches_the_slot_layout():
    state = initial_state(GameSettings())
    assert (state.week, state.finished) == (1, False)
    assert [seat.role for seat in state.seats] == list(ROLES)
    assert sum(seat.inventory for seat in state.seats) == 48
    assert sum(sum(state.seat(r).goods_slots) for r in ROLES[:3]) == 24
    assert sum(state.seat(Role.FACTORY).goods_slots) == 8
    assert units(state) == 80
    assert [len(seat.incoming_orders) for seat in state.seats] == [0, 2, 2, 2]
    assert [len(seat.production_orders) for seat in state.seats] == [0, 0, 0, 2]
    assert all(seat.total_cost == 0 for seat in state.seats)
    assert all(seat.cost == Decimal("6.00") for seat in state.seats)


def test_retailer_incoming_order_is_customer_demand():
    state = initial_state(GameSettings())
    for _ in range(4):
        state = advance(GameSettings(), state, FOURS)
    assert state.week == 5
    assert state.seat(Role.RETAILER).incoming_order == 8
    assert state.seat(Role.WHOLESALER).incoming_order == 4


def test_order_arrives_two_weeks_later_and_shipment_two_weeks_after_that():
    state = initial_state(CONSTANT)
    states = [state]
    orders = [FOURS | {Role.RETAILER: 5}] + [FOURS] * 5
    for week_orders in orders:
        state = advance(CONSTANT, state, week_orders)
        states.append(state)
    wholesaler = [s.seat(Role.WHOLESALER) for s in states]
    retailer = [s.seat(Role.RETAILER) for s in states]
    assert [w.incoming_order for w in wholesaler[:4]] == [4, 4, 5, 4]
    assert [w.shipped for w in wholesaler[:4]] == [4, 4, 5, 4]
    assert [r.incoming_delivery for r in retailer[:6]] == [4, 4, 4, 4, 5, 4]


def test_factory_order_reaches_factory_inventory_after_four_weeks():
    state = initial_state(CONSTANT)
    states = [state]
    orders = [FOURS | {Role.FACTORY: 5}] + [FOURS] * 5
    for week_orders in orders:
        state = advance(CONSTANT, state, week_orders)
        states.append(state)
    factory = [s.seat(Role.FACTORY) for s in states]
    assert [f.production_orders for f in factory[:3]] == [(4, 4), (4, 5), (5, 4)]
    assert [f.goods_slots[-1] for f in factory[:4]] == [4, 4, 5, 4]
    assert [f.incoming_delivery for f in factory[:6]] == [4, 4, 4, 4, 5, 4]
    assert factory[4].inventory == 13


def test_advance_is_pure():
    settings = GameSettings()
    state = initial_state(settings)
    before = state.model_dump()
    nxt = advance(settings, state, FOURS)
    assert state.model_dump() == before
    assert nxt is not state
    assert nxt.week == 2
    with pytest.raises(ValidationError):
        state.week = 3
    with pytest.raises(ValidationError):
        state.seats[0].inventory = 0


def test_last_week_runs_in_full_and_finishes():
    settings = CONSTANT.model_copy(update={"weeks": 2})
    week2 = advance(settings, initial_state(settings), FOURS)
    done = advance(settings, week2, FOURS | {Role.RETAILER: 7, Role.FACTORY: 6})
    assert (done.week, done.finished) == (2, True)
    assert all(seat.total_cost == Decimal("12.00") for seat in done.seats)
    wholesaler, factory = done.seat(Role.WHOLESALER), done.seat(Role.FACTORY)
    assert wholesaler.incoming_orders == (4, 7)
    assert factory.production_orders == (4, 6)
    keep = {"total_cost", "incoming_orders", "production_orders"}
    assert wholesaler.model_dump(exclude=keep) == week2.seat("wholesaler").model_dump(exclude=keep)


def test_advance_on_a_finished_game_raises():
    settings = CONSTANT.model_copy(update={"weeks": 1})
    done = advance(settings, initial_state(settings), FOURS)
    before = done.model_dump()
    with pytest.raises(GameFinishedError) as info:
        advance(settings, done, FOURS)
    assert isinstance(info.value, ValueError)
    assert done.model_dump() == before


@pytest.mark.parametrize(
    ("orders", "role"),
    [
        ({r: 4 for r in ROLES[:3]}, "factory"),
        (FOURS | {"shop": 4}, "shop"),
        (FOURS | {7: 4}, "7"),
        (FOURS | {Role.WHOLESALER: 4.0}, "wholesaler"),
        (FOURS | {Role.WHOLESALER: "4"}, "wholesaler"),
        (FOURS | {Role.DISTRIBUTOR: True}, "distributor"),
        (FOURS | {Role.RETAILER: -1}, "retailer"),
        (FOURS | {Role.FACTORY: 1000}, "factory"),
    ],
)
def test_bad_orders_raise_naming_the_role(orders, role):
    settings = GameSettings()
    state = initial_state(settings)
    before = state.model_dump()
    with pytest.raises(InvalidOrdersError) as info:
        advance(settings, state, orders)
    assert isinstance(info.value, ValueError)
    assert info.value.role == role
    assert str(info.value).startswith(f"{role}: ")
    assert state.model_dump() == before


def test_orders_accept_role_names_as_strings_and_the_max_order():
    settings = GameSettings()
    state = advance(
        settings, initial_state(settings), {"retailer": 999, **{r: 0 for r in ROLES[1:]}}
    )
    assert state.seat(Role.WHOLESALER).incoming_orders == (4, 999)


@pytest.mark.parametrize("delay", [1, 3])
def test_slot_counts_follow_the_delays(delay):
    settings = CONSTANT.model_copy(
        update={"order_delay": delay, "shipping_delay": delay, "production_delay": delay}
    )
    state = initial_state(settings)
    assert [len(seat.incoming_orders) for seat in state.seats] == [0, delay, delay, delay]
    assert [len(seat.goods_slots) for seat in state.seats] == [delay] * 4
    assert len(state.seat(Role.FACTORY).production_orders) == delay
    assert units(state) == 48 + 4 * 4 * delay
    nxt = advance(settings, state, FOURS | {Role.RETAILER: 9})
    assert nxt.seat(Role.WHOLESALER).incoming_orders[-1] == 9


@pytest.mark.parametrize("delay", [1, 3])
def test_starting_backlog_is_carried_into_week_one(delay):
    settings = GameSettings(
        starting_inventory=0,
        starting_backlog=4,
        order_delay=delay,
        shipping_delay=delay,
        production_delay=delay,
    )
    state = initial_state(settings)
    assert [len(seat.incoming_orders) for seat in state.seats] == [0, delay, delay, delay]
    assert [len(seat.goods_slots) for seat in state.seats] == [delay] * 4
    assert len(state.seat(Role.FACTORY).production_orders) == delay
    for seat in state.seats:
        # Amount to ship = incoming order 4 + starting backlog 4; only the delivery of 4 ships.
        assert (seat.incoming_order, seat.incoming_delivery) == (4, 4)
        assert (seat.shipped, seat.inventory, seat.backlog) == (4, 0, 4)
        assert seat.cost == Decimal("4.00")


def test_starting_backlog_ships_in_full_when_stock_allows():
    settings = GameSettings(starting_inventory=0, starting_backlog=2, supply_line=10)
    retailer = initial_state(settings).seat(Role.RETAILER)
    assert (retailer.shipped, retailer.inventory, retailer.backlog) == (6, 4, 0)


def test_order_delay_one_is_received_next_week():
    settings = CONSTANT.model_copy(update={"order_delay": 1})
    nxt = advance(settings, initial_state(settings), FOURS | {Role.RETAILER: 9})
    assert nxt.seat(Role.WHOLESALER).incoming_order == 9


def test_shorter_chain_and_unknown_seat():
    settings = CONSTANT.model_copy(update={"roles": (Role.RETAILER, Role.FACTORY)})
    state = initial_state(settings)
    assert units(state) == 2 * 12 + 2 * 4 + 2 * 4
    assert state.seat(Role.FACTORY).production_orders == (4, 4)
    with pytest.raises(KeyError):
        state.seat(Role.WHOLESALER)
    nxt = advance(settings, state, {"retailer": 4, "factory": 4})
    assert nxt.seat("factory").incoming_order == 4


def test_mixed_delays_size_each_pipeline_and_time_the_factory():
    settings = CONSTANT.model_copy(
        update={"order_delay": 1, "shipping_delay": 2, "production_delay": 3}
    )
    state = initial_state(settings)
    assert [len(seat.incoming_orders) for seat in state.seats] == [0, 1, 1, 1]
    assert [len(seat.goods_slots) for seat in state.seats] == [2, 2, 2, 3]
    assert [len(seat.production_orders) for seat in state.seats] == [0, 0, 0, 1]
    assert units(state) == 48 + 3 * 2 * 4 + 3 * 4
    states = [state]
    orders = [FOURS | {Role.FACTORY: 5, Role.DISTRIBUTOR: 6}] + [FOURS] * 5
    for week_orders in orders:
        state = advance(settings, state, week_orders)
        states.append(state)
    factory = [s.seat(Role.FACTORY) for s in states]
    distributor = [s.seat(Role.DISTRIBUTOR) for s in states]
    # Factory Order in Week 1 enters production in Week 2 (order delay 1), arrives in Week 5.
    assert [f.incoming_delivery for f in factory[:6]] == [4, 4, 4, 4, 5, 4]
    # Distributor Order in Week 1 reaches the Factory in Week 2; its shipment arrives in Week 4.
    assert [f.incoming_order for f in factory[:3]] == [4, 6, 4]
    assert [d.incoming_delivery for d in distributor[:5]] == [4, 4, 4, 6, 4]
