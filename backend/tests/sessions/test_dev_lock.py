"""The local dev lock (Story 6.15): `POST /api/dev/class-sessions/{id}/lock` locks a Class
session before its Start date and opens its Class games, as the sweep does at the Start date, so
the end-to-end tests can play a real Class game. Not routed in production
(`tests/messaging/test_dev_mailbox.py` checks that no `/api/dev` path is)."""

import uuid

from tests.classes.test_roster_upload import clock, klass
from tests.identity.helpers import CSRF, client
from tests.sessions.test_lock import _empty
from tests.sessions.test_open_games import confirmed, games_of
from tests.sessions.test_student_choice import email
from tests.sessions.test_student_home import home

__all__ = ["_empty", "clock", "klass"]


async def lock(session_id: str):
    async with client() as c:
        return await c.post(f"/api/dev/class-sessions/{session_id}/lock", headers=CSRF)


async def test_it_locks_now_and_opens_the_games(klass):
    session_id, _ = await confirmed(klass, 2)
    [(_, _, lifecycle, _, settings, _)] = games_of(session_id)
    assert (lifecycle, settings) == ("not_started", None)
    first = await lock(session_id)
    assert (first.status_code, first.json()) == (200, {"locked": True})
    [(game_id, _, lifecycle, _, settings, _)] = games_of(session_id)
    assert lifecycle == "not_started" and settings is not None  # the snapshot is in
    # The Student sees the game, ready to start, before the Start date.
    game = (await home(email(0)))["game"]
    assert (game["id"], game["status"]) == (game_id, "ready")
    again = await lock(session_id)
    assert (again.status_code, again.json()) == (200, {"locked": False})


async def test_an_unknown_session_is_not_found(klass):
    for session_id in (str(uuid.uuid7()), "ikke-en-id"):
        answer = await lock(session_id)
        assert (answer.status_code, answer.json()["error"]["code"]) == (404, "not_found")
