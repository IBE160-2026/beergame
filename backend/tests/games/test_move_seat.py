"""`games.commands.move_seat` (Story 5.10, FR-20, AD-2, AD-5, AD-8): a Student moves to a free
Seat or swaps with another Student, across the Class games of one Class session, before they
start. Occupancy stays append-only: the Seat left free gets a row with no occupant kind and the
reason `moved`."""

import uuid

import psycopg
import pytest

from app.engine import GameSettings
from app.modules.games import commands, repo, service
from app.platform.events.registry import COMMAND_TOPICS
from tests.games.helpers import execute, listening, query
from tests.games.test_assign_seat import assert_refused, version
from tests.games.test_class_games import SESSION, class_game

A = uuid.UUID("01900000-0000-7000-8000-0000000000a1")
B = uuid.UUID("01900000-0000-7000-8000-0000000000b2")


async def seat(game_id: str, role: str, student: uuid.UUID) -> None:
    await commands.assign_seat(game_id, role, "student", user_id=student)


def holders(url: str, game_id: str) -> dict[str, str | None]:
    """Each Seat's current Student by Role (None: free), from the latest occupancy row."""
    found = query(
        url,
        "SELECT DISTINCT ON (s.id) s.role, o.user_id::text FROM seats s "
        "LEFT JOIN seat_occupancy o ON o.seat_id = s.id WHERE s.game_id = %s "
        "ORDER BY s.id, o.id DESC",
        (game_id,),
    )
    return dict(found)


async def test_a_move_to_a_free_seat_leaves_a_free_seat_row(games_db):
    first, second = await class_game(1), await class_game(2)
    await seat(first, "factory", A)
    with listening(games_db) as events:
        await commands.move_seat(first, "factory", second, "wholesaler")
        received = events.drain()
    assert holders(games_db, first)["factory"] is None
    assert holders(games_db, second)["wholesaler"] == str(A)
    rows = query(
        games_db,
        "SELECT s.role, o.from_week, o.occupant_kind, o.policy_id, o.reason, o.user_id::text "
        "FROM seat_occupancy o JOIN seats s ON s.id = o.seat_id ORDER BY o.id",
    )
    assert rows == [
        ("factory", 1, "student", None, "initial", str(A)),
        ("wholesaler", 1, "student", None, "initial", str(A)),
        ("factory", 1, None, None, "moved", None),
    ]
    # Each Game's version rises once, with its Class session and the Student told.
    assert {(e["topic"], e["id"]) for e in received} == {
        ("game", first),
        ("game", second),
        ("session", str(SESSION)),
        ("user", str(A)),
    }
    assert {e["topic"] for e in received} == COMMAND_TOPICS["games.move_seat"]
    assert (version(games_db, first), version(games_db, second)) == (3, 2)
    # The freed Seat reads as free everywhere and takes a new occupant.
    game = await service.get_game(first)
    assert next(s for s in game.seats if s.role == "factory").occupant_kind is None
    history = await service.occupancy_history(first)
    assert [(r.occupant_kind, r.reason) for r in history] == [
        ("student", "initial"),
        (None, "moved"),
    ]
    await seat(first, "factory", B)
    assert holders(games_db, first)["factory"] == str(B)


async def test_a_swap_exchanges_two_students_across_games(games_db):
    first, second = await class_game(1), await class_game(2)
    await seat(first, "retailer", A)
    await seat(second, "distributor", B)
    with listening(games_db) as events:
        await commands.move_seat(second, "distributor", first, "retailer")
        received = events.drain()
    assert holders(games_db, first)["retailer"] == str(B)
    assert holders(games_db, second)["distributor"] == str(A)
    assert {(e["topic"], e["id"]) for e in received if e["topic"] == "user"} == {
        ("user", str(A)),
        ("user", str(B)),
    }
    assert query(games_db, "SELECT count(*) FROM seat_occupancy WHERE occupant_kind IS NULL") == [
        (0,)
    ]


async def test_a_move_within_one_game_changes_the_role(games_db):
    game_id = await class_game(1)
    await seat(game_id, "retailer", A)
    await commands.move_seat(game_id, "retailer", game_id, "factory")
    assert holders(games_db, game_id) == {
        "retailer": None,
        "factory": str(A),
        "wholesaler": None,
        "distributor": None,
    }
    assert version(games_db, game_id) == 3  # one bump for the one Game


async def test_the_games_are_locked_in_id_order(games_db, monkeypatch):
    first, second = await class_game(1), await class_game(2)
    await seat(second, "factory", A)
    locked: list[uuid.UUID] = []
    lock = repo.lock_game

    async def recording(session, game_id):
        locked.append(game_id)
        return await lock(session, game_id)

    monkeypatch.setattr(repo, "lock_game", recording)
    # From the newer Game to the older one: the older (lower id) is locked first.
    await commands.move_seat(second, "factory", first, "factory")
    assert locked[:2] == sorted([uuid.UUID(first), uuid.UUID(second)])


async def test_move_seat_refusals_change_nothing(games_db):
    first, second = await class_game(1), await class_game(2)
    other = await class_game(1, uuid.UUID("01900000-0000-7000-8000-000000000002"))
    await seat(first, "retailer", A)
    await seat(second, "retailer", B)
    await commands.assign_seat(second, "factory", "rule_based")
    simulation = await commands.create("simulation", GameSettings(), seed=1)
    cases = [
        (first, "retailer", first, "retailer", "same_seat", 422),
        (first, "factory", second, "factory", "seat_not_student", 409),
        (second, "factory", first, "factory", "seat_not_student", 409),  # an AI player
        (first, "retailer", second, "factory", "seat_occupied", 409),
        (first, "retailer", other, "factory", "class_session_mismatch", 422),
        (first, "nope", second, "factory", "unknown_role", 422),
        (simulation, "retailer", simulation, "factory", "class_session_mismatch", 422),
        (first, "retailer", str(uuid.uuid7()), "factory", "game_not_found", 404),
    ]
    for source, role, target, to_role, code, status in cases:
        await assert_refused(
            games_db, source, code, status, commands.move_seat(source, role, target, to_role)
        )
    execute(games_db, "UPDATE games SET lifecycle = 'running' WHERE id = %s", (second,))
    await assert_refused(
        games_db,
        first,
        "game_already_started",
        409,
        commands.move_seat(first, "retailer", second, "wholesaler"),
    )


async def test_a_free_seat_row_has_no_kind_and_only_the_moved_reason(games_db):
    game_id = await class_game(1)
    (seat_id,) = query(games_db, "SELECT id FROM seats WHERE role = 'factory'")[0]
    for kind, reason, policy, user in (
        (None, "initial", None, None),
        ("rule_based", "moved", None, None),
        (None, "moved", "placeholder-0", None),
        (None, "moved", None, A),
    ):
        with pytest.raises(psycopg.errors.CheckViolation):
            execute(
                games_db,
                "INSERT INTO seat_occupancy (id, seat_id, from_week, occupant_kind, policy_id, "
                "reason, user_id) VALUES (%s, %s, 1, %s, %s, %s, %s)",
                (uuid.uuid7(), seat_id, kind, policy, reason, user),
            )
    assert version(games_db, game_id) == 1
