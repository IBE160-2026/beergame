"""Choosing the Demand pattern and its seed of a Class session (Story 5.4, FR-12, FR-13, AD-1,
AD-3): saved with «Lagre Klasseøkt» and judged by the engine alone, with the allowed range under
each field; the series read back as the engine materialises it, for the staff only; nothing
changes once locked. The api's clock is fixed; the database clock is never read."""

import pytest

from app.engine import GameSettings
from app.engine.demand import SEED_MAX, series
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_roster_upload import clock, klass
from tests.classes.test_staff import ASSISTANT, call, put_staff
from tests.sessions.test_dates import (
    DAY,
    OUTSIDER,
    PLAN,
    STUDENT,
    at,
    new_session,
    refusal,
    student_of,
)
from tests.sessions.test_settings import check, problem, save, stored

__all__ = ["clock", "klass"]

STEP = {"kind": "step", "start": 4, "new_level": 8, "change_week": 5}
RANDOM = {"kind": "random", "mean": 8, "spread": 2}
NOISE = {"kind": "step+noise", "start": 4, "new_level": 8, "change_week": 5, "spread": 2}


@pytest.fixture(autouse=True)
def _empty_ai(ai_db):
    """No model config: the sessions are Rule-based, which the demand does not care about."""


async def demand_of(session_id: str, email: str = LECTURER):
    return await call(email, "GET", f"/api/class-sessions/{session_id}/demand-series")


@pytest.mark.parametrize(
    "pattern",
    [
        {"kind": "fixed", "values": [4] * 10 + [9] * 26},
        {**STEP, "new_level": 12, "change_week": 7},
        RANDOM,
        NOISE,
    ],
)
async def test_each_pattern_is_stored_and_its_series_is_the_engines(klass, pattern):
    session_id = await new_session(klass)
    seed = stored(session_id).demand_seed
    response = await save(session_id, {"demand": pattern})
    assert response.status_code == 200
    after = stored(session_id)
    assert after.demand.model_dump(mode="json") == pattern
    # The seed drawn at creation is kept when none is sent.
    assert after.demand_seed == seed
    assert response.json()["is_classic"] is False
    body = (await demand_of(session_id)).json()
    assert body == {"demand": list(series(after.demand, 36, seed))}


async def test_the_same_settings_and_seed_always_give_the_same_series(klass):
    session_id = await new_session(klass)
    assert (await save(session_id, {"demand": RANDOM, "demand_seed": 42})).status_code == 200
    first = (await demand_of(session_id)).json()["demand"]
    second = (await demand_of(session_id)).json()["demand"]
    assert first == second == list(series(GameSettings(demand=RANDOM).demand, 36, 42))
    assert len(first) == 36
    assert all(6 <= value <= 10 for value in first)
    # Another seed gives another series.
    assert (await save(session_id, {"demand_seed": 43})).status_code == 200
    assert (await demand_of(session_id)).json()["demand"] != first


async def test_the_classic_series_steps_from_4_to_8_in_week_5(klass):
    session_id = await new_session(klass)
    assert (await demand_of(session_id)).json()["demand"] == [4] * 4 + [8] * 32


