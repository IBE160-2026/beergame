"""«Simulert, samme kunder» (Story 9.8, FR-44, AD-1): the Game played again by the Rule-based rule,
once with only the viewer's Seat counting På vei and once with every Seat counting it."""

from decimal import Decimal

import pytest

from app.analysis.simulated import simulate
from app.engine import ROLES, GameSettings, advance, demand_series, initial_state
from app.sim import load_rule_based_params, rule_based_policy

SETTINGS = GameSettings()
PARAMS = load_rule_based_params("placeholder-unverified")


def played_by_policy(settings: GameSettings, params) -> tuple[Decimal, Decimal]:
    """The chain's holding and backorder cost when the trace runner's Rule-based policy plays
    every Seat: an independent run of the same rule."""
    policy = rule_based_policy(params)
    state = initial_state(settings)
    states, placed = [], []
    holding = backorder = Decimal(0)
    while not state.finished:
        states.append(state)
        for seat in state.seats:
            holding += settings.holding_cost * seat.inventory
            backorder += settings.backorder_cost * seat.backlog
        orders = policy(settings, states, placed)
        placed.append(orders)
        state = advance(settings, state, orders)
    return holding, backorder


def test_all_four_counting_is_the_rule_based_chain_and_the_same_for_every_seat():
    holding, backorder = played_by_policy(SETTINGS, PARAMS)
    rows = {
        role: simulate(SETTINGS, 1, demand_series(SETTINGS), PARAMS, role).rows for role in ROLES
    }
    for own, every in rows.values():
        assert (own.counts_supply_line, every.counts_supply_line) == ("own", "all")
        assert (every.holding_cost, every.backorder_cost) == (holding, backorder)
        assert every.total_cost == holding + backorder
        assert own.total_cost == own.holding_cost + own.backorder_cost
    # Which Seat counts På vei changes the `own` row.
    assert len({own.total_cost for own, _ in rows.values()}) > 1


def test_only_the_viewer_counts_is_the_chain_with_beta_0_elsewhere():
    blind = PARAMS.model_copy(update={"beta": Decimal(0)})
    # With beta 0 in the set itself, nobody counts På vei: both rows are the blind chain.
    holding, backorder = played_by_policy(SETTINGS, blind)
    found = simulate(SETTINGS, 1, demand_series(SETTINGS), blind, "wholesaler")
    for row in found.rows:
        assert (row.holding_cost, row.backorder_cost) == (holding, backorder)
    assert (found.params_id, found.params_version) == (PARAMS.id, PARAMS.version)


def test_the_same_input_gives_the_same_rows():
    first = simulate(SETTINGS, 1, demand_series(SETTINGS), PARAMS, "factory")
    assert simulate(SETTINGS, 1, list(demand_series(SETTINGS)), PARAMS, "factory") == first


def test_a_demand_series_other_than_the_settings_give_and_an_unknown_role_are_refused():
    other = (5,) * SETTINGS.weeks
    with pytest.raises(ValueError, match="demand series"):
        simulate(SETTINGS, 1, other, PARAMS, "retailer")
    short = GameSettings(roles=("retailer", "wholesaler"))
    with pytest.raises(ValueError, match="not a Role"):
        simulate(short, 1, demand_series(short), PARAMS, "factory")
