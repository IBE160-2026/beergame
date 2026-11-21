"""Opening the Debrief (Story 9.2, FR-42, FR-14, AD-3, AD-8, AD-9, AD-21, AD-25).

`POST /api/me/class-sessions/{id}/debrief` opens the Student's Debrief session once their Class
game has finished (step 1, one row per Game); `GET /api/debriefs/{id}` reads it. Before that every
Debrief route answers 403 `debrief_not_open`, and in a held Class session 403 `debrief_held` until
every Class game has finished, with the error envelope only. The sweep releases a held session
once and tells each seated Student. The api's clock is fixed and the sweep is handed its `now`."""

import uuid

from app.modules.debrief import commands, rules
from app.modules.messaging import delivery
from app.modules.ops import sweep
from app.modules.progress import service as progress
from app.modules.sessions import service as sessions
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import clock, klass
from tests.classes.test_staff import call
from tests.classes.test_student_registration import emitted
from tests.messaging.helpers import rows
from tests.sessions.test_dates import OUTSIDER, START
from tests.sessions.test_lock import MINUTE, _empty
from tests.sessions.test_open_games import confirmed, games_of
from tests.sessions.test_start_game import start, task_done
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "emitted", "klass"]

LOCKED = START + MINUTE


def path(session_id: str) -> str:
    return f"/api/me/class-sessions/{session_id}/debrief"


async def open_(who: str, session_id: str):
    return await call(who, "POST", path(session_id))


async def home(who: str) -> dict:
    response = await call(who, "GET", "/api/me/class-sessions")
    assert response.status_code == 200
    [item] = response.json()["items"]
    return item


async def hold(session_id: str, release: str = "hold"):
    return await call(
        LECTURER,
        "PUT",
        f"/api/class-sessions/{session_id}",
        json={"ai_mode": "rule_based", "debrief_release": release},
    )


def finish(game_id: str) -> None:
    execute("UPDATE games SET lifecycle = 'finished' WHERE id = %s", game_id)


def refused(response, code: str) -> None:
    """403 with `code` and the error envelope only: no demand, Weeks or Seats (FR-14)."""
    assert response.status_code == 403
    assert list(response.json()) == ["error"]
    assert response.json()["error"]["code"] == code


def debriefs() -> list[tuple]:
    return rows("SELECT id::text, game_id::text, step FROM debrief_sessions ORDER BY id")


async def players_of(session_id: str, n: int) -> dict[str, list[str]]:
    """The Students' addresses by Game id."""
    by_game: dict[str, list[str]] = {}
    for i in range(n):
        by_game.setdefault((await home(email(i)))["game"]["id"], []).append(email(i))
    return by_game


async def test_a_finished_game_opens_one_debrief_at_step_one(klass, emitted):
    session_id, seated = await confirmed(klass, 4)
    await sweep.run(LOCKED)
    [(game_id, *_)] = games_of(session_id)
    # Not started, running and playing out are all not finished.
    refused(await open_(email(0), session_id), "debrief_not_open")
    await task_done(seated[0], session_id)
    assert (await start(email(0), game_id)).status_code == 200
    refused(await open_(email(0), session_id), "debrief_not_open")
    assert (await home(email(0)))["game"]["debrief"] == "not_open"
    execute("UPDATE games SET lifecycle = 'playing_out' WHERE id = %s", game_id)
    refused(await open_(email(0), session_id), "debrief_not_open")
    assert debriefs() == []
    finish(game_id)
    emitted.clear()
    first = await open_(email(0), session_id)
    assert first.status_code == 200
    body = first.json()
    assert set(body) == {"id", "class_session_id", "game_id", "game_number", "role", "step"}
    assert (body["class_session_id"], body["game_id"], body["step"]) == (session_id, game_id, 1)
    assert body["game_number"] == 1
    assert body["role"] == (await home(email(0)))["game"]["role"]
    assert emitted == [("debrief", body["id"])]
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["debrief.open"]
    # Opened again, and by another Student of the same Game: the same session, no event.
    emitted.clear()
    again = await open_(email(0), session_id)
    other = await open_(email(1), session_id)
    assert again.json() == body
    assert other.json()["id"] == body["id"] and other.json()["role"] != body["role"]
    assert emitted == []
    assert debriefs() == [(body["id"], game_id, 1)]
    # Read by its id.
    read = await call(email(1), "GET", f"/api/debriefs/{body['id']}")
    assert read.status_code == 200 and read.json() == other.json()
    assert (await home(email(0)))["game"]["debrief"] == "open"
    # The read by id follows the same rule: a game that is not finished refuses it alike.
    execute("UPDATE games SET lifecycle = 'playing_out' WHERE id = %s", game_id)
    refused(await call(email(1), "GET", f"/api/debriefs/{body['id']}"), "debrief_not_open")


