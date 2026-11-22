"""Start the Replay after passing the Debrief quiz (Story 10.3, FR-18, FR-30, FR-34, FR-48, FR-49,
AD-2, AD-4, AD-5, AD-13, AD-16).

`POST /api/me/class-sessions/{id}/replay` makes the Student's one `replay` Game: the Class
session's frozen snapshot with the Replay's own settings, series and seed, the Student in the Role
of their own game, AI players of the session's AI mode in the others, started at once. Hjem
(`/api/me/class-sessions`) shows it with its Seats. The steps before the quiz are recorded
directly; no Class game is played. The api's clock is fixed and the sweep is handed its `now`."""

import asyncio
import uuid

import pytest

from app.engine import ReplayTemplate, demand_series, replay_settings
from app.modules.games import commands as games_commands
from app.modules.ops import sweep
from app.modules.progress import service as progress
from app.modules.replay import repo as replay_repo
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_classes import make
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_staff import call
from tests.classes.test_student_registration import emitted
from tests.messaging.helpers import rows
from tests.sessions.test_ai_mode import two_levels
from tests.sessions.test_dates import OUTSIDER, START, TEST, at, student_of
from tests.sessions.test_lock import MINUTE, _empty
from tests.sessions.test_open_games import confirmed
from tests.sessions.test_student_choice import email
from tests.sessions.test_student_home import home

__all__ = ["_empty", "clock", "emitted", "klass", "two_levels"]

BEFORE_QUIZ = ("class_game", "debrief")
STRANGER = "fremmed@x.no"


async def start(session_id: str, who: str):
    return await call(who, "POST", f"/api/me/class-sessions/{session_id}/replay")


async def passed(user_id: uuid.UUID, session_id: str) -> None:
    for step in (*BEFORE_QUIZ, "quiz_passed"):
        await progress.record_step(user_id, uuid.UUID(session_id), step, NOW)


def replay_games(session_id: str) -> list[tuple]:
    return rows(
        "SELECT g.id::text, g.lifecycle, r.user_id FROM games g JOIN replays r ON r.game_id = g.id "
        "WHERE g.class_session_id = %s AND g.purpose = 'replay' ORDER BY g.id",
        session_id,
    )


def holders(game_id: str) -> dict[str, tuple]:
    """Each Seat's current occupant: Role → (kind, reason, user id)."""
    found = rows(
        "SELECT DISTINCT ON (s.id) s.role, o.occupant_kind, o.reason, o.user_id FROM seats s "
        "JOIN seat_occupancy o ON o.seat_id = s.id WHERE s.game_id = %s ORDER BY s.id, o.id DESC",
        game_id,
    )
    return {role: (kind, reason, user) for role, kind, reason, user in found}


def replay_step(item: dict) -> dict:
    return next(step for step in item["steps"] if step["step"] == "replay")


