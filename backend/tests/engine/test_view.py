from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.engine import (
    CostLine,
    GameSettings,
    NeighbourNumber,
    OrderPreview,
    Role,
    SeatView,
    SupplyLineSlot,
    advance,
    initial_state,
    neighbour_numbers,
    placed_orders,
    seat_detail,
    seat_view,
)
from app.engine.demand import DemandStep
from app.engine.view import starting_supply_line


def play(settings, weeks, policy):
    """Opened states 1..weeks and the Order maps of Weeks 1..weeks-1."""
    states = [initial_state(settings)]
    orders = []
    while len(states) < weeks:
        placed = policy(states[-1])
        orders.append(placed)
        states.append(advance(settings, states[-1], placed))
    return states, orders


def pass_through(state):
    return {seat.role: seat.incoming_order for seat in state.seats}


def independent_supply_line(settings, states, role):
    """Units ordered and not received, counted from the pipelines: Orders still in the upstream
    Seat's order slots (or the Factory's production slots) after this Week's one was received,
    the upstream Seat's backlog, and the goods in transit to this Seat."""
    state = states[-1]
    index = settings.roles.index(role)
    seat = state.seat(role)
    if index == len(settings.roles) - 1:
        return sum(seat.production_orders[1:]) + sum(seat.goods_slots)
    upstream = state.seats[index + 1]
    return sum(upstream.incoming_orders[1:]) + upstream.backlog + sum(seat.goods_slots)


def test_week_1_classic_view():
    settings = GameSettings()
    view = seat_view(settings, [initial_state(settings)], [], Role.WHOLESALER)
    assert view == SeatView(
        role=Role.WHOLESALER,
        inventory=12,
        backlog=0,
        incoming_orders=(4,),
        supply_line=12,
        order_history=(),
    )
    assert view.neighbour_numbers == ()


@pytest.mark.parametrize(
    ("delays", "starting_inventory", "starting_backlog"),
    [
        ((2, 2, 2), 12, 0),
        ((1, 1, 1), 12, 0),
        ((3, 3, 3), 12, 0),
        ((1, 3, 2), 12, 0),
        ((3, 1, 3), 12, 0),
        ((2, 2, 2), 0, 20),
        ((1, 3, 2), 0, 7),
    ],
)
def test_supply_line_is_ordered_minus_received_in_a_stepped_game(
    delays, starting_inventory, starting_backlog
):
    order_delay, shipping_delay, production_delay = delays
    settings = GameSettings(
        order_delay=order_delay,
        shipping_delay=shipping_delay,
        production_delay=production_delay,
        starting_inventory=starting_inventory,
        starting_backlog=starting_backlog,
        demand=DemandStep(kind="step", start=4, new_level=9, change_week=3),
    )
    states, orders = play(settings, 20, pass_through)
    for week in range(1, 21):
        for role in settings.roles:
            view = seat_view(settings, states[:week], orders[: week - 1], role)
            assert view.supply_line == independent_supply_line(settings, states[:week], role)
            assert len(view.incoming_orders) == week
            assert view.order_history == tuple(o[role] for o in orders[: week - 1])


def test_view_takes_string_roles_and_role_keys():
    settings = GameSettings()
    states, orders = play(settings, 3, pass_through)  # Order maps keyed by Role
    assert all(isinstance(key, Role) for key in orders[0])
    by_role = seat_view(settings, states, orders, "factory")
    as_text = [{str(role): value for role, value in o.items()} for o in orders]
    assert seat_view(settings, states, as_text, Role.FACTORY) == by_role
    assert by_role.role is Role.FACTORY
    assert by_role.order_history == tuple(o[Role.FACTORY] for o in orders)


def test_starting_supply_line_per_role():
    settings = GameSettings(order_delay=1, shipping_delay=2, production_delay=3, supply_line=5)
    assert starting_supply_line(settings, Role.RETAILER) == 5 * (1 + 2)
    assert starting_supply_line(settings, Role.FACTORY) == 5 * (1 + 3)


def test_starting_backlog_is_owed_to_every_role_but_the_last():
    settings = GameSettings(starting_inventory=0, starting_backlog=20)
    assert starting_supply_line(settings, Role.WHOLESALER) == 4 * 4 + 20
    assert starting_supply_line(settings, Role.FACTORY) == 4 * 4


