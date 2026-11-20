"""Information visibility on the Klasseøkt (Story 5.16, FR-83, AD-1, AD-3, AD-4, AD-17): behind
`FEATURE_INFO_VISIBILITY`, two views (the Seat directly upstream, the Seat directly downstream),
both off by default, stored in the session's `GameSettings` (schema version 2) and frozen into
every Class game's snapshot by the lock. Off, the api refuses a view with `feature_disabled` and
nothing else changes. The api's clock is fixed and the sweep is handed its `now`; the database
clock is never read."""

import json

import pytest

from app.engine import GameSettings
from app.modules.ops import sweep
from app.platform.config import get_settings
from tests.classes.test_classes import LECTURER
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import clock, klass
from tests.classes.test_staff import call
from tests.messaging.helpers import rows
from tests.sessions.test_dates import START, new_session, refusal
from tests.sessions.test_lock import MINUTE
from tests.sessions.test_open_games import confirmed, games_of
from tests.sessions.test_settings import check, problem, save, stored

__all__ = ["clock", "klass"]

OFF = {"upstream": False, "downstream": False}
UP = {"upstream": True, "downstream": False}
BOTH = {"upstream": True, "downstream": True}


@pytest.fixture(autouse=True)
def _empty(ai_db, mail_db, games_db):
    """No model config, no notices and no Games."""


def flag(monkeypatch, on: bool) -> None:
    monkeypatch.setenv("FEATURE_INFO_VISIBILITY", "true" if on else "false")
    get_settings.cache_clear()


async def read(session_id: str) -> dict:
    return (await call(LECTURER, "GET", f"/api/class-sessions/{session_id}")).json()


async def test_both_views_are_off_by_default_and_each_can_be_switched_on(klass, monkeypatch):
    flag(monkeypatch, True)
    session_id = await new_session(klass)
    body = await read(session_id)
    assert body["info_visibility_enabled"] is True
    assert body["game_settings"]["schema_version"] == 2
    assert body["game_settings"]["info_visibility"] == OFF
    assert body["is_classic"] is True
    response = await save(session_id, {"info_visibility": {"upstream": True}})
    assert response.status_code == 200
    saved = response.json()
    assert saved["game_settings"]["info_visibility"] == UP
    assert saved["is_classic"] is False
    # It changes no arithmetic, so it raises no warning.
    assert saved["settings_warnings"] == []
    assert stored(session_id).info_visibility.upstream is True
    assert (await save(session_id, {"info_visibility": BOTH})).status_code == 200
    assert stored(session_id).info_visibility == GameSettings(info_visibility=BOTH).info_visibility
    assert (await check(session_id, {"info_visibility": BOTH})).json()["errors"] == {}
    # Switched off again: the Classic preset once more.
    assert (await save(session_id, {"info_visibility": OFF})).status_code == 200
    assert (await read(session_id))["is_classic"] is True


async def test_settings_stored_before_the_field_read_with_both_views_off(klass, monkeypatch):
    flag(monkeypatch, True)
    session_id = await new_session(klass)
    old = stored(session_id).model_dump(mode="json")
    old["schema_version"] = 1
    del old["info_visibility"]
    execute(
        "UPDATE class_sessions SET game_settings = %s::jsonb WHERE id = %s",
        json.dumps(old),
        session_id,
    )
    body = await read(session_id)
    assert body["game_settings"]["schema_version"] == 2
    assert body["game_settings"]["info_visibility"] == OFF
    # A save writes the current version.
    assert (await save(session_id, {"info_visibility": UP})).status_code == 200
    (row,) = rows("SELECT game_settings FROM class_sessions WHERE id = %s", session_id)
    assert (row[0]["schema_version"], row[0]["info_visibility"]) == (2, UP)


@pytest.mark.parametrize(
    "views",
    [{"upstream": "yes"}, {"upstream": 1}, {"left": True}, 5, None, [True, False]],
)
async def test_a_view_that_is_not_a_boolean_is_refused(klass, monkeypatch, views):
    flag(monkeypatch, True)
    session_id = await new_session(klass)
    before = stored(session_id)
    status, code, fields = refusal(await save(session_id, {"info_visibility": views}))
    assert (status, code, fields) == (
        422,
        "invalid_settings",
        {"info_visibility": problem("invalid", None, None)},
    )
    assert stored(session_id) == before
    errors = (await check(session_id, {"info_visibility": views})).json()["errors"]
    assert errors == {"info_visibility": problem("invalid", None, None)}