async def test_a_student_who_passed_the_quiz_starts_one_replay_in_their_own_role(
    klass, emitted, monkeypatch
):
    session_id, seated = await confirmed(klass, 3)
    await sweep.run(START + MINUTE)  # locks the session and opens its Class game
    [(class_game, class_number)] = rows(
        "SELECT id::text, game_number FROM games WHERE class_session_id = %s", session_id
    )

    # Without the quiz: the step is locked, no Replay block, and the start is refused (AD-16).
    item = await home(email(0))
    assert item["replay"] is None and replay_step(item)["state"] == "locked"
    refused = await start(session_id, email(0))
    assert (refused.status_code, refused.json()["error"]["code"]) == (403, "quiz_required")
    await progress.record_step(seated[0], uuid.UUID(session_id), "class_game", NOW)
    refused = await start(session_id, email(0))
    assert refused.json()["error"]["code"] == "quiz_required"

    # Passed: «Start Replay» shows and the Replay step is the current one.
    await passed(seated[0], session_id)
    item = await home(email(0))
    assert item["replay"] == {"can_start": True, "game": None}
    assert replay_step(item) | {"step": None} == {
        "step": None,
        "state": "current",
        "held": False,
        "quiz_changed": False,
        "group_open": False,
        "closed": False,
        "counts": None,
        "corrected": False,
    }

    # Two presses at once, from two devices: one Replay, and both get it.
    emitted.clear()
    first, second = await asyncio.gather(start(session_id, email(0)), start(session_id, email(0)))
    assert sorted([first.status_code, second.status_code]) == [200, 201]
    game_id = first.json()["game_id"]
    assert second.json()["game_id"] == game_id
    assert replay_games(session_id) == [(game_id, "running", seated[0])]
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["replay.start"]
    assert ("user", str(seated[0])) in emitted
    again = await start(session_id, email(0))
    assert (again.status_code, again.json()["game_id"]) == (200, game_id)
    # A start that read no Replay just before the other one committed: its Game is rolled back.
    real_read = replay_repo.replay_game
    reads = []

    async def stale_once(session, user_id, class_session_id):
        reads.append(user_id)
        return None if len(reads) == 1 else await real_read(session, user_id, class_session_id)

    monkeypatch.setattr(replay_repo, "replay_game", stale_once)
    raced = await start(session_id, email(0))
    monkeypatch.setattr(replay_repo, "replay_game", real_read)
    assert (raced.status_code, raced.json()["game_id"]) == (200, game_id) and len(reads) == 2
    assert rows("SELECT count(*) FROM games WHERE purpose = 'replay'") == [(1,)]

    # The Replay: the frozen runtime and rules version, its own settings, series and seed (AD-4).
    [(snapshot,)] = rows("SELECT snapshot FROM class_sessions WHERE id = %s", session_id)
    [(purpose, number, settings, series, seed, rules_version, runtime)] = rows(
        "SELECT purpose, game_number, settings, demand_series, demand_seed, rules_version, "
        "session_runtime FROM games WHERE id = %s",
        game_id,
    )
    assert (purpose, number) == ("replay", None)
    template = ReplayTemplate.model_validate(snapshot["session_runtime"]["pins"]["replay_template"])
    drawn = replay_settings(template, seed)
    assert settings == drawn.model_dump(mode="json") and seed == drawn.demand_seed
    assert series == list(demand_series(drawn))
    assert (runtime, rules_version) == (snapshot["session_runtime"], snapshot["rules_version"])
    assert 30 <= settings["weeks"] <= 40 and settings["guided_weeks"] == 0

    # The Student holds the Role of their own Class game; AI players of the session's mode the rest.
    [(own_role,)] = rows(
        "SELECT s.role FROM seats s JOIN seat_occupancy o ON o.seat_id = s.id "
        "WHERE s.game_id = %s AND o.user_id = %s",
        class_game,
        seated[0],
    )
    seats = holders(game_id)
    assert seats.pop(own_role) == ("student", "initial", seated[0])
    assert set(seats.values()) == {("rule_based", "initial", None)} and len(seats) == 3

    # Hjem: the Class game stays the Student's game; the Replay is current, its AI Seats `ai`.
    item = await home(email(0))
    assert (item["game"]["id"], item["game"]["number"]) == (class_game, class_number)
    replay = item["replay"]
    assert replay["can_start"] is False
    assert (replay["game"]["id"], replay["game"]["role"], replay["game"]["status"]) == (
        game_id,
        own_role,
        "running",
    )
    assert replay["game"]["week"] == 1
    assert sorted(seat["holder"] for seat in replay["game"]["seats"]) == [
        "ai",
        "ai",
        "ai",
        "student",
    ]
    assert [seat["role"] for seat in replay["game"]["seats"] if seat["mine"]] == [own_role]
    assert replay_step(item)["state"] == "current"
    text = str(replay)
    assert not any(word in text for word in ("rule_based", "llm", "user_id"))

    # A sweep leaves a running Replay as it was. (Takeover and playout have no sweep action yet;
    # their finders must filter on the policy columns `test_policy.py` pins for `replay`.)
    before = rows("SELECT lifecycle, version FROM games WHERE id = %s", game_id)
    await sweep.run(START + 60 * MINUTE)
    assert rows("SELECT lifecycle, version FROM games WHERE id = %s", game_id) == before
    assert holders(game_id) == {own_role: ("student", "initial", seated[0]), **seats}

    # A start whose Game was stored but not started: the next request starts it, never a second.
    await passed(seated[1], session_id)
    real_start = games_commands.start

    async def failing(game_id: str) -> int:
        raise RuntimeError("the start failed")

    monkeypatch.setattr(games_commands, "start", failing)
    with pytest.raises(RuntimeError):
        await start(session_id, email(1))
    monkeypatch.setattr(games_commands, "start", real_start)
    [(stored, lifecycle, _)] = [g for g in replay_games(session_id) if g[2] == seated[1]]
    assert lifecycle == "not_started"
    # Hjem offers «Start Replay» again over the stored Replay's Seats.
    waiting = (await home(email(1)))["replay"]
    assert (waiting["can_start"], waiting["game"]["id"], waiting["game"]["status"]) == (
        True,
        stored,
        "ready",
    )
    resumed = await start(session_id, email(1))
    assert (resumed.status_code, resumed.json()["game_id"]) == (200, stored)
    assert [g[1] for g in replay_games(session_id)] == ["running", "running"]

    # After the Test deadline: no start, and Stegene says the step is not done (FR-18).
    await passed(seated[2], session_id)
    at(monkeypatch, TEST)  # the api's clock at the Test deadline
    late = await start(session_id, email(2))
    assert (late.status_code, late.json()["error"]["code"]) == (409, "test_deadline_passed")
    item = await home(email(2))
    assert item["replay"] == {"can_start": False, "game": None}
    assert (replay_step(item)["state"], replay_step(item)["closed"]) == ("current", True)
    # A Replay started before the deadline is still the Student's (Story 10.6 closes it).
    assert (await start(session_id, email(0))).json()["game_id"] == game_id
    assert len(replay_games(session_id)) == 2


