"""A shipping capacity on the Klasseøkt (Story 5.15, FR-12, AD-4, AD-17): behind
`FEATURE_CAPACITY`, one Role or every Role capped per Week, judged by the engine (1 to 100, a
non-blocking warning below peak demand), stored in the session's `GameSettings` and frozen by the
lock. Off, the api refuses a capacity with `feature_disabled` and nothing else changes. The api's
clock is fixed; the database clock is never read."""

from datetime import timedelta

import pytest

from app.modules.ops import sweep
from app.platform.config import get_settings
from tests.classes.test_classes import LECTURER
from tests.classes.test_roster_upload import clock, klass
from tests.classes.test_staff import call
from tests.messaging.helpers import rows
from tests.sessions.test_dates import PLAN, START, new_session, refusal
from tests.sessions.test_settings import check, problem, save, stored

__all__ = ["clock", "klass"]

ALL = {"retailer": 6, "wholesaler": 6, "distributor": 6, "factory": 6}
BELOW_PEAK = {"code": "capacity_below_peak_demand", "field": "capacity.retailer"}


@pytest.fixture(autouse=True)
def _empty(ai_db, mail_db, games_db):
    """No model config, no notices and no Games."""


def flag(monkeypatch, on: bool) -> None:
    monkeypatch.setenv("FEATURE_CAPACITY", "true" if on else "false")
    get_settings.cache_clear()


async def read(session_id: str) -> dict:
    return (await call(LECTURER, "GET", f"/api/class-sessions/{session_id}")).json()


async def test_capacity_is_off_by_default_and_one_role_can_be_capped(klass, monkeypatch):
    flag(monkeypatch, True)
    session_id = await new_session(klass)
    body = await read(session_id)
    assert body["capacity_enabled"] is True
    assert "capacity" not in body["game_settings"]
    response = await save(session_id, {"capacity": {"retailer": 6}})
    assert response.status_code == 200
    saved = response.json()
    assert saved["game_settings"]["capacity"] == {"retailer": 6}
    assert saved["is_classic"] is False
    # Below the step pattern's peak of 8: a warning that never blocks.
    (warning,) = saved["settings_warnings"]
    assert {"code": warning["code"], "field": warning["field"]} == BELOW_PEAK
    assert warning["values"] == {"role": "retailer", "capacity": "6", "peak_demand": "8"}
    assert stored(session_id).capacity_of("retailer") == 6
    # Switched off again: no Seat is capped.
    assert (await save(session_id, {"capacity": None})).status_code == 200
    assert stored(session_id).capacity is None


async def test_every_role_can_be_capped_and_the_check_warns_for_each(klass, monkeypatch):
    flag(monkeypatch, True)
    session_id = await new_session(klass)
    checked = (await check(session_id, {"capacity": ALL})).json()
    assert checked["errors"] == {}
    assert [w["field"] for w in checked["warnings"]] == [f"capacity.{role}" for role in ALL]
    assert (await save(session_id, {"capacity": ALL})).status_code == 200
    assert stored(session_id).capacity == ALL


@pytest.mark.parametrize(
    ("capacity", "field", "expected"),
    [
        ({"retailer": 0}, "capacity.retailer", problem("out_of_range", "1", "100")),
        ({"factory": 101}, "capacity.factory", problem("out_of_range", "1", "100")),
        ({"retailer": -2}, "capacity.retailer", problem("out_of_range", "1", "100")),
        ({"retailer": "x"}, "capacity.retailer", problem("not_a_number", "1", "100")),
        ({"retailer": 2.5}, "capacity.retailer", problem("not_a_number", "1", "100")),
        ({"boss": 5}, "capacity", problem("invalid", None, None)),
        (7, "capacity", problem("invalid", None, None)),
    ],
)
async def test_a_capacity_that_is_not_a_whole_number_above_0_is_refused(
    klass, monkeypatch, capacity, field, expected
):
    flag(monkeypatch, True)
    session_id = await new_session(klass)
    before = stored(session_id)
    status, code, fields = refusal(await save(session_id, {"capacity": capacity}))
    assert (status, code) == (422, "invalid_settings")
    assert fields == {field: expected}
    assert stored(session_id) == before
    assert (await check(session_id, {"capacity": capacity})).json()["errors"] == {field: expected}


async def test_with_the_flag_off_a_capacity_is_refused_and_nothing_else_changes(klass, monkeypatch):
    flag(monkeypatch, False)
    session_id = await new_session(klass)
    body = await read(session_id)
    assert body["capacity_enabled"] is False
    assert "capacity" not in body["game_settings"]
    before = stored(session_id)
    status, code, fields = refusal(await save(session_id, {"capacity": {"retailer": 6}}))
    assert (status, code, fields) == (422, "feature_disabled", {"capacity": "feature_disabled"})
    assert stored(session_id) == before
    checked = (await check(session_id, {"capacity": {"retailer": 6}})).json()
    assert checked["errors"] == {"capacity": problem("feature_disabled", None, None)}
    # No capacity, or an empty one, is no capacity: other settings save as before.
    for empty in (None, {}):
        assert (await save(session_id, {"capacity": empty, "weeks": 30})).status_code == 200
    assert (await save(session_id, {"weeks": 31})).status_code == 200
    assert (stored(session_id).weeks, stored(session_id).capacity) == (31, None)


async def test_a_capacity_stored_before_the_flag_went_off_is_kept(klass, monkeypatch):
    flag(monkeypatch, True)
    session_id = await new_session(klass)
    assert (await save(session_id, {"capacity": {"factory": 9}})).status_code == 200
    flag(monkeypatch, False)
    assert (await save(session_id, {"weeks": 30})).status_code == 200
    assert (stored(session_id).weeks, stored(session_id).capacity_of("factory")) == (30, 9)
    # Sent back unchanged it is no change; changed, it is refused.
    resend = {"capacity": {"factory": 9}, "weeks": 32}
    assert (await save(session_id, resend)).status_code == 200
    status, code, _ = refusal(await save(session_id, {"capacity": {"factory": 8}}))
    assert (status, code) == (422, "feature_disabled")
    assert (stored(session_id).weeks, stored(session_id).capacity_of("factory")) == (32, 9)


async def test_the_lock_freezes_the_capacity_and_it_no_longer_changes(klass, monkeypatch):
    flag(monkeypatch, True)
    session_id = await new_session(klass)
    response = await save(session_id, {"capacity": {"retailer": 6}}, dates=PLAN)
    assert response.status_code == 200
    assert (await sweep.run(START + timedelta(minutes=1)))["sessions.lock"] == 1
    (snapshot,) = rows("SELECT snapshot FROM class_sessions WHERE id = %s", session_id)[0]
    assert snapshot["settings"]["capacity"] == {"retailer": 6}
    status, code, fields = refusal(await save(session_id, {"capacity": {"retailer": 7}}))
    assert (status, code, fields) == (409, "session_locked", {"game_settings": "locked"})
    # With the flag off as well, a locked session still answers that it is locked.
    flag(monkeypatch, False)
    status, code, _ = refusal(await save(session_id, {"capacity": {"retailer": 7}}))
    assert (status, code) == (409, "session_locked")
    assert stored(session_id).capacity_of("retailer") == 6
