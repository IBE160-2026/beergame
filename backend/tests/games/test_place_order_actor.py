"""Story 6.12 (AD-2, AD-8): `place_order` with an `actor` places the Order only for the Student who
holds the Seat, and tells each Student whose waiting status changed (`user:<id>`)."""

import uuid

import pytest

from app.modules.games import commands
from tests.conftest import TEST_DATABASE_URL
from tests.games.helpers import listening, query
from tests.games.test_set_snapshot import SETTINGS, snapshot

FREE = {
    **snapshot(),
    "settings": SETTINGS.model_copy(update={"guided_weeks": 0}).model_dump(mode="json"),
}
"""A Class game snapshot without Guided Weeks: the Students' own Orders complete each Week."""


async def class_game(*roles: str) -> tuple[str, dict[str, uuid.UUID]]:
    """A started Class game with one Student on each of `roles`; the other Seats are Rule-based."""
    game_id = await commands.create("class", class_session_id=uuid.uuid7(), game_number=1)
    students = {role: uuid.uuid7() for role in roles}
    for role, user in students.items():
        await commands.assign_seat(game_id, role, "student", user_id=user)
    await commands.set_snapshot(game_id, FREE, keep_students=list(students.values()))
    await commands.start(game_id)
    return game_id, students


def state(game_id: str) -> tuple[int, int]:
    """(version, Decision log rows) of the Game."""
    [(version,)] = query(TEST_DATABASE_URL, "SELECT version FROM games WHERE id = %s", (game_id,))
    [(rows,)] = query(
        TEST_DATABASE_URL, "SELECT count(*) FROM seat_weeks WHERE game_id = %s", (game_id,)
    )
    return version, rows


async def test_an_actor_who_does_not_hold_the_seat_is_refused_and_nothing_is_written(games_db):
    game_id, students = await class_game("retailer", "wholesaler")
    before = state(game_id)
    for seat, actor in [
        ("retailer", uuid.uuid7()),  # a stranger
        ("retailer", students["wholesaler"]),  # another Student of the Game
        ("factory", students["retailer"]),  # a Rule-based Seat
        ("retailer", "not-a-user-id"),
    ]:
        with pytest.raises(commands.CommandError) as refused:
            await commands.place_order(game_id, seat, 1, 4, "student", actor=actor)
        assert (refused.value.code, refused.value.status) == ("seat_not_yours", 409)
    assert state(game_id) == before


async def test_a_stored_order_is_told_only_to_its_student_also_after_the_week(games_db):
    """Story 6.13: `order_exists` comes before `week_not_open`, but never before the actor
    check: another Student learns nothing about the Seat's Order (FR-5)."""
    game_id, students = await class_game("retailer")
    placed = await commands.place_order(
        game_id, "retailer", 1, 24, "student", actor=students["retailer"]
    )
    assert placed.open_week == 2  # the only Student completed Week 1
    with pytest.raises(commands.CommandError) as refused:
        await commands.place_order(game_id, "retailer", 1, 9, "student", actor=uuid.uuid7())
    assert refused.value.code == "seat_not_yours"
    with pytest.raises(commands.CommandError) as retried:
        await commands.place_order(game_id, "retailer", 1, 9, "student", actor=students["retailer"])
    assert retried.value.code == "order_exists"


async def test_the_actor_who_holds_the_seat_orders_and_no_actor_skips_the_check(games_db):
    game_id, students = await class_game("retailer", "wholesaler")
    placed = await commands.place_order(
        game_id, "retailer", 1, 24, "student", actor=students["retailer"]
    )
    assert (placed.week, placed.open_week) == (1, 1)  # the Wholesaler has not ordered
    # A call without a person (the order source, a test) is not checked.
    await commands.place_order(game_id, "wholesaler", 1, 7, "student")
    rows = query(
        TEST_DATABASE_URL,
        'SELECT s.role, w."order", w.decided_by FROM seat_weeks w JOIN seats s ON s.id = w.seat_id '
        "WHERE w.game_id = %s AND w.week = 1 AND s.role IN ('retailer', 'wholesaler') "
        "ORDER BY s.role",
        (game_id,),
    )
    assert rows == [("retailer", 24, "student"), ("wholesaler", 7, "student")]


async def test_users_told_are_the_actor_and_every_student_when_the_week_completes(games_db):
    game_id, students = await class_game("retailer", "wholesaler")
    with listening(games_db) as events:
        await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
        first = events.drain()
        placed = await commands.place_order(
            game_id, "wholesaler", 1, 4, "student", actor=students["wholesaler"]
        )
        second = events.drain()
    assert placed.open_week == 2

    def told(received: list[dict]) -> set[str]:
        return {item["id"] for item in received if item["topic"] == "user"}

    # Week 1 still waits for the Wholesaler: only the Retailer's own status changed.
    assert told(first) == {str(students["retailer"])}
    assert {item["topic"] for item in first} == {"game", "session", "user"}
    # The Wholesaler's Order completed Week 1: both Students see Week 2.
    assert told(second) == {str(each) for each in students.values()}
