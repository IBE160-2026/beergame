"""Golden traces: the engine must reproduce files that were not written by the engine."""

import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.engine import GameSettings, advance, initial_state

GOLDEN = Path(__file__).parent / "golden"
FIELDS = (
    "incoming_order",
    "incoming_delivery",
    "shipped",
    "inventory",
    "backlog",
    "incoming_orders",
    "goods_slots",
    "production_orders",
)


def as_row(week, seat):
    row = {"week": week, "role": seat.role.value, "cost": seat.cost}
    return row | seat.model_dump(mode="json", include=set(FIELDS))


def expected_row(row):
    return row | {"cost": Decimal(row["cost"])}


@pytest.mark.parametrize("name", ["constant-4.json", "classic-step-pass-through.json"])
def test_golden_trace(name):
    golden = json.loads((GOLDEN / name).read_text(encoding="utf-8"))
    settings = GameSettings.model_validate(golden["settings"])
    state = initial_state(settings)
    rows = []
    for orders in golden["orders"]:
        rows.extend(as_row(state.week, seat) for seat in state.seats)
        state = advance(settings, state, orders)
    assert rows == [expected_row(row) for row in golden["rows"]]
    final = golden["final"]
    assert (state.week, state.finished) == (final["week"], final["finished"])
    assert {s.role.value: s.total_cost for s in state.seats} == {
        role: Decimal(total) for role, total in final["total_cost"].items()
    }
