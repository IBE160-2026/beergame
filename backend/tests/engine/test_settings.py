from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.engine import ROLES, DemandStep, GameSettings, InfoVisibility, Role


def test_classic_defaults_dump_as_json_with_decimal_strings():
    assert GameSettings().model_dump(mode="json") == {
        "schema_version": 2,
        "roles": ["retailer", "wholesaler", "distributor", "factory"],
        "starting_inventory": 12,
        "starting_backlog": 0,
        "supply_line": 4,
        "order_delay": 2,
        "shipping_delay": 2,
        "production_delay": 2,
        "demand": {"kind": "step", "start": 4, "new_level": 8, "change_week": 5},
        "demand_seed": None,
        "holding_cost": "0.50",
        "backorder_cost": "1.00",
        "weeks": 36,
        "guided_weeks": 4,
        "max_order": 999,
        "info_visibility": {"upstream": False, "downstream": False},
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
    assert [step.level_for(week) for week in range(1, 8)] == [4, 4, 4, 4, 8, 8, 8]


def test_settings_are_frozen():
    settings = GameSettings()
    with pytest.raises(ValidationError):
        settings.weeks = 10


@pytest.mark.parametrize(
    "override",
    [
        {"colour": "red"},
        {"schema_version": 3},
        {"schema_version": True},
        {"schema_version": 1.0},
        {"schema_version": 1, "info_visibility": {"upstream": False}},
        {"info_visibility": {"upstream": "true"}},
        {"info_visibility": {"upstream": 1}},
        {"info_visibility": {"left": True}},
        {"info_visibility": True},
        {"starting_inventory": -1},
        {"starting_inventory": True},
        {"starting_inventory": "12"},
        {"supply_line": 4.0},
        {"starting_backlog": -1},
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
        {"demand": {"kind": "fixed", "values": []}},
        {"demand": {"kind": "fixed", "values": [4, -1]}},
        {"demand": {"kind": "random", "mean": 4, "spread": 2.0}},
        {"demand": {"kind": "random", "mean": -1, "spread": 2}},
        {"demand": {"kind": "step+noise", "start": 4, "new_level": 8, "change_week": 5}},
        {"demand": {"kind": "poisson", "mean": 4}},
        {"demand_seed": "42"},
        {"demand_seed": 4.0},
        {"demand_seed": True},
    ],
)
def test_basic_type_and_sign_constraints(override):
    with pytest.raises(ValidationError):
        GameSettings(**override)


def test_settings_stored_as_version_1_read_as_version_2_with_every_view_off():
    # Story 5.16 bumped the schema; a version-1 dump (no `info_visibility`) still reads.
    old = GameSettings().model_dump(mode="json")
    old["schema_version"] = 1
    del old["info_visibility"]
    settings = GameSettings.model_validate(old)
    assert settings == GameSettings()
    assert settings.schema_version == 2
    assert settings.info_visibility == InfoVisibility(upstream=False, downstream=False)
    assert not settings.info_visibility.on


def test_information_visibility_holds_an_upstream_and_a_downstream_view():
    settings = GameSettings(info_visibility={"upstream": True})
    assert settings.info_visibility.on
    assert (settings.info_visibility.upstream, settings.info_visibility.downstream) == (True, False)
    assert settings.model_dump(mode="json")["info_visibility"] == {
        "upstream": True,
        "downstream": False,
    }
    assert GameSettings.model_validate_json(settings.model_dump_json()) == settings
    assert settings != GameSettings()
