import pytest

from app.engine import GameSettings, guided_order
from app.engine.demand import DemandFixed, DemandRandom, DemandStep


@pytest.mark.parametrize(
    ("demand", "seed", "expected"),
    [
        (DemandStep(kind="step", start=4, new_level=8, change_week=5), None, 4),
        (DemandStep(kind="step", start=7, new_level=2, change_week=5), None, 7),
        (DemandFixed(kind="fixed", values=(5,) + (9,) * 35), None, 5),
        (DemandRandom(kind="random", mean=6, spread=2), 42, 6),
    ],
)
def test_guided_order_is_the_starting_demand(demand, seed, expected):
    assert guided_order(GameSettings(demand=demand, demand_seed=seed)) == expected


def test_guided_order_is_the_starting_demand_even_above_the_maximum_order():
    assert guided_order(GameSettings(max_order=3)) == 4
