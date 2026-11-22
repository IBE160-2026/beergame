"""An own Replay scenario on a Class session (Story 10.2, FR-49, FR-12, FR-18, FR-66, AD-4,
AD-12): judged by the engine's template validation, warned about when it probably makes the
Replay easier, stored on «Lagre Klasseøkt», pinned at the lock and copied with the session. The
api's clock is fixed and the sweep is handed its `now`; the database clock is never read."""

import json
from datetime import timedelta
from decimal import Decimal

import pytest

from app.engine import GameSettings, IntRange, ReplayTemplate, default_replay_template
from app.engine.demand import DemandFixed, DemandRandom, DemandStep, DemandStepNoise
from app.modules.ops import sweep
from app.modules.sessions import service
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import clock, klass
from tests.classes.test_staff import ASSISTANT, call, put_staff
from tests.messaging.helpers import rows
from tests.sessions.test_dates import PLAN, START, iso, new_session, refusal
from tests.sessions.test_rerun import copy, flag

__all__ = ["clock", "klass"]

CLASSIC = GameSettings()
EXACT = service.class_game_template(CLASSIC).model_dump(mode="json")
"""The Class game's exact Classic settings as an own scenario's fields."""
OWN = {
    key: value
    for key, value in {
        **EXACT,
        "weeks": {"minimum": 30, "maximum": 40},
        "guided_weeks": 0,
        "demand": {
            "kind": "step",
            "start": 4,
            "new_level": 12,
            "change_week": {"minimum": 6, "maximum": 10},
            "spread": 3,
        },
    }.items()
    if key in service.REPLAY_EDITABLE
}
"""A harder own scenario: a larger step, more variation, ranged length and step Week."""


@pytest.fixture(autouse=True)
def _empty(ai_db, games_db):
    """No model config (Rule-based sessions) and no Games."""


async def save(session_id: str, choice: str | None, template: dict | None = None, **extra):
    body: dict = {"ai_mode": "rule_based", **extra}
    if choice is not None:
        body["replay_scenario"] = choice
    if template is not None:
        body["replay_template"] = template
    return await call(LECTURER, "PUT", f"/api/class-sessions/{session_id}", json=body)


def stored(session_id: str) -> tuple:
    return rows(
        "SELECT replay_scenario, replay_template FROM class_sessions WHERE id = %s", session_id
    )[0]


def own(**changes) -> dict:
    return {**OWN, **changes}


# --- The warning list, one rule at a time (pure). ---


def codes(template: dict, settings: GameSettings = CLASSIC) -> list[tuple[str, str]]:
    found = service.replay_warnings(ReplayTemplate.model_validate(template), settings)
    return [(w.code, w.field) for w in found]


BASE = {**EXACT, "guided_weeks": 0}
"""The Class game's exact settings without Guided Weeks: no warning at all."""


def test_the_class_games_exact_settings_without_guided_weeks_warn_of_nothing():
    assert codes(BASE) == []


def test_any_guided_weeks_warn_by_their_highest_value():
    assert codes(EXACT) == [("replay_guided_weeks", "guided_weeks")]
    assert codes({**BASE, "guided_weeks": {"minimum": 0, "maximum": 2}}) == [
        ("replay_guided_weeks", "guided_weeks")
    ]


def test_a_shorter_delay_warns_by_its_lowest_value_per_delay():
    assert codes({**BASE, "order_delay": 1, "production_delay": {"minimum": 1, "maximum": 3}}) == [
        ("replay_delay_shorter", "order_delay"),
        ("replay_delay_shorter", "production_delay"),
    ]
    assert codes({**BASE, "shipping_delay": 3}) == []
    warning = service.replay_warnings(
        ReplayTemplate.model_validate({**BASE, "order_delay": 1}), CLASSIC
    )[0]
    assert warning.values == {"replay": "1", "class_game": "2"}


def test_a_higher_starting_inventory_warns_by_its_highest_value():
    assert codes({**BASE, "starting_inventory": {"minimum": 0, "maximum": 13}}) == [
        ("replay_inventory_higher", "starting_inventory")
    ]
    assert codes({**BASE, "starting_inventory": 6}) == []


def test_lower_demand_warns_by_the_peak_level():
    lower = {**BASE, "demand": {**BASE["demand"], "new_level": 7}}
    assert codes(lower) == [("replay_demand_lower", "demand")]
    random = {**BASE, "demand": {"kind": "random", "mean": 8, "spread": 2}}
    # Random demand at the old peak: not lower, but the step is gone.
    assert codes(random) == [("replay_demand_no_change", "demand")]


