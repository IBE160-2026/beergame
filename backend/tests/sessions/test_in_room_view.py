"""Story 8.11 through the api: a Lecturer marks a Class game «I rommet» during a Lab hour from
Spillstyring (`POST /api/games/{id}/in-room`) and ends it (`DELETE …/in-room`). Spillinnsikt offers
it only while a Lab hour of the Class session is on; the Oversikt carries the mark; each Student's
play envelope reads the line with their own minutes; a moved or removed Lab hour and the sweep at
its end move or end the mark; an Assistant lecturer and a Student are refused (FR-36, AD-2, AD-9,
AD-12). One short Class game (`three_students_in_uke_2`) per test; the api's clock is the
injected `NOW`, the clock Lab hours are judged on."""

from datetime import datetime, timedelta

from app.modules.ops import sweep
from tests.classes.test_classes import LECTURER, OTHER, make
from tests.classes.test_staff import ASSISTANT, call, put_staff
from tests.messaging.helpers import rows
from tests.sessions.test_adjustment import save, user_id
from tests.sessions.test_dates import NOW
from tests.sessions.test_game_end import _empty, clock, klass
from tests.sessions.test_game_insight import insight
from tests.sessions.test_lab_hours import add, change, remove
from tests.sessions.test_orders import code, order
from tests.sessions.test_overview import overview
from tests.sessions.test_pause_view import three_students_in_uke_2
from tests.sessions.test_student_home import home

__all__ = ["_empty", "clock", "klass"]

MINUTE = timedelta(minutes=1)
ENDS = NOW + 50 * MINUTE


async def mark(who: str, game_id: str, minutes: object):
    return await call(who, "POST", f"/api/games/{game_id}/in-room", json={"minutes": minutes})


async def unmark(who: str, game_id: str):
    return await call(who, "DELETE", f"/api/games/{game_id}/in-room")


async def play(who: str, game_id: str) -> dict:
    answer = await call(who, "GET", f"/api/me/games/{game_id}/play")
    assert answer.status_code == 200
    return answer.json()


def parse(value: str | None) -> datetime | None:
    return None if value is None else datetime.fromisoformat(value)


def due_of(game_id: str, user: str) -> tuple:
    [found] = rows(
        "SELECT t.wait_started_at, t.takeover_due_at FROM seat_turns t "
        "WHERE t.game_id = %s AND t.week = 2 AND t.seat_id IN (SELECT o.seat_id FROM "
        "seat_occupancy o WHERE o.user_id = %s)",
        game_id,
        user,
    )
    return found


