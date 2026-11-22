"""Reading `llm_call` rows (FR-67, FR-69): what one call's attempts cost and took, for reports
such as `python -m app.sim endpoint`, a scope's cost per Game and day for
`python -m app.ai.cli cost`, and the player attempts of a simulation batch's Games for
`python -m app.sim report` (Story 2.11). Only `app/ai` reads the table (AD-6)."""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ARRAY, Uuid, any_, func, literal, or_, select, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.budget import BudgetScope
from app.ai.db import transaction
from app.ai.models import (
    budgets,
    default_pins,
    effort_measurements,
    llm_calls,
    model_configs,
    model_freezes,
)

CALL_TABLE = llm_calls.name
"""The call table's name, for the personal-data registry (Story 15.2): only `app/ai` spells it."""

TABLES_WITHOUT_PERSONAL_DATA = {
    budgets.name: "Budgets per scope.",
    default_pins.name: "Pinned model configs.",
    model_configs.name: "Model configs.",
    effort_measurements.name: "Simulation measurements.",
    model_freezes.name: "Study freezes of a model config: ids and times only (Story 15.5).",
}
"""The `app/ai` tables that hold no personal data, for the registry (Story 15.2, AD-14)."""

EMPTY_REQUEST = literal({}, JSONB)
"""The request body of a call whose body was cleared (Story 15.2)."""


@dataclass(frozen=True)
class Attempt:
    id: uuid.UUID
    attempt: int
    outcome: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal
    served_model: str | None
    served_by: str | None
    error: str | None


@dataclass(frozen=True)
class CostLine:
    """The summed cost and the number of attempts of one group of `llm_call` rows."""

    key: str
    usd: Decimal
    calls: int


@dataclass(frozen=True)
class Costs:
    total: CostLine
    games: list[CostLine]
    """Per Game in the rows' caller reference (`-` for rows without one), dearest first."""
    days: list[CostLine]
    """Per UTC day of `started_at`, oldest first."""


async def costs(scope: BudgetScope) -> Costs:
    """The AI cost of a scope summed from its settled `llm_call` rows (every outcome, so failed
    and late attempts count too), in total, per Game and per day (FR-69)."""
    where = (llm_calls.c.scope_kind == scope.kind) & (llm_calls.c.scope_id == scope.id)
    usd = func.coalesce(func.sum(llm_calls.c.cost_usd), 0)
    calls = func.count(llm_calls.c.id)
    # Labelled, so GROUP BY and ORDER BY name the column instead of repeating its parameters.
    game = func.coalesce(llm_calls.c.caller_ref["game"].astext, "-").label("game")
    day = func.to_char(func.timezone("UTC", llm_calls.c.started_at), "YYYY-MM-DD").label("day")
    usd = usd.label("usd")
    async with transaction(None) as session:
        total = (await session.execute(select(usd, calls).where(where))).one()
        games = (
            await session.execute(
                select(game, usd, calls)
                .where(where)
                .group_by(game)
                .order_by(usd.desc(), game.asc())
            )
        ).all()
        days = (
            await session.execute(select(day, usd, calls).where(where).group_by(day).order_by(day))
        ).all()

    def line(key: str, amount: object, count: int) -> CostLine:
        return CostLine(key, Decimal(str(amount)).quantize(Decimal("1e-8")), count)

    return Costs(
        line("total", *total),
        [line(*row) for row in games],
        [line(*row) for row in days],
    )


async def get(ids: Sequence[uuid.UUID]) -> list[Attempt]:
    """The rows with these ids, in attempt order."""
    if not ids:
        return []
    columns = [getattr(llm_calls.c, name) for name in Attempt.__dataclass_fields__]
    async with transaction(None) as session:
        rows = (
            await session.execute(
                select(*columns)
                .where(llm_calls.c.id.in_(list(ids)))
                .order_by(llm_calls.c.started_at, llm_calls.c.attempt)
            )
        ).all()
    return [Attempt(*row) for row in rows]


