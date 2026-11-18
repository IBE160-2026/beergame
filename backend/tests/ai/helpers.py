"""Shared pieces for the `app.ai` tests."""

import copy
import json
from pathlib import Path

import psycopg

from tests.conftest import libpq_dsn

CONFIGS = Path(__file__).resolve().parents[2] / "ai-configs"
MOCK = json.loads((CONFIGS / "mock.json").read_text(encoding="utf-8"))


def mock_config(**changes: object) -> dict:
    """The shipped mock config with an empty `prompts` map (so a test names the prompt versions
    it relies on) and top-level fields replaced."""
    data = copy.deepcopy(MOCK)
    data["prompts"] = {}
    data.update(changes)
    return data


def query(url: str, sql: str, params: tuple = ()) -> list[tuple]:
    with psycopg.connect(libpq_dsn(url)) as conn:
        return conn.execute(sql, params).fetchall()


async def stored_config(*, limit: str = "10", **changes: object) -> str:
    """Store the mock config with the `player_order` prompt and an evaluation budget of `limit`
    USD (no reserve); returns its id. For the tests of LLM players (Story 2.5)."""
    from decimal import Decimal

    from app.ai import budget, config

    data = mock_config(prompts={"player_order": 1}, **changes)
    row = await config.add(config.parse(data))
    await budget.set_budget(
        budget.BudgetScope.evaluation(row.id), limit=Decimal(limit), reserve=Decimal(0)
    )
    return str(row.id)
