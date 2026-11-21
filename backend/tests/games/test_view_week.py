"""Story 6.10: `games.commands.view_week` records that a Student opened a Guided Week, once, and
the view that leaves no Student Seat unviewed advances exactly one Week in its transaction
(FR-24, AD-2, AD-8)."""

import uuid

import pytest
from sqlalchemy import event

from app.engine import GameSettings
from app.modules.games import commands, service
from app.platform.db import get_engine
from tests.conftest import TEST_DATABASE_URL
from tests.games.helpers import listening, query, seat_student, student_of, view

ROLES = ("retailer", "wholesaler", "distributor", "factory")
SHORT = GameSettings(weeks=8, guided_weeks=2)


async def started(*students: str, settings: GameSettings = SHORT) -> str:
    """A started Game in which `students` hold their Seats and Rule-based players the rest."""
    game_id = await commands.create("simulation", settings, seed=1)
    seat_student(TEST_DATABASE_URL, game_id, *students)
    await commands.start(game_id)
    return game_id


def stored(game_id: str) -> tuple:
    """Version, opened Weeks, Decision log rows and viewed turns."""
    (row,) = query(
        TEST_DATABASE_URL,
        "SELECT (SELECT version FROM games WHERE id = %s), "
        "(SELECT count(*) FROM game_weeks WHERE game_id = %s), "
        "(SELECT count(*) FROM seat_weeks WHERE game_id = %s), "
        "(SELECT count(*) FROM seat_turns WHERE game_id = %s AND viewed_at IS NOT NULL)",
        (game_id,) * 4,
    )
    return row


def guided_rows(game_id: str, week: int) -> list[tuple]:
    return query(
        TEST_DATABASE_URL,
        "SELECT s.role, w.order, w.decided_by, w.occupant_kind FROM seat_weeks w "
        "JOIN seats s ON s.id = w.seat_id WHERE w.game_id = %s AND w.week = %s "
        "ORDER BY s.position",
        (game_id, week),
    )


async def test_a_view_is_recorded_once_and_the_last_one_advances_in_its_transaction(games_db):
    game_id = await started("retailer", "factory")
    # Every Seat's Guided Order was placed when the Week opened, the Students' too.
    assert guided_rows(game_id, 1) == [
        ("retailer", 4, "guided", "student"),
        ("wholesaler", 4, "guided", "rule_based"),
        ("distributor", 4, "guided", "rule_based"),
        ("factory", 4, "guided", "student"),
    ]
    version, weeks, rows, viewed = stored(game_id)
    assert (weeks, rows, viewed) == (1, 4, 0)
    with listening(games_db) as events:
        assert await view(game_id, "retailer", 1) is True
        received = events.drain()
    assert received == [
        {"topic": "game", "id": game_id, "version": version + 1},
        {"topic": "user", "id": str(student_of(game_id, "retailer")), "version": None},
    ]
    assert stored(game_id) == (version + 1, 1, 4, 1)  # waits for the Fabrikk's view
    turn = await service.open_turn(game_id, "retailer")
    assert turn.viewed_at is not None and turn.viewed_at >= turn.opened_at
    # The same view again changes nothing: no write, no version, no event.
    with listening(games_db) as events:
        assert await view(game_id, "retailer", 1) is False
        assert events.drain() == []
    assert stored(game_id) == (version + 1, 1, 4, 1)
    assert (await service.open_turn(game_id, "retailer")).viewed_at == turn.viewed_at

    commits: list[bool] = []
    engine = get_engine().sync_engine
    commit = lambda conn: commits.append(True)  # noqa: E731
    event.listen(engine, "commit", commit)
    try:
        with listening(games_db) as events:
            assert await view(game_id, "factory", 1) is True
            received = events.drain()
    finally:
        event.remove(engine, "commit", commit)
    assert len(commits) == 1  # the view and the advance are one transaction
    students = sorted(str(student_of(game_id, role)) for role in ("retailer", "factory"))
    assert received == [
        {"topic": "game", "id": game_id, "version": version + 2},
        *({"topic": "user", "id": student, "version": None} for student in students),
    ]
    assert stored(game_id)[:3] == (version + 2, 2, 8)
    assert [row[2] for row in guided_rows(game_id, 2)] == ["guided"] * 4


async def test_a_game_without_students_passes_its_guided_weeks_as_before(games_db):
    game_id = await started()
    assert (await service.get_game(game_id)).lifecycle == "finished"
    rows = query(
        TEST_DATABASE_URL,
        "SELECT DISTINCT decided_by FROM seat_weeks WHERE game_id = %s AND week <= 2",
        (game_id,),
    )
    assert rows == [("guided",)]


async def assert_refused(game_id: str, call, code: str, status: int) -> None:
    before = stored(game_id)
    with listening(TEST_DATABASE_URL) as events:
        with pytest.raises(commands.CommandError) as caught:
            await call
        assert events.drain() == []
    assert (caught.value.code, caught.value.status) == (code, status)
    assert stored(game_id) == before


async def test_refusals_write_nothing(games_db):
    game_id = await started("retailer", "wholesaler")
    retailer = student_of(game_id, "retailer")
    cases = [
        (commands.view_week(game_id, "retailer", 2, actor=retailer), "week_not_open", 409),
        (commands.view_week(game_id, "retailer", "1", actor=retailer), "week_not_open", 409),
        (commands.view_week(game_id, "factory", 1, actor=retailer), "seat_not_student", 409),
        (
            commands.view_week(game_id, "retailer", 1, actor=student_of(game_id, "wholesaler")),
            "seat_not_yours",
            409,
        ),
        (commands.view_week(game_id, "retailer", 1, actor="nobody"), "seat_not_yours", 409),
        (commands.view_week(game_id, "brewer", 1, actor=retailer), "seat_not_found", 404),
    ]
    for call, code, status in cases:
        await assert_refused(game_id, call, code, status)
    with pytest.raises(commands.CommandError) as caught:
        await commands.view_week(str(uuid.uuid7()), "retailer", 1, actor=retailer)
    assert caught.value.code == "game_not_found"


async def test_only_a_guided_week_of_a_running_game_is_viewed(games_db):
    free = await started("retailer", settings=GameSettings(weeks=8, guided_weeks=0))
    await assert_refused(free, view(free, "retailer", 1), "week_not_guided", 409)
    created = await commands.create("simulation", SHORT, seed=1)
    seat_student(TEST_DATABASE_URL, created, "retailer")
    await assert_refused(created, view(created, "retailer", 1), "game_not_started", 409)
    finished = await started("retailer")
    await commands.switch_to_rule_based(finished, "retailer", "takeover_staff")
    assert (await service.get_game(finished)).lifecycle == "finished"
    await assert_refused(finished, view(finished, "retailer", 1), "game_finished", 409)


async def test_a_week_opened_without_the_students_guided_order_gets_it_at_the_view(
    games_db, monkeypatch
):
    """A Game started before Story 6.10 placed no Student's Guided Order when the Week opened;
    the view places it, so the Week can still complete."""
    from app.modules.players import service as players

    real = players._order

    def before_6_10(turn):
        if turn.occupant_kind is players.games_service.OccupantKind.STUDENT:
            return None
        return real(turn)

    monkeypatch.setattr(players, "_order", before_6_10)
    game_id = await started("retailer")
    monkeypatch.undo()
    assert [row[0] for row in guided_rows(game_id, 1)] == ["wholesaler", "distributor", "factory"]
    assert await view(game_id, "retailer", 1)
    assert guided_rows(game_id, 1)[0] == ("retailer", 4, "guided", "student")
    assert stored(game_id)[1] == 2  # the view completed Week 1
