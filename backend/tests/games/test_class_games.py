"""Class games (Story 5.9, AD-2, AD-4, AD-5, AD-6, AD-13): created with no settings snapshot under
their Class session and game number, Seats held by `student` occupants with the Student's id, a
start refused until the snapshot exists, and LLM calls charged to the Class session's budget."""

import uuid

import pytest

from app.ai import budget
from app.engine import GameSettings
from app.modules.games import commands, service
from app.modules.games.schemas import SessionRuntime
from tests.games.helpers import counts, execute, listening, query
from tests.games.test_assign_seat import assert_refused, occupancy

SESSION = uuid.UUID("01900000-0000-7000-8000-000000000001")
IN_SESSION = {"class_session_id": SESSION, "game_number": 1}


async def class_game(number: int = 1, session: uuid.UUID = SESSION) -> str:
    return await commands.create("class", class_session_id=session, game_number=number)


async def test_a_class_game_has_four_free_seats_and_no_snapshot(games_db):
    with listening(games_db) as events:
        game_id = await class_game(3)
        received = events.drain()
    ((purpose, number, session, *snapshot),) = query(
        games_db,
        "SELECT purpose, game_number, class_session_id, settings, demand_series, demand_seed, "
        "rules_version, session_runtime FROM games WHERE id = %s",
        (game_id,),
    )
    assert (purpose, number, session) == ("class", 3, SESSION)
    assert snapshot == [None] * 5
    assert [r[0] for r in query(games_db, "SELECT role FROM seats ORDER BY position")] == [
        "retailer",
        "wholesaler",
        "distributor",
        "factory",
    ]
    assert counts(games_db) == (1, 4, 0)
    # Listed in the Lecturer overview: the Class session hears of it too (AD-8, AD-13).
    assert received == [
        {"topic": "game", "id": game_id, "version": 1},
        {"topic": "session", "id": str(SESSION), "version": None},
    ]
    game = await service.get_game(game_id)
    assert (game.settings, game.session_runtime, game.class_session_id, game.game_number) == (
        None,
        None,
        str(SESSION),
        3,
    )
    assert await service.budget_scope(game_id) is None


@pytest.mark.parametrize(
    ("kwargs", "code"),
    [
        ({"settings": GameSettings(), **IN_SESSION}, "settings_not_allowed"),
        ({"seed": 4, **IN_SESSION}, "settings_not_allowed"),
        ({"rule_based_params": "placeholder-0", **IN_SESSION}, "settings_not_allowed"),
        ({"batch_id": str(uuid.uuid7()), **IN_SESSION}, "settings_not_allowed"),
        ({"game_number": 1}, "class_session_required"),
        ({"class_session_id": SESSION}, "class_session_required"),
        ({"class_session_id": SESSION, "game_number": 0}, "class_session_required"),
    ],
)
async def test_a_class_game_takes_its_session_and_no_settings(games_db, kwargs, code):
    with pytest.raises(commands.CommandError) as caught:
        await commands.create("class", **kwargs)
    assert (caught.value.code, caught.value.status) == (code, 422)
    assert counts(games_db) == (0, 0, 0)


async def test_a_simulation_game_takes_settings_and_no_class_session(games_db):
    for kwargs, code in (
        ({}, "settings_required"),
        (
            {"settings": GameSettings(), "class_session_id": SESSION, "game_number": 1},
            "class_session_not_allowed",
        ),
    ):
        with pytest.raises(commands.CommandError) as caught:
            await commands.create("simulation", **kwargs)
        assert (caught.value.code, caught.value.status) == (code, 422)
    assert counts(games_db) == (0, 0, 0)


async def test_one_game_number_per_class_session(games_db):
    await class_game(1)
    await class_game(1, uuid.uuid7())
    with pytest.raises(Exception, match="uq_games_class_session_number"):
        await class_game(1)
    assert counts(games_db) == (2, 8, 0)


