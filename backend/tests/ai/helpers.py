"""Shared pieces for the `app.ai` tests."""

import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.ai import ratelimit
from tests.conftest import kept_connection

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
    return kept_connection(url).execute(sql, params).fetchall()


ROOMY_BUDGET_S = 600
"""The Order time budget `stored_config` gives each Effort level unless a test names its own.
A turn's deadline is real time from the Week's opening, and a Week's LLM jobs run one after
another, so the shipped 8 s could run out on a busy machine and turn an expected answer into
a `timeout` fallback. Tests about deadlines set their own budget."""


def roomy_levels() -> list[dict]:
    """The mock config's Effort levels with `ROOMY_BUDGET_S` as the Order time budget."""
    return [{**level, "order_time_budget_s": ROOMY_BUDGET_S} for level in MOCK["effort_levels"]]


async def stored_config(*, limit: str = "10", **changes: object) -> str:
    """Store the mock config with the `player_order` prompt, roomy Order time budgets
    (`ROOMY_BUDGET_S`) and an evaluation budget of `limit` USD (no reserve); returns its id.
    For the tests of LLM players (Story 2.5)."""
    from decimal import Decimal

    from app.ai import budget, config

    changes.setdefault("effort_levels", roomy_levels())
    data = mock_config(prompts={"player_order": 1}, **changes)
    row = await config.add(config.parse(data))
    await budget.set_budget(
        budget.BudgetScope.evaluation(row.id), limit=Decimal(limit), reserve=Decimal(0)
    )
    return str(row.id)


class StoppedClock(ratelimit.Clock):
    """A clock for the gateway that moves only when a test moves it: it stands still while a
    call prepares, so deadline checks see exactly the time the test says passed, however busy
    the machine is. `given` records the timeout each attempt got (see `stop_attempts`)."""

    def __init__(self, at: datetime | None = None) -> None:
        self.at = at or datetime(2026, 1, 1, tzinfo=UTC)
        self.given: list[float] = []

    def now(self) -> datetime:
        return self.at

    def monotonic(self) -> float:
        return self.at.timestamp()

    async def sleep(self, seconds: float) -> None:
        self.at += timedelta(seconds=max(seconds, 0))


def stop_attempts(monkeypatch, clock: StoppedClock) -> None:
    """Route every gateway attempt through `clock`: it records the attempt's timeout, and an
    attempt that times out moves the clock on by that whole timeout (the time it waited)."""
    from app.ai import gateway

    real = gateway._attempt

    async def timed(call, model, output_schema, seconds):
        clock.given.append(seconds)
        attempt = await real(call, model, output_schema, seconds)
        if attempt.outcome == "timeout":
            clock.at += timedelta(seconds=seconds)
        return attempt

    monkeypatch.setattr(gateway, "_attempt", timed)
