"""Budgets (`ai.budget`, AD-6, AD-22, FR-69).

One row per scope: a model config's evaluation budget (simulation runs) or a Class session's
budget. Money is `NUMERIC(18,8)` USD. The row holds `limit`, `reserve` (kept for the Debrief and
the AI assessment), `spent` and `players_exhausted_at` (the cost-limit state). The gateway adds
each attempt's cost to `spent` (`charge`); reservations against it come with Story 2.8.

Other modules read and change budgets only through this module (AD-6); Epic 5 creates a Class
session's row with `set_budget(BudgetScope.class_session(id))`, whose limit defaults to
`AI_DEFAULT_SESSION_BUDGET_USD`.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import config
from app.ai.db import transaction
from app.ai.models import budgets
from app.platform.config import get_settings

ScopeKind = Literal["evaluation", "class_session"]


@dataclass(frozen=True)
class BudgetScope:
    """Whose budget a call charges. `effort_level` is the Effort level the scope froze (a
    simulation batch, later a Class session); the gateway uses the config's first level when it
    is `None`. It does not take part in equality: one scope has one budget row."""

    kind: ScopeKind
    id: uuid.UUID
    effort_level: str | None = field(default=None, compare=False)

    @classmethod
    def evaluation(
        cls, config_id: uuid.UUID | str, *, effort_level: str | None = None
    ) -> BudgetScope:
        return cls("evaluation", uuid.UUID(str(config_id)), effort_level)

    @classmethod
    def class_session(
        cls, class_session_id: uuid.UUID | str, *, effort_level: str | None = None
    ) -> BudgetScope:
        return cls("class_session", uuid.UUID(str(class_session_id)), effort_level)


@dataclass(frozen=True)
class Budget:
    scope: BudgetScope
    limit: Decimal
    reserve: Decimal
    spent: Decimal
    players_exhausted_at: datetime | None
    updated_at: datetime


class BudgetRefused(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def _amount(name: str, value: Decimal) -> Decimal:
    if not value.is_finite() or value < 0:
        raise BudgetRefused("amount_invalid", f"{name} must be a USD amount of at least 0")
    if value >= Decimal(10) ** 10:
        raise BudgetRefused("amount_invalid", f"{name} is too large")
    if value != value.quantize(Decimal("1e-8")):
        raise BudgetRefused("amount_invalid", f"{name} has more than 8 decimal places")
    return value


def _row(row: Any) -> Budget:
    return Budget(
        BudgetScope(row.scope_kind, row.scope_id),
        row.limit_usd,
        row.reserve_usd,
        row.spent_usd,
        row.players_exhausted_at,
        row.updated_at,
    )


async def set_budget(
    scope: BudgetScope,
    *,
    limit: Decimal | None = None,
    reserve: Decimal | None = None,
    session: AsyncSession | None = None,
) -> Budget:
    """Create the scope's one row, or change its limit and reserve (spent and
    `players_exhausted_at` stay). A Class session's limit defaults to
    `AI_DEFAULT_SESSION_BUDGET_USD`; an evaluation budget needs one. The reserve defaults to
    `AI_BUDGET_RESERVE_USD` (a placeholder until the prototype, issue #8)."""
    settings = get_settings()
    if limit is None:
        if scope.kind != "class_session":
            raise BudgetRefused("limit_required", "an evaluation budget needs a limit")
        limit = settings.ai_default_session_budget_usd
    if reserve is None:
        reserve = settings.ai_budget_reserve_usd
    limit = _amount("limit", limit)
    reserve = _amount("reserve", reserve)
    if reserve > limit:
        raise BudgetRefused(
            "reserve_above_limit", f"the reserve {reserve} is larger than the limit {limit}"
        )
    async with transaction(session) as s:
        if scope.kind == "evaluation" and await config.get(scope.id, session=s) is None:
            raise BudgetRefused("config_not_found", f"no model config {scope.id}")
        statement = insert(budgets).values(
            id=uuid.uuid7(),
            scope_kind=scope.kind,
            scope_id=scope.id,
            limit_usd=limit,
            reserve_usd=reserve,
        )
        statement = statement.on_conflict_do_update(
            constraint="uq_ai_budgets_scope",
            set_={
                "limit_usd": statement.excluded.limit_usd,
                "reserve_usd": statement.excluded.reserve_usd,
                "updated_at": func.now(),
            },
        ).returning(*budgets.c)
        return _row((await s.execute(statement)).one())


async def get(scope: BudgetScope, *, session: AsyncSession | None = None) -> Budget | None:
    async with transaction(session) as s:
        row = (
            await s.execute(
                select(budgets).where(
                    budgets.c.scope_kind == scope.kind, budgets.c.scope_id == scope.id
                )
            )
        ).one_or_none()
    return None if row is None else _row(row)


async def charge(scope: BudgetScope, amount: Decimal, *, session: AsyncSession) -> None:
    """Add one attempt's cost to `spent` with a single `UPDATE`, in the caller's transaction
    (the gateway writes the attempt's `llm_call` row in the same one). Story 2.8 replaces this
    with reserve-then-settle."""
    await session.execute(
        update(budgets)
        .where(budgets.c.scope_kind == scope.kind, budgets.c.scope_id == scope.id)
        .values(spent_usd=budgets.c.spent_usd + amount, updated_at=func.now())
    )