async def test_every_other_caller_is_refused_alike(klass):
    await make(OUTSIDER, roles=())
    session_id, _ = await confirmed(klass, 5)  # two Class games
    await sweep.run(LOCKED)
    by_game = await players_of(session_id, 5)
    for game_id, *_ in games_of(session_id):
        finish(game_id)
    first, second = list(by_game)
    mine = (await open_(by_game[first][0], session_id)).json()
    # Another Game's Student may not read it, nor may staff or an outsider.
    for who in (by_game[second][0], LECTURER, OUTSIDER):
        refused(await call(who, "GET", f"/api/debriefs/{mine['id']}"), "forbidden")
    for who in (LECTURER, OUTSIDER):
        refused(await open_(who, session_id), "forbidden")
    for bad in ("nope", str(uuid.uuid4())):
        refused(await open_(by_game[first][0], bad), "forbidden")
        refused(await call(by_game[first][0], "GET", f"/api/debriefs/{bad}"), "forbidden")


async def test_held_debriefs_wait_for_every_class_game_and_are_released_once(klass, emitted):
    session_id, seated = await confirmed(klass, 5)
    assert (await hold(session_id)).json()["debrief_release"] == "hold"
    await sweep.run(LOCKED)
    by_game = await players_of(session_id, 5)
    first, second = list(by_game)
    finish(first)
    who = by_game[first][0]
    user_id = rows("SELECT id FROM users WHERE email = %s", who)[0][0]
    await progress.record_step(user_id, uuid.UUID(session_id), "class_game", LOCKED)
    refused(await open_(who, session_id), "debrief_held")
    # A Debrief session that exists (opened by another way in) is held by its read too.
    opened = await commands.open(uuid.UUID(first), uuid.UUID(session_id))
    refused(await call(who, "GET", f"/api/debriefs/{opened.id}"), "debrief_held")
    item = await home(who)
    assert item["game"]["debrief"] == "held"
    debrief = [step for step in item["steps"] if step["step"] == "debrief"]
    assert debrief == [{"step": "debrief", "state": "locked", "held": True, "quiz_changed": False}]
    # The other game still running: its Students are told it has not finished.
    refused(await open_(by_game[second][0], session_id), "debrief_not_open")
    assert (await sweep.run(LOCKED + MINUTE))["debrief.release"] == 0
    # Another game's Debrief id reads as one that does not exist, never as held (FR-5).
    refused(await call(by_game[second][0], "GET", f"/api/debriefs/{opened.id}"), "forbidden")
    # The last Class game finishes: open at once, before the sweep releases it. The end records
    # `class_game` for every Student each Game ever seated (Story 6.18), as here.
    finish(second)
    for student in seated:
        await progress.record_step(student, uuid.UUID(session_id), "class_game", LOCKED)
    assert (await open_(who, session_id)).status_code == 200
    emitted.clear()
    assert (await sweep.run(LOCKED + 2 * MINUTE))["debrief.release"] == 1
    assert (await sweep.run(LOCKED + 3 * MINUTE))["debrief.release"] == 0
    assert rows("SELECT count(*) FROM debrief_releases")[0][0] == 1
    told = rows(
        "SELECT user_id, dedupe_key, ref::text FROM notices WHERE kind = 'debrief_released'"
    )
    assert sorted(user for user, _, _ in told) == sorted(seated)
    assert all(key == f"debrief_released:{session_id}:{user}" for user, key, _ in told)
    assert {ref for _, _, ref in told} == {session_id}
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["debrief.release"] == {"user"}
    steps = (await home(who))["steps"]
    assert [step for step in steps if step["step"] == "debrief"][0]["state"] == "current"


async def test_the_choice_is_saved_before_the_start_date_and_frozen_after(klass):
    session_id, _ = await confirmed(klass, 1)
    read = await call(LECTURER, "GET", f"/api/class-sessions/{session_id}")
    assert read.json()["debrief_release"] == "open"
    assert (await hold(session_id)).json()["debrief_release"] == "hold"
    # Left out, it is kept.
    kept = await call(
        LECTURER, "PUT", f"/api/class-sessions/{session_id}", json={"ai_mode": "rule_based"}
    )
    assert kept.json()["debrief_release"] == "hold"
    refused_bad = await hold(session_id, "later")
    assert refused_bad.status_code == 422
    await sweep.run(LOCKED)
    late = await hold(session_id, "open")
    assert late.status_code == 409
    assert late.json()["error"]["code"] == "session_locked"
    assert late.json()["error"]["fields"] == {"debrief_release": "locked"}
    assert (await hold(session_id)).status_code == 200


def test_stegene_says_the_debrief_is_held_only_where_it_would_be_current():
    done = {progress.Step.CLASS_GAME}
    held = sessions.stegene(True, done, held=True)
    assert [(s.step, s.state, s.held) for s in held[:3]] == [
        ("class_game", "done", False),
        ("debrief", "locked", True),
        ("quiz", "locked", False),
    ]
    # While the game runs, the Debrief is locked for that reason, not the hold.
    running = sessions.stegene(True, set(), held=True)
    assert [(s.state, s.held) for s in running[:2]] == [("current", False), ("locked", False)]
    assert sessions.stegene(True, done)[1].state == "current"


def test_the_release_notice_is_a_digest_kind_the_sweep_acts_on():
    assert delivery.DEBRIEF_RELEASED_KIND == commands.RELEASED_NOTICE
    assert delivery.KINDS[commands.RELEASED_NOTICE].mode == delivery.DIGEST
    assert "debrief.release" in [action.name for action in sweep.DUE_ACTIONS]


def test_the_one_rule_is_the_one_sessions_reads():
    assert sessions._debrief_state == [rules.state]
