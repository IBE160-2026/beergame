"""The default Replay scenario of a Class session (Story 10.1, FR-49, AD-4, AD-23): the session
stores only the choice, the Klasseøkt reads the template derived from the current Game settings,
and the lock pins the template of the settings it freezes. The api's clock is fixed and the sweep
is handed its `now`; the database clock is never read."""

from datetime import timedelta

import pytest

from app.engine import GameSettings, IntRange, ReplayTemplate, default_replay_template
from app.modules.ops import sweep
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import clock, klass
from tests.classes.test_staff import ASSISTANT, call, put_staff
from tests.messaging.helpers import rows
from tests.sessions.test_dates import PLAN, START, new_session
from tests.sessions.test_settings import save

__all__ = ["clock", "klass"]

EDITED = {
    "demand": {"kind": "step+noise", "start": 5, "new_level": 9, "change_week": 7, "spread": 3},
    "shipping_delay": 3,
}


@pytest.fixture(autouse=True)
def _empty(ai_db, games_db):
    """No model config (Rule-based sessions) and no Games."""


def stored_row(session_id: str) -> tuple:
    return rows(
        "SELECT replay_scenario, game_settings, snapshot FROM class_sessions WHERE id = %s",
        session_id,
    )[0]


async def test_the_klasseokt_reads_the_default_derived_from_the_current_settings(klass):
    session_id = await new_session(klass)
    body = (await call(LECTURER, "GET", f"/api/class-sessions/{session_id}")).json()
    assert body["replay_scenario"] == "default"
    classic = default_replay_template(GameSettings())
    assert ReplayTemplate.model_validate(body["replay_template"]) == classic
    assert body["replay_template"]["weeks"] == {"minimum": 30, "maximum": 40}

    # An edit before the Start date: the template follows, and only the choice is stored.
    response = await save(session_id, EDITED)
    assert response.status_code == 200
    template = ReplayTemplate.model_validate(response.json()["replay_template"])
    assert (template.demand.start, template.demand.new_level, template.demand.spread) == (5, 9, 3)
    assert template.demand.change_week == IntRange(minimum=5, maximum=12)
    assert template.shipping_delay == 3
    choice, _, snapshot = stored_row(session_id)
    assert (choice, snapshot) == ("default", None)
    columns = rows(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'class_sessions'"
    )
    assert not any("template" in name for (name,) in columns)

    # An Assistant lecturer reads it too.
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")
    seen = (await call(ASSISTANT, "GET", f"/api/class-sessions/{session_id}")).json()
    assert seen["replay_template"] == response.json()["replay_template"]


async def test_the_lock_pins_the_template_of_the_settings_it_freezes(klass):
    session_id = await new_session(klass)
    assert (await save(session_id, EDITED, dates=PLAN)).status_code == 200
    assert (await sweep.run(START + timedelta(minutes=1)))["sessions.lock"] == 1
    _, settings, snapshot = stored_row(session_id)
    pinned = snapshot["session_runtime"]["pins"]["replay_template"]
    wanted = default_replay_template(GameSettings.model_validate(settings))
    assert ReplayTemplate.model_validate(pinned) == wanted
    assert pinned["demand"]["spread"] == 3 and pinned["shipping_delay"] == 3
    # The Klasseøkt now reads the pinned template, not a new derivation: a pin that differs from
    # what the settings would give now is what it shows.
    execute(
        "UPDATE class_sessions SET snapshot = jsonb_set(snapshot, "
        "'{session_runtime,pins,replay_template,weeks}', '{\"minimum\": 31, \"maximum\": 33}') "
        "WHERE id = %s",
        session_id,
    )
    body = (await call(LECTURER, "GET", f"/api/class-sessions/{session_id}")).json()
    assert body["replay_template"] == {**pinned, "weeks": {"minimum": 31, "maximum": 33}}

    # A session locked before Story 10.1 has no pin: it shows the default of its frozen settings.
    execute(
        "UPDATE class_sessions SET snapshot = snapshot #- '{session_runtime,pins,replay_template}' "
        "WHERE id = %s",
        session_id,
    )
    body = (await call(LECTURER, "GET", f"/api/class-sessions/{session_id}")).json()
    assert body["locked"] is True
    assert body["replay_template"] == pinned
