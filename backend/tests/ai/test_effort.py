"""Story 2.12: approve measured Effort levels, offer only those, pin the default model config,
and seed the zero-config default (FR-68, FR-78, FR-79, AD-6, AD-17, C-3)."""

import dataclasses
import json
import uuid
from decimal import Decimal

import psycopg
import pytest

from app.ai import config, seed
from app.platform.config import get_settings
from tests.ai.helpers import CONFIGS, MOCK, query, stored_config
from tests.conftest import reset_caches
from tests.games.helpers import execute

LINES = {"cost_per_game_usd": "0.10", "time_per_order_p95_s": "8", "switched_share": "0.25"}
MEASURED = {"cost_per_game_usd": "0.04", "time_per_order_p95_s": "2.5", "switched_share": "0"}


def verdicts(**changes: tuple[str | None, str | None, str]) -> tuple[config.PassVerdict, ...]:
    found = []
    for name in config.PASS_LINE_NAMES:
        line, measured, verdict = changes.get(name, (LINES[name], MEASURED[name], "pass"))
        found.append(
            config.PassVerdict(
                name,
                None if line is None else Decimal(line),
                None if measured is None else Decimal(measured),
                verdict,
            )
        )
    return tuple(found)


def figures(config_id: str, **changes: object) -> config.EffortFigures:
    """The figures of a real batch of 2 Games of `standard` that passed every line."""
    base = config.EffortFigures(
        model_config_id=config_id,
        effort_levels=("standard",),
        mock=False,
        games=2,
        cost_per_game_usd=Decimal("0.04"),
        time_per_order_median_s=Decimal("1.2"),
        time_per_order_p95_s=Decimal("2.5"),
        retries_per_order_mean=Decimal("0.25"),
        fallback_share=Decimal("0.0625"),
        switched_share=Decimal(0),
        pass_lines=verdicts(),
    )
    return dataclasses.replace(base, **changes)


def set_env(monkeypatch, app_env: str) -> None:
    monkeypatch.setenv("APP_ENV", app_env)
    get_settings.cache_clear()


def real_spec(**changes: object) -> config.ModelConfigSpec:
    data = json.loads((CONFIGS / "openrouter-deepseek.json").read_text(encoding="utf-8"))
    data.update(changes)
    return config.parse(data)


async def test_approval_stores_the_measurement_and_offers_the_level(ai_db):
    config_id = await stored_config()
    before = await config.get(config_id)
    batch = uuid.uuid4()
    row = await config.approve_effort(config_id, "standard", batch, figures(config_id))
    assert (row.batch_id, row.mock, row.games) == (batch, False, 2)
    assert (row.cost_per_game_usd, row.time_per_order_p95_s) == (Decimal("0.04"), Decimal("2.5"))
    assert (row.time_per_order_median_s, row.retries_per_order_mean) == (
        Decimal("1.2"),
        Decimal("0.25"),
    )
    assert (row.fallback_share, row.switched_share) == (Decimal("0.0625"), Decimal(0))
    assert row.pass_lines["cost_per_game_usd"] == {
        "line": "0.10",
        "measured": "0.04",
        "verdict": "pass",
    }
    # The model config row itself is not changed (not even marked referenced).
    assert await config.get(config_id) == before
    offered = await config.offered_effort_levels(config_id)
    assert [(level.name, level.default, level.measurement.id) for level in offered] == [
        ("standard", True, row.id)
    ]
    # The evidence never changes.
    with pytest.raises(psycopg.errors.RestrictViolation):
        execute(ai_db, "UPDATE effort_measurements SET games = 3")
    with pytest.raises(psycopg.errors.RestrictViolation):
        execute(ai_db, "DELETE FROM effort_measurements")


