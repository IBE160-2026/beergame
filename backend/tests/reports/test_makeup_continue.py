"""Story 13.5 at the api (FR-17, FR-20, AD-13, AD-16, AD-21): a finished Oppfølgingsspill is the
Student's game for the Debrief, the Replay and the Individual test.

`games.service.student_game` is read case by case as a Student's games change: a Class game only,
a Class game with an unfinished make-up, one with a finished make-up, an unfinished make-up only,
a finished make-up only, and a make-up closed at the Test deadline. Each runs on one short Class
game (`short_game`, six Weeks), as in `test_makeup.py`."""

import uuid

from app.modules.games import commands
from app.modules.games import service as games_service
from app.modules.reports import service as reports
from app.modules.tests import adapted
from app.platform.db import get_sessionmaker
from tests.classes.test_classes import LECTURER
from tests.classes.test_invitation_counts import execute
from tests.classes.test_staff import call
from tests.classes.test_student_registration import emitted
from tests.debrief.test_debrief import open_
from tests.messaging.helpers import rows
from tests.replay.test_start import passed
from tests.replay.test_start import start as start_replay
from tests.reports.test_makeup import give
from tests.reports.test_studentside import record
from tests.sessions.test_dates import student_of
from tests.sessions.test_game_end import WEEKS, _empty, clock, klass, play_weeks, short_game
from tests.sessions.test_start_game import start, task_done
from tests.sessions.test_student_choice import email
from tests.sessions.test_student_home import home

__all__ = ["_empty", "clock", "emitted", "klass"]

LATE = "late@x.no"


async def theirs(user_id: uuid.UUID, session_id: str) -> games_service.StudentGame | None:
    async with get_sessionmaker()() as s:
        return await games_service.student_game(s, user_id, uuid.UUID(session_id))


def step(item: dict, name: str) -> dict:
    return next(s for s in item["steps"] if s["step"] == name)


def class_game_events(user_id: uuid.UUID) -> int:
    return rows(
        "SELECT count(*) FROM progress_steps WHERE user_id = %s AND step = 'class_game'", user_id
    )[0][0]


async def given(session_id: str, user_id: uuid.UUID) -> str:
    answer = await give(LECTURER, session_id, user_id)
    assert answer.status_code == 200, answer.text
    return answer.json()["makeup"]["game_id"]


async def test_a_finished_makeup_becomes_the_students_game_but_a_started_debrief_stays(
    klass, emitted
):
    session_id, game_id, (a, b) = await short_game(klass)
    sid = uuid.UUID(session_id)
    # Group debrief: the make-up's Debrief is a Personal debrief whatever the mode.
    execute("UPDATE class_sessions SET debrief_mode = 'group' WHERE id = %s", session_id)

    # A Class game only.
    assert (found := await theirs(a, session_id)) is not None
    assert (found.game_id, found.makeup, found.debrief_personal) == (
        uuid.UUID(game_id),
        False,
        False,
    )
    await play_weeks(game_id, WEEKS)
    assert class_game_events(a) == class_game_events(b) == 1

    # A Class game with an unfinished make-up: still the Class game.
    makeup_a, makeup_b = await given(session_id, a), await given(session_id, b)
    assert (await theirs(a, session_id)).game_id == uuid.UUID(game_id)
    item = await home(email(1))
    assert (item["game"]["id"], item["makeup"]["id"]) == (game_id, makeup_b)
    assert step(item, "debrief")["after_makeup"] is False

    # A starts the Debrief on the Class game: their Explanation names it.
    opened = await open_(email(0), session_id)
    assert opened.status_code == 200 and opened.json()["game_id"] == game_id
    sent = await call(
        email(0), "POST", f"/api/debriefs/{opened.json()['id']}/explanation", json={"text": "Min."}
    )
    assert sent.status_code == 201
    # The 48-hour fallback's row is the sweep's, not B's: it starts nothing for B.
    execute(
        "INSERT INTO debrief_alone (debrief_id, user_id, step, reason, since) "
        "VALUES (%s, %s, 1, 'fallback', now())",
        opened.json()["id"],
        b,
    )

    # A Class game with a finished make-up: the make-up, a Personal debrief.
    for i, makeup_id in ((0, makeup_a), (1, makeup_b)):
        assert (await start(email(i), makeup_id)).status_code == 200
        await play_weeks(makeup_id, WEEKS)
    found = await theirs(b, session_id)
    assert (found.game_id, found.makeup, found.debrief_personal, found.number) == (
        uuid.UUID(makeup_b),
        True,
        True,
        None,
    )
    # The finish recorded `class_game` again for nobody: one step event each.
    assert class_game_events(a) == class_game_events(b) == 1
    # The Class game stays the Student's to open (its result), and still counts them in.
    assert (await call(email(1), "GET", f"/api/me/games/{game_id}/result")).status_code == 200
    async with get_sessionmaker()() as s:
        students = await games_service.game_students(s, uuid.UUID(game_id))
    assert {a, b} <= {each.user_id for each in students}

    # B's Hjem: the make-up is the game, with the Debrief open; not shown twice.
    item = await home(email(1))
    assert (item["game"]["id"], item["game"]["makeup"], item["game"]["debrief"]) == (
        makeup_b,
        True,
        "open",
    )
    assert item["makeup"] is None
    assert [s["state"] for s in item["steps"]][:2] == ["done", "current"]
    # «Gå til Debrief» on its end screen opens a Personal debrief of the make-up.
    mine = await call(email(1), "GET", f"/api/me/games/{makeup_b}")
    assert mine.json()["debrief"] == "open"
    opened_b = await open_(email(1), session_id)
    assert opened_b.status_code == 200
    assert (opened_b.json()["game_id"], opened_b.json()["group"], opened_b.json()["makeup"]) == (
        makeup_b,
        None,
        True,
    )
    assert rows("SELECT shared FROM debrief_sessions WHERE game_id = %s", makeup_b) == [(False,)]

    # A started the Debrief on the Class game: it keeps that game.
    reopened = await open_(email(0), session_id)
    assert reopened.json()["id"] == opened.json()["id"]
    assert reopened.json()["game_id"] == game_id
    assert (await home(email(0)))["game"]["id"] == makeup_a
    # Staff read A's Debrief summary against the game it ran on.
    staff = await call(
        LECTURER, "GET", f"/api/class-sessions/{session_id}/students/{a}/debrief-summary"
    )
    assert (staff.json()["game_id"], staff.json()["makeup"]) == (game_id, False)
    staff_b = await call(
        LECTURER, "GET", f"/api/class-sessions/{session_id}/students/{b}/debrief-summary"
    )
    assert (staff_b.json()["game_id"], staff_b.json()["makeup"]) == (makeup_b, True)

    # The Studentside shows the make-up as the game; Completion counts each game once.
    page = (await record(LECTURER, session_id, b)).json()
    assert (page["game"]["game_id"], page["game"]["makeup"]) == (makeup_b, True)
    # Both games ordered in full: the tie names the Class game, read once beside the make-up.
    status = await reports.completion_status(b, sid)
    assert (status.share_game, status.ordered_share, status.step("class_game").done) == (
        "class",
        100,
        True,
    )


