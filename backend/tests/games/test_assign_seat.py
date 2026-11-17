import asyncio
import uuid
from types import MappingProxyType

import psycopg
import pytest

from app.engine import GameSettings, Role
from app.modules.games import commands, service
from app.modules.games import policy as policy_module
from app.modules.games.schemas import Purpose
from tests.conftest import libpq_dsn
from tests.games.helpers import execute, listening, query


async def new_game(**settings) -> str:
    return await commands.create("simulation", GameSettings(**settings), seed=1)


def occupancy(url: str) -> list[tuple]:
    return query(
        url,
        "SELECT s.role, o.from_week, o.occupant_kind, o.policy_id, o.reason, o.id "
        "FROM seat_occupancy o JOIN seats s ON s.id = o.seat_id ORDER BY s.position, o.id",
    )


def version(url: str, game_id: str) -> int:
    return query(url, "SELECT version FROM games WHERE id = %s", (game_id,))[0][0]


async def test_assign_appends_an_initial_row_and_bumps_the_version(games_db):
    game_id = await new_game()
    with listening(games_db) as events:
        row_id = await commands.assign_seat(game_id, Role.WHOLESALER, "rule_based")
        received = events.drain()
    assert uuid.UUID(row_id).version == 7
    assert [row[:5] for row in occupancy(games_db)] == [
        ("wholesaler", 1, "rule_based", None, "initial")
    ]
    assert str(occupancy(games_db)[0][5]) == row_id
    assert version(games_db, game_id) == 2
    assert received == [{"topic": "game", "id": game_id, "version": 2}]


async def test_scripted_occupant_stores_its_policy_id(games_db):
    game_id = await new_game()
    await commands.assign_seat(game_id, "factory", "scripted", "constant-4")
    assert [row[:5] for row in occupancy(games_db)] == [
        ("factory", 1, "scripted", "constant-4", "initial")
    ]


async def test_every_seat_filled_reads_back_through_the_service(games_db):
    game_id = await new_game()
    for role in ("retailer", "wholesaler", "distributor"):
        await commands.assign_seat(game_id, role, "rule_based")
    await commands.assign_seat(game_id, "factory", "scripted", "constant-4")
    game = await service.get_game(game_id)
    assert game is not None and game.version == 5
    assert [(s.role, s.occupant_kind, s.policy_id) for s in game.seats] == [
        ("retailer", "rule_based", None),
        ("wholesaler", "rule_based", None),
        ("distributor", "rule_based", None),
        ("factory", "scripted", "constant-4"),
    ]


async def assert_refused(url: str, game_id: str, code: str, status: int, call) -> None:
    before_rows = occupancy(url)
    before_version = version(url, game_id) if game_id else None
    with listening(url) as events:
        with pytest.raises(commands.CommandError) as caught:
            await call
        assert events.drain() == []
    assert (caught.value.code, caught.value.status) == (code, status)
    assert occupancy(url) == before_rows
    if game_id:
        assert version(url, game_id) == before_version


async def test_a_second_assign_answers_seat_occupied(games_db):
    game_id = await new_game()
    await commands.assign_seat(game_id, "retailer", "rule_based")
    await assert_refused(
        games_db,
        game_id,
        "seat_occupied",
        409,
        commands.assign_seat(game_id, "retailer", "scripted", "constant-4"),
    )


@pytest.mark.parametrize("kind", ["llm", "student", "robot"])
async def test_other_occupant_kinds_are_refused(games_db, kind):
    game_id = await new_game()
    await assert_refused(
        games_db,
        game_id,
        "occupant_kind_not_allowed",
        422,
        commands.assign_seat(game_id, "retailer", kind),
    )


@pytest.mark.parametrize(
    ("kind", "policy_id", "code"),
    [
        ("scripted", None, "policy_id_required"),
        ("scripted", "constant-5", "unknown_policy"),
        ("rule_based", "constant-4", "policy_id_not_allowed"),
    ],
)
async def test_policy_id_rules(games_db, kind, policy_id, code):
    game_id = await new_game()
    await assert_refused(
        games_db, game_id, code, 422, commands.assign_seat(game_id, "retailer", kind, policy_id)
    )


