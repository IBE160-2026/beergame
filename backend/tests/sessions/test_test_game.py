"""A Lecturer's private test Game (Story 6.20, FR-87, FR-34, AD-4, AD-12, AD-13, AD-17).

«Start testspill» on the Klasseøkt makes a `lecturer_test` Game on the Class session's current
settings, the Lecturer in the chosen Seat and AI players in the others, and starts it. The Lecturer
plays it through the Student play routes (`authz.own_seat`), and the session stays unlocked.

The rule for later epics: a test Game is in no Class session list, summary, funnel or step. Every
report, statistic and export reads through `reports.scope`, which excludes `lecturer_test`. Here
every such endpoint that exists answers the same with and without the test Game, and no `progress`
step is recorded for it. The api's clock is fixed before the Start date."""

import json

import pytest

from app.modules.games import commands as games_commands
from app.platform.config import get_settings
from tests.classes.test_classes import LECTURER, OTHER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_staff import ASSISTANT, call, put_staff
from tests.classes.test_student_registration import emitted
from tests.messaging.helpers import rows
from tests.sessions.test_lock import MINUTE, _empty
from tests.sessions.test_open_games import confirmed
from tests.sessions.test_rerun import flag
from tests.sessions.test_student_choice import email
from tests.sessions.test_student_home import home

__all__ = ["_empty", "clock", "emitted", "klass"]


async def start_test(session_id: str, role: str = "wholesaler", who: str = LECTURER):
    return await call(
        who, "POST", f"/api/class-sessions/{session_id}/test-game", json={"role": role}
    )


async def class_session(session_id: str, who: str = LECTURER) -> dict:
    response = await call(who, "GET", f"/api/class-sessions/{session_id}")
    assert response.status_code == 200
    return response.json()


async def lists(session_id: str) -> dict:
    """Every Class session list, summary and step that exists, as its readers see it."""
    allocation = await call(LECTURER, "GET", f"/api/class-sessions/{session_id}/allocation")
    overview = await call(LECTURER, "GET", "/api/lecturer-home/class-sessions")
    return {
        "allocation": allocation.json(),
        "overview": overview.json(),
        "hjem": await home(email(0)),
        "steps": rows("SELECT user_id, step FROM progress_steps ORDER BY user_id, step"),
        "class_games": rows(
            "SELECT game_number FROM games WHERE class_session_id = %s AND game_number IS NOT NULL",
            session_id,
        ),
    }


@pytest.fixture
def flag_off(monkeypatch):
    """`FEATURE_LECTURER_TEST_GAME` off for one test; the cached settings are read again after."""
    flag(monkeypatch, False, "FEATURE_LECTURER_TEST_GAME")
    yield
    monkeypatch.undo()
    get_settings.cache_clear()


async def test_with_the_flag_off_nothing_shows_and_the_route_is_not_found(klass, flag_off):
    session_id, _ = await confirmed(klass, 1)
    shown = await class_session(session_id)
    assert (shown["lecturer_test_enabled"], shown["test_game"]) == (False, None)
    refused = await start_test(session_id)
    assert (refused.status_code, refused.json()["error"]["code"]) == (404, "not_found")
    assert rows("SELECT count(*) FROM games WHERE purpose = 'lecturer_test'") == [(0,)]


async def test_only_the_owner_starts_one_and_only_before_the_start_date(klass, monkeypatch):
    session_id, _ = await confirmed(klass, 1)
    # A start that fails after the Game was stored: the next press starts that Game, no second.
    real_start = games_commands.start

    async def failing(game_id: str) -> int:
        raise RuntimeError("the start failed")

    monkeypatch.setattr(games_commands, "start", failing)
    with pytest.raises(RuntimeError):
        await start_test(session_id)
    monkeypatch.setattr(games_commands, "start", real_start)
    again = await start_test(session_id)
    assert again.status_code == 201
    assert rows("SELECT id::text, lifecycle FROM games WHERE purpose = 'lecturer_test'") == [
        (again.json()["id"], "running")
    ]
    put_staff(klass, await make(ASSISTANT), "assistant")
    for who in (OTHER, ASSISTANT, email(0)):
        assert (await start_test(session_id, who=who)).status_code == 403
    # The Start date has passed on the api's fixed clock.
    execute("UPDATE class_sessions SET start_at = %s WHERE id = %s", NOW - MINUTE, session_id)
    refused = await start_test(session_id)
    assert (refused.status_code, refused.json()["error"]["code"]) == (409, "session_locked")