def test_less_variable_demand_warns_against_the_class_games_spread():
    noisy = GameSettings(
        demand=DemandStepNoise(kind="step+noise", start=4, new_level=8, change_week=5, spread=3),
        demand_seed=1,
    )
    assert codes({**BASE, "demand": {**BASE["demand"], "spread": 2}}, noisy) == [
        ("replay_demand_less_variable", "demand")
    ]
    assert codes({**BASE, "demand": {**BASE["demand"], "spread": 3}}, noisy) == []
    random = GameSettings(demand=DemandRandom(kind="random", mean=6, spread=2), demand_seed=1)
    assert codes({**BASE, "demand": {"kind": "random", "mean": 6, "spread": 0}}, random) == [
        ("replay_demand_less_variable", "demand")
    ]


def test_a_fixed_series_that_stops_changing_warns():
    series = GameSettings(demand=DemandFixed(kind="fixed", values=(4,) * 4 + (8,) * 32))
    flat = {**BASE, "demand": {"kind": "fixed", "values": [8] * 36, "spread": 0}}
    assert codes(flat, series) == [("replay_demand_no_change", "demand")]
    assert codes({**BASE, "demand": {"kind": "fixed", "values": [4, 8], "spread": 0}}, series) == []


def test_the_class_game_template_maps_each_pattern_kind():
    step = service.class_game_template(CLASSIC).demand
    assert (step.kind, step.change_week, step.spread) == ("step", 5, 0)
    plain = GameSettings(demand=DemandStep(kind="step", start=3, new_level=9, change_week=7))
    assert service.class_game_template(plain).demand.new_level == 9
    fixed = GameSettings(demand=DemandFixed(kind="fixed", values=(5,) * 36))
    assert service.class_game_template(fixed).demand.spread == 0
    exact = service.class_game_template(CLASSIC)
    assert (exact.weeks, exact.guided_weeks, exact.holding_cost) == (36, 4, Decimal("0.50"))


# --- Judging a draft (pure). ---


def test_a_draft_names_each_problem_with_its_range():
    _, problems, _ = service.judge_replay_template(
        CLASSIC, own(weeks="abc", order_delay=9, roles=["retailer"])
    )
    assert problems["weeks"].code == "not_a_number"
    assert (problems["weeks"].minimum, problems["weeks"].maximum) == ("1", "100")
    assert problems["order_delay"].code == "out_of_range"
    assert problems["order_delay"].maximum == "3"
    assert problems["roles"].code == "not_editable"


def test_a_change_week_after_the_shortest_game_is_refused():
    draft = own(
        weeks={"minimum": 20, "maximum": 40},
        demand={**OWN["demand"], "change_week": 25},
    )
    template, problems, _ = service.judge_replay_template(CLASSIC, draft)
    assert template is None
    assert problems["demand.change_week"].code == "demand_change_week_outside_game"


def test_a_stored_own_template_follows_the_game_settings_and_a_locked_change_is_refused():
    stored_own = ReplayTemplate.model_validate({**EXACT, **OWN}).model_dump(mode="json")
    row = {"replay_scenario": "own", "replay_template": stored_own}
    capped = CLASSIC.model_copy(update={"capacity": {"retailer": 20}})
    choice, template = service._replay_to_store(row, capped, "own", None, locked=False)
    assert choice == "own" and template["capacity"] == {"retailer": 20}
    assert template["weeks"] == {"minimum": 30, "maximum": 40}
    assert service._replay_to_store(row, CLASSIC, "own", None, locked=True) is None
    default = {"replay_scenario": "default", "replay_template": None}
    with pytest.raises(service.SessionLocked):
        service._replay_to_store(default, CLASSIC, "own", None, locked=True)
    with pytest.raises(service.InvalidReplayScenario):
        service._replay_to_store(default, CLASSIC, "own", None, locked=False)


def test_no_demand_warning_stands_beside_a_demand_error():
    # A lower level (a warning on its own) with a change Week after the Game (an error).
    lower = {"kind": "step", "start": 4, "new_level": 3, "change_week": 99, "spread": 0}
    _, problems, risky = service.judge_replay_template(CLASSIC, own(demand=lower))
    assert "demand.change_week" in problems
    assert [w for w in risky if w.field == "demand"] == []


# --- Over the api. ---


