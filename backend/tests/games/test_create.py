import uuid
from decimal import Decimal

import pytest

from app.engine import (
    RULES_VERSION,
    DemandRandom,
    GameSettings,
    Role,
    SettingsError,
    demand_series,
)
from app.modules.games import commands, service
from app.platform.config import get_settings
from tests.games.helpers import counts, listening, play_to_end, query


async def test_create_stores_a_not_started_game_with_four_free_seats(games_db):
    with listening(games_db) as events:
        game_id = await commands.create("simulation", GameSettings(), seed=123)
        received = events.drain()
    assert uuid.UUID(game_id).version == 7
    ((lifecycle, purpose, version),) = query(
        games_db, "SELECT lifecycle, purpose, version FROM games WHERE id = %s", (game_id,)
    )
    assert (lifecycle, purpose, version) == ("not_started", "simulation", 1)
    seats = query(games_db, "SELECT id, role, position FROM seats ORDER BY position")
    assert [(role, position) for _, role, position in seats] == [
        ("retailer", 0),
        ("wholesaler", 1),
        ("distributor", 2),
        ("factory", 3),
    ]
    assert all(seat_id.version == 7 for seat_id, _, _ in seats)
    assert counts(games_db) == (1, 4, 0)  # create fills no Seat
    assert received == [{"topic": "game", "id": game_id, "version": 1}]


async def test_create_freezes_the_snapshot(games_db):
    game_id = await commands.create("simulation", GameSettings(), seed=123)
    ((settings, series, seed, rules_version, runtime),) = query(
        games_db,
        "SELECT settings, demand_series, demand_seed, rules_version, session_runtime "
        "FROM games WHERE id = %s",
        (game_id,),
    )
    expected = GameSettings(demand_seed=123)
    assert settings == expected.model_dump(mode="json")
    assert settings["schema_version"] == 2
    assert settings["holding_cost"] == "0.50"
    assert GameSettings.model_validate(settings) == expected
    assert series == list(demand_series(expected))
    assert len(series) == 36 and series[:5] == [4, 4, 4, 4, 8]
    assert seed == 123
    assert rules_version == RULES_VERSION
    assert runtime == {
        "schema_version": 1,
        "ai_mode": "rule_based",
        "rule_based_params": "placeholder-unverified",
        "rule_based_params_version": 1,
        "model_config_id": None,
        "effort_level": None,
        "play_guard_params": "placeholder-1",
        "play_guard_params_version": 1,
        # Frozen by a Class session's lock only (Story 5.11).
        "inactivity_limit_hours": None,
        "prompt_versions": None,
        "pins": None,
    }


def two_levels() -> list[dict]:
    level = {"provider_params": {}, "attempt_timeout_s": 4, "order_time_budget_s": 8}
    return [{"name": "standard", **level}, {"name": "deep", **level}]


async def test_create_freezes_a_model_config_and_its_effort_level(games_db, ai_db):
    """Story 2.5 (AD-4, AD-22, FR-78): the config id and one of its Effort levels go into the
    `SessionRuntime`, the config is marked referenced, and `budget_scope` answers its
    evaluation budget with that level."""
    from app.ai import budget, config
    from tests.ai.helpers import stored_config

    config_id = await stored_config(effort_levels=two_levels())
    game_id = await commands.create(
        "simulation", GameSettings(), seed=1, model_config_id=config_id, effort_level="deep"
    )
    ((runtime,),) = query(games_db, "SELECT session_runtime FROM games WHERE id = %s", (game_id,))
    assert (runtime["ai_mode"], runtime["model_config_id"], runtime["effort_level"]) == (
        "llm",
        config_id,
        "deep",
    )
    assert (await config.get(config_id)).referenced
    scope = await service.budget_scope(game_id)
    assert scope == budget.BudgetScope.evaluation(config_id)
    assert scope.effort_level == "deep"
    default = await commands.create("simulation", GameSettings(), seed=1, model_config_id=config_id)
    assert (await service.budget_scope(default)).effort_level == "standard"
    plain = await commands.create("simulation", GameSettings(), seed=1)
    assert await service.budget_scope(plain) is None


