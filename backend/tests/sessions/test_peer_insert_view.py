"""Story 8.8 through the api: «Sett inn KI-spiller for Jonas» (`POST /api/me/games/{id}/seats/
{role}/takeover`). The other Students read the absent Seat's insert time before it passes, the
control once it has passed (paused or not), and after a press the AI player with who put it in;
a second press is told who came first; nobody outside the game may press (FR-89, FR-37, FR-5,
AD-10, AD-12, UX-DR27).

One short Class game (`three_students_in_uke_2`) serves the whole story, so it is played once.
Insert times that must have passed are written directly, read from the database clock."""

import uuid
from datetime import datetime, timedelta

from app.modules.games import commands
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_staff import call
from tests.messaging.helpers import rows
from tests.sessions.test_dates import OUTSIDER
from tests.sessions.test_game_end import _empty, clock, klass
from tests.sessions.test_orders import code, order
from tests.sessions.test_pause_view import name_of, pause, three_students_in_uke_2
from tests.sessions.test_play import play
from tests.sessions.test_student_home import home

__all__ = ["_empty", "clock", "klass"]


async def insert(who: str, game_id: str, role: str):
    return await call(who, "POST", f"/api/me/games/{game_id}/seats/{role}/takeover")


def seat_of(seats: list[dict], role: str) -> dict:
    return next(seat for seat in seats if seat["role"] == role)


def set_insert(game_id: str, role: str, offset: timedelta) -> None:
    """The Seat's insert time in Uke 2 at the database clock plus `offset`."""
    execute(
        "UPDATE seat_turns SET insert_allowed_at = clock_timestamp() + %s WHERE game_id = %s "
        "AND week = 2 AND seat_id = (SELECT id FROM seats WHERE game_id = %s AND role = %s)",
        offset,
        game_id,
        game_id,
        role,
    )


async def test_students_put_an_ai_player_in_an_absent_seat(klass):
    _, game_id, by_role = await three_students_in_uke_2(klass)
    (sara_role, sara), (jonas_role, jonas), (third_role, third) = by_role.items()
    assert (await order(sara, game_id, 2, {"order": 4})).status_code == 204

    # Before the Pause nothing is said: the automatic Takeover governs the Seat's own limit.
    seat = seat_of((await home(third))["game"]["seats"], jonas_role)
    assert (seat["insert_at"], seat["can_insert"]) == (None, False)
    assert code(await insert(third, game_id, jonas_role)) == (409, "insert_not_allowed_yet")

    # Paused: the others read Jonas's own insert time, never why; Jonas does not.
    assert (await pause(sara, game_id)).status_code == 200
    [(due,)] = rows(
        "SELECT t.insert_allowed_at FROM seat_turns t JOIN seats s ON s.id = t.seat_id "
        "WHERE t.game_id = %s AND t.week = 2 AND s.role = %s",
        game_id,
        jonas_role,
    )
    for who in (sara, third):
        seat = seat_of((await home(who))["game"]["seats"], jonas_role)
        assert datetime.fromisoformat(seat["insert_at"]) == due
        assert (seat["insert_agreed"], seat["can_insert"]) == (False, False)
    own = seat_of((await home(jonas))["game"]["seats"], jonas_role)
    assert (own["insert_at"], own["can_insert"]) == (None, False)
    # An agreed time reads as one («Avtalt tid …») on Spill too.
    set_insert(game_id, jonas_role, timedelta(hours=2))
    seat = seat_of((await play(third, game_id)).json()["table_status"]["seats"], jonas_role)
    assert (seat["insert_agreed"], seat["can_insert"]) == (True, False)

    # Passed: the control shows to every other Student on Spill and Hjem, still paused.
    set_insert(game_id, jonas_role, -timedelta(seconds=1))
    for who in (sara, third):
        seat = seat_of((await play(who, game_id)).json()["table_status"]["seats"], jonas_role)
        assert (seat["insert_at"], seat["can_insert"]) == (None, True)
        assert seat_of((await home(who))["game"]["seats"], jonas_role)["can_insert"]
    assert not seat_of((await home(jonas))["game"]["seats"], jonas_role)["can_insert"]
    # Nobody else may press, and a Student cannot press for their own Seat.
    await make(OUTSIDER, roles=())
    assert code(await insert(OUTSIDER, game_id, jonas_role)) == (403, "forbidden")
    assert code(await insert(LECTURER, game_id, jonas_role)) == (403, "forbidden")
    assert code(await insert(jonas, game_id, jonas_role)) == (409, "seat_not_yours")
    assert code(await insert(third, game_id, sara_role)) == (409, "order_exists")

    # Sara presses: the game as it now stands names who put the AI player in.
    pressed = await insert(sara, game_id, jonas_role)
    assert pressed.status_code == 200
    seat = seat_of(pressed.json()["seats"], jonas_role)
    assert (seat["holder"], seat["taken_over"], seat["can_insert"], seat["inserted_by"]) == (
        "ai",
        True,
        False,
        name_of(sara),
    )
    assert seat["ordering_for"] == name_of(jonas)
    # Jonas's own Seat is taken over: «Ta tilbake setet» follows from Story 8.4's view.
    assert seat_of((await home(jonas))["game"]["seats"], jonas_role)["mine"]
    assert seat_of((await home(jonas))["game"]["seats"], jonas_role)["taken_over"]

    # The third Student pressed too late: told who came first, by kind and id.
    late = await insert(third, game_id, jonas_role)
    assert code(late) == (409, "takeover_exists")
    [(sara_id,)] = rows("SELECT id FROM users WHERE email = %s", sara)
    assert late.json()["error"]["fields"]["acted_by"] == {
        "kind": "student",
        "user_id": str(sara_id),
    }
    seat = seat_of((await home(third))["game"]["seats"], jonas_role)
    assert seat["inserted_by"] == name_of(sara)

    # A Lecturer put an AI player in the third Seat first: the Student is told so by kind only,
    # never the staff member's id.
    set_insert(game_id, third_role, -timedelta(seconds=1))
    await commands.takeover(game_id, third_role, actor="staff", actor_user_id=uuid.uuid7())
    staff_first = await insert(sara, game_id, third_role)
    assert code(staff_first) == (409, "takeover_exists")
    assert staff_first.json()["error"]["fields"]["acted_by"] == {"kind": "staff", "user_id": None}
