"""Story 13.4 at the api (FR-17, FR-20, FR-29, FR-30, FR-5, AD-2, AD-4, AD-8, AD-9, AD-12,
AD-13): «Gi oppfølgingsspill», `POST /api/class-sessions/{id}/students/{user_id}/makeup`.

The give, the play and Completion run on one short Class game, as in `test_completion_status.py`;
the refusals and the late registrant need no played game, only a locked Class session."""

import asyncio
import uuid
from datetime import timedelta

from app.modules.games import commands
from app.modules.games import service as games_service
from app.modules.games.service import Purpose
from app.modules.identity.schemas import AccountRole
from app.modules.messaging import delivery
from app.modules.ops import sweep
from app.modules.reports import makeup as reports_makeup
from app.modules.reports import scope
from app.modules.reports import service as reports
from app.modules.sessions import service as sessions
from app.platform import jobs
from app.platform.db import get_sessionmaker
from app.platform.email.render import Recipient, Section, render
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_staff import ASSISTANT, call, put_staff
from tests.classes.test_student_registration import emitted, set_clock
from tests.messaging.helpers import rows
from tests.reports.test_completion_status import obligatory
from tests.reports.test_studentside import ADMIN, OTHER_LECTURER, record
from tests.sessions.test_allocation import students
from tests.sessions.test_dates import NOW, OUTSIDER, START, TEST, student_of
from tests.sessions.test_game_end import WEEKS, _empty, clock, klass, play_weeks, short_game
from tests.sessions.test_lock import MINUTE, dated
from tests.sessions.test_orders import code
from tests.sessions.test_start_game import start
from tests.sessions.test_student_choice import email
from tests.sessions.test_student_home import home

__all__ = ["_empty", "clock", "emitted", "klass"]


def makeup_path(session_id: str, student: object) -> str:
    return f"/api/class-sessions/{session_id}/students/{student}/makeup"


async def give(who: str, session_id: str, student: object):
    return await call(who, "POST", makeup_path(session_id, student))


def audited() -> list[tuple]:
    return rows(
        "SELECT actor_user_id, target_ids, change FROM audit_events "
        "WHERE action = 'makeup.given' ORDER BY occurred_at, id"
    )


def written() -> tuple:
    return rows(
        "SELECT (SELECT count(*) FROM makeup_games), (SELECT count(*) FROM games "
        "WHERE purpose = 'makeup'), (SELECT count(*) FROM notices WHERE kind = 'makeup_given'), "
        "(SELECT count(*) FROM audit_events WHERE action = 'makeup.given')"
    )[0]


def class_step(body: dict) -> dict:
    return next(s for s in body["completion"]["steps"] if s["step"] == "class_game")


