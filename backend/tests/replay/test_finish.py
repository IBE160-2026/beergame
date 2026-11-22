"""Finish the Replay and unlock the next step (Story 10.5, FR-18, FR-29, FR-34, FR-48, FR-49, FR-50,
AD-4, AD-8, AD-13, AD-16).

The Student's last Order finishes the Replay through `games.commands.finish`; `replay`'s finish
hook records the `replay` step once, at database time, in that transaction (emitting `user:<id>`),
so Hjem's Stegene shows Replay done and the Individual test current. The finished Replay is read
again but takes no Order, the sweep's finished-game check takes it like any Game, staff open it on
Spillinnsikt marked as a Replay (reached from the Student's Seat on the Class game's), and the
Debrief's narration leaves it out. One Class session, one Replay of three Weeks (the drawn settings
shortened), played over the api."""

import uuid
from datetime import timedelta

from app.modules.debrief import narration
from app.modules.games import service as games_service
from app.modules.ops import sweep
from app.modules.replay import jobs as replay_jobs
from app.modules.replay import service as replay_service
from app.platform import jobs
from app.platform.db import get_sessionmaker
from tests.classes.test_classes import LECTURER
from tests.classes.test_staff import call
from tests.classes.test_student_registration import emitted
from tests.messaging.helpers import rows
from tests.replay.test_start import replay_step, start
from tests.sessions.test_play import FORBIDDEN, keys, play, running
from tests.sessions.test_student_choice import email
from tests.sessions.test_student_home import _empty, clock, home, klass

__all__ = ["_empty", "clock", "emitted", "klass"]

WEEKS = 3


def replay_steps(session_id: str) -> list[tuple]:
    return rows(
        "SELECT user_id, at FROM progress_steps WHERE class_session_id = %s AND step = 'replay'",
        session_id,
    )


