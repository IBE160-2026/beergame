"""Story 6.12: «Bekreft ordre på 24» places the Student's Order for the open Week through
`POST /api/me/games/{id}/weeks/{week}/order`, only through `games.commands.place_order` with the
Student as actor (FR-24, AD-2). The client sends no `version`; a refusal answers the command's
code; any other game is refused alike (FR-5)."""

import uuid

from app.engine import GameSettings
from tests.classes.test_classes import make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_staff import call
from tests.conftest import TEST_DATABASE_URL
from tests.games.helpers import query
from tests.sessions.test_dates import OUTSIDER
from tests.sessions.test_guided_weeks import view, weeks_and_orders
from tests.sessions.test_play import play, running
from tests.sessions.test_student_home import _empty, clock, klass

__all__ = ["_empty", "clock", "klass"]

CLASSIC = GameSettings()


async def order(who: str, game_id: str, week: int, body: object):
    return await call(who, "POST", f"/api/me/games/{game_id}/weeks/{week}/order", json=body)


async def free_week(klass: str, students: int = 1) -> tuple[str, dict[str, str]]:
    """`students` Students (the other Seats Rule-based) past the Guided Weeks: (game id, email by
    Role)."""
    _, game_id, by_role = await running(klass, students=students)
    for week in range(1, CLASSIC.guided_weeks + 1):
        for who in by_role.values():
            assert (await view(who, game_id, week)).status_code == 204
    return game_id, by_role


def code(response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


async def test_the_student_orders_once_and_the_week_moves_on(klass):
    game_id, by_role = await free_week(klass)
    [(role, who)] = by_role.items()
    week = CLASSIC.guided_weeks + 1
    envelope = (await play(who, game_id)).json()
    assert envelope["seat_state"]["week"] == week
    assert envelope["turn"] == {"guided": False, "order": None, "viewed": False}
    answer = await order(who, game_id, week, {"order": 24})
    assert answer.status_code == 204 and answer.content == b""
    [(decided_by, placed)] = query(
        TEST_DATABASE_URL,
        'SELECT w.decided_by, w."order" FROM seat_weeks w JOIN seats s ON s.id = w.seat_id '
        "WHERE w.game_id = %s AND w.week = %s AND s.role = %s",
        (game_id, week, role),
    )
    assert (decided_by, placed) == ("student", 24)
    # The only Student completed the Week: the next one is open and waits for them.
    envelope = (await play(who, game_id)).json()
    assert envelope["seat_state"]["week"] == week + 1
    assert envelope["seat_state"]["history"][-1]["order"] == 24
    assert envelope["turn"]["order"] is None
    # An Order for a Week the game has left is refused.
    assert code(await order(who, game_id, week, {"order": 5})) == (409, "week_not_open")


async def test_an_order_already_placed_is_not_placed_again(klass):
    game_id, by_role = await free_week(klass, students=2)
    week = CLASSIC.guided_weeks + 1
    who = next(iter(by_role.values()))
    before_order = (await play(who, game_id)).json()["seat_state"]
    assert (await order(who, game_id, week, {"order": 9})).status_code == 204
    # The other Student has not ordered: the Week is open and shows the placed Order. The Seat's
    # numbers, the preview bases included, stay those of the Week before the Order, so the
    # screen's preview of the sent Order (`lib/preview.ts`) does not count it twice.
    after = (await play(who, game_id)).json()
    assert after["turn"] == {"guided": False, "order": 9, "viewed": False}
    assert after["seat_state"] == before_order
    before = weeks_and_orders(game_id)
    assert code(await order(who, game_id, week, {"order": 24})) == (409, "order_exists")
    assert weeks_and_orders(game_id) == before


async def test_invalid_orders_and_guided_weeks_are_refused_with_nothing_written(klass):
    _, game_id, by_role = await running(klass, students=1)
    [who] = by_role.values()
    before = weeks_and_orders(game_id)
    # A Guided Week's fixed Order was placed when it opened (Story 6.10): it stands.
    assert code(await order(who, game_id, 1, {"order": 4})) == (409, "order_exists")
    for value in [-1, CLASSIC.max_order + 1]:
        assert code(await order(who, game_id, 1, {"order": value})) == (422, "order_invalid")
    for body in [{"order": "24"}, {"order": 2.5}, {}, {"order": 4, "version": 3}]:
        assert (await order(who, game_id, 1, body)).status_code == 422
    assert weeks_and_orders(game_id) == before


async def test_another_game_is_refused_alike_and_a_finished_one_by_code(klass):
    _, game_id, by_role = await running(klass, students=1)
    [who] = by_role.values()
    week = 1
    await make(OUTSIDER, roles=())
    refusals = [
        await order(OUTSIDER, game_id, week, {"order": 4}),
        await order(who, str(uuid.uuid7()), week, {"order": 4}),
        await order(who, "not-an-id", week, {"order": 4}),
    ]
    assert {r.status_code for r in refusals} == {403}
    assert len({r.content for r in refusals}) == 1
    execute("UPDATE games SET lifecycle = 'finished' WHERE id = %s", game_id)
    assert code(await order(who, game_id, week, {"order": 4})) == (409, "game_finished")