REFUSALS = [
    ("config_mismatch", {"model_config_id": str(uuid.uuid4())}, "standard"),
    ("effort_level_unknown", {}, "turbo"),
    ("mock_batch", {"mock": True}, "standard"),
    ("effort_level_mismatch", {"effort_levels": ("fast",)}, "standard"),
    ("effort_level_mismatch", {"effort_levels": ("fast", "standard")}, "standard"),
    ("effort_level_mismatch", {"effort_levels": ()}, "standard"),
    (
        "pass_line_missing",
        {"pass_lines": verdicts(switched_share=(None, "0", "no line"))},
        "standard",
    ),
    (
        "pass_line_missing",
        {"pass_lines": verdicts()[:2]},
        "standard",
    ),
    (
        "pass_line_missed",
        {"pass_lines": verdicts(cost_per_game_usd=("0.10", "0.12", "miss"))},
        "standard",
    ),
    (
        "pass_line_missed",
        {"pass_lines": verdicts(time_per_order_p95_s=("8", "2.5", "miss (cut short)"))},
        "standard",
    ),
    (
        "pass_line_missed",
        {"pass_lines": verdicts(switched_share=("0.25", None, "n/a"))},
        "standard",
    ),
    (
        "pass_line_missed",  # a verdict that disagrees with its numbers is not trusted
        {"pass_lines": verdicts(cost_per_game_usd=("0.10", "0.11", "pass"))},
        "standard",
    ),
]


@pytest.mark.parametrize(("code", "changes", "level"), REFUSALS)
async def test_an_approval_is_refused_and_stores_nothing(ai_db, code, changes, level):
    config_id = await stored_config(
        effort_levels=[
            {"name": "standard", "attempt_timeout_s": 4, "order_time_budget_s": 8},
            {"name": "fast", "attempt_timeout_s": 2, "order_time_budget_s": 4},
        ]
    )
    with pytest.raises(config.ConfigRefused) as info:
        await config.approve_effort(config_id, level, uuid.uuid4(), figures(config_id, **changes))
    assert info.value.code == code
    assert query(ai_db, "SELECT count(*) FROM effort_measurements") == [(0,)]


async def test_a_batch_is_approved_once_and_unknown_configs_are_refused(ai_db):
    config_id = await stored_config()
    batch = uuid.uuid4()
    await config.approve_effort(config_id, "standard", batch, figures(config_id))
    with pytest.raises(config.ConfigRefused) as info:
        await config.approve_effort(config_id, "standard", batch, figures(config_id))
    assert info.value.code == "already_approved"
    missing = str(uuid.uuid4())
    with pytest.raises(config.ConfigNotFound):
        await config.approve_effort(missing, "standard", uuid.uuid4(), figures(missing))
    assert query(ai_db, "SELECT count(*) FROM effort_measurements") == [(1,)]


async def test_only_measured_levels_are_offered_in_config_order(ai_db):
    config_id = await stored_config(
        effort_levels=[
            {"name": "deep", "attempt_timeout_s": 6, "order_time_budget_s": 8},
            {"name": "standard", "attempt_timeout_s": 4, "order_time_budget_s": 8},
            {"name": "fast", "attempt_timeout_s": 2, "order_time_budget_s": 4},
        ]
    )
    assert await config.offered_effort_levels(config_id) == []
    for level in ("fast", "standard"):
        await config.approve_effort(
            config_id, level, uuid.uuid4(), figures(config_id, effort_levels=(level,))
        )
    newer = await config.approve_effort(
        config_id, "fast", uuid.uuid4(), figures(config_id, effort_levels=("fast",))
    )
    offered = await config.offered_effort_levels(config_id)
    assert [(level.name, level.default) for level in offered] == [
        ("standard", True),
        ("fast", False),
    ]
    assert offered[1].measurement.id == newer.id  # the newest measurement of the level
    with pytest.raises(config.ConfigNotFound):
        await config.offered_effort_levels(str(uuid.uuid4()))


