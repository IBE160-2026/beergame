"""The Replay walkthrough (Story 10.7, FR-15, FR-34, FR-44, FR-50, NFR-9, AD-6, AD-7, AD-9, AD-12).

`GET /api/me/games/{id}/walkthrough` sets a Student's finished Replay beside their own Class game:
both runs' Week rows, their Totalkostnad, and one or two Replay moments rendered by code from the
stored facts set; the first ready view stores both `fact_set_id`s and fixes the line. A Replay's
finish defers one `llm-batch` job (AI text on); while it is live and the wait limit has not passed
the walkthrough is `pending`, after it the code line shows unmarked. A Class game played mostly by
AI players gives at least three moments and no comparison. A closed or unfinished Replay has no
walkthrough; only its own Student reads it. One Class session: a 14-Uke Class game shared by a
Student who ordered and one whose Seat was Rule-based, each with a Replay of ten Uker."""

import uuid
from decimal import Decimal
from types import SimpleNamespace

import psycopg
import pytest

from app.ai import mock, seed
from app.analysis import narration as narration_rules
from app.analysis.facts import MOMENTS
from app.modules.content import service as content
from app.modules.games import commands as games_commands
from app.modules.games import service as games_service
from app.modules.identity.schemas import AccountRole
from app.modules.replay import jobs as replay_jobs
from app.modules.replay import service as replay_service
from app.modules.replay import walkthrough
from app.platform.db import get_sessionmaker
from app.platform.events.registry import COMMAND_TOPICS
from tests.analysis.test_moments import facts_numbers, numbers
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import clock, klass
from tests.classes.test_staff import call
from tests.classes.test_student_registration import emitted
from tests.debrief.test_explanation import played
from tests.messaging.helpers import rows
from tests.replay.test_start import start
from tests.sessions.test_lock import _empty

__all__ = ["_empty", "clock", "emitted", "klass"]

WEEKS = 10
"""Ten Uker: enough own Orders for the Replay's facts to hold moments (FR-44)."""
ORDERS = (4, 12, 0, 8, 16, 4, 8, 2, 20, 6)
ADMIN = "admin-107@x.no"


def path(game_id: str) -> str:
    return f"/api/me/games/{game_id}/walkthrough"


async def read(who: str, game_id: str) -> dict:
    response = await call(who, "GET", path(game_id))
    assert response.status_code == 200, response.text
    return response.json()


async def refused(who: str, game_id: str, status: int, code: str) -> None:
    response = await call(who, "GET", path(game_id))
    assert (response.status_code, response.json()["error"]["code"]) == (status, code)


async def play_replay(who: str, game_id: str) -> None:
    """Every Uke with the Student's own Order through `place_order`, as the route places it
    (the Replay's AI players order at each Uke's opening)."""
    [(user_id,)] = rows("SELECT id FROM users WHERE email = %s", who)
    seat = next(s for s in (await games_service.get_game(game_id)).seats if s.user_id)
    for week, order in enumerate(ORDERS, start=1):
        await games_commands.place_order(game_id, seat.role, week, order, "student", actor=user_id)


def seat_rows(game_id: str, role: str) -> list[tuple]:
    """The golden source (NFR-9): the Seat's `seat_weeks` rows as stored."""
    return rows(
        "SELECT sw.week, sw.\"order\", (sw.state_seen->>'net_inventory')::int, "
        "(sw.state_seen->>'total_cost')::numeric, (sw.state_seen->>'week_cost')::numeric "
        "FROM seat_weeks sw JOIN seats s ON s.id = sw.seat_id "
        "WHERE sw.game_id = %s AND s.role = %s ORDER BY sw.week",
        game_id,
        role,
    )


def assert_run_is_the_rows(run: dict, game_id: str, role: str) -> None:
    stored = seat_rows(game_id, role)
    assert [
        (w["week"], w["order"], w["net_inventory"], Decimal(w["total_cost"])) for w in run["weeks"]
    ] == [(week, order, net, total) for week, order, net, total, _ in stored]
    assert Decimal(run["total_cost"]) == sum(cost for *_, cost in stored)
    # The last Uke's «Kostnad så langt» is the Totalkostnad.
    assert Decimal(run["weeks"][-1]["total_cost"]) == Decimal(run["total_cost"])