async def test_a_lecturer_marks_a_game_in_a_lab_hour_and_ends_it(klass):
    session_id, game_id, by_role = await three_students_in_uke_2(klass)
    sara, jonas, third = by_role.values()
    jonas_id = user_id(jonas)
    assert (await save(LECTURER, session_id, jonas_id, {"time_factor": 2})).status_code == 200
    assert (await order(sara, game_id, 2, {"order": 4})).status_code in (200, 204)
    wait, due = due_of(game_id, user_id(third))
    assert due == wait + timedelta(hours=24)

    # Outside every Lab hour: offered, but unavailable, and the api refuses.
    before = (await insight(LECTURER, game_id)).json()
    assert (before["can_mark_in_room"], before["lab_hour_ends_at"], before["in_room"]) == (
        True,
        None,
        None,
    )
    assert code(await mark(LECTURER, game_id, 10)) == (409, "not_in_lab_hour")

    lab = await add(session_id, starts=NOW - 10 * MINUTE, ends=ENDS)
    assert lab.status_code == 201
    lab_id = lab.json()["id"]
    assert parse((await insight(LECTURER, game_id)).json()["lab_hour_ends_at"]) == ENDS
    for wrong in (1, 121, 7.5):
        assert code(await mark(LECTURER, game_id, wrong)) == (422, "minutes_out_of_range")

    marked = await mark(LECTURER, game_id, 10)
    assert marked.status_code == 200
    body = marked.json()
    assert (parse(body["in_room"]["until"]), body["in_room"]["minutes"]) == (ENDS, 10)
    assert body["lab_hour_ends_at"] is None  # marked: «Ikke i rommet lenger» instead
    assert due_of(game_id, user_id(third)) == (wait, wait + 10 * MINUTE)
    assert due_of(game_id, jonas_id)[1] == wait + 20 * MINUTE
    # The Oversikt carries the mark for the wall's row label.
    [row] = [
        g for g in (await overview(LECTURER, session_id)).json()["items"] if g["game_id"] == game_id
    ]
    assert parse(row["in_room_until"]) == ENDS
    # Each Student reads the line with their own minutes; Jonas's 2 × is his alone.
    for who, minutes in ((sara, 10), (third, 10), (jonas, 20)):
        line = (await play(who, game_id))["table_status"]["in_room"]
        assert (parse(line["until"]), line["minutes"]) == (ENDS, minutes)
    # Hjem carries the same line (Epic 8 close-out).
    jonas_home = (await home(jonas))["game"]["in_room"]
    assert (parse(jonas_home["until"]), jonas_home["minutes"]) == (ENDS, 20)
    assert code(await mark(LECTURER, game_id, 20)) == (409, "already_in_room")

    # The Lab hour moves: the mark follows its new end. Removed: the mark ends.
    later = ENDS + 30 * MINUTE
    assert (
        await change(session_id, lab_id, starts=NOW - 10 * MINUTE, ends=later)
    ).status_code == 200
    assert parse((await insight(LECTURER, game_id)).json()["in_room"]["until"]) == later
    assert (await remove(session_id, lab_id)).status_code == 204
    assert (await insight(LECTURER, game_id)).json()["in_room"] is None
    assert due_of(game_id, user_id(third)) == (wait, wait + timedelta(hours=24))
    assert (await play(sara, game_id))["table_status"]["in_room"] is None
    assert (await home(sara))["game"]["in_room"] is None

    # Marked again in a new Lab hour, then «Ikke i rommet lenger» by the Lecturer.
    assert (await add(session_id, starts=NOW - MINUTE, ends=ENDS)).status_code == 201
    assert (await mark(LECTURER, game_id, 15)).status_code == 200
    ended = await unmark(LECTURER, game_id)
    assert ended.status_code == 200
    assert ended.json()["in_room"] is None
    assert parse(ended.json()["lab_hour_ends_at"]) == ENDS  # it may be marked again
    assert code(await unmark(LECTURER, game_id)) == (409, "not_in_room")

    # Marked once more: the sweep ends it at the Lab hour's end.
    assert (await mark(LECTURER, game_id, 10)).status_code == 200
    assert (await sweep.run(ENDS))["games.end_in_room"] == 1
    assert (await insight(LECTURER, game_id)).json()["in_room"] is None

    actions = [
        action
        for (action,) in rows(
            "SELECT action FROM audit_events WHERE target_ids->>'game_id' = %s "
            "AND action LIKE 'game.%%room%%' ORDER BY id",
            game_id,
        )
    ]
    # The Lab hour's removal and the sweep end it as no person: only the Lecturer's own presses.
    assert actions == [
        "game.marked_in_room",
        "game.marked_in_room",
        "game.in_room_ended",
        "game.marked_in_room",
    ]


async def test_an_assistant_a_student_and_others_are_refused(klass):
    session_id, game_id, by_role = await three_students_in_uke_2(klass)
    sara = next(iter(by_role.values()))
    assert (await add(session_id, starts=NOW - MINUTE, ends=ENDS)).status_code == 201
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")
    refused = [
        await mark(ASSISTANT, game_id, 10),
        await mark(sara, game_id, 10),
        await mark(OTHER, game_id, 10),
        await mark(LECTURER, "not-an-id", 10),
        await unmark(ASSISTANT, game_id),
        await unmark(sara, game_id),
    ]
    assert {r.status_code for r in refused} == {403}
    seen = (await insight(ASSISTANT, game_id)).json()
    assert (seen["can_mark_in_room"], seen["lab_hour_ends_at"]) == (False, None)
    assert (await play(sara, game_id))["table_status"]["in_room"] is None