@pytest.mark.parametrize(
    ("config", "level", "code"),
    [
        ("stored", "turbo", "effort_level_unknown"),
        ("019a0000-0000-7000-8000-000000000000", None, "config_not_found"),
        ("not-an-id", None, "config_not_found"),
        (None, "standard", "model_config_required"),
    ],
)
async def test_create_refuses_an_unknown_config_or_effort_level(
    games_db, ai_db, config, level, code
):
    from tests.ai.helpers import stored_config

    config_id = await stored_config() if config == "stored" else config
    with pytest.raises(commands.CommandError) as refused:
        await commands.create(
            "simulation", GameSettings(), seed=1, model_config_id=config_id, effort_level=level
        )
    assert (refused.value.code, refused.value.status) == (code, 422)
    assert counts(games_db) == (0, 0, 0)


async def test_demand_pattern_and_seed_replace_the_settings_ones(games_db):
    pattern = DemandRandom(kind="random", mean=6, spread=3)
    game_id = await commands.create(
        "simulation", GameSettings(demand_seed=5), demand_pattern=pattern, seed=77
    )
    ((settings, series, seed),) = query(
        games_db, "SELECT settings, demand_series, demand_seed FROM games WHERE id = %s", (game_id,)
    )
    expected = GameSettings(demand=pattern, demand_seed=77)
    assert seed == 77 and settings["demand_seed"] == 77
    assert settings["demand"] == pattern.model_dump(mode="json")
    assert series == list(demand_series(expected))


async def test_the_settings_seed_is_used_when_no_seed_is_given(games_db):
    game_id = await commands.create("simulation", GameSettings(demand_seed=99))
    assert query(games_db, "SELECT demand_seed FROM games WHERE id = %s", (game_id,)) == [(99,)]


async def test_a_seed_is_drawn_when_none_is_given(games_db):
    pattern = DemandRandom(kind="random", mean=4, spread=2)
    first = await commands.create("simulation", GameSettings(), demand_pattern=pattern)
    second = await commands.create("simulation", GameSettings(), demand_pattern=pattern)
    rows = query(games_db, "SELECT id::text, settings, demand_seed, demand_series FROM games")
    by_id = {row[0]: row[1:] for row in rows}
    for game_id in (first, second):
        settings, seed, series = by_id[game_id]
        assert settings["demand_seed"] == seed
        assert 0 <= seed <= 999_999_999
        assert series == list(demand_series(GameSettings(demand=pattern, demand_seed=seed)))
    assert by_id[first][1] != by_id[second][1]


async def test_a_game_of_fewer_roles_gets_one_seat_per_role(games_db):
    roles = (Role.RETAILER, Role.FACTORY)
    await commands.create("simulation", GameSettings(roles=roles), seed=1)
    assert query(games_db, "SELECT role FROM seats ORDER BY position") == [
        ("retailer",),
        ("factory",),
    ]


@pytest.mark.parametrize(
    ("settings", "fields"),
    [
        (
            GameSettings(guided_weeks=5),
            {"guided_weeks": "guided_weeks_not_before_demand_change"},
        ),
        (
            GameSettings(weeks=101, holding_cost=Decimal("0.505")),
            {"holding_cost": "too_many_decimal_places", "weeks": "out_of_range"},
        ),
    ],
)
async def test_invalid_settings_store_nothing_and_return_the_engine_codes(
    games_db, settings, fields
):
    with listening(games_db) as events:
        with pytest.raises(commands.CommandError) as caught:
            await commands.create("simulation", settings, seed=1)
        assert events.drain() == []
    error = caught.value
    assert (error.code, error.status) == ("invalid_settings", 422)
    assert error.fields == fields
    assert all(isinstance(e, SettingsError) for e in error.errors)
    assert {e.field: e.code for e in error.errors} == fields
    assert counts(games_db) == (0, 0, 0)


async def test_an_out_of_range_seed_is_an_engine_error(games_db):
    with pytest.raises(commands.CommandError) as caught:
        await commands.create("simulation", GameSettings(), seed=-1)
    assert caught.value.fields == {"demand_seed": "out_of_range"}
    assert counts(games_db) == (0, 0, 0)