def narration_jobs() -> list[tuple]:
    return rows(
        "SELECT queue_name, queueing_lock, args FROM procrastinate_jobs "
        "WHERE task_name = %s ORDER BY id",
        walkthrough.NARRATE_TASK,
    )


def record(game_id: str) -> tuple:
    [found] = rows(
        "SELECT replay_fact_set_id::text, compared_game_id::text, compared_fact_set_id::text, "
        "narration_text, narration_ai_generated, narration_llm_call_id "
        "FROM replay_walkthroughs WHERE replay_game_id = %s",
        game_id,
    )
    return found


def forget(game_id: str, fact_set_id: str) -> None:
    """Delete the line and the record, as if neither had been stored (the job runs again)."""
    execute("DELETE FROM replay_walkthroughs WHERE replay_game_id = %s", game_id)
    execute("DELETE FROM replay_narrations WHERE fact_set_id = %s", fact_set_id)


@pytest.mark.long
async def test_the_walkthrough_sets_the_replay_beside_the_class_game(klass, emitted, monkeypatch):
    await seed.ensure_zero_config()  # the default mock config, now with `replay_walkthrough`
    drawn = replay_service.replay_settings
    monkeypatch.setattr(
        replay_service,
        "replay_settings",
        lambda template, seed: drawn(template, seed).model_copy(update={"weeks": WEEKS}),
    )
    session_id, class_game, _, game_of, me = await played(klass)
    mate = next(who for who, game in game_of.items() if game == class_game and who != me)
    stranger = next(who for who, game in game_of.items() if game != class_game)
    replays = {}
    for who in (me, mate, stranger):
        dev = f"/api/dev/class-sessions/{session_id}/quiz-passed"
        assert (await call(who, "POST", dev)).status_code == 204
        replays[who] = (await start(session_id, who)).json()["game_id"]
    mine = replays[me]
    role = next(
        str(s.role) for s in (await games_service.get_game(mine)).seats if s.user_id is not None
    )

    # Not finished yet: no walkthrough (409), and it is never anyone else's to read (403).
    await refused(me, mine, 409, "replay_not_finished")
    await play_replay(me, mine)

    # The finish deferred one job on `llm-batch`, ids only, keyed by the Game (AI text is on).
    assert narration_jobs() == [("llm-batch", walkthrough.narration_key(mine), {"game_id": mine})]
    # Before the job, inside the wait limit: pending, nothing else, nothing stored.
    pending = await read(me, mine)
    assert pending["state"] == "pending"
    assert 1 <= pending["retry_after_seconds"] <= 45
    assert (pending["replay"], pending["class_game"], pending["moments"]) == (None, None, [])
    assert rows("SELECT count(*) FROM replay_walkthroughs") == [(0,)]

    # The wait limit passed (database time): the code line, unmarked; the first view stores the
    # record with both facts sets.
    real_settings = walkthrough.get_settings
    monkeypatch.setattr(
        walkthrough, "get_settings", lambda: SimpleNamespace(replay_walkthrough_wait_seconds=0)
    )
    # Story 13.10: before any walkthrough record, the Student report's read sets the Replay
    # beside the same Class game (`student_game`).
    [(my_id,)] = rows("SELECT id FROM users WHERE email = %s", me)
    early = await replay_service.report_replay(my_id, uuid.UUID(session_id))
    assert early is not None and early.class_game is not None
    assert rows("SELECT count(*) FROM replay_walkthroughs") == [(0,)]
    first = await read(me, mine)
    replay_facts = await games_service.fact_set(mine, role)
    class_facts = await games_service.fact_set(class_game, role)
    _, templates = await content.narration_templates(2)
    code = walkthrough.code_text(replay_facts.facts, templates)
    assert code
    assert first["state"] == "ready" and first["role"] == role
    assert first["narration"] == {"text": code, "ai_generated": False, "llm_call_id": None}
    assert record(mine) == (
        replay_facts.id,
        class_game,
        class_facts.id,
        code,
        False,
        None,
    )

    # Golden (NFR-9): every number of both runs is the two Games' `seat_weeks` rows.
    assert first["mostly_ai"] is False
    assert_run_is_the_rows(first["replay"], mine, role)
    assert_run_is_the_rows(first["class_game"], class_game, role)
    assert len(first["replay"]["weeks"]) == WEEKS and len(first["class_game"]["weeks"]) == 14
    assert first["class_game"]["game_number"] is not None
    # Story 13.10: the Student report's read sets the same two runs side by side, with the
    # Replay's own settings as its scenario (FR-58).
    reported = await replay_service.report_replay(my_id, uuid.UUID(session_id))
    assert reported is not None and (reported.state, reported.role) == ("finished", role)
    assert reported.settings.weeks == WEEKS and not reported.mostly_ai
    assert reported.class_game is not None and early.class_game == reported.class_game
    for run, shown in (
        (reported.replay, first["replay"]),
        (reported.class_game, first["class_game"]),
    ):
        assert [w.model_dump(mode="json") for w in run.weeks] == shown["weeks"]
        assert run.total_cost == Decimal(shown["total_cost"])
    # One or two moments of the Student's own Replay Orders, every number from the facts.
    by_id = {moment.id: moment for moment in replay_facts.facts.seat.moments}
    assert len(by_id) == MOMENTS
    # The two ranked first (a Detected pattern first, then the higher later cost, then the
    # earlier Uke), shown by Uke; the code line ties exactly those two.
    ranked = sorted(
        by_id.values(),
        key=lambda m: (m.chosen_by != "pattern", -m.later_cost, m.week),
    )
    expected = sorted(ranked[:2], key=lambda m: m.week)
    assert [m["id"] for m in first["moments"]] == [m.id for m in expected]
    own_line = walkthrough.code_output(replay_facts.facts)
    assert own_line is not None
    assert own_line.sentences[0].fact_ids == tuple(m.id for m in expected)
    for shown in first["moments"]:
        moment = by_id[shown["id"]]
        assert (shown["week"], shown["order"]) == (moment.week, moment.order)
        for text in (shown["heading"], shown["reckoning"], shown["later"], *shown["patterns"]):
            assert set(numbers(text)) <= facts_numbers(moment), text
    # Two views alike; the record is never changed.
    assert await read(me, mine) == first
    with pytest.raises(psycopg.errors.RestrictViolation):
        execute("UPDATE replay_walkthroughs SET narration_text = 'endret'")

    # The job, the mock answering its own choice: accepted, stored marked with its call, and the
    # waiting page hears of it (`user`). The Student who saw the code line keeps it.
    emitted.clear()
    await replay_jobs.narrate_walkthrough.func(mine)
    [(text, ai, call_id)] = rows(
        "SELECT text, ai_generated, llm_call_id FROM replay_narrations WHERE fact_set_id = %s",
        replay_facts.id,
    )
    assert (text, ai) == (code, True) and call_id is not None
    student = rows("SELECT id FROM users WHERE email = %s", me)[0][0]
    assert ("user", str(student)) in emitted
    [(purpose, kind, scope_id)] = rows(
        "SELECT purpose, scope_kind, scope_id::text FROM llm_call WHERE id = %s", call_id
    )
    assert (purpose, kind, scope_id) == ("replay_walkthrough", "class_session", session_id)
    assert (await read(me, mine))["narration"] == first["narration"]
    # Stored once: a second delivery calls nothing and changes nothing.
    calls = rows("SELECT count(*) FROM llm_call")
    assert await walkthrough.narrate(mine) is False
    assert rows("SELECT count(*) FROM llm_call") == calls
    with pytest.raises(psycopg.errors.RestrictViolation):
        execute("UPDATE replay_narrations SET text = 'endret'")
    # A first view after the line was stored shows it, marked (FR-34).
    execute("DELETE FROM replay_walkthroughs WHERE replay_game_id = %s", mine)
    assert (await read(me, mine))["narration"] == {
        "text": code,
        "ai_generated": True,
        "llm_call_id": str(call_id),
    }

    # A provider failure and a rejected answer each store the code line, unmarked (AD-7).
    forget(mine, replay_facts.id)
    with mock.outage():
        assert await walkthrough.narrate(mine) is True
    assert (await read(me, mine))["narration"] == first["narration"]
    forget(mine, replay_facts.id)
    unknown = (
        '{"sentences": [{"template_id": "narration-supply-line", "fact_ids": ["moment:x:99"]}]}'
    )
    with mock.script(unknown):
        assert await walkthrough.narrate(mine) is True
    assert (await read(me, mine))["narration"] == first["narration"]
    assert narration_rules.validate_ai_text(
        narration_rules.AiTextOutput.model_validate_json(unknown), replay_facts.facts, templates
    ).reason == ("unknown_fact")

    # A Class game played mostly by AI players (the mate's Seat was Rule-based), AI text off for
    # this view: the code line at once, at least three Replay moments with their patterns, and no
    # comparison (FR-44, FR-15).
    monkeypatch.setattr(walkthrough, "get_settings", real_settings)
    monkeypatch.setattr(walkthrough, "enabled_pin", lambda pins: None)
    await play_replay(mate, replays[mate])
    theirs = await read(mate, replays[mate])
    assert (theirs["state"], theirs["mostly_ai"], theirs["class_game"]) == ("ready", True, None)
    assert len(theirs["moments"]) >= MOMENTS
    their_facts = await games_service.fact_set(replays[mate], theirs["role"])
    assert [m["id"] for m in theirs["moments"]] == [
        m.id for m in sorted(their_facts.facts.seat.moments, key=lambda m: m.week)
    ]
    assert all(moment["patterns"] for moment in theirs["moments"])
    assert theirs["narration"]["ai_generated"] is False
    assert_run_is_the_rows(theirs["replay"], replays[mate], theirs["role"])
    assert theirs["role"] != role  # the mate's own Role of the shared Class game

    # A Replay closed at the Test deadline (Story 10.6) has none: a stable code.
    assert await games_commands.close(replays[stranger], "test_deadline") is True
    await refused(stranger, replays[stranger], 409, "replay_closed")

    # Only its own Student: another Student, the Lecturer, an Admin, the Class game, no Game.
    await make(ADMIN, roles=(AccountRole.admin,))
    for who in (mate, stranger, LECTURER, ADMIN):
        assert (await call(who, "GET", path(mine))).status_code == 403
    assert (await call(me, "GET", path(class_game))).status_code == 403
    assert (await call(me, "GET", path(str(uuid.uuid4())))).status_code == 403
    assert (await call(me, "GET", path("not-a-game"))).status_code == 403

    # The registry: the stored line tells its Student; the record tells no one.
    assert COMMAND_TOPICS["replay.store_narration"] == frozenset({"user"})
    assert COMMAND_TOPICS["replay.record_walkthrough"] == frozenset()


async def test_the_finish_hook_defers_only_for_a_replay_with_ai_text_on(klass, monkeypatch):
    """The hook is registered for every worker (through `replay.jobs`) and defers nothing for a
    Game no `replays` row names, or with the pin off."""
    assert games_service._finish_hooks["replay.walkthrough"] is walkthrough._defer_on_finish
    assert replay_jobs.walkthrough is walkthrough
    deferred = []

    async def defer(*args, **kwargs):
        deferred.append(kwargs)

    monkeypatch.setattr(walkthrough.jobs, "defer", defer)
    on = {"debrief_ai_text": {"enabled": True, "model_config_id": str(uuid.uuid4())}}
    async with get_sessionmaker().begin() as s:
        for pins in (on, {}, {"debrief_ai_text": {"enabled": False, "model_config_id": None}}):
            await walkthrough._defer_on_finish(
                s, games_service.FinishedGame(uuid.uuid4(), "replay", uuid.uuid4(), pins, ())
            )
    assert deferred == []