async def test_a_late_registrants_makeup_opens_the_debrief_replay_and_test(klass, emitted):
    session_id, _, _ = await short_game(klass, students=1)
    sid = uuid.UUID(session_id)
    late = await student_of(klass, LATE)
    await task_done(late, session_id)
    closing = await student_of(klass, "closing@x.no")

    # No game yet: Stegene has nothing current.
    assert await theirs(late, session_id) is None
    makeup_id = await given(session_id, late)

    # An unfinished make-up only: no game; the Debrief opens when the make-up is finished.
    assert await theirs(late, session_id) is None
    item = await home(LATE)
    assert (item["game"], item["makeup"]["id"]) == (None, makeup_id)
    assert (step(item, "class_game")["state"], step(item, "debrief")) == (
        "current",
        step(item, "debrief") | {"state": "locked", "after_makeup": True},
    )
    assert (await open_(LATE, session_id)).status_code == 403
    assert (await start(LATE, makeup_id)).status_code == 200
    await play_weeks(makeup_id, WEEKS - 1)
    assert await theirs(late, session_id) is None
    assert step(await home(LATE), "debrief")["after_makeup"] is True

    # Its last Week: a finished make-up only is the Student's game; the step is recorded once.
    await play_weeks(makeup_id, WEEKS)
    found = await theirs(late, session_id)
    assert (found.game_id, found.makeup) == (uuid.UUID(makeup_id), True)
    assert class_game_events(late) == 1
    item = await home(LATE)
    assert (item["game"]["id"], item["makeup"]) == (makeup_id, None)
    assert [s["state"] for s in item["steps"]][:2] == ["done", "current"]
    assert step(item, "debrief")["after_makeup"] is False
    opened = await open_(LATE, session_id)
    assert opened.status_code == 200 and opened.json()["game_id"] == makeup_id

    # The Replay takes the make-up's Role; the Adapted items read the make-up's facts set.
    await passed(late, session_id)
    replay = await start_replay(session_id, LATE)
    assert replay.status_code == 201, replay.text
    replay_game = await games_service.get_game(replay.json()["game_id"])
    [seat] = [s for s in replay_game.seats if s.occupant_kind == "student"]
    assert seat.role == found.role
    async with get_sessionmaker()() as s:
        own, _ = await adapted._sources(s, late, sid)
    assert (own.game_id, own.role) == (uuid.UUID(makeup_id), found.role)
    await adapted.warm(late, sid)
    stored = await games_service.fact_set(makeup_id, found.role)
    assert rows("SELECT game_id FROM fact_sets WHERE id = %s", stored.id) == [
        (uuid.UUID(makeup_id),)
    ]

    # A make-up closed at the Test deadline never becomes the Student's game.
    closed_id = await given(session_id, closing)
    await task_done(closing, session_id)
    assert (await start("closing@x.no", closed_id)).status_code == 200
    assert await commands.close(closed_id, "test_deadline") is True
    assert await theirs(closing, session_id) is None
    item = await home("closing@x.no")
    assert (item["game"], step(item, "debrief")["after_makeup"]) == (None, False)
    # No game to play any more: nothing is current, as before a make-up was given.
    assert step(item, "class_game")["state"] == "locked"
    assert class_game_events(closing) == 0
