"""Story 9.1: the Detected pattern definitions (FR-44, AD-23): a closed list of three, each with an
exact definition worded as a pattern, typed thresholds and one mechanism."""

import copy
import importlib.util
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.analysis.patterns import MECHANISMS, REVIEW, PatternSet

MIGRATION = (
    Path(__file__).parents[2]
    / "migrations"
    / "versions"
    / "0101_fact_sets_and_detected_patterns.py"
)


def _version_1() -> dict:
    spec = importlib.util.spec_from_file_location("migration_0101", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.DETECTED_PATTERNS_V1


V1 = _version_1()
"""Version 1 as migration 0101 stores it."""


def test_version_1_holds_the_three_patterns_with_placeholder_thresholds():
    patterns = PatternSet.model_validate(V1)
    assert [p.id for p in patterns.patterns] == [
        "surge-after-shortage",
        "large-order-full-supply-line",
        "low-after-overshoot",
    ]
    assert [p.mechanism for p in patterns.patterns] == [
        "demand_information_lost",
        "supply_line",
        "delay",
    ]
    assert set(MECHANISMS) == {p.mechanism for p in patterns.patterns}
    assert all(p.review == REVIEW for p in patterns.patterns)
    assert REVIEW == "to be reviewed by two lecturers before pilot"
    assert patterns.following_weeks == 4
    surge, large, low = patterns.patterns
    assert (surge.lookback_weeks, surge.min_ratio, surge.min_excess) == (2, Decimal("1.5"), 4)
    assert (large.min_ratio, large.min_excess, large.min_cover_weeks) == (
        Decimal("1.5"),
        4,
        Decimal(6),
    )
    assert (low.max_ratio, low.min_shortfall, low.min_cover_weeks) == (Decimal("0.5"), 2, 4)
    # Stored as JSON and read back unchanged.
    assert PatternSet.model_validate(patterns.model_dump(mode="json")) == patterns


def _changed(index: int, **fields) -> dict:
    body = copy.deepcopy(V1)
    body["patterns"][index] |= fields
    return body


@pytest.mark.parametrize(
    "body",
    [
        _changed(0, definition="En stor ordre fordi lageret var tomt."),
        _changed(1, name="Skyldes leveringstiden"),
        _changed(2, definition="Lav ordre på grunn av overskudd."),
        _changed(0, definition="Dette førte til restordre."),
        _changed(0, definition="Derfor  steg ordren."),
        _changed(1, definition="Ordren steg som  følge av mangel."),
        _changed(2, review="Lav fordi lageret var fullt."),
        _changed(0, min_ratio="0.9"),
        _changed(1, min_excess=0),
        _changed(1, min_cover_weeks="0"),
        _changed(2, max_ratio="1.5"),
        _changed(2, min_shortfall=0),
        _changed(1, definition="Forårsaket svingninger."),
        _changed(2, name="Svært lav ordre!"),
        _changed(0, mechanism="neighbours"),
        _changed(1, id="surge-after-shortage"),
        _changed(2, min_cover_weeks="-1"),
        _changed(0, lookback_weeks="2"),
        _changed(0, extra=1),
        {**V1, "patterns": V1["patterns"][:2]},
        {**V1, "patterns": list(reversed(V1["patterns"]))},
        {**V1, "following_weeks": 0},
    ],
)
def test_a_set_that_states_a_cause_or_breaks_the_closed_list_is_refused(body):
    with pytest.raises(ValidationError):
        PatternSet.model_validate(body)


PATTERNS = PatternSet.model_validate(V1)
SURGE, LARGE, LOW = PATTERNS.patterns


def _matches(pattern, *, order, incoming, inventory=0, supply_line=0, backlogs=(0,)):
    return pattern.matches(
        order=order,
        incoming=incoming,
        inventory=inventory,
        supply_line=supply_line,
        backlogs=backlogs,
    )


@pytest.mark.parametrize(
    ("order", "incoming", "backlogs", "hit"),
    [
        (10, 4, (1,), True),  # shortage this Week; 10 ≥ 6 and 10 − 4 ≥ 4
        (10, 4, (1, 0, 0), True),  # two Weeks after the shortage
        (10, 4, (1, 0, 0, 0), False),  # three Weeks after: too late
        (10, 4, (0,), False),  # no shortage
        (7, 4, (1,), False),  # 7 − 4 < 4
        (14, 10, (1,), False),  # 14 < 1.5 · 10
        (4, 0, (1,), True),  # nothing came in: 4 ≥ 0 and 4 − 0 ≥ 4
    ],
)
def test_surge_after_shortage(order, incoming, backlogs, hit):
    assert _matches(SURGE, order=order, incoming=incoming, backlogs=backlogs) is hit


@pytest.mark.parametrize(
    ("order", "incoming", "supply_line", "hit"),
    [
        (10, 4, 24, True),  # 24 = 6 · 4
        (10, 4, 23, False),
        (7, 4, 40, False),  # 7 − 4 < 4
        (4, 0, 6, True),  # at least 1 unit a Week: 6 · 1
        (4, 0, 5, False),
    ],
)
def test_large_order_with_a_full_supply_line(order, incoming, supply_line, hit):
    assert _matches(LARGE, order=order, incoming=incoming, supply_line=supply_line) is hit


@pytest.mark.parametrize(
    ("order", "incoming", "inventory", "hit"),
    [
        (2, 4, 16, True),  # 2 ≤ 2, 4 − 2 ≥ 2, 16 = 4 · 4
        (2, 4, 15, False),  # no overshoot
        (3, 4, 40, False),  # 3 > 0.5 · 4
        (0, 1, 40, False),  # 1 − 0 < 2
        (0, 0, 40, False),
        (4, 8, 32, True),
    ],
)
def test_low_after_overshoot(order, incoming, inventory, hit):
    assert _matches(LOW, order=order, incoming=incoming, inventory=inventory) is hit
