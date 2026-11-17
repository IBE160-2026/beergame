from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.engine import ROLES, DemandStep, GameSettings, Role


def test_classic_defaults_dump_as_json_with_decimal_strings():
    assert GameSettings().model_dump(mode="json") == {
        "schema_version": 1,
        "roles": ["retailer", "wholesaler", "distributor", "factory"],
        "starting_inventory": 12,
        "supply_line": 4,
        "order_delay": 2,
        "shipping_delay": 2,
        "production_delay": 2,
        "demand": {"kind": "step", "start": 4, "new_level": 8, "change_week": 5},
        "holding_cost": "0.50",
        "backorder_cost": "1.00",
        "weeks": 36,
        "guided_weeks": 4,
        "max_order": 999,
    }


def test_roles_run_downstream_first():
    assert ROLES == (Role.RETAILER, Role.WHOLESALER, Role.DISTRIBUTOR, Role.FACTORY)
    assert GameSettings().roles == ROLES


def test_json_round_trip_keeps_decimals():
    settings = GameSettings(holding_cost="0.25")
    again = GameSettings.model_validate_json(settings.model_dump_json())
    assert again == settings
    assert again.holding_cost == Decimal("0.25")


def test_step_demand():
    step = DemandStep(kind="step", start=4, new_level=8, change_week=5)
    assert [step.demand_for(week) for week in range(1, 8)] == [4, 4, 4, 4, 8, 8, 8]


def test_settings_are_frozen():
    settings = GameSettings()
    with pytest.raises(ValidationError):
        settings.weeks = 10


@pytest.mark.parametrize(
    "override",
    [
        {"colour": "red"},
        {"schema_version": 2},
        {"starting_inventory": -1},
        {"starting_inventory": True},
        {"starting_inventory": "12"},
        {"supply_line": 4.0},
        {"order_delay": 0},
        {"shipping_delay": 0},
        {"production_delay": 0},
        {"weeks": 0},
        {"guided_weeks": -1},
        {"max_order": -1},
        {"holding_cost": "-0.50"},
        {"backorder_cost": "NaN"},
        {"roles": []},
        {"roles": ["retailer", "retailer"]},
        {"roles": ["shop"]},
        {"demand": {"kind": "random", "start": 4, "new_level": 8, "change_week": 5}},
        {"demand": {"kind": "step", "start": -1, "new_level": 8, "change_week": 5}},
        {"demand": {"kind": "step", "start": 4, "new_level": 8, "change_week": 0}},
    ],
)
def test_basic_type_and_sign_constraints(override):
    with pytest.raises(ValidationError):
        GameSettings(**override)
