"""Rate how believable the AI players were (Story 10.8, FR-70, FR-50, SM-10, AD-12, AD-13, AD-15).

`GET`/`POST /api/me/games/{id}/believability`: a finished Class game with an AI-held Seat, or a
finished Replay, asks its Student once on a five-point scale; the answer is stored once per Student
and Game with the Game's purpose and frozen AI mode, and only its Student reads it back.
`GET`/`POST /api/me/games/{id}/another-round`: after the Replay-gjennomgang, once per Student and
Class session. A Game that has not finished or was closed at the Test deadline asks nobody, and
staff never read an answer. No game is played out: one started Class game (three Students and a
Rule-based player) is marked finished in SQL, and two one-Uke Replays are started."""

import uuid

import psycopg
import pytest

from app.modules.games import service as games_service
from app.modules.identity.schemas import AccountRole
from app.modules.replay import service as replay_service
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_staff import call
from tests.messaging.helpers import rows
from tests.replay.test_start import start
from tests.sessions.test_play import running
from tests.sessions.test_student_choice import email
from tests.sessions.test_student_home import _empty, clock, klass

__all__ = ["_empty", "clock", "klass"]

ADMIN = "admin-108@x.no"


def rate_path(game_id: str) -> str:
    return f"/api/me/games/{game_id}/believability"


def round_path(game_id: str) -> str:
    return f"/api/me/games/{game_id}/another-round"


async def asked(who: str, game_id: str) -> dict:
    response = await call(who, "GET", rate_path(game_id))
    assert response.status_code == 200, response.text
    return response.json()


async def rate(who: str, game_id: str, rating: object) -> tuple[int, dict]:
    response = await call(who, "POST", rate_path(game_id), json={"rating": rating})
    return response.status_code, response.json()


def code(answer: tuple[int, dict]) -> tuple[int, str]:
    return answer[0], answer[1]["error"]["code"]


