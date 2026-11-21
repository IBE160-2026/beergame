"""«Start spillet» (Story 6.5, FR-22, AD-2, AD-4, AD-8): `POST /api/me/games/{id}/start` starts
the Student's own Class game through `games.commands.start` once they have done the Starting task;
a game started first by another counts as done; a game without its snapshot answers
`game_not_ready`; every other game is refused alike. The game's `status` and open `week` reach
Hjem and the game route. The api's clock is fixed and the sweep is handed its `now`."""

import uuid

import pytest

from app.modules.ops import sweep
from app.modules.progress import service as progress
from app.platform import auth
from tests.classes.test_classes import make
from tests.classes.test_roster_upload import NOW
from tests.classes.test_staff import call
from tests.classes.test_student_registration import emitted
from tests.sessions.test_dates import OUTSIDER, START
from tests.sessions.test_lock import MINUTE
from tests.sessions.test_open_games import confirmed, games_of
from tests.sessions.test_student_choice import email
from tests.sessions.test_student_home import _empty, clock, game_of, home, klass

__all__ = ["_empty", "clock", "emitted", "klass"]


async def start(who: str, game_id: str):
    return await call(who, "POST", f"/api/me/games/{game_id}/start")


async def task_done(user_id: uuid.UUID, session_id: str) -> None:
    await progress.record_step(user_id, uuid.UUID(session_id), "starting_task", NOW)


async def test_a_student_starts_the_game_and_everyone_in_it_hears_of_it(klass, emitted):
    session_id, seated = await confirmed(klass, 2)
    await sweep.run(START + MINUTE)  # locked, snapshot taken, two AI players
    game = (await home(email(0)))["game"]
    assert (game["status"], game["week"]) == ("ready", None)
    await task_done(seated[0], session_id)
    emitted.clear()
    response = await start(email(0), game["id"])
    assert response.status_code == 200
    started = response.json()
    assert (started["status"], started["week"]) == ("running", 1)

    # The same Seats; now that it runs, each also tells whether it has ordered (Story 6.14).
    def people(seats: list[dict]) -> list[tuple]:
        return [(s["role"], s["holder"], s["name"], s["mine"]) for s in seats]

    assert started["id"] == game["id"]
    assert people(started["seats"]) == people(game["seats"])
    assert {s["ordered"] for s in game["seats"]} == {None}
    assert {s["ordered"] for s in started["seats"]} == {True, False}
    [stored] = games_of(session_id)
    assert stored[2] == "running"
    # The command's events: the game, its Class session and both seated Students (AD-8).
    assert {("game", game["id"]), ("session", session_id)} <= set(emitted)
    assert {item for topic, item in emitted if topic == "user"} == {str(u) for u in seated}
    # The other Student's Hjem and game route read it as started, in Week 1.
    other = (await home(email(1)))["game"]
    assert (other["status"], other["week"]) == ("running", 1)
    assert (await game_of(email(1), game["id"])).json()["status"] == "running"


async def test_a_game_started_first_by_another_counts_as_done(klass):
    session_id, seated = await confirmed(klass, 2)
    await sweep.run(START + MINUTE)
    game_id = (await home(email(0)))["game"]["id"]
    for user in seated:
        await task_done(user, session_id)
    assert (await start(email(1), game_id)).status_code == 200
    again = await start(email(0), game_id)
    assert again.status_code == 200
    assert (again.json()["status"], again.json()["week"]) == ("running", 1)
    version = games_of(session_id)[0][3]
    assert (await start(email(0), game_id)).status_code == 200
    assert games_of(session_id)[0][3] == version  # a repeat writes nothing


async def test_the_starting_task_comes_first(klass):
    session_id, seated = await confirmed(klass, 1)
    await sweep.run(START + MINUTE)
    game_id = (await home(email(0)))["game"]["id"]
    refused = await start(email(0), game_id)
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "starting_task_required"
    assert games_of(session_id)[0][2] == "not_started"


async def test_a_game_without_its_snapshot_is_not_ready(klass, monkeypatch):
    """Past the Start date the Student sees the game, but until the lock has run (or while it is
    refused) the game has no snapshot: no start is offered and a start answers `game_not_ready`."""
    session_id, seated = await confirmed(klass, 1)
    monkeypatch.setattr(auth, "utcnow", lambda: START + MINUTE)  # no sweep: no snapshot
    game = (await home(email(0)))["game"]
    assert (game["status"], game["week"]) == ("not_ready", None)
    await task_done(seated[0], session_id)
    refused = await start(email(0), game["id"])
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "game_not_ready"
    assert games_of(session_id)[0][2] == "not_started"


@pytest.mark.parametrize("before_start", [False, True])
async def test_any_other_game_is_refused_alike(klass, before_start):
    session_id, seated = await confirmed(klass, 5)  # two Class games
    if not before_start:
        await sweep.run(START + MINUTE)
    games = [g[0] for g in games_of(session_id)]
    for user in seated:
        await task_done(user, session_id)
    await make(OUTSIDER, roles=())
    if before_start:
        # Before the Start date even the Student's own game is not theirs to start.
        refusals = [await start(email(0), game_id) for game_id in games]
    else:
        mine = (await home(email(0)))["game"]["id"]
        other = next(g for g in games if g != mine)
        refusals = [
            await start(email(0), other),
            await start(email(0), str(uuid.uuid7())),
            await start(email(0), "not-a-uuid"),
            await start(OUTSIDER, mine),
        ]
    assert {r.status_code for r in refusals} == {403}
    assert len({r.content for r in refusals}) == 1
    assert {g[2] for g in games_of(session_id)} == {"not_started"}


async def test_a_game_that_plays_out_reads_running_and_a_finished_one_finished(klass):
    """`status` follows the Game's lifecycle: playing out is still running in its open Week; a
    finished game has no Week (FR-14)."""
    from tests.classes.test_invitation_counts import execute

    session_id, seated = await confirmed(klass, 1)
    await sweep.run(START + MINUTE)
    game_id = (await home(email(0)))["game"]["id"]
    await task_done(seated[0], session_id)
    assert (await start(email(0), game_id)).status_code == 200
    execute("UPDATE games SET lifecycle = 'playing_out' WHERE id = %s", game_id)
    game = (await home(email(0)))["game"]
    assert (game["status"], game["week"]) == ("running", 1)
    execute("UPDATE games SET lifecycle = 'finished' WHERE id = %s", game_id)
    game = (await game_of(email(0), game_id)).json()
    assert (game["status"], game["week"]) == ("finished", None)
    # A start on a finished game counts as done, too.
    assert (await start(email(0), game_id)).json()["status"] == "finished"
