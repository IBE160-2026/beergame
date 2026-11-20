"""Story 1.8: `games.views.seat_state` is the information boundary (AD-3, FR-14, FR-23)."""

import json
import uuid
from decimal import Decimal

import pytest

from app.engine import (
    GameSettings,
    Role,
    SeatView,
    advance,
    demand_series,
    guided_order,
    initial_state,
    rule_based,
    seat_view,
)
from app.engine.state import SeatState as EngineSeat
from app.engine.state import WeekState
from app.modules.games import commands, service, views
from app.modules.games.schemas import SeatState
from app.platform.parameter_sets import read_parameter_set
from tests.games.helpers import execute, play_week

ROLES = ("retailer", "wholesaler", "distributor", "factory")


def params() -> rule_based.RuleBasedParams:
    set_id = rule_based.DEFAULT_SET_ID
    return rule_based.parse_params(read_parameter_set("rule_based", set_id), set_id)


def play(settings: GameSettings) -> tuple[list[WeekState], list[dict]]:
    """Every opened Week of a Game played by four Rule-based players, and its Orders."""
    rule = params()
    states = [initial_state(settings)]
    orders: list[dict] = []
    while True:
        state = states[-1]
        if state.week <= settings.guided_weeks:
            placed = {role: guided_order(settings) for role in settings.roles}
        else:
            placed = {
                role: rule_based.order(settings, seat_view(settings, states, orders, role), rule)
                for role in settings.roles
            }
        following = advance(settings, state, placed)
        if following.finished:
            return states, orders
        orders.append(placed)
        states.append(following)


CLASSIC = GameSettings(demand_seed=7)
STATES, ORDERS = play(CLASSIC)
ALLOWED_KEYS = set(SeatState.model_fields) | {
    "stage",
    "quantity",
    "arrival_week",
    "kind",
    "units",
    "rate",
    "amount",
    "order",
    "cost",
    "holding_cost",
    "backorder_cost",
    "order_arrival_week",
    "supply_line_base",
    "position_base",
    "value",
}
ALLOWED_TEXT = set(ROLES) | {"ordered", "in_transit", "in_production", "holding", "backorder"}


def keys_and_texts(value, keys: set, texts: set) -> None:
    if isinstance(value, dict):
        keys |= set(value)
        for item in value.values():
            keys_and_texts(item, keys, texts)
    elif isinstance(value, list):
        for item in value:
            keys_and_texts(item, keys, texts)
    elif isinstance(value, str):
        texts.add(value)


def every_state():
    for week in range(1, len(STATES) + 1):
        for role in CLASSIC.roles:
            yield (
                week,
                role,
                views.build_seat_state(CLASSIC, STATES[:week], ORDERS[: week - 1], role),
            )


def test_the_classic_game_has_36_opened_weeks():
    assert len(STATES) == CLASSIC.weeks == 36


def test_every_seat_state_holds_numbers_and_roles_only():
    series = list(demand_series(CLASSIC))
    for week, role, seat in every_state():
        data = json.loads(seat.model_dump_json())
        keys: set = set()
        texts: set = set()
        keys_and_texts(data, keys, texts)
        assert keys <= ALLOWED_KEYS, keys - ALLOWED_KEYS
        assert not {"weeks", "demand", "demand_seed", "seed", "name", "names"} & keys
        for text in texts - ALLOWED_TEXT:
            Decimal(text)  # money travels as decimal strings; anything else is not allowed
        assert data["schema_version"] == 3 and data["week"] == week
        assert data["neighbour_numbers"] == []
        # No future demand: the series up to the next Week never appears.
        if week < CLASSIC.weeks:
            ahead = json.dumps(series[: week + 1], separators=(",", ":"))
            assert ahead not in seat.model_dump_json()
        if role == Role.RETAILER:
            assert data["incoming_orders"] == series[:week]
        assert len(data["incoming_orders"]) == week