async def test_a_seed_that_is_not_a_whole_number_is_invalid(games_db):
    with pytest.raises(commands.CommandError) as caught:
        await commands.create("simulation", GameSettings(), seed="12")  # type: ignore[arg-type]
    assert (caught.value.code, caught.value.fields) == (
        "invalid_settings",
        {"demand_seed": "invalid"},
    )
    assert counts(games_db) == (0, 0, 0)


async def test_an_unknown_parameter_set_stores_nothing(games_db):
    with pytest.raises(commands.CommandError) as caught:
        await commands.create("simulation", GameSettings(), seed=1, rule_based_params="nope")
    assert (caught.value.code, caught.value.status) == ("unknown_parameter_set", 422)
    assert counts(games_db) == (0, 0, 0)


async def test_an_invalid_parameter_set_stores_nothing(games_db, monkeypatch):
    monkeypatch.setattr(commands, "read_parameter_set", lambda kind, set_id: '{"id": "x"}')
    with pytest.raises(commands.CommandError) as caught:
        await commands.create("simulation", GameSettings(), seed=1)
    assert (caught.value.code, caught.value.status) == ("invalid_parameter_set", 422)
    assert counts(games_db) == (0, 0, 0)


@pytest.mark.parametrize("purpose", ["replay", "makeup", "party"])
async def test_purposes_without_a_policy_cannot_be_created_yet(games_db, purpose):
    with pytest.raises(commands.CommandError) as caught:
        await commands.create(purpose, GameSettings(), seed=1)
    assert (caught.value.code, caught.value.status) == ("purpose_not_supported", 422)
    assert counts(games_db) == (0, 0, 0)


async def test_service_reads_the_game_back(games_db):
    game_id = await commands.create("simulation", GameSettings(), seed=8)
    game = await service.get_game(game_id)
    assert game is not None
    assert (game.id, game.lifecycle, game.version, game.demand_seed) == (
        game_id,
        "not_started",
        1,
        8,
    )
    assert [seat.role for seat in game.seats] == [
        "retailer",
        "wholesaler",
        "distributor",
        "factory",
    ]
    assert all(seat.occupant_kind is None for seat in game.seats)
    assert game.session_runtime.rule_based_params == "placeholder-unverified"


@pytest.mark.parametrize("game_id", ["not-a-uuid", "01a1eb10-f299-75a6-8ec2-a251c50791e1"])
async def test_service_answers_none_for_an_unknown_game(games_db, game_id):
    assert await service.get_game(game_id) is None


async def test_capacity_is_refused_when_feature_capacity_is_off(games_db, monkeypatch):
    monkeypatch.setenv("FEATURE_CAPACITY", "false")
    with listening(games_db) as events:
        with pytest.raises(commands.CommandError) as caught:
            await commands.create("simulation", GameSettings(capacity={"retailer": 6}), seed=1)
        assert events.drain() == []
    error = caught.value
    assert (error.code, error.status) == ("invalid_settings", 422)
    assert error.fields == {"capacity": "capacity_disabled"}
    assert counts(games_db) == (0, 0, 0)


async def test_feature_capacity_off_leaves_games_without_capacity_unchanged(games_db, monkeypatch):
    monkeypatch.setenv("FEATURE_CAPACITY", "false")
    game_id = await commands.create("simulation", GameSettings(), seed=123)
    ((settings,),) = query(games_db, "SELECT settings FROM games WHERE id = %s", (game_id,))
    assert "capacity" not in settings
    assert settings == GameSettings(demand_seed=123).model_dump(mode="json")


async def test_capacity_out_of_range_is_an_engine_error(games_db, monkeypatch):
    monkeypatch.setenv("FEATURE_CAPACITY", "true")
    with pytest.raises(commands.CommandError) as caught:
        await commands.create("simulation", GameSettings(capacity={"factory": 0}), seed=1)
    assert caught.value.fields == {"capacity.factory": "out_of_range"}
    (error,) = caught.value.errors
    assert (error.minimum, error.maximum) == (1, 100)
    assert counts(games_db) == (0, 0, 0)


