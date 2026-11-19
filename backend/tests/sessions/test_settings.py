"""Changing the Game settings of a Class session (Story 5.3, FR-12, FR-18, AD-1, AD-19): saved
with «Lagre Klasseøkt» and judged as a draft by the check route, both by the engine alone, with
stable codes and the allowed range; warnings never block; nothing changes once locked. The api's
clock is fixed (2026-11-19 09:00 UTC); the database clock is never read."""

import pytest

from app.engine import GameSettings
from app.modules.sessions import service
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_roster_upload import clock, klass
from tests.classes.test_staff import ASSISTANT, call, put_staff
from tests.messaging.helpers import rows
from tests.sessions.test_dates import DAY, PLAN, at, iso, new_session, refusal

__all__ = ["clock", "klass"]


@pytest.fixture(autouse=True)
def _empty_ai(ai_db):
    """No model config: the sessions are Rule-based, which the settings do not care about."""


async def save(session_id: str, settings: dict, *, dates: dict | None = None, email=LECTURER):
    body: dict = {"ai_mode": "rule_based", "game_settings": settings}
    if dates is not None:
        body["dates"] = iso(dates)
    return await call(email, "PUT", f"/api/class-sessions/{session_id}", json=body)


async def check(session_id: str, settings: dict, email=LECTURER):
    return await call(
        email,
        "POST",
        f"/api/class-sessions/{session_id}/settings-check",
        json={"game_settings": settings},
    )


def stored(session_id: str) -> GameSettings:
    (row,) = rows("SELECT game_settings FROM class_sessions WHERE id = %s", session_id)
    return GameSettings.model_validate(row[0])


def problem(code: str, minimum: str | None, maximum: str | None, places: int | None = None):
    return {"code": code, "minimum": minimum, "maximum": maximum, "decimal_places": places}


async def test_a_changed_setting_is_stored_and_the_session_is_no_longer_classic(klass):
    session_id = await new_session(klass)
    seed = stored(session_id).demand_seed
    response = await save(session_id, {"order_delay": 3, "holding_cost": "0.75"})
    assert response.status_code == 200
    body = response.json()
    assert body["is_classic"] is False
    assert body["game_settings"]["order_delay"] == 3
    assert body["game_settings"]["holding_cost"] == "0.75"
    after = stored(session_id)
    # Laid over the stored settings: the rest and the seed stay.
    assert (after.order_delay, after.shipping_delay, after.demand_seed) == (3, 2, seed)
    # The calibration line's values come from the server, Classic.
    assert body["calibrated_settings"]["order_delay"] == 2
    assert body["calibrated_settings"]["weeks"] == 36


@pytest.mark.parametrize(
    ("draft", "field", "expected"),
    [
        ({"order_delay": 4}, "order_delay", problem("out_of_range", "1", "3")),
        ({"shipping_delay": 0}, "shipping_delay", problem("out_of_range", "1", "3")),
        ({"weeks": -1}, "weeks", problem("out_of_range", "1", "100")),
        ({"weeks": "x"}, "weeks", problem("not_a_number", "1", "100")),
        ({"starting_inventory": 101}, "starting_inventory", problem("out_of_range", "0", "100")),
        ({"max_order": 0}, "max_order", problem("out_of_range", "1", "9999")),
        ({"production_delay": 5}, "production_delay", problem("out_of_range", "1", "3")),
        ({"supply_line": 101}, "supply_line", problem("out_of_range", "0", "100")),
        ({"starting_backlog": 101}, "starting_backlog", problem("out_of_range", "0", "100")),
        ({"guided_weeks": -1}, "guided_weeks", problem("out_of_range", "0", "20")),
        (
            {"holding_cost": "100.01"},
            "holding_cost",
            problem("out_of_range", "0.00", "100.00", 2),
        ),
        (
            {"holding_cost": "0.505"},
            "holding_cost",
            problem("too_many_decimal_places", "0.00", "100.00", 2),
        ),
        (
            {"backorder_cost": "abc"},
            "backorder_cost",
            problem("not_a_number", "0.00", "100.00", 2),
        ),
        (
            {"guided_weeks": 5},
            "guided_weeks",
            problem("guided_weeks_not_before_demand_change", "0", "4"),
        ),
        (
            {"weeks": 4, "guided_weeks": 4},
            "guided_weeks",
            problem("guided_weeks_leave_no_weeks_to_play", "0", "3"),
        ),
        (
            {"starting_backlog": 3},
            "starting_backlog",
            problem("starting_inventory_and_backlog", None, None),
        ),
    ],
)
async def test_each_range_error_carries_its_range_and_stores_nothing(klass, draft, field, expected):
    session_id = await new_session(klass)
    before = stored(session_id)
    status, code, fields = refusal(await save(session_id, draft))
    assert (status, code) == (422, "invalid_settings")
    assert fields[field] == expected
    assert stored(session_id) == before
    # The check route says the same, and stores nothing either.
    checked = await check(session_id, draft)
    assert checked.status_code == 200
    assert checked.json()["errors"][field] == expected
    assert stored(session_id) == before