async def test_the_owner_plays_a_test_game_that_no_class_session_list_counts(klass):
    """The whole path on a short game (3 Uker, 1 Veiledet uke): start, play as a Student would,
    finish, and the Class session's lists, Hjem and steps as before (FR-87, AD-13)."""
    session_id, _ = await confirmed(klass, 2)
    execute(
        "UPDATE class_sessions SET game_settings = game_settings || %s::jsonb WHERE id = %s",
        json.dumps({"weeks": 3, "guided_weeks": 1}),
        session_id,
    )
    stored = rows("SELECT game_settings FROM class_sessions WHERE id = %s", session_id)[0][0]
    before = await lists(session_id)

    started = await start_test(session_id, "wholesaler")
    assert started.status_code == 201
    game_id = started.json()["id"]
    assert (await start_test(session_id)).json()["error"]["code"] == "test_game_running"
    lecturer = rows("SELECT id FROM users WHERE email = %s", LECTURER)[0][0]
    [(purpose, lifecycle, number, settings, owner_session)] = rows(
        "SELECT purpose, lifecycle, game_number, settings, class_session_id::text FROM games "
        "WHERE id = %s",
        game_id,
    )
    assert (purpose, lifecycle, number, owner_session) == (
        "lecturer_test",
        "running",
        None,
        session_id,
    )
    assert settings == stored  # the session's current settings, seed and all
    # The session stays unlocked and unchanged; its settings can still be saved.
    assert rows(
        "SELECT locked_at, game_settings FROM class_sessions WHERE id = %s", session_id
    ) == [(None, stored)]

    # The same play routes as a Student's own Seat (AD-12); another Lecturer is refused.
    mine = await call(LECTURER, "GET", f"/api/me/games/{game_id}")
    assert mine.status_code == 200
    game = mine.json()
    assert (game["number"], game["test_game"], game["role"], game["status"]) == (
        None,
        True,
        "wholesaler",
        "running",
    )
    assert game["class_session_id"] == session_id and game["briefing_first"] is False
    assert {
        (s["role"], s["holder"], s["mine"]) for s in game["seats"] if s["role"] != "wholesaler"
    } == {
        ("retailer", "ai", False),
        ("distributor", "ai", False),
        ("factory", "ai", False),
    }
    assert (await call(OTHER, "GET", f"/api/me/games/{game_id}")).status_code == 403
    assert (await call(email(0), "GET", f"/api/me/games/{game_id}")).status_code == 403
    shown = await class_session(session_id)
    assert shown["test_game"] == {"id": game_id, "status": "running"}
    assert await lists(session_id) == before  # running: in no list either

    base = f"/api/me/games/{game_id}/weeks"
    assert (await call(LECTURER, "POST", f"{base}/1/view")).status_code == 204
    for week in (2, 3):
        assert (
            await call(LECTURER, "POST", f"{base}/{week}/order", json={"order": 4})
        ).status_code == 204
    assert (await call(LECTURER, "GET", f"/api/me/games/{game_id}/result")).status_code == 200
    assert (await class_session(session_id))["test_game"] == {"id": game_id, "status": "finished"}

    # Absent from every Class session list, summary and step, running and finished alike.
    assert await lists(session_id) == before
    assert rows("SELECT count(*) FROM progress_steps WHERE user_id = %s", lecturer) == [(0,)]
    # Finished, a new one may start before the Start date.
    assert (await start_test(session_id, "factory")).status_code == 201