def other_seats_scrambled(states: list[WeekState], role: Role) -> list[WeekState]:
    sentinel = 987_654
    scrambled = []
    for state in states:
        seats = tuple(
            seat
            if seat.role == role
            else EngineSeat(
                role=seat.role,
                incoming_order=sentinel,
                incoming_delivery=sentinel,
                shipped=sentinel,
                inventory=sentinel,
                backlog=sentinel,
                cost=Decimal(sentinel),
                total_cost=Decimal(sentinel),
                incoming_orders=(sentinel,) * len(seat.incoming_orders),
                goods_slots=(sentinel,) * len(seat.goods_slots),
                production_orders=(sentinel,) * len(seat.production_orders),
            )
            for seat in state.seats
        )
        scrambled.append(state.model_copy(update={"seats": seats}))
    return scrambled


def test_a_seat_state_never_reads_another_seat_the_week_count_or_the_seed():
    longer = GameSettings.model_validate(
        {**CLASSIC.model_dump(), "weeks": 40, "demand_seed": 123456}
    )
    for week in (1, 2, 5, 12, 36):
        for role in CLASSIC.roles:
            states, orders = STATES[:week], ORDERS[: week - 1]
            seat = views.build_seat_state(CLASSIC, states, orders, role)
            scrambled = views.build_seat_state(
                CLASSIC, other_seats_scrambled(states, role), orders, role
            )
            assert scrambled == seat
            assert "987654" not in scrambled.model_dump_json()
            assert views.build_seat_state(longer, states, orders, role) == seat


def test_a_seat_state_never_reads_demand_beyond_its_week():
    """Two Games that share demand up to Week t and differ after it look the same to every
    Seat in Weeks 1..t."""
    other = GameSettings.model_validate(
        {
            **CLASSIC.model_dump(),
            "demand": {"kind": "fixed", "values": list(demand_series(CLASSIC))[:12] + [20] * 24},
        }
    )
    other_states, other_orders = play(other)
    assert list(demand_series(other))[12:] != list(demand_series(CLASSIC))[12:]
    for week in range(1, 13):
        for role in CLASSIC.roles:
            assert views.build_seat_state(
                other, other_states[:week], other_orders[: week - 1], role
            ) == views.build_seat_state(CLASSIC, STATES[:week], ORDERS[: week - 1], role)


def test_only_the_retailer_sees_customer_demand():
    series = list(demand_series(CLASSIC))
    for week, role, seat in every_state():
        if role == Role.RETAILER:
            assert seat.incoming_orders == tuple(series[:week])
        else:
            # Everyone else's incoming order is its downstream Seat's Order of order_delay
            # Weeks earlier (the starting supply line before Week 1).
            downstream = CLASSIC.roles[CLASSIC.roles.index(role) - 1]
            placed = week - CLASSIC.order_delay
            expected = ORDERS[placed - 1][downstream] if placed >= 1 else CLASSIC.supply_line
            assert seat.incoming_order == expected


def test_seat_state_is_a_seat_view_the_engine_accepts():
    seat = views.build_seat_state(CLASSIC, STATES[:9], ORDERS[:8], Role.DISTRIBUTOR)
    assert isinstance(seat, SeatView)
    assert rule_based.order(CLASSIC, seat, params()) == rule_based.order(
        CLASSIC, seat_view(CLASSIC, STATES[:9], ORDERS[:8], Role.DISTRIBUTOR), params()
    )


def test_week_1_retailer_state_of_a_classic_game():
    seat = views.build_seat_state(CLASSIC, STATES[:1], [], "retailer")
    data = json.loads(seat.model_dump_json())
    assert data["week"] == 1 and data["role"] == "retailer"
    assert (data["inventory"], data["backlog"], data["incoming_order"]) == (12, 0, 4)
    assert (data["supply_line"], data["overdue"], data["position"]) == (12, 0, 24)
    assert [(s["stage"], s["quantity"], s["arrival_week"]) for s in data["supply_line_slots"]] == [
        ("in_transit", 4, 2),
        ("in_transit", 4, 3),
        ("ordered", 4, 4),
    ]
    assert data["cost_lines"][0] == {
        "kind": "holding",
        "units": 12,
        "rate": "0.50",
        "amount": "6.00",
    }
    assert (data["week_cost"], data["total_cost"]) == ("6.00", "6.00")
    assert (data["min_order"], data["max_order"]) == (0, 999)
    assert data["preview"] == {
        "order_arrival_week": 5,
        "supply_line_base": 12,
        "position_base": 24,
    }


