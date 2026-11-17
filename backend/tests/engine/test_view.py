import pytest
from pydantic import ValidationError

from app.engine import (
    GameSettings,
    NeighbourNumber,
    Role,
    SeatView,
    advance,
    initial_state,
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
