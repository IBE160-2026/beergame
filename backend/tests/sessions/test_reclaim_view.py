"""Story 8.4 through the api: the Student whose Seat an AI player took over presses «Ta tilbake
setet»; the request is queued and shown on their own Seat only, a repeat changes nothing, another
Student is refused `seat_not_yours`, and the Seat is theirs again when the next Uke opens (FR-37,
AD-2, AD-12). The Takeover runs at its stored due time (Issue #63)."""

import uuid
from datetime import timedelta

from app.modules.ops import sweep
from tests.classes.test_classes import make
from tests.classes.test_staff import call
from tests.conftest import TEST_DATABASE_URL
from tests.games.helpers import query
from tests.sessions.test_dates import OUTSIDER
from tests.sessions.test_guided_weeks import view as view_as
from tests.sessions.test_orders import code
from tests.sessions.test_play import running
from tests.sessions.test_student_home import _empty, clock, home, klass
from tests.sessions.test_takeover_view import due, seat

__all__ = ["_empty", "clock", "klass"]


async def reclaim(who: str, game_id: str, role: str):
    return await call(who, "POST", f"/api/me/games/{game_id}/seats/{role}/reclaim")


async def test_the_student_takes_the_seat_back_from_the_next_uke(klass):
    _, game_id, by_role = await running(klass, students=2)
    first, absent = by_role
    assert (await view_as(by_role[first], game_id, 1)).status_code == 204
    await sweep.run(due(game_id, absent) + timedelta(seconds=30))
    assert seat((await home(by_role[absent]))["game"]["seats"], absent)["taken_over"] is True

    # Another Student of the game may not ask for it; a game not theirs is forbidden (FR-5).
    assert code(await reclaim(by_role[first], game_id, absent)) == (409, "seat_not_yours")
    assert code(await reclaim(by_role[absent], game_id, first)) == (409, "seat_not_yours")
    await make(OUTSIDER, roles=())
    assert code(await reclaim(OUTSIDER, game_id, absent)) == (403, "forbidden")
    assert code(await reclaim(by_role[absent], str(uuid.uuid7()), absent)) == (403, "forbidden")
    assert (
        query(TEST_DATABASE_URL, "SELECT 1 FROM seat_reclaims WHERE game_id = %s", (game_id,)) == []
    )

    answer = await reclaim(by_role[absent], game_id, absent)
    assert answer.status_code == 200
    own = seat(answer.json()["seats"], absent)
    assert (own["holder"], own["taken_over"], own["reclaim_queued"]) == ("ai", True, True)
    # A second press answers the same and changes nothing.
    again = await reclaim(by_role[absent], game_id, absent)
    assert again.status_code == 200 and seat(again.json()["seats"], absent)["reclaim_queued"]
    other = seat((await home(by_role[first]))["game"]["seats"], absent)
    assert other["reclaim_queued"] is False

    # The other Student opens the Guided Uke 2: Uke 3 opens with the Seat back.
    assert (await view_as(by_role[first], game_id, 2)).status_code == 204
    back = await home(by_role[absent])
    mine = seat(back["game"]["seats"], absent)
    assert (mine["holder"], mine["taken_over"], mine["reclaim_queued"]) == ("student", False, False)
    assert back["game"]["week"] == 3
