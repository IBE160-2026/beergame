"""`SeatState` version 2 (Story 6.6): `net_inventory` on the Week and on each `history` row;
version 3 (Story 6.7): `holding_cost` and `backorder_cost` on each `history` row; version 4
(Story 6.16): the running cost sums on the Week and on each `history` row. A state stored as
version 1, 2 or 3 (a Decision log row's `state_seen` written before them) reads as version 4 with
the same numbers, so the finished-game check still finds it equal to what the Seat saw."""

import pytest
from pydantic import ValidationError

from app.engine import GameSettings, Role
from app.modules.games.checks import _decision_log
from app.modules.games.schemas import SeatState
from app.modules.games.views import build_seat_state
from tests.engine.test_view import play, stepped


def week_6() -> tuple[GameSettings, list, list]:
    settings = GameSettings()
    states, orders = play(settings, 6, stepped)
    return settings, states, orders


RUNNING = ("total_holding_cost", "total_backorder_cost")


def as_version_3(state: SeatState) -> dict:
    stored = state.model_dump(mode="json")
    stored["schema_version"] = 3
    for name in RUNNING:
        del stored[name]
    for row in stored["history"]:
        for name in ("total_cost", *RUNNING):
            del row[name]
    return stored


def as_version_2(state: SeatState) -> dict:
    stored = as_version_3(state)
    stored["schema_version"] = 2
    for row in stored["history"]:
        del row["holding_cost"], row["backorder_cost"]
    return stored


def as_version_1(state: SeatState) -> dict:
    stored = as_version_2(state)
    stored["schema_version"] = 1
    del stored["net_inventory"]
    for row in stored["history"]:
        del row["net_inventory"]
    return stored


@pytest.mark.parametrize("older", [as_version_1, as_version_2, as_version_3])
def test_an_older_state_reads_as_version_4_with_the_same_numbers(older):
    settings, states, orders = week_6()
    for role in settings.roles:
        state = build_seat_state(settings, states, orders[:5], role)
        assert state.schema_version == 4
        assert state.net_inventory == state.inventory - state.backlog
        assert all(row.holding_cost + row.backorder_cost == row.cost for row in state.history)
        assert state.total_holding_cost + state.total_backorder_cost == state.total_cost
        assert SeatState.model_validate(older(state)) == state


@pytest.mark.parametrize("older", [as_version_1, as_version_2, as_version_3])
def test_an_older_uke_1_state_reads_as_version_4(older):
    settings, states, orders = week_6()
    state = build_seat_state(settings, states[:1], [], "wholesaler")
    assert state.history == () and state.total_holding_cost == state.total_cost
    assert SeatState.model_validate(older(state)) == state


@pytest.mark.parametrize("older", [as_version_1, as_version_2, as_version_3])
def test_the_finished_game_check_accepts_an_older_row(older):
    settings, states, orders = week_6()
    state = build_seat_state(settings, states[:4], orders[:3], Role.WHOLESALER)
    row = {"week": 4, "role": "wholesaler", "state_seen": older(state)}
    assert _decision_log(settings, states, orders, [row]) == []


@pytest.mark.parametrize(
    "change",
    [
        lambda s: s.update(net_inventory=0),  # version 1 never held it
        lambda s: s["history"][0].update(net_inventory=0),
        lambda s: s.update(schema_version=True),  # not a whole number
        lambda s: s.update(schema_version=1.0),
        lambda s: s.update(schema_version=5),
        lambda s: s.update(total_holding_cost="1.00"),  # older versions never held it
        lambda s: s["history"][0].update(total_cost="1.00"),
        lambda s: s["history"][0].update(holding_cost="1.00"),  # older versions never held it
        lambda s: s["history"][0].update(backorder_cost="1.00"),
        lambda s: s.update(cost_lines=[]),  # no rates: the cost split stays missing
        lambda s: s["cost_lines"][0].update(rate="many"),
        lambda s: s["cost_lines"][0].update(rate="Infinity"),
        lambda s: s["cost_lines"][1].update(rate="sNaN"),
        lambda s: s.update(inventory="12"),  # malformed: the field check names it
        lambda s: s["history"].append("not a row"),
    ],
)
def test_a_malformed_stored_state_is_refused(change):
    settings, states, orders = week_6()
    stored = as_version_1(build_seat_state(settings, states, orders[:5], "retailer"))
    change(stored)
    with pytest.raises(ValidationError):
        SeatState.model_validate(stored)


@pytest.mark.parametrize("older", [as_version_2, as_version_3, None])
def test_a_newer_state_without_net_inventory_is_refused(older):
    settings, states, orders = week_6()
    state = build_seat_state(settings, states, orders[:5], "factory")
    stored = older(state) if older else state.model_dump(mode="json")
    del stored["net_inventory"]
    with pytest.raises(ValidationError):
        SeatState.model_validate(stored)


@pytest.mark.parametrize("older", [as_version_3, None])
def test_a_state_without_its_cost_split_is_refused(older):
    settings, states, orders = week_6()
    state = build_seat_state(settings, states, orders[:5], "factory")
    stored = older(state) if older else state.model_dump(mode="json")
    del stored["history"][0]["holding_cost"]
    with pytest.raises(ValidationError):
        SeatState.model_validate(stored)


@pytest.mark.parametrize("missing", ["total_holding_cost", "total_backorder_cost"])
def test_a_version_4_state_without_its_running_sums_is_refused(missing):
    settings, states, orders = week_6()
    stored = build_seat_state(settings, states, orders[:5], "factory").model_dump(mode="json")
    del stored[missing]
    with pytest.raises(ValidationError):
        SeatState.model_validate(stored)