@pytest.mark.parametrize(
    ("draft", "code", "field", "values"),
    [
        (
            {"supply_line": 5},
            "supply_line_differs_from_demand",
            "supply_line",
            {"supply_line": "5", "starting_demand": "4"},
        ),
        (
            {"backorder_cost": "0.50"},
            "backorder_not_above_holding",
            "backorder_cost",
            {"backorder_cost": "0.50", "holding_cost": "0.50"},
        ),
        (
            {"weeks": 20},
            "too_few_weeks_for_demand_change",
            "weeks",
            {"arrival_week": "21", "weeks": "20"},
        ),
        (
            {"max_order": 50},
            "max_order_may_bind",
            "max_order",
            {"max_order": "50", "peak_demand": "8", "threshold": "80"},
        ),
    ],
)
async def test_each_warning_is_shown_and_never_blocks(klass, draft, code, field, values):
    session_id = await new_session(klass)
    expected = {"code": code, "field": field, "values": values}
    checked = await check(session_id, draft)
    assert checked.json() == {"errors": {}, "warnings": [expected]}
    response = await save(session_id, draft)
    assert response.status_code == 200
    assert response.json()["settings_warnings"] == [expected]


async def test_a_classic_session_has_no_warning(klass):
    session_id = await new_session(klass)
    body = (await call(LECTURER, "GET", f"/api/class-sessions/{session_id}")).json()
    assert body["settings_warnings"] == []


async def test_a_setting_with_an_error_has_no_warning_beside_it(klass):
    session_id = await new_session(klass)
    # 0 is out of range and would also be a low maximum Order: the error alone stands.
    checked = (await check(session_id, {"max_order": 0, "supply_line": 5})).json()
    assert list(checked["errors"]) == ["max_order"]
    assert [w["field"] for w in checked["warnings"]] == ["supply_line"]


async def test_a_mistyped_setting_hides_no_error_or_warning_elsewhere(klass):
    session_id = await new_session(klass)
    checked = (
        await check(session_id, {"shipping_delay": 0, "order_delay": 4, "supply_line": 5})
    ).json()
    assert checked["errors"] == {
        "shipping_delay": problem("out_of_range", "1", "3"),
        "order_delay": problem("out_of_range", "1", "3"),
    }
    assert [w["field"] for w in checked["warnings"]] == ["supply_line"]


async def test_settings_are_judged_before_the_dates(klass):
    session_id = await new_session(klass)
    bad_dates = {**PLAN, "play_deadline": PLAN["start_at"] - DAY}
    status, code, _ = refusal(await save(session_id, {"order_delay": 4}, dates=bad_dates))
    assert (status, code) == (422, "invalid_settings")


async def test_once_locked_settings_do_not_change_and_the_check_is_refused(klass, monkeypatch):
    session_id = await new_session(klass)
    assert (await save(session_id, {}, dates=PLAN)).status_code == 200
    at(monkeypatch, PLAN["start_at"] + DAY)
    status, code, fields = refusal(await save(session_id, {"order_delay": 3}))
    assert (status, code, fields) == (409, "session_locked", {"game_settings": "locked"})
    assert stored(session_id).order_delay == 2
    status, code, fields = refusal(await check(session_id, {"order_delay": 3}))
    assert (status, code, fields) == (409, "session_locked", {"game_settings": "locked"})
    # The settings resent as they stand still save, so deadlines can move after the start.
    resend = {
        key: value
        for key, value in stored(session_id).model_dump(mode="json").items()
        if key in service.EDITABLE_SETTINGS
    }
    assert (await save(session_id, resend)).status_code == 200


async def test_an_assistant_may_not_check_or_change_settings(klass):
    session_id = await new_session(klass)
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")
    assert (await check(session_id, {"weeks": 30}, email=ASSISTANT)).status_code == 403
    assert (await save(session_id, {"weeks": 30}, email=ASSISTANT)).status_code == 403
    assert stored(session_id).weeks == 36


async def test_an_unknown_setting_is_refused(klass):
    session_id = await new_session(klass)
    status, code, fields = refusal(await save(session_id, {"colour": "red"}))
    assert (status, code, fields) == (
        422,
        "invalid_settings",
        {"colour": problem("not_editable", None, None)},
    )


@pytest.mark.parametrize(
    "draft",
    [
        {"roles": ["retailer", "factory"]},
        {"schema_version": 1},
        {"capacity": {"retailer": 6}},
    ],
)
async def test_settings_this_screen_does_not_own_are_refused(klass, draft):
    # The chain is the engine's; capacity is Story 5.15's. The Demand pattern and seed are
    # editable since Story 5.4 (`test_demand.py`).
    session_id = await new_session(klass)
    before = stored(session_id)
    status, code, fields = refusal(await save(session_id, {**draft, "weeks": 30}))
    (key,) = draft
    assert (status, code, fields) == (
        422,
        "invalid_settings",
        {key: problem("not_editable", None, None)},
    )
    assert stored(session_id) == before
    assert (await check(session_id, draft)).json()["errors"] == {
        key: problem("not_editable", None, None)
    }
