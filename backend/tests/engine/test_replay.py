"""Replay (Story 1.10, FR-29): a stored Game equals the engine's replay of its Orders."""

import sys
import types
from decimal import Decimal

from app.engine import ROLES, GameSettings, Role, advance, initial_state
from app.engine.replay import replay
from app.engine.rules import v1

CLASSIC = GameSettings()
FOURS = {role: 4 for role in ROLES}


def play(settings, orders):
    states = [initial_state(settings)]
    for placed in orders:
        states.append(advance(settings, states[-1], placed))
    return states


def classic_game():
    orders = [dict(FOURS) for _ in range(CLASSIC.weeks)]
    orders[9] = {**FOURS, Role.WHOLESALER: 9}
    return play(CLASSIC, orders), orders


def with_seat(states, s, role, **update):
    state = states[s]
    seats = tuple(
        seat.model_copy(update=update) if seat.role == role else seat for seat in state.seats
    )
    changed = list(states)
    changed[s] = state.model_copy(update={"seats": seats})
    return changed


def keys(violations):
    return {(v.rule, v.week, v.role) for v in violations}


def test_a_stored_game_equals_its_replay():
    states, orders = classic_game()
    assert replay(CLASSIC, states, orders, 1) == ()


def test_an_opened_week_without_its_finish_replays_too():
    states, orders = classic_game()
    assert replay(CLASSIC, states[:12], orders[:11], 1) == ()


def test_a_changed_state_shows_at_its_week_and_role():
    states, orders = classic_game()
    changed = with_seat(states, 9, Role.RETAILER, inventory=states[9].seats[0].inventory + 1)
    (violation,) = replay(CLASSIC, changed, orders, 1)
    assert (violation.rule, violation.week, violation.role) == ("replay", 10, Role.RETAILER)
    assert "inventory" in violation.message
    assert violation.expected.startswith("inventory=")


def test_a_changed_cost_shows_at_its_week_and_role():
    states, orders = classic_game()
    changed = with_seat(states, 36, Role.FACTORY, total_cost=Decimal("1.00"))
    assert keys(replay(CLASSIC, changed, orders, 1)) == {("replay", 36, Role.FACTORY)}


def test_a_changed_order_shows_from_the_week_it_reaches():
    states, orders = classic_game()
    changed = [dict(placed) for placed in orders]
    changed[6][Role.WHOLESALER] = 5
    found = replay(CLASSIC, states, changed, 1)
    assert found
    assert min(v.week for v in found) == 8
    assert ("replay", 8, Role.DISTRIBUTOR) in keys(found)


def test_a_missing_or_extra_state_is_reported():
    states, orders = classic_game()
    missing = replay(CLASSIC, states[:-1], orders, 1)
    assert keys(missing) == {("replay", 36, None)}
    assert "did not store" in missing[0].message
    extra = replay(CLASSIC, [*states, states[-1]], orders, 1)
    assert keys(extra) == {("replay", 36, None)}
    assert "does not reach" in extra[0].message


def test_orders_after_the_end_are_reported_and_not_replayed():
    states, orders = classic_game()
    (violation,) = replay(CLASSIC, states, [*orders, FOURS], 1)
    assert (violation.rule, violation.week, violation.role) == ("replay", 36, None)
    assert "after it finished" in violation.message


def test_a_wrong_week_or_seat_count_is_one_violation():
    states, orders = classic_game()
    moved = list(states)
    moved[3] = states[3].model_copy(update={"week": 9})
    (violation,) = replay(CLASSIC, moved, orders, 1)
    assert (violation.rule, violation.week, violation.role) == ("replay", 9, None)
    short = list(states)
    short[3] = states[3].model_copy(update={"seats": states[3].seats[:3]})
    (violation,) = replay(CLASSIC, short, orders, 1)
    assert (violation.week, violation.role, violation.actual) == (4, None, "3")


def test_a_seat_in_the_wrong_place_names_the_role():
    states, orders = classic_game()
    swapped = list(states)
    seats = states[2].seats
    swapped[2] = states[2].model_copy(update={"seats": (seats[1], seats[0], *seats[2:])})
    found = replay(CLASSIC, swapped, orders, 1)
    assert ("replay", 3, Role.RETAILER) in keys(found)
    assert found[0].message.startswith("the stored state differs from the replay in role")


def test_orders_the_engine_refuses_stop_the_replay():
    states, orders = classic_game()
    missing_role = [dict(placed) for placed in orders]
    del missing_role[4][Role.FACTORY]
    found = replay(CLASSIC, states, missing_role, 1)
    assert ("replay", 5, Role.FACTORY) in keys(found)
    assert any("refused" in v.message for v in found)
    unknown_key = [dict(placed) for placed in orders]
    unknown_key[0]["bogus"] = 4
    found = replay(CLASSIC, states, unknown_key, 1)
    assert ("replay", 1, None) in keys(found)


def test_a_version_without_a_package_is_one_violation():
    states, orders = classic_game()
    (violation,) = replay(CLASSIC, states, orders, 99)
    assert (violation.rule, violation.week, violation.role, violation.actual) == (
        "rules_version",
        None,
        None,
        "99",
    )


def test_the_same_orders_replayed_at_another_version_differ(monkeypatch):
    """A throwaway `v2` with one changed rule (holding cost doubled) shows the selection."""
    states, orders = classic_game()

    def advance_v2(settings, state, placed):
        following = v1.advance(settings, state, placed)
        seats = tuple(seat.model_copy(update={"cost": seat.cost * 2}) for seat in following.seats)
        return following.model_copy(update={"seats": seats})

    v2 = types.ModuleType("app.engine.rules.v2")
    v2.initial_state = v1.initial_state
    v2.advance = advance_v2
    monkeypatch.setitem(sys.modules, "app.engine.rules.v2", v2)
    assert replay(CLASSIC, states, orders, 1) == ()
    found = replay(CLASSIC, states, orders, 2)
    assert {v.rule for v in found} == {"replay"}
    assert ("replay", 2, Role.RETAILER) in keys(found)