def test_view_of_a_role_not_in_the_game_raises():
    settings = GameSettings(roles=(Role.RETAILER, Role.FACTORY))
    with pytest.raises(ValueError, match="not a Role"):
        seat_view(settings, [initial_state(settings)], [], Role.WHOLESALER)


def test_view_needs_an_opened_week():
    with pytest.raises(ValueError, match="at least one"):
        seat_view(GameSettings(), [], [], Role.RETAILER)


def test_view_needs_one_order_map_per_earlier_week():
    settings = GameSettings()
    states, orders = play(settings, 3, pass_through)
    with pytest.raises(ValueError, match="one Order map"):
        seat_view(settings, states, orders[:1], Role.RETAILER)


def test_view_rejects_states_out_of_sequence_or_finished():
    settings = GameSettings(weeks=2)
    states, orders = play(settings, 2, pass_through)
    with pytest.raises(ValueError, match="item 1"):
        seat_view(settings, [states[0], states[0]], orders, Role.RETAILER)
    finished = advance(settings, states[1], pass_through(states[1]))
    with pytest.raises(ValueError, match="item 1"):
        seat_view(settings, [states[0], finished], orders, Role.RETAILER)


def view(**changes):
    data = {
        "role": Role.RETAILER,
        "inventory": 12,
        "backlog": 0,
        "incoming_orders": (4,),
        "supply_line": 12,
        "order_history": (),
    }
    return SeatView(**(data | changes))


@pytest.mark.parametrize(
    "changes",
    [
        {"incoming_orders": ()},
        {"order_history": (4,)},
        {"incoming_orders": (4, 4), "order_history": ()},
        {"inventory": -1},
        {"backlog": -1},
        {"supply_line": -1},
        {"incoming_orders": (-1,)},
        {"inventory": 1.5},
        {"inventory": "12"},
        {"name": "Kari"},
    ],
)
def test_bad_views_are_rejected(changes):
    with pytest.raises(ValidationError):
        view(**changes)


def test_neighbour_numbers_are_labelled_numbers():
    number = NeighbourNumber(role=Role.WHOLESALER, week=3, quantity="inventory", value=7)
    assert view(neighbour_numbers=(number,)).neighbour_numbers == (number,)
    with pytest.raises(ValidationError):
        NeighbourNumber(role=Role.WHOLESALER, week=0, quantity="inventory", value=7)
    with pytest.raises(ValidationError):
        NeighbourNumber(role=Role.WHOLESALER, week=1, quantity="name", value=7)


def test_view_is_frozen():
    with pytest.raises(ValidationError):
        view().inventory = 3


# --- seat_detail and placed_orders (Story 1.8) ---------------------------------------------


def stepped(state):
    """Orders that differ by Role and Week, so a mixed-up history shows."""
    return {seat.role: seat.incoming_order + index for index, seat in enumerate(state.seats)}


def test_week_1_classic_detail_of_the_retailer():
    settings = GameSettings()
    detail = seat_detail(settings, [initial_state(settings)], [], Role.RETAILER)
    assert detail.week == 1
    assert (detail.incoming_order, detail.incoming_delivery, detail.shipped) == (4, 4, 4)
    assert detail.supply_line_slots == (
        SupplyLineSlot(stage="in_transit", quantity=4, arrival_week=2),
        SupplyLineSlot(stage="in_transit", quantity=4, arrival_week=3),
        SupplyLineSlot(stage="ordered", quantity=4, arrival_week=4),
    )
    assert detail.overdue == 0
    assert detail.position == 12 - 0 + 12
    assert detail.cost_lines == (
        CostLine(kind="holding", units=12, rate=Decimal("0.50"), amount=Decimal("6.00")),
        CostLine(kind="backorder", units=0, rate=Decimal("1.00"), amount=Decimal("0.00")),
    )
    assert detail.week_cost == detail.total_cost == Decimal("6.00")
    assert detail.history == ()
    assert (detail.min_order, detail.max_order) == (0, 999)
    assert detail.preview == OrderPreview(
        order_arrival_week=5, supply_line_base=12, position_base=24
    )