# --- the stored path --------------------------------------------------------------------------


async def started_game() -> str:
    """Students hold every Seat, so the Game waits in Week 1 (Story 2.1)."""
    from tests.conftest import TEST_DATABASE_URL
    from tests.games.helpers import seat_student

    game_id = await commands.create("simulation", GameSettings(), seed=7)
    seat_student(TEST_DATABASE_URL, game_id, *(role.value for role in GameSettings().roles))
    await commands.start(game_id)
    return game_id


async def test_seat_state_reads_the_stored_week(games_db):
    game_id = await started_game()
    for role in ROLES:
        stored = await service.seat_state(game_id, role)
        assert stored == views.build_seat_state(CLASSIC, STATES[:1], [], role)
        assert await service.seat_state(game_id, role, 1) == stored
    game = await service.get_game(game_id)
    assert game is not None
    by_id = await service.seat_state(game_id, game.seats[2].id)
    assert by_id.role == Role.DISTRIBUTOR


async def test_seat_state_of_a_later_week_uses_the_orders_in_the_decision_log(games_db):
    game_id = await started_game()
    await play_week(game_id)  # Weeks 1 and 2 are Guided: the Orders of `play` (Story 1.9)
    await play_week(game_id)
    for role in ROLES:
        assert await service.seat_state(game_id, role) == views.build_seat_state(
            CLASSIC, STATES[:3], ORDERS[:2], role
        )
        assert await service.seat_state(game_id, role, 2) == views.build_seat_state(
            CLASSIC, STATES[:2], ORDERS[:1], role
        )


async def test_open_turn_reports_the_stored_turn(games_db):
    game_id = await started_game()
    turn = await service.open_turn(game_id, "factory")
    assert turn.week == 1 and turn.ordered_at is None
    expected = rule_based.order(CLASSIC, seat_view(CLASSIC, STATES[:1], [], Role.FACTORY), params())
    assert turn.rule_based_reference_order == expected


async def test_view_errors(games_db):
    created = await commands.create("simulation", GameSettings(), seed=7)
    started = await started_game()
    cases = [
        (service.seat_state("nope", "retailer"), "game_not_found", 404),
        (service.seat_state(str(uuid.uuid7()), "retailer"), "game_not_found", 404),
        (service.seat_state(started, "brewer"), "seat_not_found", 404),
        (service.seat_state(started, str(uuid.uuid7())), "seat_not_found", 404),
        (service.seat_state(created, "retailer"), "game_not_started", 409),
        (service.open_turn(created, "retailer"), "game_not_started", 409),
        (service.seat_state(started, "retailer", 2), "week_not_open", 409),
        (service.seat_state(started, "retailer", 0), "week_not_open", 409),
    ]
    for call, code, status in cases:
        with pytest.raises(service.ViewError) as caught:
            await call
        assert (caught.value.code, caught.value.status) == (code, status)


async def test_open_turn_without_a_turn_row_is_not_open(games_db):
    game_id = await started_game()
    execute(
        games_db,
        "INSERT INTO game_weeks (game_id, week, state) VALUES (%s, 2, %s::jsonb)",
        (game_id, STATES[1].model_dump_json()),
    )
    with pytest.raises(service.ViewError) as caught:
        await service.open_turn(game_id, "retailer")
    assert caught.value.code == "week_not_open"
    assert (await service.open_turn(game_id, "retailer", 1)).week == 1
