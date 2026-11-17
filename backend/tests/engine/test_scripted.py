import inspect

import pytest

from app.engine import RULES_VERSION, Role, SeatView
from app.engine.scripted import REGISTRY


def view(**changes) -> SeatView:
    data = {
        "role": Role.RETAILER,
        "inventory": 12,
        "backlog": 0,
        "incoming_orders": (4,),
        "supply_line": 12,
        "order_history": (),
    }
    return SeatView(**{**data, **changes})


def test_registry_starts_with_the_constant_policy_only():
    assert set(REGISTRY) == {"constant-4"}


@pytest.mark.parametrize(
    "seat",
    [
        view(),
        view(role=Role.FACTORY, inventory=0, backlog=500, supply_line=0),
        view(incoming_orders=(4, 8, 30), order_history=(0, 999), inventory=500),
    ],
)
def test_constant_policy_orders_four_whatever_it_sees(seat):
    assert REGISTRY["constant-4"](seat) == 4


def test_every_policy_takes_only_a_seat_view():
    for policy in REGISTRY.values():
        assert list(inspect.signature(policy).parameters) == ["view"]


def test_registry_is_closed_to_writes():
    with pytest.raises(TypeError):
        REGISTRY["other"] = REGISTRY["constant-4"]  # type: ignore[index]


def test_rules_version_is_a_positive_whole_number():
    assert isinstance(RULES_VERSION, int) and RULES_VERSION >= 1