EXPORT_COLUMNS = (
    "id",
    "purpose",
    "model_config_id",
    "provider",
    "endpoint",
    "model_version",
    "quantisation",
    "effort_level",
    "seed",
    "temperature",
    "prompt_version",
    "attempt",
    "input_tokens",
    "output_tokens",
    "reasoning_tokens",
    "cost_usd",
    "latency_ms",
    "outcome",
    "served_model",
    "served_by",
    "started_at",
)
"""The call metadata in the pseudonymised export (Story 15.4, FR-67, FR-71): no body, no caller
reference and no error text, which could quote what the call was about."""


async def export_metadata(
    ids: Sequence[uuid.UUID], session: AsyncSession | None = None
) -> tuple[tuple[str, ...], list[tuple]]:
    """The metadata of the calls with these ids, oldest first (Story 15.4)."""
    if not ids:
        return EXPORT_COLUMNS, []
    columns = [getattr(llm_calls.c, name) for name in EXPORT_COLUMNS]
    async with transaction(session) as session:
        rows = (
            await session.execute(
                select(*columns)
                .where(llm_calls.c.id == any_(literal(list(ids), ARRAY(Uuid))))
                .order_by(llm_calls.c.started_at, llm_calls.c.id)
            )
        ).all()
    return EXPORT_COLUMNS, [tuple(row) for row in rows]


PLAYER_PURPOSE = "player_order"
"""The purpose of an LLM player's Order (`players.llm.PURPOSE`); named here, since `app/ai`
imports nothing from `modules` (AD-6)."""


@dataclass(frozen=True)
class GameAttempt:
    """One player attempt of a Game, as a simulation batch report reads it (Story 2.11)."""

    id: uuid.UUID
    game: str
    """The Game id in the row's caller reference."""
    attempt: int
    outcome: str
    effort_level: str
    started_at: datetime
    latency_ms: int
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    cost_usd: Decimal


async def game_attempts(game_ids: Sequence[str]) -> list[GameAttempt]:
    """Every `player_order` attempt whose caller reference names one of `game_ids`, of every
    outcome, oldest first (FR-67, FR-78)."""
    if not game_ids:
        return []
    game = llm_calls.c.caller_ref["game"].astext
    columns = [
        llm_calls.c.id,
        game.label("game"),
        llm_calls.c.attempt,
        llm_calls.c.outcome,
        llm_calls.c.effort_level,
        llm_calls.c.started_at,
        llm_calls.c.latency_ms,
        llm_calls.c.input_tokens,
        llm_calls.c.output_tokens,
        llm_calls.c.reasoning_tokens,
        llm_calls.c.cost_usd,
    ]
    async with transaction(None) as session:
        rows = (
            await session.execute(
                select(*columns)
                .where(
                    llm_calls.c.purpose == PLAYER_PURPOSE,
                    game.in_([str(game_id) for game_id in game_ids]),
                )
                .order_by(llm_calls.c.started_at, llm_calls.c.id)
            )
        ).all()
    return [GameAttempt(*row) for row in rows]


async def clear_bodies_of_user(session: AsyncSession, user_id: uuid.UUID) -> int:
    """Story 15.2 (FR-76, AD-14): empty the scrubbed request and the response of every call made
    for the User, in the caller's transaction: those whose `caller_ref` names them (a Debrief
    follow-up question quotes the Student's own text). The row stays, with its cost, tokens and
    outcome, so cost sums do not change. Idempotent; returns how many rows held a body."""
    result = await session.execute(
        update(llm_calls)
        .where(
            llm_calls.c.caller_ref["user_id"].astext == str(user_id),
            or_(llm_calls.c.request != EMPTY_REQUEST, llm_calls.c.response.is_not(None)),
        )
        .values(request=EMPTY_REQUEST, response=None)
    )
    return result.rowcount or 0
