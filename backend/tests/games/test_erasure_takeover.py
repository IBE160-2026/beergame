"""The Takeover before a User is erased (Story 15.2, FR-76, AD-2, AD-5): `games.service.
hand_over_seats_of` hands every Seat the User holds in a running Game to an AI player at once,
paused or not, due or not, ordered or not, with reason `takeover_inactivity` and no actor; drops
their queued Reclaims, so no Week opening gives a Seat back; tells the others only; and leaves a
Seat that ordered the Game's last Week as it is. No clock is compared."""

from app.modules.games import commands
from app.modules.games import service as games_service
from tests.conftest import TEST_DATABASE_URL
from tests.games.helpers import query
from tests.games.test_reclaim import occupancy, queued, taken_over
from tests.games.test_takeover import class_game


def notified() -> set:
    return {
        user
        for (user,) in query(
            TEST_DATABASE_URL, "SELECT user_id FROM notices WHERE kind = 'takeover_notice'", ()
        )
    }


async def test_a_paused_seat_that_is_not_due_is_handed_over_at_once(games_db, mail_db):
    game_id, students = await class_game(guided_weeks=0)
    sara, jonas = students["retailer"], students["factory"]
    await commands.place_order(game_id, "factory", 1, 4, "student", actor=jonas)
    await commands.pause(game_id, actor=sara)

    written = await games_service.hand_over_seats_of(jonas)

    assert len(written) == 1
    # Ordered already: the AI player takes the next Week, by the system, with no actor.
    from_week, kind, reason, user, actor = occupancy(game_id, "factory")[-1]
    assert (from_week, kind != "student", reason, user, actor) == (
        2,
        True,
        "takeover_inactivity",
        None,
        None,
    )
    assert notified() == {sara}
    # Again: nothing left to hand over.
    assert await games_service.hand_over_seats_of(jonas) == []
    assert len(occupancy(game_id, "factory")) == 2


async def test_a_queued_reclaim_is_dropped_so_no_week_gives_the_seat_back(games_db, mail_db):
    game_id, students = await taken_over()
    jonas = students["factory"]
    assert await commands.request_reclaim(game_id, "factory", actor=jonas)
    assert queued(game_id) == [("factory", jonas)]
    before = occupancy(game_id)

    assert await games_service.hand_over_seats_of(jonas) == []

    assert queued(game_id) == []
    assert occupancy(game_id) == before


async def test_a_seat_that_ordered_the_last_week_stays_as_it_is(games_db, mail_db):
    game_id, students = await class_game(guided_weeks=0)
    sara, jonas = students["retailer"], students["factory"]
    weeks = 8  # `SETTINGS.weeks`
    for week in range(1, weeks):
        await commands.place_order(game_id, "retailer", week, 4, "student", actor=sara)
        await commands.place_order(game_id, "factory", week, 4, "student", actor=jonas)
    await commands.place_order(game_id, "factory", weeks, 4, "student", actor=jonas)
    before = occupancy(game_id)

    assert await games_service.hand_over_seats_of(jonas) == []

    assert occupancy(game_id) == before
    assert notified() == set()
