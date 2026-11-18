"""Reading `llm_call` rows (FR-67, FR-69): what one call's attempts cost and took, for reports
such as `python -m app.sim endpoint`, a scope's cost per Game and day for
`python -m app.ai.cli cost`, and the player attempts of a simulation batch's Games for
`python -m app.sim report` (Story 2.11). Only `app/ai` reads the table (AD-6)."""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select

from app.ai.budget import BudgetScope
from app.ai.db import transaction
from app.ai.models import llm_calls


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
