"""Zero-config start (AD-17, Story 2.12).

In `local`, `test` and `ci`, when no model config is stored, the api, a worker and
`python -m app.sim` seed one config named `mock` for the mock provider: its one Effort level,
a measurement marked `mock` that makes the level offered there, an evaluation budget, and a pin
that makes it the active default. Every later epic so finds a default model config with no key.
With `APP_ENV=production` nothing is seeded; there a mock measurement never counts and the mock
config can never be pinned (`ai.config`).
"""

from decimal import Decimal

import structlog
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import budget, config
from app.ai.db import transaction
from app.ai.models import model_configs
from app.platform.config import get_settings

log = structlog.get_logger(__name__)

MOCK_SPEC: dict[str, object] = {
    "name": "mock",
    "provider": "mock",
    "endpoint": "mock://local",
    "region": "local",
    "model_version": "mock-1",
    "quantisation": "none",
    "prices": {"input_usd_per_mtok": "0.10", "output_usd_per_mtok": "0.40"},
    "rate_limit_rpm": 600,
    "prompts": {
        "player_order": 1,
        "recognition_probe": 1,
        "debrief_narration": 1,
        "quiz_explanation": 1,
    },
    "effort_levels": [
        {
            "name": "standard",
            "provider_params": {},
            "attempt_timeout_s": 4,
            "order_time_budget_s": 8,
            "placeholder": True,
            "label": "Standard",
            "effect": "Testmodell: svarer straks og koster ingenting.",
        }
    ],
}
"""The seeded config: the content of `ai-configs/mock.json` (a test keeps them equal)."""

BUDGET_USD = Decimal("10")
"""The seeded evaluation budget's limit: mock money, the mock costs nothing real."""

SEED_LOCK = 0x2_12_A1_0C
"""The advisory lock key that keeps processes starting together from seeding twice."""


async def _offer_and_pin(row: config.ModelConfig, s: AsyncSession) -> str:
    """A mock row's measurement, evaluation budget and pin, so it is the offered default."""
    level = row.spec.effort_levels[0].name
    await config.add_mock_measurement(row.id, level, session=s)
    await budget.set_budget(budget.BudgetScope.evaluation(row.id), limit=BUDGET_USD, session=s)
    await config.pin(row.id, session=s)
    return level


async def _missing_prompts(s: AsyncSession) -> tuple[config.ModelConfig, dict[str, int]] | None:
    """The active default when it is a mock config whose `prompts` map lacks a purpose the
    seeded spec names, with the purposes to add; None otherwise."""
    default = await config.active_default(session=s)
    if default is None or default.spec.provider != "mock":
        return None
    wanted: dict[str, int] = dict(MOCK_SPEC["prompts"])  # type: ignore[call-overload]
    missing = {name: v for name, v in wanted.items() if name not in default.spec.prompts}
    return (default, missing) if missing else None


async def ensure_zero_config() -> str | None:
    """Seed the `mock` config when the environment allows it and no config is stored; returns
    the new config's id, else None. One transaction under an advisory lock.

    A later epic's purposes reach a database seeded before them the way an operator adds them
    (`config edit ID --prompt …`, Story 9.14): when the active default is a mock config without a
    purpose of `MOCK_SPEC`, a new row is derived from it with those prompts, measured as mock and
    pinned; Class sessions created before keep the config they hold."""
    if get_settings().app_env not in config.MOCK_ENVS:
        return None
    async with transaction(None) as s:
        await s.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": SEED_LOCK})
        if (await s.execute(select(model_configs.c.id).limit(1))).first() is not None:
            found = await _missing_prompts(s)
            if found is None:
                return None
            source, missing = found
            row = await config.derive(source.id, prompts=missing, session=s)
            level = await _offer_and_pin(row, s)
            log.info(
                "zero_config_prompts_added",
                model_config_id=str(row.id),
                derived_from=str(source.id),
                purposes=sorted(missing),
            )
            return str(row.id)
        row = await config.add(config.parse(MOCK_SPEC), session=s)
        level = await _offer_and_pin(row, s)
    log.info("zero_config_seeded", model_config_id=str(row.id), effort_level=level)
    return str(row.id)


async def ensure_zero_config_logged() -> None:
    """`ensure_zero_config` for process start: a database error is logged, never raised, so a
    process whose database is not migrated yet still starts."""
    try:
        await ensure_zero_config()
    except DBAPIError as exc:
        log.warning(
            "zero_config_failed",
            error_code="db_error",
            exc_type=type(getattr(exc, "orig", exc)).__name__,
        )
