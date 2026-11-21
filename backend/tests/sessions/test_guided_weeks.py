"""Story 6.10: four Students play the Guided Weeks of a Classic Class game through the api. Each
Guided Week opens with every Seat's fixed Order (`guided`); a Student's view
(`POST /api/me/games/{id}/weeks/{week}/view`) counts as ordering, and the view that leaves no
Student to wait for advances exactly one Week, whatever order the views come in (FR-24, AD-2)."""

import asyncio
import uuid

from app.engine import GameSettings, guided_order
from tests.classes.test_classes import make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_staff import call
from tests.games.helpers import query
from tests.sessions.test_dates import OUTSIDER
from tests.sessions.test_play import play, running
from tests.sessions.test_student_home import _empty, clock, klass

__all__ = ["_empty", "clock", "klass"]

CLASSIC = GameSettings()


async def view(who: str, game_id: str, week: int):
    return await call(who, "POST", f"/api/me/games/{game_id}/weeks/{week}/view")


def weeks_and_orders(game_id: str) -> tuple[list[tuple], list[tuple]]:
    """The opened Week states (week, finished) and the Decision log (week, order, decided_by)."""
    from tests.conftest import TEST_DATABASE_URL

    states = query(
        TEST_DATABASE_URL,
        "SELECT week, finished FROM game_weeks WHERE game_id = %s ORDER BY week, finished",
        (game_id,),
    )
    orders = query(
        TEST_DATABASE_URL,
        'SELECT week, "order", decided_by FROM seat_weeks WHERE game_id = %s ORDER BY week',
        (game_id,),
    )
    return states, orders


async def test_four_students_view_the_guided_weeks_in_any_order(klass):
    _, game_id, by_role = await running(klass)
    roles = list(by_role)
    fixed = guided_order(CLASSIC)
    arrivals = {
        1: roles,  # one after the other
        2: roles[::-1],
        3: [roles[2], roles[0], roles[3], roles[1]],
        4: None,  # all four at the same moment
    }
    for week, order in arrivals.items():
        # The Week opened with four guided Orders and waits for the views.
        states, orders = weeks_and_orders(game_id)
        assert states == [(w, False) for w in range(1, week + 1)]
        assert [row for row in orders if row[0] == week] == [(week, fixed, "guided")] * 4
        envelope = (await play(by_role[roles[0]], game_id)).json()
        assert envelope["turn"] == {"guided": True, "order": fixed, "viewed": False}
        if order is None:
            answers = await asyncio.gather(*(view(by_role[role], game_id, week) for role in roles))
            assert [answer.status_code for answer in answers] == [204] * 4
        else:
            for index, role in enumerate(order):
                assert (await view(by_role[role], game_id, week)).status_code == 204
                if index < 3:  # still open: a repeated view changes nothing
                    assert weeks_and_orders(game_id)[0][-1] == (week, False)
                    assert (await view(by_role[role], game_id, week)).status_code == 204
                    assert len(weeks_and_orders(game_id)[0]) == week
        # Exactly one advance: the next Week is open, once.
        assert weeks_and_orders(game_id)[0] == [(w, False) for w in range(1, week + 2)]
    # Week 5 is played: no guided Order, and it waits for the Students' own Orders.
    states, orders = weeks_and_orders(game_id)
    assert states[-1] == (5, False)
    assert len(orders) == 16 and {row[2] for row in orders} == {"guided"}
    envelope = (await play(by_role[roles[0]], game_id)).json()
    assert envelope["seat_state"]["week"] == 5
    assert envelope["turn"] == {"guided": False, "order": None, "viewed": False}
    refused = await view(by_role[roles[0]], game_id, 5)
    assert (refused.status_code, refused.json()["error"]["code"]) == (409, "week_not_guided")
    stale = await view(by_role[roles[0]], game_id, 4)
    assert (stale.status_code, stale.json()["error"]["code"]) == (409, "week_not_open")


async def test_the_envelope_says_when_the_student_has_viewed(klass):
    _, game_id, by_role = await running(klass)
    who = next(iter(by_role.values()))
    assert (await view(who, game_id, 1)).status_code == 204
    envelope = (await play(who, game_id)).json()
    assert envelope["turn"] == {"guided": True, "order": 4, "viewed": True}


async def test_another_game_is_refused_alike(klass):
    _, game_id, by_role = await running(klass, students=4)
    await make(OUTSIDER, roles=())
    who = next(iter(by_role.values()))
    refusals = [
        await view(OUTSIDER, game_id, 1),
        await view(who, str(uuid.uuid7()), 1),
        await view(who, "not-an-id", 1),
    ]
    assert {r.status_code for r in refusals} == {403}
    assert len({r.content for r in refusals}) == 1
    execute("UPDATE games SET lifecycle = 'finished' WHERE id = %s", game_id)
    ended = await view(who, game_id, 1)
    assert (ended.status_code, ended.json()["error"]["code"]) == (409, "game_finished")
