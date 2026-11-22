"""Close unfinished Replays at the Test deadline (Story 10.6, FR-18, FR-48, AD-2, AD-5, AD-8, AD-9,
AD-13, AD-15, AD-16).

The sweep's `games.close_at_test_deadline` calls `games.commands.close(game, test_deadline)` for
each Replay not finished once its Student's `effective_test_deadline` has passed at the sweep's
`now`: `finished` with `end_reason = test_deadline`, never played out, no `replay` step, the Orders
as they were. `place_order` refuses `409 test_deadline_passed` after the deadline, before and after
the close, and an `ai-orders` job ends on it. One Class session with three Students: one Replay
left unfinished, one played to its end in time, one stored but never started. The api's clock is
fixed (`klass`) and the sweep is handed its `now`."""

import uuid

import pytest

from app.modules.games import commands as games_commands
from app.modules.games import service as games_service
from app.modules.ops import sweep
from app.modules.players import jobs as llm_jobs
from app.modules.players import rescue
from app.modules.replay import service as replay_service
from app.platform.db import get_sessionmaker
from tests.classes.test_classes import LECTURER
from tests.classes.test_staff import call
from tests.classes.test_student_registration import emitted
from tests.messaging.helpers import rows
from tests.replay.test_finish import replay_steps
from tests.replay.test_start import replay_step, start
from tests.sessions.test_dates import TEST, at
from tests.sessions.test_lock import MINUTE
from tests.sessions.test_play import running
from tests.sessions.test_student_choice import email
from tests.sessions.test_student_home import _empty, clock, home, klass

__all__ = ["_empty", "clock", "emitted", "klass"]

WEEKS = 3


def game_row(game_id: str) -> tuple:
    [found] = rows("SELECT lifecycle, end_reason, version FROM games WHERE id = %s", game_id)
    return found


def played(game_id: str) -> tuple:
    """What the Replay has stored: its Week states and its Decision log rows."""
    return (
        rows(
            "SELECT week, finished, state FROM game_weeks WHERE game_id = %s ORDER BY 1, 2", game_id
        ),
        rows(
            'SELECT seat_id, week, "order", decided_by FROM seat_weeks WHERE game_id = %s '
            "ORDER BY 1, 2",
            game_id,
        ),
    )


async def order(who: str, game_id: str, week: int):
    return await call(who, "POST", f"/api/me/games/{game_id}/weeks/{week}/order", json={"order": 8})