async def test_students_rate_the_ai_players_once_and_only_they_read_it(klass, monkeypatch):
    drawn = replay_service.replay_settings
    monkeypatch.setattr(
        replay_service,
        "replay_settings",
        lambda template, seed: drawn(template, seed).model_copy(update={"weeks": 1}),
    )
    session_id, class_game, _ = await running(klass, 3)
    me, mate = email(0), email(1)
    ai_mode = rows("SELECT ai_mode FROM class_sessions WHERE id = %s", session_id)[0][0]
    # The fourth Seat is an AI player, which ordered when Uke 1 opened (AD-15).
    assert rows(
        "SELECT count(*) FROM seat_weeks "
        "WHERE game_id = %s AND occupant_kind IN ('llm', 'rule_based')",
        class_game,
    ) == [(1,)]

    # Running: nobody is asked yet, and an answer is refused.
    assert await asked(me, class_game) == {"offered": False, "rating": None}
    assert code(await rate(me, class_game, 4)) == (409, "not_offered")

    # Finished (marked in SQL: playing it out would cost a game per test).
    execute("UPDATE games SET lifecycle = 'finished' WHERE id = %s", class_game)
    assert await asked(me, class_game) == {"offered": True, "rating": None}
    for wrong in (0, 6, "4", None):
        assert (await rate(me, class_game, wrong))[0] == 422
    assert await rate(me, class_game, 4) == (201, {"offered": True, "rating": 4})
    # Once: a second answer replaces nothing.
    assert code(await rate(me, class_game, 2)) == (409, "already_answered")
    assert await asked(me, class_game) == {"offered": True, "rating": 4}
    [(student,)] = rows("SELECT id FROM users WHERE email = %s", me)
    assert rows(
        "SELECT user_id, purpose, ai_mode, rating FROM believability_ratings WHERE game_id = %s",
        class_game,
    ) == [(student, "class", ai_mode, 4)]
    # The table holds no name; the row is written once.
    assert {
        name
        for (name,) in rows(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'believability_ratings'"
        )
    } == {"game_id", "user_id", "purpose", "ai_mode", "rating", "created_at"}

    # Another Student of the game reads only their own (none yet); staff, an Admin and any other
    # id are refused (FR-5, AD-12).
    assert await asked(mate, class_game) == {"offered": True, "rating": None}
    await make(ADMIN, roles=(AccountRole.admin,))
    for who in (LECTURER, ADMIN):
        assert (await call(who, "GET", rate_path(class_game))).status_code == 403
        assert (await call(who, "POST", rate_path(class_game), json={"rating": 3})).status_code == (
            403
        )
    assert (await call(me, "GET", rate_path(str(uuid.uuid4())))).status_code == 403
    assert (await call(me, "GET", rate_path("not-a-game"))).status_code == 403

    # A finished Class game no AI player ever held asks nobody (the same snapshot, no Seats).
    alone = uuid.uuid4()
    execute(
        "INSERT INTO games (id, purpose, lifecycle, version, settings, demand_series, "
        "demand_seed, rules_version, session_runtime, class_session_id, game_number) "
        "SELECT %s, purpose, 'finished', 0, settings, demand_series, demand_seed, rules_version, "
        "session_runtime, class_session_id, 99 FROM games WHERE id = %s",
        alone,
        class_game,
    )
    assert await games_service.believability(alone, student) == games_service.Believability(
        offered=False, rating=None
    )
    try:
        await games_service.rate_believability(alone, student, 3)
    except games_service.BelievabilityRefused as refused:
        assert refused.code == "not_offered"
    else:
        raise AssertionError("a Game no AI player held took an answer")

    # The Replay: asked always once finished, beside the another-round question.
    for who in (me, mate):
        dev = f"/api/dev/class-sessions/{session_id}/quiz-passed"
        assert (await call(who, "POST", dev)).status_code == 204
    mine = (await start(session_id, me)).json()["game_id"]
    theirs = (await start(session_id, mate)).json()["game_id"]
    assert await asked(me, mine) == {"offered": False, "rating": None}
    not_finished = await call(me, "GET", round_path(mine))
    assert (not_finished.status_code, not_finished.json()["error"]["code"]) == (
        409,
        "replay_not_finished",
    )
    ordered = await call(me, "POST", f"/api/me/games/{mine}/weeks/1/order", json={"order": 8})
    assert ordered.status_code == 204
    steps = "SELECT step FROM progress_steps WHERE user_id = %s ORDER BY step"
    steps_before = rows(steps, student)
    assert ("replay",) in steps_before
    assert await asked(me, mine) == {"offered": True, "rating": None}
    assert await rate(me, mine, 5) == (201, {"offered": True, "rating": 5})
    assert rows(
        "SELECT purpose, ai_mode, rating FROM believability_ratings WHERE game_id = %s", mine
    ) == [("replay", ai_mode, 5)]

    assert (await call(me, "GET", round_path(mine))).json() == {"answer": None}
    answered = await call(me, "POST", round_path(mine), json={"answer": True})
    assert (answered.status_code, answered.json()) == (201, {"answer": True})
    again = await call(me, "POST", round_path(mine), json={"answer": False})
    assert (again.status_code, again.json()["error"]["code"]) == (409, "already_answered")
    assert (await call(me, "GET", round_path(mine))).json() == {"answer": True}
    assert (await call(me, "POST", round_path(mine), json={"answer": "ja"})).status_code == 422
    assert rows("SELECT user_id, class_session_id::text, answer FROM replay_another_round") == [
        (student, session_id, True)
    ]
    # Only the Replay's own Student: the mate, staff, an Admin and the Class game are refused.
    for who in (mate, LECTURER, ADMIN):
        assert (await call(who, "GET", round_path(mine))).status_code == 403
        assert (await call(who, "GET", rate_path(mine))).status_code == 403
    assert (await call(me, "GET", round_path(class_game))).status_code == 403
    # Answering recorded, blocked and unlocked nothing: the steps are as at the Replay's end.
    assert rows(steps, student) == steps_before

    # A Replay closed at the Test deadline asks nothing (Story 10.6).
    execute(
        "UPDATE games SET lifecycle = 'finished', end_reason = 'test_deadline' WHERE id = %s",
        theirs,
    )
    assert await asked(mate, theirs) == {"offered": False, "rating": None}
    assert code(await rate(mate, theirs, 3)) == (409, "not_offered")
    closed = await call(mate, "GET", round_path(theirs))
    assert (closed.status_code, closed.json()["error"]["code"]) == (409, "replay_closed")

    # The registry: an answer tells no one.
    assert COMMAND_TOPICS["replay.answer_another_round"] == frozenset()
    # Written once: the triggers refuse any change of an answer.
    for change in (
        "UPDATE believability_ratings SET rating = 1",
        "UPDATE replay_another_round SET answer = false",
    ):
        with pytest.raises(psycopg.errors.RestrictViolation):
            execute(change)