async def test_a_lecturer_gives_a_makeup_that_the_student_plays_and_completion_reads(
    klass, emitted
):
    session_id, game_id, seated = await short_game(klass)
    sid = uuid.UUID(session_id)
    obligatory(session_id)
    me = seated[0]
    # Two own Orders of five Weeks after the Guided Week, then an AI player holds the Seat.
    await play_weeks(game_id, 3)
    role = next(
        s.role for s in (await games_service.get_game(game_id)).seats if str(s.user_id) == str(me)
    )
    await commands.switch_to_rule_based(game_id, role, "takeover_inactivity")
    await play_weeks(game_id, WEEKS)
    before = (await record(LECTURER, session_id, me)).json()
    assert class_step(before)["done"] is False
    assert (before["can_give_makeup"], before["makeup"]) == (True, None)
    assert before["completion"]["share_game"] is None
    steps_before = rows("SELECT step, at FROM progress_steps WHERE user_id = %s ORDER BY step", me)
    emitted.clear()

    given = await give(LECTURER, session_id, me)
    assert given.status_code == 200
    assert given.headers["cache-control"] == "no-store"
    body = given.json()
    assert body["can_give_makeup"] is False
    makeup = body["makeup"]
    assert (makeup["state"], makeup["open_until"][:10]) == ("ready", TEST.isoformat()[:10])
    makeup_id = makeup["game_id"]
    game = await games_service.get_game(makeup_id)
    assert (game.lifecycle, str(game.class_session_id)) == ("not_started", session_id)
    # The Class session's frozen snapshot, unchanged (AD-4).
    [(frozen,)] = rows("SELECT snapshot FROM class_sessions WHERE id = %s", session_id)
    [(settings, demand, seed, version, runtime)] = rows(
        "SELECT settings, demand_series, demand_seed, rules_version, session_runtime FROM games "
        "WHERE id = %s",
        makeup_id,
    )
    assert (settings, demand, seed, version, runtime) == (
        frozen["settings"],
        frozen["demand_series"],
        frozen["demand_seed"],
        frozen["rules_version"],
        frozen["session_runtime"],
    )
    # The Student in their own Role, an AI player of the session's mode in each other Seat.
    held = {s.role: (s.occupant_kind, s.user_id and str(s.user_id)) for s in game.seats}
    assert held[role] == ("student", str(me))
    assert {kind for r, (kind, _) in held.items() if r != role} == {"rule_based"}
    lecturer_id = rows("SELECT id FROM users WHERE email = %s", LECTURER)[0][0]
    [(actor, target, change)] = audited()
    assert actor == lecturer_id
    assert target == {"class_session_id": session_id, "user_id": str(me), "game_id": makeup_id}
    assert change == {"role": role}
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["reports.give_makeup"]
    assert {("user", str(me)), ("session", session_id)} <= set(emitted)
    [(kind, user, ref)] = rows("SELECT kind, user_id, ref FROM notices WHERE kind = 'makeup_given'")
    assert (kind, user, ref) == ("makeup_given", me, sid)
    async with get_sessionmaker()() as s:
        context = await sessions.makeup_given_mail_context(s, me, sid, NOW)
    assert context is not None and context["at"] == TEST

    # A second press answers the same one and writes nothing.
    counted = written()
    emitted.clear()
    again = await give(LECTURER, session_id, me)
    assert again.status_code == 200 and again.json()["makeup"]["game_id"] == makeup_id
    assert written() == counted and emitted == []

    # Hjem: the Class game stays the Student's game; the make-up is its own card.
    item = await home(email(0))
    assert item["game"]["id"] == game_id
    card = item["makeup"]
    assert (card["id"], card["makeup"], card["replay"], card["number"]) == (
        makeup_id,
        True,
        False,
        None,
    )
    assert (card["status"], card["briefing_first"], card["debrief"]) == ("ready", False, None)
    assert (await home(email(1)))["makeup"] is None
    # Nobody plays it with the Student, so no time to play is proposed in it.
    proposed = await call(
        email(0), "POST", f"/api/me/games/{makeup_id}/time-proposal", json={"at": TEST.isoformat()}
    )
    assert code(proposed) == (403, "forbidden")
    accepted = await call(
        email(0), "POST", f"/api/me/games/{makeup_id}/time-proposal/{uuid.uuid7()}/accept"
    )
    assert code(accepted) == (403, "forbidden")

    # Not on the overview wall, in no Class game list or per-Class-game read.
    async with get_sessionmaker()() as s:
        listed = {g.id for g in await games_service.class_games(s, sid)}
        per_class = {g.game_id for g in await scope.reporting_games(s, sid, [Purpose.CLASS])}
        everything = {g.game_id for g in await scope.reporting_games(s, sid)}
    assert uuid.UUID(makeup_id) not in listed | per_class
    assert uuid.UUID(makeup_id) in everything

    # The Student starts it after the pre-play gate (done in the Class game) and plays it out;
    # only AI players are waited for.
    assert (await start(email(0), makeup_id)).status_code == 200
    await play_weeks(makeup_id, WEEKS)
    assert (await games_service.get_game(makeup_id)).lifecycle == "finished"
    assert (await call(email(0), "GET", f"/api/me/games/{makeup_id}/result")).status_code == 200

    # Completion: the step is done from the make-up's share; the line names that game. No step
    # event is recorded by the make-up (Story 13.5 turns it on).
    status = await reports.completion_status(me, sid)
    assert (status.step("class_game").done, status.share_game, status.ordered_share) == (
        True,
        "makeup",
        100,
    )
    after = (await record(LECTURER, session_id, me)).json()
    assert (after["completion"]["share_game"], after["makeup"]["state"]) == ("makeup", "finished")
    assert class_step(after)["done"] is True
    assert (
        rows("SELECT step, at FROM progress_steps WHERE user_id = %s ORDER BY step", me)
        == steps_before
    )
    async with get_sessionmaker()() as s:
        assert await sessions.makeup_given_mail_context(s, me, sid, NOW) is None