def test_week_1_classic_detail_of_the_factory_is_in_production():
    settings = GameSettings()
    detail = seat_detail(settings, [initial_state(settings)], [], "factory")
    assert [slot.stage for slot in detail.supply_line_slots] == [
        "in_production",
        "in_production",
        "ordered",
    ]
    assert [slot.arrival_week for slot in detail.supply_line_slots] == [2, 3, 4]
    assert detail.overdue == 0


@pytest.mark.parametrize(
    ("delays", "starting_inventory", "starting_backlog"),
    [
        ((2, 2, 2), 12, 0),
        ((1, 1, 1), 12, 0),
        ((3, 3, 3), 12, 0),
        ((1, 3, 2), 12, 0),
        ((3, 1, 3), 12, 0),
        ((2, 2, 2), 0, 20),
    ],
)
def test_detail_agrees_with_the_pipelines_in_every_week(
    delays, starting_inventory, starting_backlog
):
    order_delay, shipping_delay, production_delay = delays
    settings = GameSettings(
        order_delay=order_delay,
        shipping_delay=shipping_delay,
        production_delay=production_delay,
        starting_inventory=starting_inventory,
        starting_backlog=starting_backlog,
        demand=DemandStep(kind="step", start=4, new_level=9, change_week=3),
    )
    states, orders = play(settings, 16, stepped)
    last = settings.roles[-1]
    for week in range(1, 17):
        for index, role in enumerate(settings.roles):
            view = seat_view(settings, states[:week], orders[: week - 1], role)
            detail = seat_detail(settings, states[:week], orders[: week - 1], role)
            seat = states[week - 1].seat(role)
            assert detail.week == week
            slots = detail.supply_line_slots
            assert sum(slot.quantity for slot in slots) + detail.overdue == view.supply_line
            arrivals = [slot.arrival_week for slot in slots]
            assert arrivals == sorted(arrivals) and min(arrivals, default=week + 1) > week
            upstream_backlog = 0 if role == last else states[week - 1].seats[index + 1].backlog
            assert detail.overdue == upstream_backlog
            assert detail.net_inventory == seat.inventory - seat.backlog
            assert detail.position == detail.net_inventory + view.supply_line
            assert detail.preview.supply_line_base == view.supply_line
            assert detail.preview.position_base == detail.position
            goods = production_delay if role == last else shipping_delay
            assert detail.preview.order_arrival_week == week + order_delay + goods
            assert detail.total_cost == seat.total_cost + seat.cost
            assert sum(line.amount for line in detail.cost_lines) == detail.week_cost
            # «Kostnad så langt» (Story 6.16): the running split adds up to the Total cost.
            holding, backorder = (line.amount for line in detail.cost_lines)
            assert detail.total_holding_cost == (
                sum(r.holding_cost for r in detail.history) + holding
            )
            assert detail.total_backorder_cost == (
                sum(r.backorder_cost for r in detail.history) + backorder
            )
            assert detail.total_holding_cost + detail.total_backorder_cost == detail.total_cost
            # Alle rader's column line: the Netto lager to the left, plus Levering, minus Ordre inn.
            if detail.history:
                assert detail.net_inventory == (
                    detail.history[-1].net_inventory
                    + detail.incoming_delivery
                    - detail.incoming_order
                )
            assert [row.order for row in detail.history] == list(view.order_history)
            assert [row.week for row in detail.history] == list(range(1, week))
            for row, earlier in zip(detail.history, states[: week - 1], strict=True):
                assert row.inventory == earlier.seat(role).inventory
                assert row.net_inventory == row.inventory - row.backlog
                assert row.cost == earlier.seat(role).cost
                assert row.holding_cost == settings.holding_cost * row.inventory
                assert row.backorder_cost == settings.backorder_cost * row.backlog
                assert row.holding_cost + row.backorder_cost == row.cost
                assert row.total_cost == earlier.seat(role).total_cost + row.cost
                assert row.total_holding_cost + row.total_backorder_cost == row.total_cost
                past = seat_detail(settings, states[: row.week], orders[: row.week - 1], role)
                assert (row.supply_line, row.position) == (
                    past.preview.supply_line_base,
                    past.position,
                )


