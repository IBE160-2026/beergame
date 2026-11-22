"""Story 8.14 at the api: a Class game unfinished at the Play deadline is played out by the
sweep, its Students read it as ended at the Spillfrist on Hjem and Spill, and the Class game step
counts every Student it ever seated (FR-38, FR-28, FR-17, AD-16). The clocks are passed in."""

import uuid

from app.modules.games import service as games_service
from app.modules.ops import sweep
from app.modules.progress import service as progress
from tests.conftest import TEST_DATABASE_URL, kept_connection
from tests.sessions.test_dates import PLAY
from tests.sessions.test_game_end import (
    _empty,
    clock,
    emitted,
    klass,
    play_weeks,
    result,
    short_game,
)
from tests.sessions.test_student_choice import email
from tests.sessions.test_student_home import game_of, home

__all__ = ["_empty", "clock", "emitted", "klass"]


def decided(game_id: str, user: uuid.UUID) -> list[tuple]:
    """(week, decided_by, reason) of the Seat the Student held first, by Week."""
    return (
        kept_connection(TEST_DATABASE_URL)
        .execute(
            "SELECT w.week, w.decided_by, w.reason FROM seat_weeks w JOIN seat_occupancy o "
            "ON o.seat_id = w.seat_id AND o.reason = 'initial' WHERE w.game_id = %s "
            "AND o.user_id = %s ORDER BY w.week",
            (game_id, user),
        )
        .fetchall()
    )


async def test_the_playout_ends_the_game_at_the_play_deadline_for_every_student(
    klass, emitted, monkeypatch
):
    from app.modules.games import commands
    from tests.classes.test_classes import LECTURER
    from tests.sessions.test_overview import overview

    session_id, game_id, seated = await short_game(klass)
    await play_weeks(game_id, 2)
    # The second Student's Seat was taken over and never given back.
    replaced = next(
        s for s in (await games_service.get_game(game_id)).seats if str(s.user_id) == str(seated[1])
    )
    await commands.switch_to_rule_based(game_id, replaced.role, "takeover_inactivity")
    assert (await home(email(0)))["game"]["played_out"] is False
    emitted.clear()

    # While AI players play it out (held here: no Week advances), Hjem and Spill say so.
    async def later(game_id: str) -> None:
        return None

    monkeypatch.setattr(commands, "_settle", later)
    await sweep.run(PLAY)
    item = await home(email(0))
    assert (item["game"]["status"], item["game"]["played_out"]) == ("running", True)
    assert (await game_of(email(0), game_id)).json()["played_out"] is True
    monkeypatch.undo()
    assert await commands.advance(game_id)

    assert (await games_service.get_game(game_id)).lifecycle == "finished"
    for user in seated:
        assert await progress.has_step(user, uuid.UUID(session_id), "class_game")
    assert {("game", game_id), ("session", session_id)} <= set(emitted)
    assert {("user", str(user)) for user in seated} <= set(emitted)
    # Hjem and Spill read it as ended by the playout; the chain's cost is there.
    item = await home(email(0))
    assert (item["game"]["status"], item["game"]["played_out"]) == ("finished", True)
    own = await game_of(email(0), game_id)
    assert own.status_code == 200 and own.json()["played_out"] is True
    assert (await result(email(0), game_id)).status_code == 200
    # The Weeks the playout played are marked `playout` and decided by an AI player (AD-15).
    rows = decided(game_id, seated[0])
    assert [w for w, *_ in rows] == list(range(1, 7))
    assert all(by != "student" and reason == "playout" for _, by, reason in rows[2:])
    # The Oversikt: the game is «Ferdig», its played-out Seat carries the `playout` mark, and the
    # Trakt counts both Students' Class game step (FR-39, AD-25).
    staff = (await overview(LECTURER, session_id)).json()
    [game] = staff["items"]
    assert game["status"] == "finished"
    assert "playout" in {seat["mark"] for seat in game["seats"]}
    stages = {stage["stage"]: stage["count"] for stage in staff["funnel"]}
    assert stages["class_game"] == len(seated)


async def test_the_dev_playout_runs_at_the_play_deadline_once(klass):
    """The local dev route the end-to-end tests use instead of waiting for the Play deadline:
    the playout of one Class game at its Class session's deadline; a repeat changes nothing."""
    from tests.identity.helpers import CSRF, client

    _, game_id, _ = await short_game(klass)
    async with client() as c:
        played = await c.post(f"/api/dev/games/{game_id}/playout", headers=CSRF)
        again = await c.post(f"/api/dev/games/{game_id}/playout", headers=CSRF)
        unknown = await c.post("/api/dev/games/ikke-en-id/playout", headers=CSRF)
    assert (played.status_code, played.json()) == (200, {"played_out": True})
    assert (again.status_code, again.json()) == (200, {"played_out": False})
    assert (await games_service.get_game(game_id)).lifecycle == "finished"
    assert (unknown.status_code, unknown.json()["error"]["code"]) == (404, "not_found")