@pytest.mark.parametrize(
    ("draft", "field", "expected"),
    [
        (
            {"demand": {"kind": "fixed", "values": [4] * 10}},
            "demand.values",
            problem("fixed_series_length", "36", "36"),
        ),
        (
            {"demand": {"kind": "fixed", "values": []}},
            "demand.values",
            problem("fixed_series_length", "36", "36"),
        ),
        (
            {"weeks": 500, "demand": {**STEP, "change_week": ""}},
            "demand.change_week",
            problem("not_a_number", "1", "36"),
        ),
        (
            {"demand": {"kind": "fixed", "values": [4] * 35 + [101]}},
            "demand.values",
            problem("out_of_range", "0", "100"),
        ),
        (
            {"demand": {"kind": "fixed", "values": [4] * 35 + ["x"]}},
            "demand.values",
            problem("not_a_number", "0", "100"),
        ),
        ({"demand": {**STEP, "start": -1}}, "demand.start", problem("out_of_range", "0", "100")),
        (
            {"demand": {**STEP, "new_level": "åtte"}},
            "demand.new_level",
            problem("not_a_number", "0", "100"),
        ),
        (
            {"demand": {**STEP, "change_week": 40}},
            "demand.change_week",
            problem("demand_change_week_outside_game", "1", "36"),
        ),
        (
            {"demand": {**STEP, "change_week": 0}},
            "demand.change_week",
            problem("out_of_range", "1", "36"),
        ),
        (
            {"weeks": 30, "demand": {**STEP, "change_week": ""}},
            "demand.change_week",
            problem("not_a_number", "1", "30"),
        ),
        (
            {"demand": {**STEP, "change_week": 3}},
            "guided_weeks",
            problem("guided_weeks_not_before_demand_change", "0", "2"),
        ),
        ({"demand": {**RANDOM, "mean": 101}}, "demand.mean", problem("out_of_range", "0", "100")),
        ({"demand": {**RANDOM, "spread": 21}}, "demand.spread", problem("out_of_range", "0", "20")),
        ({"demand": {**NOISE, "spread": -1}}, "demand.spread", problem("out_of_range", "0", "20")),
        (
            {"demand": {"kind": "random", "mean": 8}},
            "demand.spread",
            problem("not_a_number", "0", "20"),
        ),
        ({"demand": {"kind": "wave"}}, "demand", problem("invalid", None, None)),
        ({"demand": {**STEP, "colour": 1}}, "demand", problem("invalid", None, None)),
        ({"demand": "step"}, "demand", problem("invalid", None, None)),
        (
            {"demand": RANDOM, "demand_seed": "x"},
            "demand_seed",
            problem("not_a_number", "0", str(SEED_MAX)),
        ),
        (
            {"demand": RANDOM, "demand_seed": -1},
            "demand_seed",
            problem("out_of_range", "0", str(SEED_MAX)),
        ),
        (
            {"demand": RANDOM, "demand_seed": None},
            "demand_seed",
            problem("demand_seed_required", None, None),
        ),
    ],
)
async def test_each_invalid_pattern_names_its_field_and_range_and_stores_nothing(
    klass, draft, field, expected
):
    session_id = await new_session(klass)
    before = stored(session_id)
    status, code, fields = refusal(await save(session_id, draft))
    assert (status, code) == (422, "invalid_settings")
    assert fields[field] == expected
    assert stored(session_id) == before
    # The check answers the same, and stores nothing either.
    assert (await check(session_id, draft)).json()["errors"][field] == expected
    assert stored(session_id) == before


async def test_an_unreadable_pattern_hides_no_error_elsewhere(klass):
    session_id = await new_session(klass)
    errors = (await check(session_id, {"order_delay": 4, "demand": {**STEP, "start": "x"}})).json()[
        "errors"
    ]
    assert set(errors) == {"order_delay", "demand.start"}


async def test_a_pattern_starting_off_the_supply_line_warns_and_still_saves(klass):
    session_id = await new_session(klass)
    response = await save(session_id, {"demand": {**RANDOM, "mean": 6}})
    assert response.status_code == 200
    assert [w["code"] for w in response.json()["settings_warnings"]] == [
        "supply_line_differs_from_demand"
    ]


async def test_once_locked_the_pattern_and_seed_do_not_change(klass, monkeypatch):
    session_id = await new_session(klass)
    assert (await save(session_id, {}, dates=PLAN)).status_code == 200
    before = stored(session_id)
    at(monkeypatch, PLAN["start_at"] + DAY)
    for draft in ({"demand": RANDOM}, {"demand_seed": 7}):
        status, code, fields = refusal(await save(session_id, draft))
        assert (status, code, fields) == (409, "session_locked", {"game_settings": "locked"})
        status, code, _ = refusal(await check(session_id, draft))
        assert (status, code) == (409, "session_locked")
    assert stored(session_id) == before
    # The pattern and seed resent as they stand still save; the series is still read.
    resend = {"demand": before.demand.model_dump(), "demand_seed": before.demand_seed}
    assert (await save(session_id, resend)).status_code == 200
    assert (await demand_of(session_id)).status_code == 200


async def test_only_the_classes_staff_read_the_series(klass):
    session_id = await new_session(klass)
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")
    assert (await demand_of(session_id, ASSISTANT)).status_code == 200
    # The Assistant reads it, but may not change the pattern.
    assert (await save(session_id, {"demand": RANDOM}, email=ASSISTANT)).status_code == 403
    await student_of(klass)
    await make(OUTSIDER, roles=())
    for email in (STUDENT, OUTSIDER):
        response = await demand_of(session_id, email)
        assert (response.status_code, response.json()["error"]["code"]) == (403, "forbidden")
    assert (
        await call(LECTURER, "GET", "/api/class-sessions/nope/demand-series")
    ).status_code == 403
    # The Student's own read never carries the series, the seed or the Weeks (AD-3).
    assert (await save(session_id, {"demand": RANDOM}, dates=PLAN)).status_code == 200
    [item] = (await call(STUDENT, "GET", "/api/me/class-sessions")).json()["items"]
    assert not {"game_settings", "demand", "demand_seed", "weeks"} & set(item)