async def test_scripted_is_refused_where_the_purpose_policy_says_so(games_db, monkeypatch):
    no_scripts = policy_module.POLICIES[Purpose.SIMULATION].model_copy(
        update={"scripted_occupants": False}
    )
    monkeypatch.setattr(
        policy_module,
        "POLICIES",
        MappingProxyType({**policy_module.POLICIES, Purpose.LECTURER_TEST: no_scripts}),
    )
    game_id = await commands.create("lecturer_test", GameSettings(), seed=1)
    await assert_refused(
        games_db,
        game_id,
        "occupant_kind_not_allowed",
        422,
        commands.assign_seat(game_id, "retailer", "scripted", "constant-4"),
    )
    await commands.assign_seat(game_id, "retailer", "rule_based")
    assert [row[2] for row in occupancy(games_db)] == ["rule_based"]


@pytest.mark.parametrize("role", ["wholesaler", "chef"])
async def test_a_role_without_a_seat_is_refused(games_db, role):
    game_id = await new_game(roles=(Role.RETAILER, Role.FACTORY))
    await assert_refused(
        games_db, game_id, "unknown_role", 422, commands.assign_seat(game_id, role, "rule_based")
    )


@pytest.mark.parametrize("game_id", ["not-a-uuid", str(uuid.uuid7())])
async def test_an_unknown_game_is_refused(games_db, game_id):
    await assert_refused(
        games_db, "", "game_not_found", 404, commands.assign_seat(game_id, "retailer", "rule_based")
    )


async def test_a_started_game_is_refused(games_db):
    game_id = await new_game()
    execute(games_db, "UPDATE games SET lifecycle = 'running' WHERE id = %s", (game_id,))
    await assert_refused(
        games_db,
        game_id,
        "game_already_started",
        409,
        commands.assign_seat(game_id, "retailer", "rule_based"),
    )


async def test_occupancy_rows_cannot_be_updated_or_deleted(games_db):
    game_id = await new_game()
    await commands.assign_seat(game_id, "retailer", "rule_based")
    for statement in (
        "UPDATE seat_occupancy SET occupant_kind = 'scripted'",
        "DELETE FROM seat_occupancy",
    ):
        with pytest.raises(psycopg.errors.RestrictViolation, match="append-only"):
            execute(games_db, statement)
    assert [row[2] for row in occupancy(games_db)] == ["rule_based"]


async def test_assign_waits_for_the_game_row_lock(games_db):
    game_id = await new_game()
    with psycopg.connect(libpq_dsn(games_db)) as holder:
        holder.execute("SELECT 1 FROM games WHERE id = %s FOR UPDATE", (game_id,))
        task = asyncio.create_task(commands.assign_seat(game_id, "retailer", "rule_based"))
        await asyncio.sleep(0.5)
        assert not task.done()
        assert occupancy(games_db) == []
        holder.rollback()
        await asyncio.wait_for(task, timeout=5)
    assert len(occupancy(games_db)) == 1


async def test_two_assigns_racing_for_one_seat_give_one_row(games_db):
    game_id = await new_game()
    results = await asyncio.gather(
        commands.assign_seat(game_id, "retailer", "rule_based"),
        commands.assign_seat(game_id, "retailer", "scripted", "constant-4"),
        return_exceptions=True,
    )
    errors = [r for r in results if isinstance(r, commands.CommandError)]
    assert len(errors) == 1 and errors[0].code == "seat_occupied"
    assert len(occupancy(games_db)) == 1
    assert version(games_db, game_id) == 2


async def test_the_service_reports_the_latest_occupancy_row(games_db):
    game_id = await new_game()
    await commands.assign_seat(game_id, "retailer", "rule_based")
    ((seat_id,),) = query(games_db, "SELECT id FROM seats WHERE role = 'retailer'")
    execute(
        games_db,
        "INSERT INTO seat_occupancy (id, seat_id, from_week, occupant_kind, policy_id, reason) "
        "VALUES (%s, %s, 3, 'scripted', 'constant-4', 'takeover_staff')",
        (uuid.uuid7(), seat_id),
    )
    game = await service.get_game(game_id)
    assert game is not None
    assert (game.seats[0].occupant_kind, game.seats[0].policy_id) == ("scripted", "constant-4")


async def test_a_game_id_that_is_not_text_is_not_found(games_db):
    with pytest.raises(commands.CommandError) as caught:
        await commands.assign_seat(5, "retailer", "rule_based")  # type: ignore[arg-type]
    assert caught.value.code == "game_not_found"
    assert await service.get_game(None) is None  # type: ignore[arg-type]
    assert await service.get_game(5) is None  # type: ignore[arg-type]