async def test_a_late_registrant_gets_a_drawn_role_and_refusals_write_nothing(klass, monkeypatch):
    session_id = await dated(klass)
    sid = uuid.UUID(session_id)
    first, _ = await students(klass, 2)
    await make(OTHER_LECTURER)
    await make(ADMIN, roles=(AccountRole.admin,))
    await make(OUTSIDER, roles=())
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")

    # Before `sessions.lock`: not offered, refused.
    assert (await record(LECTURER, session_id, first)).json()["can_give_makeup"] is False
    assert code(await give(LECTURER, session_id, first)) == (409, "session_not_locked")
    await sweep.run(START + MINUTE)
    late = await student_of(klass, "late@x.no")

    # A Student who registered after the allocation has no Seat: «ikke gjort», and offered.
    page = (await record(LECTURER, session_id, late)).json()
    assert (page["game"], class_step(page)["done"], page["can_give_makeup"]) == (
        None,
        False,
        True,
    )
    # Anyone but a Lecturer of the Class: one answer, whether or not the Student exists.
    refusals = [
        await give(ASSISTANT, session_id, late),
        await give(OTHER_LECTURER, session_id, late),
        await give(ADMIN, session_id, late),
        await give(OUTSIDER, session_id, late),
        await give("s1@x.no", session_id, late),
        await give(LECTURER, session_id, uuid.uuid7()),
        await give(LECTURER, session_id, "not-an-id"),
        await give(LECTURER, str(uuid.uuid7()), late),
    ]
    assert len({(r.status_code, r.text) for r in refusals}) == 1
    assert code(refusals[0]) == (403, "forbidden")
    assert (await record(ASSISTANT, session_id, late)).json()["can_give_makeup"] is False

    # No Test deadline, then one that has passed (the app's clock), then an archived Class.
    execute("UPDATE class_sessions SET test_deadline = NULL WHERE id = %s", session_id)
    assert code(await give(LECTURER, session_id, late)) == (409, "no_test_deadline")
    execute("UPDATE class_sessions SET test_deadline = %s WHERE id = %s", TEST, session_id)
    set_clock(monkeypatch, TEST)
    assert (await record(LECTURER, session_id, late)).json()["can_give_makeup"] is False
    assert code(await give(LECTURER, session_id, late)) == (409, "test_deadline_passed")
    set_clock(monkeypatch, NOW)
    execute("UPDATE classes SET archived_at = now() WHERE id = %s", klass)
    assert (await record(LECTURER, session_id, late)).json()["can_give_makeup"] is False
    assert code(await give(LECTURER, session_id, late)) == (409, "class_archived")
    assert written() == (0, 0, 0, 0)
    execute("UPDATE classes SET archived_at = NULL WHERE id = %s", klass)

    # Given, by two presses at the same moment: one Game, one row, one notice, one audit row.
    first_press, second_press = await asyncio.gather(
        give(LECTURER, session_id, late), give(LECTURER, session_id, late)
    )
    assert first_press.status_code == second_press.status_code == 200
    given = first_press.json()
    assert second_press.json()["makeup"]["game_id"] == given["makeup"]["game_id"]
    assert written() == (1, 1, 1, 1)
    # A Role drawn from the four, the other three AI players.
    game = await games_service.get_game(given["makeup"]["game_id"])
    students_in = [s for s in game.seats if s.occupant_kind == "student"]
    assert [str(s.user_id) for s in students_in] == [str(late)]
    assert [change for _, _, change in audited()] == [{"role": students_in[0].role}]
    async with get_sessionmaker()() as s:
        assert await games_service.student_game(s, late, sid) is None
    # The Student who never had a Seat passes the pre-play gate first, through the make-up.
    card = (await home("late@x.no"))["makeup"]
    assert (card["briefing_first"], card["status"]) == (True, "ready")
    refused = await start("late@x.no", given["makeup"]["game_id"])
    assert refused.json()["error"]["code"] == "starting_task_required"
    task = await call(
        "late@x.no", "GET", f"/api/me/games/{given['makeup']['game_id']}/starting-task"
    )
    assert task.status_code == 200

    # The sweep closes it at the Student's Test deadline without a playout, once.
    action = next(a for a in sweep.DUE_ACTIONS if a.name == "games.close_at_test_deadline")
    makeup_id = str(game.id)
    assert makeup_id not in await action.find(TEST - MINUTE)
    due = TEST + timedelta(minutes=1)
    assert makeup_id in await action.find(due)
    assert await action.act(makeup_id, due) is True
    assert await action.act(makeup_id, due) is False
    closed = await games_service.get_game(makeup_id)
    assert closed.lifecycle == "finished"
    [(reason,)] = rows("SELECT end_reason FROM games WHERE id = %s", makeup_id)
    assert reason == "test_deadline"
    assert (await record(LECTURER, session_id, late)).json()["makeup"]["state"] == "ended"


def test_the_makeup_notice_is_a_digest_mail_loaded_by_the_worker():
    """Story 13.4 (AD-9): the kind is registered in the digest delivery of Story 3.5, its mail
    renders in Norwegian, and the worker loads the lookup the mail reads."""
    assert delivery.MAKEUP_GIVEN_KIND == reports_makeup.NOTICE
    assert delivery.KINDS[reports_makeup.NOTICE].mode == delivery.DIGEST
    assert "app.modules.reports.service" in jobs.TASK_MODULES
    template = delivery.KINDS[reports_makeup.NOTICE].template
    context = {"class_name": "Logistikk", "at": TEST}
    mail = render(Recipient("a@x.no", context=context), [Section(template)], digest=False)
    assert mail.subject == "Du har fått et Oppfølgingsspill"
    assert "Oppfølgingsspill i Klassen Logistikk" in mail.text
    assert "Testfristen" in mail.html and "Logistikk" in mail.html