async def test_only_the_students_own_locked_session_starts_a_replay(klass):
    session_id, seated = await confirmed(klass, 1)
    # Before the Start date the session is not the Student's to start in.
    assert (await start(session_id, email(0))).status_code == 403
    await sweep.run(START + MINUTE)
    outsider = await student_of(klass, OUTSIDER)  # in the Class, but no Seat: no game, no Replay
    await passed(outsider, session_id)
    await passed(seated[0], session_id)
    await make(STRANGER, roles=())  # in no Class
    for who, target in (
        (OUTSIDER, session_id),
        (STRANGER, session_id),
        (email(0), str(uuid.uuid7())),
        (email(0), "not-an-id"),
    ):
        refused = await start(target, who)
        assert (refused.status_code, refused.json()["error"]["code"]) == (403, "forbidden")
    # Hjem offers no Replay to a Student with no game, quiz step or not.
    assert (await home(OUTSIDER))["replay"] is None
    assert rows("SELECT count(*) FROM replays") == [(0,)]


async def test_llm_players_take_the_other_seats_and_the_cost_limit_makes_them_rule_based(
    klass, two_levels, monkeypatch
):
    session_id, seated = await confirmed(klass, 2, "llm")
    await sweep.run(START + MINUTE)
    for user_id in seated:
        await passed(user_id, session_id)
    game_id = (await start(session_id, email(0))).json()["game_id"]
    kinds = sorted(kind for kind, _, _ in holders(game_id).values())
    assert kinds == ["llm", "llm", "llm", "student"]
    [(model_config,)] = rows("SELECT session_runtime FROM games WHERE id = %s", game_id)
    assert model_config["model_config_id"] == str(two_levels)

    async def limited(session, game) -> bool:
        return True

    monkeypatch.setattr(games_commands, "_cost_limited", limited)
    game_id = (await start(session_id, email(1))).json()["game_id"]
    ai = [(kind, reason) for kind, reason, user in holders(game_id).values() if user is None]
    assert ai == [("rule_based", "cost_limit")] * 3