async def test_the_last_order_finishes_the_replay_and_unlocks_the_next_step(
    klass, emitted, monkeypatch
):
    drawn = replay_service.replay_settings
    monkeypatch.setattr(
        replay_service,
        "replay_settings",
        lambda template, seed: drawn(template, seed).model_copy(update={"weeks": WEEKS}),
    )
    session_id, class_game, _ = await running(klass, 3)
    student = rows("SELECT id FROM users WHERE email = %s", email(0))[0][0]
    # The local dev route the live Playwright test uses records the steps up to the quiz; a
    # session that is not the Student's own answers 404 and records nothing.
    dev = f"/api/dev/class-sessions/{session_id}/quiz-passed"
    unknown = f"/api/dev/class-sessions/{uuid.uuid4()}/quiz-passed"
    assert (await call(email(0), "POST", unknown)).status_code == 404
    assert (await call(email(0), "POST", dev)).status_code == 204
    assert (await call(email(0), "POST", dev)).status_code == 204  # once more: nothing new
    assert sorted(
        step
        for (step,) in rows(
            "SELECT step FROM progress_steps WHERE user_id = %s AND class_session_id = %s",
            student,
            session_id,
        )
    ) == ["class_game", "debrief", "quiz_passed", "starting_task"]  # the task was done to play
    game_id = (await start(session_id, email(0))).json()["game_id"]

    # Every Week reads alike: nothing says which one is the last (FR-49).
    for week in range(1, WEEKS + 1):
        shown = (await play(email(0), game_id)).json()
        assert shown["seat_state"]["week"] == week
        assert not keys(shown) & FORBIDDEN
        assert replay_steps(session_id) == []
        if week == WEEKS:
            emitted.clear()
        ordered = await call(
            email(0), "POST", f"/api/me/games/{game_id}/weeks/{week}/order", json={"order": 8}
        )
        assert ordered.status_code == 204

    # The last Order finished it and recorded the step once, with its time (FR-18, AD-16).
    card = (await call(email(0), "GET", f"/api/me/games/{game_id}")).json()
    assert (card["status"], card["replay"], card["debrief"]) == ("finished", True, None)
    [(user_id, at)] = replay_steps(session_id)
    assert user_id == student and at is not None
    assert ("user", str(student)) in emitted and ("game", game_id) in emitted

    # Hjem: Replay done, the Individual test the current step; the block reads the finished Replay.
    item = await home(email(0))
    assert replay_step(item)["state"] == "done"
    assert next(s for s in item["steps"] if s["step"] == "test")["state"] == "current"
    assert item["replay"]["game"]["status"] == "finished"
    assert item["replay"]["can_start"] is False

    # Read again, never ordered again (409).
    result = await call(email(0), "GET", f"/api/me/games/{game_id}/result")
    assert result.status_code == 200
    assert [row["role"] for row in result.json()["roles"]]
    again = await call(
        email(0), "POST", f"/api/me/games/{game_id}/weeks/{WEEKS}/order", json={"order": 8}
    )
    assert again.status_code == 409
    after = await call(
        email(0), "POST", f"/api/me/games/{game_id}/weeks/{WEEKS + 1}/order", json={"order": 8}
    )
    assert after.status_code == 409

    # The hooks again, for the Replay and for the Class game: still one step, the Class game's
    # finish records none (no `replays` row names it).
    async with get_sessionmaker().begin() as s:
        await games_service.run_finish_hooks(s, uuid.UUID(game_id))
        await games_service.run_finish_hooks(s, uuid.UUID(class_game))
    assert replay_steps(session_id) == [(user_id, at)]

    # The finished-game check (FR-29, AD-4): the sweep's finder takes the Replay, and its check
    # reproduces the stored Weeks.
    async with get_sessionmaker()() as s:
        due = await games_service.unchecked_finished_game_ids(s, 100_000)
    assert uuid.UUID(game_id) in due
    now = rows("SELECT now()")[0][0]
    await sweep._verify_finished(game_id, now)
    assert rows("SELECT ok FROM game_checks WHERE game_id = %s", game_id) == [(True,)]

    # The Debrief's narration leaves the Replay out: no job at the finish, none from its sweep.
    deferred = []

    async def record(*args, **kwargs):
        deferred.append(kwargs)

    monkeypatch.setattr(jobs, "defer", record)
    pins = {narration.AI_TEXT_PIN: {"enabled": True, "model_config_id": str(uuid.uuid4())}}
    seat = uuid.uuid4()
    async with get_sessionmaker().begin() as s:
        for purpose in ("replay", "class"):
            await narration._defer_on_finish(
                s,
                games_service.FinishedGame(
                    uuid.UUID(game_id), purpose, uuid.UUID(session_id), pins, (seat,)
                ),
            )
    assert [kwargs["seat_id"] for kwargs in deferred] == [str(seat)]  # the Class game's only
    window = await games_service.finished_student_seats(now - timedelta(hours=1), now)
    assert uuid.UUID(game_id) not in {found.game_id for found in window}

    # Spillinnsikt (FR-34, AD-12): staff open the Replay, marked, its three AI Seats as `ai`.
    insight = await call(LECTURER, "GET", f"/api/games/{game_id}/insight")
    assert insight.status_code == 200
    body = insight.json()
    assert (body["replay"], body["game_number"], body["status"]) == (True, None, "finished")
    assert sorted(seat["holder"] for seat in body["seats"]) == ["ai", "ai", "ai", "student"]
    assert all(seat["links"] == [] for seat in body["seats"])  # no Debrief of its own
    assert (await call(LECTURER, "GET", f"/api/games/{class_game}/insight")).json()["replay"] is (
        False
    )
    # The Class game's Spillinnsikt leads from the Student's Seat to their Replay.
    class_seats = (await call(LECTURER, "GET", f"/api/games/{class_game}/insight")).json()["seats"]
    own = next(seat for seat in class_seats if seat["user_id"] == str(student))
    assert {"kind": "replay", "href": replay_service.insight_path(session_id, game_id)} in own[
        "links"
    ]
    others = [seat for seat in class_seats if seat["user_id"] not in (None, str(student))]
    assert others and all(link["kind"] != "replay" for seat in others for link in seat["links"])
    # A Student, even the Replay's own, is refused it (FR-5).
    assert (await call(email(0), "GET", f"/api/games/{game_id}/insight")).status_code == 403


def test_every_worker_registers_the_replay_finish_hook():
    """A Replay's last Order may be an AI player's, placed in the `ai-orders` worker: the worker
    imports `replay.jobs`, which loads `replay.service` and so registers its hook (Story 10.5)."""
    assert "app.modules.replay.jobs" in jobs.TASK_MODULES
    assert replay_jobs.service is replay_service
    assert games_service._finish_hooks["replay.step"] is replay_service._record_replay_step
