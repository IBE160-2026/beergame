"""Golden traces: the engine must reproduce files that were not written by the engine.

Every packaged rules version runs its own traces (AD-4, `app/engine/RULES_VERSIONS.md`)."""

import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.engine import GameSettings, advance, initial_state, rules

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


GOLDEN_TRACES: dict[int, tuple[str, ...]] = {
    1: (
        "constant-4.json",
        "classic-step-pass-through.json",
        "delays-1-1-1-backlog.json",
        "delays-3-3-3-backlog.json",
    ),
}
"""Rules version -> its golden trace files. A new version adds its own entry."""


def test_every_rules_version_has_golden_traces():
    assert set(GOLDEN_TRACES) == set(rules.versions())
    assert all(GOLDEN_TRACES.values())


@pytest.mark.parametrize(
    ("version", "name"),
    [(version, name) for version, names in GOLDEN_TRACES.items() for name in names],
)
def test_golden_trace(version, name):
    golden = json.loads((GOLDEN / name).read_text(encoding="utf-8"))
    settings = GameSettings.model_validate(golden["settings"])
    state = initial_state(settings, version)
    rows = []
    for orders in golden["orders"]:
        rows.extend(as_row(state.week, seat) for seat in state.seats)
        state = advance(settings, state, orders, version)
    assert rows == [expected_row(row) for row in golden["rows"]]
    final = golden["final"]
    assert (state.week, state.finished) == (final["week"], final["finished"])
    assert {s.role.value: s.total_cost for s in state.seats} == {
        role: Decimal(total) for role, total in final["total_cost"].items()
    }