async def test_a_student_takes_a_seat_with_the_id_only(games_db):
    game_id = await class_game()
    student = uuid.uuid7()
    await commands.assign_seat(game_id, "wholesaler", "student", user_id=student)
    assert [row[:5] for row in occupancy(games_db)] == [
        ("wholesaler", 1, "student", None, "initial")
    ]
    assert query(games_db, "SELECT user_id FROM seat_occupancy") == [(student,)]
    seats = {seat.role: seat for seat in (await service.get_game(game_id)).seats}
    assert (seats["wholesaler"].occupant_kind, seats["wholesaler"].user_id) == (
        "student",
        str(student),
    )
    assert seats["retailer"].user_id is None


async def test_student_seats_are_refused_where_they_do_not_belong(games_db):
    game_id = await class_game()
    other = await class_game(2)
    student = uuid.uuid7()
    await commands.assign_seat(game_id, "retailer", "student", user_id=student)
    simulation = await commands.create("simulation", GameSettings(), seed=1)
    cases = [
        (game_id, "user_id_required", 422, commands.assign_seat(game_id, "factory", "student")),
        (
            game_id,
            "user_id_not_allowed",
            422,
            commands.assign_seat(game_id, "factory", "rule_based", user_id=student),
        ),
        (
            simulation,
            "occupant_kind_not_allowed",
            422,
            commands.assign_seat(simulation, "factory", "student", user_id=student),
        ),
        # One Seat per Student per Class session, in any of its Games.
        (
            other,
            "student_already_seated",
            409,
            commands.assign_seat(other, "factory", "student", user_id=student),
        ),
        (game_id, "game_not_ready", 409, commands.assign_seat(game_id, "factory", "llm")),
    ]
    for game, code, status, call in cases:
        await assert_refused(games_db, game, code, status, call)
    # Another Class session's Game takes the same Student.
    elsewhere = await class_game(1, uuid.uuid7())
    await commands.assign_seat(elsewhere, "factory", "student", user_id=student)


async def test_a_class_game_does_not_start_before_its_snapshot(games_db):
    game_id = await class_game()
    with listening(games_db) as events:
        with pytest.raises(commands.CommandError) as caught:
            await commands.start(game_id)
        assert events.drain() == []
    assert (caught.value.code, caught.value.status) == ("game_not_ready", 409)
    assert query(games_db, "SELECT lifecycle FROM games") == [("not_started",)]


def test_a_class_game_charges_its_class_session():
    runtime = SessionRuntime(
        ai_mode="llm",
        rule_based_params="placeholder-0",
        rule_based_params_version=1,
        model_config_id=str(uuid.uuid7()),
        effort_level="standard",
    )
    scope = service.scope_of("class", runtime, SESSION)
    assert scope == budget.BudgetScope.class_session(SESSION)
    assert scope.effort_level == "standard"
    assert service.scope_of("class", None, SESSION) is None
    assert (
        service.scope_of(
            "class",
            runtime.model_copy(update={"model_config_id": None, "effort_level": None}),
            SESSION,
        )
        is None
    )
    assert service.scope_of("simulation", runtime).kind == "evaluation"


async def test_a_running_class_game_is_charged_to_its_session(games_db):
    """The stored side of the rule: `budget_scope` and its inverse `games_charged_to`."""
    simulation = await commands.create("simulation", GameSettings(), seed=1)
    game_id = await class_game()
    runtime = {
        "ai_mode": "llm",
        "rule_based_params": "placeholder-0",
        "rule_based_params_version": 1,
        "model_config_id": str(uuid.uuid7()),
        "effort_level": "standard",
    }
    # The snapshot Story 5.12 will store, copied from the simulation Game.
    execute(
        games_db,
        "UPDATE games g SET settings = s.settings, demand_series = s.demand_series, "
        "demand_seed = s.demand_seed, rules_version = s.rules_version, "
        "session_runtime = %s::jsonb, lifecycle = 'running' FROM games s "
        "WHERE g.id = %s AND s.id = %s",
        (SessionRuntime(**runtime).model_dump_json(), game_id, simulation),
    )
    scope = await service.budget_scope(game_id)
    assert scope == budget.BudgetScope.class_session(SESSION)
    assert await service.games_charged_to(scope) == [game_id]