async def test_a_mock_only_database_offers_nothing_in_production(ai_db, monkeypatch):
    """Mock measurements count in local/test/ci only. In production the mock config's calls are
    refused, a real config with only a mock measurement offers nothing, and a real config offers
    only its levels with a real measurement whose endpoint can be reached (its key is set)."""
    mock_id = await seed.ensure_zero_config()
    real = await config.add(real_spec())
    await config.add_mock_measurement(real.id, "standard")
    assert [level.name for level in await config.offered_effort_levels(mock_id)] == ["standard"]
    # Here the mock answers the real config (no key), so its mock measurement counts too.
    assert [level.name for level in await config.offered_effort_levels(real.id)] == ["standard"]

    set_env(monkeypatch, "production")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert await config.offered_effort_levels(mock_id) == []
    assert await config.offered_effort_levels(real.id) == []
    monkeypatch.setenv("OPENROUTER_API_KEY", "placeholder-not-a-key")  # never called
    assert await config.offered_effort_levels(real.id) == []
    measured = await config.approve_effort(real.id, "standard", uuid.uuid4(), figures(str(real.id)))
    offered = await config.offered_effort_levels(real.id)
    assert [(level.name, level.measurement.id) for level in offered] == [("standard", measured.id)]
    monkeypatch.delenv("OPENROUTER_API_KEY")
    assert await config.offered_effort_levels(real.id) == []  # the endpoint is refused here


async def test_in_production_nothing_is_seeded_no_mock_is_approved_and_mock_is_never_pinned(
    ai_db, monkeypatch
):
    """AD-17, the AC's proof: with `APP_ENV=production` the seed stores nothing, a mock
    measurement can never be approved, and the mock config can never be pinned."""
    mock_id = await stored_config()
    await config.add_mock_measurement(uuid.UUID(mock_id), "standard")
    set_env(monkeypatch, "production")
    assert await seed.ensure_zero_config() is None
    assert query(ai_db, "SELECT count(*) FROM ai_model_configs") == [(1,)]
    assert query(ai_db, "SELECT count(*) FROM ai_default_pins") == [(0,)]
    with pytest.raises(config.ConfigRefused) as info:
        await config.approve_effort(mock_id, "standard", uuid.uuid4(), figures(mock_id, mock=True))
    assert info.value.code == "mock_batch"
    with pytest.raises(config.ConfigRefused) as info:
        await config.pin(mock_id)
    assert info.value.code == "mock_config"
    assert await config.active_default() is None
    # An empty production database stays empty.
    from tests.conftest import AI_TABLES

    execute(ai_db, f"TRUNCATE {AI_TABLES}")
    assert await seed.ensure_zero_config() is None
    assert query(ai_db, "SELECT count(*) FROM ai_model_configs") == [(0,)]


async def test_pin_needs_an_offered_level_and_makes_the_config_the_default(ai_db):
    first = await stored_config()
    with pytest.raises(config.ConfigRefused) as info:
        await config.pin(first)
    assert info.value.code == "no_offered_level"
    with pytest.raises(config.ConfigNotFound):
        await config.pin(str(uuid.uuid4()))
    assert await config.active_default() is None

    measured = await config.approve_effort(first, "standard", uuid.uuid4(), figures(first))
    pinned = await config.pin(first)
    assert str(pinned.config.id) == first and pinned.config.referenced
    assert [level.name for level in pinned.offered] == ["standard"]
    assert [row.id for row in pinned.evidence] == [measured.id]
    assert str((await config.active_default()).id) == first

    second = await stored_config(name="second")
    await config.approve_effort(second, "standard", uuid.uuid4(), figures(second))
    await config.pin(second)
    assert str((await config.active_default()).id) == second
    # The first config is frozen: a scope holding its id keeps it for good.
    with pytest.raises(psycopg.errors.RestrictViolation):
        execute(ai_db, "UPDATE ai_model_configs SET name = 'x' WHERE id = %s", (first,))


async def test_the_zero_config_seed_stores_a_pinned_mock_config_once(ai_db):
    config_id = await seed.ensure_zero_config()
    assert config_id is not None
    found = await config.get(config_id)
    assert found.spec == config.parse(MOCK)  # the seed is `ai-configs/mock.json`
    assert found.spec == config.parse(seed.MOCK_SPEC)
    assert str((await config.active_default()).id) == config_id
    (offered,) = await config.offered_effort_levels(config_id)
    assert (offered.name, offered.default, offered.measurement.mock) == ("standard", True, True)
    assert offered.measurement.batch_id is None and offered.measurement.games is None
    assert query(ai_db, "SELECT scope_kind, scope_id::text, limit_usd FROM ai_budgets") == [
        ("evaluation", config_id, Decimal("10.00000000"))
    ]
    # A second start, or a database that already holds a config, seeds nothing.
    assert await seed.ensure_zero_config() is None
    assert query(ai_db, "SELECT count(*) FROM ai_model_configs") == [(1,)]