async def test_with_the_flag_off_a_view_is_refused_and_nothing_else_changes(klass, monkeypatch):
    flag(monkeypatch, False)
    session_id = await new_session(klass)
    body = await read(session_id)
    assert body["info_visibility_enabled"] is False
    assert body["game_settings"]["info_visibility"] == OFF
    before = stored(session_id)
    for views in ({"upstream": True}, {"downstream": True}, BOTH):
        status, code, fields = refusal(await save(session_id, {"info_visibility": views}))
        assert (status, code, fields) == (
            422,
            "feature_disabled",
            {"info_visibility": "feature_disabled"},
        )
        errors = (await check(session_id, {"info_visibility": views})).json()["errors"]
        assert errors == {"info_visibility": problem("feature_disabled", None, None)}
    assert stored(session_id) == before
    # Every view off is the default: other settings save as before.
    assert (await save(session_id, {"info_visibility": OFF, "weeks": 30})).status_code == 200
    assert (await save(session_id, {"weeks": 31})).status_code == 200
    assert (stored(session_id).weeks, stored(session_id).info_visibility.on) == (31, False)


async def test_a_view_stored_before_the_flag_went_off_is_kept(klass, monkeypatch):
    flag(monkeypatch, True)
    session_id = await new_session(klass)
    assert (await save(session_id, {"info_visibility": UP})).status_code == 200
    flag(monkeypatch, False)
    assert (await read(session_id))["info_visibility_enabled"] is False
    assert (await save(session_id, {"weeks": 30})).status_code == 200
    # Sent back unchanged, in full or in part, it is no change.
    assert (await save(session_id, {"info_visibility": UP, "weeks": 31})).status_code == 200
    assert (await save(session_id, {"info_visibility": {"upstream": True}})).status_code == 200
    assert (stored(session_id).weeks, stored(session_id).info_visibility.upstream) == (31, True)
    # Another view is refused; every view off is allowed.
    status, code, _ = refusal(await save(session_id, {"info_visibility": BOTH}))
    assert (status, code) == (422, "feature_disabled")
    assert (await save(session_id, {"info_visibility": OFF})).status_code == 200
    assert stored(session_id).info_visibility.on is False


async def test_with_the_flag_off_one_view_of_two_can_be_switched_off(klass, monkeypatch):
    flag(monkeypatch, True)
    session_id = await new_session(klass)
    assert (await save(session_id, {"info_visibility": BOTH})).status_code == 200
    flag(monkeypatch, False)
    assert (await save(session_id, {"info_visibility": UP})).status_code == 200
    assert stored(session_id).info_visibility == GameSettings(info_visibility=UP).info_visibility
    # Switching the other back on is a new view.
    status, code, _ = refusal(await save(session_id, {"info_visibility": BOTH}))
    assert (status, code) == (422, "feature_disabled")


@pytest.mark.parametrize(
    "views", [{"upstream": True, "left": True}, {"upstream": True, "downstream": "x"}]
)
async def test_with_the_flag_off_a_malformed_value_is_still_invalid(klass, monkeypatch, views):
    flag(monkeypatch, False)
    session_id = await new_session(klass)
    status, code, fields = refusal(await save(session_id, {"info_visibility": views}))
    assert (status, code, fields) == (
        422,
        "invalid_settings",
        {"info_visibility": problem("invalid", None, None)},
    )


async def test_the_lock_freezes_the_views_into_every_class_game(klass, monkeypatch):
    flag(monkeypatch, True)
    session_id, _ = await confirmed(klass, 5)
    assert (await save(session_id, {"info_visibility": UP})).status_code == 200
    assert (await sweep.run(START + MINUTE))["sessions.lock"] == 1
    ((snapshot,),) = rows("SELECT snapshot FROM class_sessions WHERE id = %s", session_id)
    assert snapshot["settings"]["info_visibility"] == UP
    games = games_of(session_id)
    assert len(games) == 2
    assert all(game[4]["info_visibility"] == UP for game in games)
    status, code, fields = refusal(await save(session_id, {"info_visibility": BOTH}))
    assert (status, code, fields) == (409, "session_locked", {"game_settings": "locked"})
    # With the flag off as well, a locked session still answers that it is locked.
    flag(monkeypatch, False)
    status, code, _ = refusal(await save(session_id, {"info_visibility": BOTH}))
    assert (status, code) == (409, "session_locked")
    assert stored(session_id).info_visibility == GameSettings(info_visibility=UP).info_visibility