async def test_the_sweep_closes_an_unfinished_replay_at_the_test_deadline(
    klass, emitted, monkeypatch
):
    drawn = replay_service.replay_settings
    monkeypatch.setattr(
        replay_service,
        "replay_settings",
        lambda template, seed: drawn(template, seed).model_copy(update={"weeks": WEEKS}),
    )
    session_id, _, _ = await running(klass, 3)
    for i in range(3):
        dev = f"/api/dev/class-sessions/{session_id}/quiz-passed"
        assert (await call(email(i), "POST", dev)).status_code == 204
    open_replay = (await start(session_id, email(0))).json()["game_id"]
    finished_replay = (await start(session_id, email(1))).json()["game_id"]
    # A Replay stored whose start failed after its commit: closed too.
    real_start = games_commands.start

    async def failing(game_id: str) -> int:
        raise RuntimeError("the start failed")

    monkeypatch.setattr(games_commands, "start", failing)
    with pytest.raises(RuntimeError):
        await start(session_id, email(2))
    monkeypatch.setattr(games_commands, "start", real_start)
    [(stored_replay,)] = rows(
        "SELECT g.id::text FROM games g JOIN replays r ON r.game_id = g.id "
        "WHERE r.class_session_id = %s AND g.lifecycle = 'not_started'",
        session_id,
    )

    # One Order in the first Replay; the second is played to its end in time.
    assert (await order(email(0), open_replay, 1)).status_code == 204
    for week in range(1, WEEKS + 1):
        assert (await order(email(1), finished_replay, week)).status_code == 204
    assert game_row(finished_replay) == ("finished", None, game_row(finished_replay)[2])
    finished_before = game_row(finished_replay)

    # Before the deadline the sweep leaves every Replay as it is.
    before = {g: game_row(g) for g in (open_replay, stored_replay)}
    assert await games_service.due_test_deadline_closes(TEST - MINUTE) == []

    # From the deadline on the app's clock, the Student's Order is refused and nothing is stored,
    # also before the sweep has closed the Replay (FR-18).
    kept = played(open_replay)
    at(monkeypatch, TEST)
    refused = await order(email(0), open_replay, 2)
    assert (refused.status_code, refused.json()["error"]["code"]) == (409, "test_deadline_passed")
    student = rows("SELECT id FROM users WHERE email = %s", email(0))[0][0]
    [own] = [s for s in (await games_service.get_game(open_replay)).seats if s.user_id]
    with pytest.raises(games_commands.CommandError) as viewed:  # a Guided Week view alike
        await games_commands.view_week(open_replay, own.role, 2, actor=student)
    assert viewed.value.code == "test_deadline_passed"
    assert played(open_replay) == kept
    # Until the sweep has closed it, Hjem and Stegene read the Replay as running, alike.
    assert replay_step(await home(email(0)))["closed"] is False
    # The command judges the deadline again at the sweep's `now` under the Game row lock: a `now`
    # before the deadline closes nothing.
    assert await games_commands.close(stored_replay, "test_deadline", due=TEST - MINUTE) is False
    assert game_row(stored_replay) == before[stored_replay]

    # At the deadline: closed once each, not played out, the Orders and Weeks as they were.
    assert sorted(await games_service.due_test_deadline_closes(TEST)) == sorted(
        [open_replay, stored_replay]
    )
    emitted.clear()
    done = await sweep.run(TEST)
    assert done["games.close_at_test_deadline"] == 2
    for game_id in (open_replay, stored_replay):
        lifecycle, end_reason, version = game_row(game_id)
        assert (lifecycle, end_reason, version) == (
            "finished",
            "test_deadline",
            before[game_id][2] + 1,
        )
        assert ("game", game_id) in emitted
    assert ("user", str(student)) in emitted
    assert played(open_replay) == kept  # no Week opened, no Order added (AD-15)
    assert rows("SELECT count(*) FROM game_weeks WHERE game_id = %s AND finished", open_replay) == [
        (0,)
    ]
    # The finished Replay is left alone; only it recorded the `replay` step (AD-16).
    assert game_row(finished_replay) == finished_before
    [(stepped, _)] = replay_steps(session_id)
    assert stepped != student

    # Again: nothing is written, by the sweep or by the command itself (idempotent).
    closed = game_row(open_replay)
    assert await games_service.due_test_deadline_closes(TEST + MINUTE) == []
    assert await sweep._close_at_test_deadline(open_replay, TEST + MINUTE) is False
    assert await games_commands.close(open_replay, "test_deadline") is False
    assert game_row(open_replay) == closed

    # The Student reads it as closed, not finished: card, Hjem, Stegene; no result, no Order.
    card = (await call(email(0), "GET", f"/api/me/games/{open_replay}")).json()
    assert (card["status"], card["end_reason"], card["replay"]) == (
        "finished",
        "test_deadline",
        True,
    )
    result = await call(email(0), "GET", f"/api/me/games/{open_replay}/result")
    assert result.status_code == 409
    refused = await order(email(0), open_replay, 2)
    assert (refused.status_code, refused.json()["error"]["code"]) == (409, "test_deadline_passed")
    item = await home(email(0))
    assert (item["replay"]["game"]["status"], item["replay"]["game"]["end_reason"]) == (
        "finished",
        "test_deadline",
    )
    assert item["replay"]["can_start"] is False
    assert (replay_step(item)["state"], replay_step(item)["closed"]) == ("current", True)
    # The Replay finished in time: its step is done, nothing says closed.
    assert replay_step(await home(email(1)))["state"] == "done"
    finished_card = (await call(email(1), "GET", f"/api/me/games/{finished_replay}")).json()
    assert finished_card["end_reason"] is None

    # Other modules read the reason through `games.service` (AD-13); staff on Spillinnsikt too.
    assert (await games_service.get_game(open_replay)).end_reason == "test_deadline"
    assert (await games_service.get_game(finished_replay)).end_reason is None
    insight = (await call(LECTURER, "GET", f"/api/games/{open_replay}/insight")).json()
    assert (insight["status"], insight["end_reason"]) == ("finished", "test_deadline")
    # Not a finished Game for its results: no finished-game check, no facts (Story 10.7's guard).
    async with get_sessionmaker()() as s:
        unchecked = await games_service.unchecked_finished_game_ids(s, 100_000)
    assert uuid.UUID(open_replay) not in unchecked
    assert open_replay not in await games_service.finished_game_ids()
    with pytest.raises(games_service.ViewError) as refused_check:
        await games_service.verify_finished(open_replay)
    assert refused_check.value.code == "game_not_finished"
    with pytest.raises(games_service.ViewError) as refused_facts:
        await games_service.fact_set(open_replay, own.role)
    assert refused_facts.value.code == "game_not_finished"

    # An `ai-orders` job still running for the closed Replay gets the same 409 and ends without an
    # Order and without a retry (AD-5); the rescue loop ends on it too. The turn is the Seat whose
    # Order for the open Week is still missing (the Student's), so no `order_exists` comes first.
    assert "test_deadline_passed" in llm_jobs.ENDED and "test_deadline_passed" in rescue.ENDED
    seat = next(s for s in (await games_service.get_game(open_replay)).seats if s.user_id)
    turn = games_service.PendingTurn.model_construct(
        game_id=open_replay,
        seat_id=seat.id,
        week=2,
        ordered=False,
        guided=False,
        occupant_kind=games_service.OccupantKind.LLM,
        rule_based_reference_order=4,
        ai_deadline_at=None,
        read_at=None,
    )

    async def pending(*args):
        return turn

    async def decided(_turn):
        return 4, games_service.DecidedBy.RULE_BASED, games_service.Fallback.TIMEOUT, ()

    monkeypatch.setattr(games_service, "llm_turn", pending)
    monkeypatch.setattr(llm_jobs, "_decide", decided)
    await llm_jobs.place_llm_order(open_replay, seat.id, 2)
    assert played(open_replay) == kept and game_row(open_replay) == closed

    # `close` is only for a purpose the policy closes at the deadline (AD-13).
    class_game = (await home(email(0)))["game"]["id"]
    with pytest.raises(games_commands.CommandError) as not_allowed:
        await games_commands.close(class_game, "test_deadline")
    assert (not_allowed.value.status, not_allowed.value.code) == (409, "close_not_allowed")