async def test_an_own_scenario_is_judged_stored_and_read_back(klass):
    session_id = await new_session(klass)

    # The form opens on the Class game's exact settings: accepted, with fixed values.
    response = await save(session_id, "own", {k: v for k, v in EXACT.items() if k in OWN})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["replay_scenario"] == "own"
    assert body["replay_template"]["weeks"] == 36
    assert body["replay_template"]["demand"]["change_week"] == 5
    assert [w["code"] for w in body["replay_warnings"]] == ["replay_guided_weeks"]

    # A single step Week and length, and a shorter delay: stored, warned, not blocked.
    single = own(weeks=30, order_delay=1, demand={**OWN["demand"], "change_week": 8})
    body = (await save(session_id, "own", single)).json()
    assert (body["replay_template"]["weeks"], body["replay_template"]["order_delay"]) == (30, 1)
    assert [(w["code"], w["field"]) for w in body["replay_warnings"]] == [
        ("replay_delay_shorter", "order_delay")
    ]
    choice, template = stored(session_id)
    assert choice == "own" and template["demand"]["change_week"] == 8

    # Ranged: stored as ranges; the check answers the same warnings without storing.
    body = (await save(session_id, "own", OWN)).json()
    assert body["replay_template"]["weeks"] == {"minimum": 30, "maximum": 40}
    assert body["replay_warnings"] == []
    checked = await call(
        LECTURER,
        "POST",
        f"/api/class-sessions/{session_id}/replay-scenario-check",
        json={"replay_template": own(order_delay=1, weeks="x")},
    )
    assert checked.status_code == 200
    assert set(checked.json()["errors"]) == {"weeks"}
    assert stored(session_id)[1]["weeks"] == {"minimum": 30, "maximum": 40}

    # A bad value: refused with the field and its range; nothing changes.
    refused = await save(session_id, "own", own(order_delay=9))
    status, code, fields = refusal(refused)
    assert (status, code, fields["order_delay"]["maximum"]) == (422, "invalid_replay_scenario", "3")
    # `own` with no template keeps the stored one; a save with no scenario keeps it too.
    assert (await save(session_id, "own")).json()["replay_template"]["weeks"]["maximum"] == 40
    assert (await save(session_id, None)).json()["replay_scenario"] == "own"

    # Back to the default: the own template is dropped and the default derived again.
    body = (await save(session_id, "default")).json()
    assert body["replay_scenario"] == "default" and body["replay_warnings"] == []
    assert body["replay_template"] == default_replay_template(CLASSIC).model_dump(mode="json")
    assert stored(session_id) == ("default", None)
    missing = await save(session_id, "own")
    assert refusal(missing)[2]["replay_template"]["code"] == "required"

    # An Assistant lecturer reads it and may not save it.
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")
    seen = await call(ASSISTANT, "GET", f"/api/class-sessions/{session_id}")
    assert seen.json()["can_manage"] is False
    denied = await call(
        ASSISTANT,
        "PUT",
        f"/api/class-sessions/{session_id}",
        json={"ai_mode": "rule_based", "replay_scenario": "own", "replay_template": OWN},
    )
    assert denied.status_code == 403


async def test_the_lock_pins_the_own_template_and_freezes_it(klass, monkeypatch):
    session_id = await new_session(klass)
    response = await save(session_id, "own", OWN, dates=iso(PLAN))
    assert response.status_code == 200, response.text
    assert (await sweep.run(START + timedelta(minutes=1)))["sessions.lock"] == 1
    (snapshot,) = rows("SELECT snapshot FROM class_sessions WHERE id = %s", session_id)[0]
    pinned = ReplayTemplate.model_validate(snapshot["session_runtime"]["pins"]["replay_template"])
    assert pinned.weeks == IntRange(minimum=30, maximum=40)
    assert pinned.demand.new_level == 12

    # Saved as it stands: fine. A change of template or choice: 409 `session_locked`.
    assert (await save(session_id, "own", OWN)).status_code == 200
    for refused in (
        await save(session_id, "own", own(weeks=31)),
        await save(session_id, "default"),
    ):
        assert refusal(refused) == (409, "session_locked", {"replay_scenario": "locked"})
    checked = await call(
        LECTURER,
        "POST",
        f"/api/class-sessions/{session_id}/replay-scenario-check",
        json={"replay_template": OWN},
    )
    assert checked.status_code == 409

    # A copy takes the own scenario along (FEATURE_RERUN), judged again for its own settings.
    flag(monkeypatch, True)
    copied = await copy(klass, session_id)
    assert copied.status_code == 201, copied.text
    assert copied.json()["replay_scenario"] == "own"
    assert copied.json()["replay_template"] == pinned.model_dump(mode="json")
    assert stored(copied.json()["id"])[0] == "own"

    # A template the engine now refuses is not copied: the copy gets the default.
    broken = {**pinned.model_dump(mode="json"), "max_order": 0}
    execute(
        "UPDATE class_sessions SET replay_template = %s::jsonb WHERE id = %s",
        json.dumps(broken),
        session_id,
    )
    fallback = await copy(klass, session_id)
    assert fallback.json()["replay_scenario"] == "default"
