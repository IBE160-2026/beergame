"""Property tests for the bookkeeping check (Story 1.5, NFR-9).

Random valid Games, drawn from a fixed seed so a failure can be reproduced: every Game the engine
plays keeps its books, and any one number altered by one is named by Week and Role. Hypothesis is
not in the Stack table, so the draws come from `random.Random` here in the tests; the engine
itself never touches `random`.
"""

import random
from decimal import Decimal

from app.engine import (
    ROLES,
    SEED_MAX,
    DemandFixed,
    DemandRandom,
    DemandStep,
    DemandStepNoise,
    GameSettings,
    advance,
    demand_series,
    initial_state,
    validate,
)
from app.engine.check import conservation

SEED = 20261117
RUNS = 300
UNITS = ("incoming_order", "incoming_delivery", "shipped", "inventory", "backlog")
SLOTS = ("goods_slots", "incoming_orders", "production_orders")
MONEY = ("cost", "total_cost")
RULE_OF = {
    "incoming_order": "incoming_order",
    "incoming_delivery": "in_transit",
    "shipped": "inventory_balance",
    "inventory": "inventory_balance",
    "backlog": "backlog_balance",
    "cost": "cost",
    "total_cost": "total_cost",
    "goods_slots": "in_transit",
    "incoming_orders": "order_slots",
    "production_orders": "order_slots",
}
"""The rule that must name a field altered on its own, in an opened or the finished state."""


def random_demand(rng, weeks):
    kind = rng.choice(("fixed", "step", "random", "step+noise"))
    if kind == "fixed":
        return DemandFixed(kind="fixed", values=[rng.randint(0, 100) for _ in range(weeks)]), None
    seed = rng.randint(0, SEED_MAX)
    if kind == "step":
        pattern = DemandStep(
            kind="step",
            start=rng.randint(0, 100),
            new_level=rng.randint(0, 100),
            change_week=rng.randint(1, weeks),
        )
        return pattern, None
    if kind == "random":
        return DemandRandom(
            kind="random", mean=rng.randint(0, 100), spread=rng.randint(0, 20)
        ), seed
    pattern = DemandStepNoise(
        kind="step+noise",
        start=rng.randint(0, 100),
        new_level=rng.randint(0, 100),
        change_week=rng.randint(1, weeks),
        spread=rng.randint(0, 20),
    )
    return pattern, seed


def random_settings(rng):
    weeks = rng.choice((rng.randint(1, 40), 100))
    demand, demand_seed = random_demand(rng, weeks)
    backlog_start = rng.random() < 0.2
    return GameSettings(
        roles=ROLES[: rng.choice((1, 2, 3, 4, 4, 4))],
        starting_inventory=0 if backlog_start else rng.randint(0, 100),
        starting_backlog=rng.randint(0, 100) if backlog_start else 0,
        supply_line=rng.randint(0, 100),
        order_delay=rng.randint(1, 3),
        shipping_delay=rng.randint(1, 3),
        production_delay=rng.randint(1, 3),
        demand=demand,
        demand_seed=demand_seed,
        holding_cost=Decimal(rng.randint(0, 10000)).scaleb(-2),
        backorder_cost=Decimal(rng.randint(0, 10000)).scaleb(-2),
        weeks=weeks,
        guided_weeks=0,
        max_order=rng.choice((1, rng.randint(1, 200), rng.randint(1, 9999))),
    )


def random_order(rng, settings, demand):
    choice = rng.random()
    if choice < 0.2:
        return 0
    if choice < 0.35:
        return settings.max_order
    if choice < 0.7:
        return rng.randint(0, settings.max_order)
    return min(settings.max_order, max(0, demand + rng.randint(-3, 3)))


def random_game(rng):
    settings = random_settings(rng)
    assert validate(settings) == (), settings.model_dump_json()
    demand = demand_series(settings)
    length = settings.weeks if rng.random() < 0.7 else rng.randint(0, settings.weeks)
    states = [initial_state(settings)]
    orders = []
    for week in range(1, length + 1):
        placed = {role: random_order(rng, settings, demand[week - 1]) for role in settings.roles}
        orders.append(placed)
        states.append(advance(settings, states[-1], placed))
    return settings, states, orders


def run_seed(run):
    """Each run draws from its own seed, so one failing run can be replayed on its own."""
    return f"{SEED}-{run}"


def games():
    for run in range(RUNS):
        rng = random.Random(run_seed(run))
        yield run, rng, *random_game(rng)


def test_every_generated_game_keeps_its_books():
    finished = 0
    for run, _, settings, states, orders in games():
        found = conservation(settings, states, orders)
        assert found == (), f"run seed {run_seed(run)!r}: {settings.model_dump_json()}\n{found[:3]}"
        finished += states[-1].finished
    assert 150 < finished < RUNS


def alter(rng, states):
    """One number of one Seat in one state, moved by one (a cent for money)."""
    s = rng.randrange(len(states))
    state = states[s]
    i = rng.randrange(len(state.seats))
    seat = state.seats[i]
    fields = UNITS + MONEY + tuple(name for name in SLOTS if getattr(seat, name))
    name = rng.choice(fields)
    sign = rng.choice((-1, 1))
    value = getattr(seat, name)
    if name in MONEY:
        value += sign * Decimal("0.01")
    elif name in UNITS:
        value += sign
    else:
        k = rng.randrange(len(value))
        value = value[:k] + (value[k] + sign,) + value[k + 1 :]
    seats = state.seats[:i] + (seat.model_copy(update={name: value}),) + state.seats[i + 1 :]
    altered = list(states)
    altered[s] = state.model_copy(update={"seats": seats})
    return altered, state.week, seat.role, name, f"{name} {sign:+d} in state {s}"


def test_any_number_altered_by_one_is_named():
    for run, rng, settings, states, orders in games():
        altered, week, role, name, change = alter(rng, states)
        found = conservation(settings, altered, orders)
        named = {(v.rule, v.week, v.role) for v in found}
        assert (RULE_OF[name], week, role) in named, (
            f"run seed {run_seed(run)!r}: {change} of {role} in Week {week} went unseen; "
            f"{settings.model_dump_json()}"
        )