async def test_a_capped_game_is_stored_played_and_verified(games_db, monkeypatch):
    monkeypatch.setenv("FEATURE_CAPACITY", "true")
    settings = GameSettings(capacity={"wholesaler": 6}, weeks=12)  # past the step to 8 a Week
    game_id = await commands.create("simulation", settings, seed=3)
    ((settings,),) = query(games_db, "SELECT settings FROM games WHERE id = %s", (game_id,))
    assert settings["capacity"] == {"wholesaler": 6}
    await commands.start(game_id)
    await play_to_end(game_id)
    shipped = query(
        games_db,
        "SELECT (w.state_seen->>'shipped')::int FROM seat_weeks w JOIN seats s "
        "ON s.id = w.seat_id WHERE w.game_id = %s AND s.role = 'wholesaler'",
        (game_id,),
    )
    assert len(shipped) == 12 and max(value for (value,) in shipped) <= 6
    check = await service.verify_finished(game_id)
    assert check.ok, check.violations


async def test_a_capacity_that_is_not_a_whole_number_is_invalid(games_db):
    unchecked = GameSettings.model_construct(capacity={Role.RETAILER: 6.5})
    with pytest.raises(commands.CommandError) as caught:
        await commands.create("simulation", unchecked, seed=1)
    assert (caught.value.code, caught.value.status) == ("invalid_settings", 422)
    assert caught.value.fields == {"capacity.retailer": "invalid"}
    assert counts(games_db) == (0, 0, 0)


async def test_information_visibility_is_refused_when_its_flag_is_off(games_db, monkeypatch):
    # Story 5.16: the engine gate fails closed, so a simulation Game obeys the flag as well.
    monkeypatch.setenv("FEATURE_INFO_VISIBILITY", "false")
    views = GameSettings(info_visibility={"upstream": True})
    with pytest.raises(commands.CommandError) as caught:
        await commands.create("simulation", views, seed=1)
    assert (caught.value.code, caught.value.fields) == (
        "invalid_settings",
        {"info_visibility": "info_visibility_disabled"},
    )
    assert counts(games_db) == (0, 0, 0)
    monkeypatch.setenv("FEATURE_INFO_VISIBILITY", "true")
    get_settings.cache_clear()
    game_id = await commands.create("simulation", views, seed=1)
    ((settings,),) = query(games_db, "SELECT settings FROM games WHERE id = %s", (game_id,))
    assert settings["info_visibility"] == {"upstream": True, "downstream": False}


def _ready_snapshot(seed: int = 5) -> dict:
    """A snapshot as `sessions.build_snapshot` makes it (Story 6.20)."""
    settings = GameSettings(demand_seed=seed)
    return {
        "settings": settings.model_dump(mode="json"),
        "demand_series": list(demand_series(settings)),
        "demand_seed": seed,
        "rules_version": RULES_VERSION,
        "session_runtime": commands.default_runtime(
            model_config_id=None, effort_level=None
        ).model_dump(mode="json"),
    }


async def test_a_test_game_stores_a_ready_snapshot_with_its_class_session_and_no_number(games_db):
    session_id = uuid.uuid7()
    snapshot = _ready_snapshot()
    game_id = await commands.create("lecturer_test", snapshot=snapshot, class_session_id=session_id)
    ((stored, number, settings, seed),) = query(
        games_db,
        "SELECT class_session_id, game_number, settings, demand_seed FROM games WHERE id = %s",
        (game_id,),
    )
    assert (stored, number, settings, seed) == (session_id, None, snapshot["settings"], 5)


@pytest.mark.parametrize(
    ("kwargs", "code"),
    [
        ({"game_number": 1}, "game_number_not_allowed"),
        ({"seed": 3}, "settings_not_allowed"),
        ({"class_session_id": None}, "class_session_required"),
    ],
)
async def test_a_test_game_refuses_a_number_a_second_snapshot_or_no_session(games_db, kwargs, code):
    given = {"snapshot": _ready_snapshot(), "class_session_id": uuid.uuid7(), **kwargs}
    with pytest.raises(commands.CommandError) as caught:
        await commands.create("lecturer_test", **given)
    assert (caught.value.code, caught.value.status) == (code, 422)
    assert counts(games_db) == (0, 0, 0)