def test_an_order_arrives_in_the_week_the_preview_names():
    settings = GameSettings()
    states, orders = play(settings, 12, stepped)
    for role in settings.roles:
        detail = seat_detail(settings, states[:3], orders[:2], role)
        later = seat_detail(settings, states[:5], orders[:4], role)
        # The Week 3 Order sits in the slots of Week 5 with the arrival Week the preview gave.
        assert any(
            slot.quantity == orders[2][role]
            and slot.arrival_week == detail.preview.order_arrival_week
            for slot in later.supply_line_slots
        )


def test_placed_orders_reads_back_the_orders_given_to_advance():
    for settings in (GameSettings(), GameSettings(order_delay=1, production_delay=3)):
        states, orders = play(settings, 10, stepped)
        assert placed_orders(settings, states) == tuple(orders)
        assert placed_orders(settings, states[:1]) == ()


def test_detail_and_placed_orders_check_their_input():
    settings = GameSettings()
    states, orders = play(settings, 3, stepped)
    with pytest.raises(ValueError, match="one Order map"):
        seat_detail(settings, states, orders[:1], Role.RETAILER)
    with pytest.raises(ValueError, match="at least one"):
        placed_orders(settings, [])
    with pytest.raises(ValueError, match="item 1"):
        placed_orders(settings, [states[0], states[0]])


# Information visibility (Story 6.21, FR-83): the neighbours' inventory and backlog only.


def _uneven(state):
    return {"retailer": 0, "wholesaler": 9, "distributor": 2, "factory": 14}


def _numbers(state, role, week):
    seat = state.seat(role)
    return [
        NeighbourNumber(role=role, week=week, quantity="inventory", value=seat.inventory),
        NeighbourNumber(role=role, week=week, quantity="backlog", value=seat.backlog),
    ]


@pytest.mark.parametrize(
    ("upstream", "downstream", "role", "shown"),
    [
        (False, False, Role.WHOLESALER, []),
        (True, False, Role.WHOLESALER, [Role.DISTRIBUTOR]),
        (False, True, Role.WHOLESALER, [Role.RETAILER]),
        (True, True, Role.WHOLESALER, [Role.DISTRIBUTOR, Role.RETAILER]),
        (True, True, Role.FACTORY, [Role.DISTRIBUTOR]),
        (True, True, Role.RETAILER, [Role.WHOLESALER]),
        (True, False, Role.FACTORY, []),
        (False, True, Role.RETAILER, []),
    ],
)
def test_neighbour_numbers_follow_the_views(upstream, downstream, role, shown):
    settings = GameSettings(info_visibility={"upstream": upstream, "downstream": downstream})
    states, _ = play(settings, 7, _uneven)
    state = states[-1]
    expected = [number for neighbour in shown for number in _numbers(state, neighbour, 7)]
    assert list(neighbour_numbers(settings, state, role.value)) == expected


def test_neighbour_numbers_are_the_neighbours_own_view():
    settings = GameSettings(info_visibility={"upstream": True, "downstream": True})
    states, orders = play(settings, 9, _uneven)
    numbers = neighbour_numbers(settings, states[-1], Role.WHOLESALER)
    for neighbour in (Role.DISTRIBUTOR, Role.RETAILER):
        own = seat_view(settings, states, orders, neighbour)
        found = {n.quantity: n.value for n in numbers if n.role == neighbour}
        assert found == {"inventory": own.inventory, "backlog": own.backlog}
    assert any(n.value > 0 for n in numbers if n.quantity == "backlog")


def test_neighbour_numbers_refuse_an_unknown_role_or_a_finished_week():
    settings = GameSettings(info_visibility={"upstream": True, "downstream": False})
    state = initial_state(settings)
    with pytest.raises(ValueError, match="not a Role"):
        neighbour_numbers(
            settings.model_copy(update={"roles": settings.roles[:2]}), state, "factory"
        )
    finished = state.model_copy(update={"finished": True})
    with pytest.raises(ValueError, match="not an opened Week"):
        neighbour_numbers(settings, finished, Role.RETAILER)