async def test_no_seed_when_a_config_is_stored(ai_db):
    await stored_config(name="mine")
    assert await seed.ensure_zero_config() is None
    assert await config.active_default() is None


async def test_a_seed_that_cannot_reach_the_database_is_logged_not_raised(
    monkeypatch, unreachable_database
):
    monkeypatch.setenv("DATABASE_URL", unreachable_database)
    reset_caches()
    await seed.ensure_zero_config_logged()  # no exception


async def test_the_api_seeds_the_zero_config_default_at_start(monkeypatch):
    from app import main

    called = []

    async def seeded():
        called.append(True)

    monkeypatch.setattr(seed, "ensure_zero_config_logged", seeded)
    async with main.lifespan(main.app):
        assert called == [True]


@pytest.mark.parametrize(
    ("argv", "seeds"),
    [(["report", "x"], True), (["trace"], False), (["demand", "--seed", "1"], False)],
)
def test_the_simulation_runner_seeds_only_before_database_commands(
    monkeypatch, capsys, argv, seeds
):
    from app import sim

    called = []

    async def seeded():
        called.append(True)

    async def report(batch_id):
        return 0

    monkeypatch.setattr(seed, "ensure_zero_config_logged", seeded)
    monkeypatch.setattr(sim, "_report_batch", report)
    assert sim.main(argv, zero_config=True) == 0
    assert called == ([True] if seeds else [])
    called.clear()
    sim.main(argv)  # tests calling `main` never seed
    assert called == []


async def test_the_default_skips_a_pin_that_offers_nothing_here(ai_db, monkeypatch):
    """A database seeded locally and then run in production keeps no usable default."""
    mock_id = await seed.ensure_zero_config()
    assert str((await config.active_default()).id) == mock_id
    set_env(monkeypatch, "production")
    assert await config.active_default() is None


async def test_concurrent_starts_seed_once(ai_db):
    import asyncio

    results = await asyncio.gather(*(seed.ensure_zero_config() for _ in range(3)))
    assert sum(result is not None for result in results) == 1
    assert query(ai_db, "SELECT count(*) FROM ai_model_configs") == [(1,)]
    assert query(ai_db, "SELECT count(*) FROM ai_default_pins") == [(1,)]


def test_mock_measurements_count_exactly_where_the_mock_may_answer():
    from app.ai import adapters

    assert config.MOCK_ENVS == adapters.MOCK_ENVS


async def test_a_malformed_batch_id_is_refused(ai_db):
    config_id = await stored_config()
    with pytest.raises(config.ConfigRefused) as info:
        await config.approve_effort(config_id, "standard", "x", figures(config_id))
    assert info.value.code == "batch_id_invalid"


@pytest.mark.parametrize(
    ("columns", "values"),
    [
        ("mock, batch_id", "false, NULL"),  # a real measurement always has a batch
        ("mock, batch_id", "true, gen_random_uuid()"),  # a mock one never has
        ("mock, batch_id, games", "false, gen_random_uuid(), 1"),  # a real one has every figure
    ],
)
def test_the_table_refuses_a_measurement_without_its_source_or_figures(ai_db, columns, values):
    execute(
        ai_db,
        "INSERT INTO ai_model_configs (id, name, provider, endpoint, region, model_version, "
        "quantisation, input_usd_per_mtok, output_usd_per_mtok, rate_limit_rpm, prompts, "
        "effort_levels) VALUES ('01a1ece0-0000-7000-8000-000000000001', 'm', 'mock', 'mock://x', "
        "'local', 'm', 'none', 0, 0, 1, '{}', '[]')",
    )
    with pytest.raises(psycopg.errors.CheckViolation):
        execute(
            ai_db,
            f"INSERT INTO effort_measurements (id, model_config_id, effort_level, pass_lines, "
            f"{columns}) VALUES (gen_random_uuid(), '01a1ece0-0000-7000-8000-000000000001', "
            f"'standard', '{{}}', {values})",
        )
