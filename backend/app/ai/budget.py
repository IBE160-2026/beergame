"""Budgets (`ai.budget`, AD-6, AD-22, FR-69).

One row per scope: a model config's evaluation budget (simulation runs) or a Class session's
budget. Money is `NUMERIC(18,8)` USD. The row holds `limit`, `reserve` (kept for the Debrief and
the AI assessment), `spent`, `reserved` (the worst-case cost of the attempts under way) and
`players_exhausted_at` (the cost-limit state).

Before each attempt the gateway reserves its worst-case cost with one conditional `UPDATE`
(`reserve`); a player purpose may take the row only up to `limit − reserve`, other purposes up
to `limit`. The attempt's `llm_call` row and `settle` (reservation off, actual cost on `spent`)
share one transaction. No limit check ever sums `llm_call` rows (Story 2.8, AD-6, FR-69). A
player reservation that does not fit sets `players_exhausted_at` once, for the rest of the
scope's life; `players` then switches the scope's LLM Seats to Rule-based players.

Other modules read and change budgets only through this module (AD-6); Epic 5 creates a Class
session's row with `set_budget(BudgetScope.class_session(id))`, whose limit defaults to
`AI_DEFAULT_SESSION_BUDGET_USD`.
"""

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import config
from app.ai.db import transaction
from app.ai.models import budgets, spend_alerts
from app.platform.config import get_settings

ScopeKind = Literal["evaluation", "class_session"]

log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class BudgetScope:
    """Whose budget a call charges. `effort_level` is the Effort level the scope froze (a
    simulation batch, later a Class session); the gateway uses the config's first level when it
    is `None`. It does not take part in equality: one scope has one budget row."""

    kind: ScopeKind
    id: uuid.UUID
    effort_level: str | None = field(default=None, compare=False)
    model_config_id: uuid.UUID | None = field(default=None, compare=False)
    """The model config a Class session's call uses, as its caller pinned it (the Debrief's
    `debrief_ai_text` pin, Story 9.14); not part of equality. Without it a Class session scope
    has no config (`scope_unresolved`)."""

    @classmethod
    def evaluation(
        cls, config_id: uuid.UUID | str, *, effort_level: str | None = None
    ) -> BudgetScope:
        return cls("evaluation", uuid.UUID(str(config_id)), effort_level)

    @classmethod
    def class_session(
        cls,
        class_session_id: uuid.UUID | str,
        *,
        effort_level: str | None = None,
        model_config_id: uuid.UUID | str | None = None,
    ) -> BudgetScope:
        config_id = None if model_config_id is None else uuid.UUID(str(model_config_id))
        return cls("class_session", uuid.UUID(str(class_session_id)), effort_level, config_id)


@dataclass(frozen=True)
class Budget:
    scope: BudgetScope
    limit: Decimal
    reserve: Decimal
    spent: Decimal
    players_exhausted_at: datetime | None
    updated_at: datetime
    reserved: Decimal = Decimal(0)
    """The worst-case cost of the attempts under way."""


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
        row.reserved_usd,
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


async def find(scope_id: uuid.UUID) -> list[Budget]:
    """Every budget row whose scope id is `scope_id` (one per scope kind at most)."""
    async with transaction(None) as s:
        rows = (
            await s.execute(
                select(budgets).where(budgets.c.scope_id == scope_id).order_by(budgets.c.scope_kind)
            )
        ).all()
    return [_row(row) for row in rows]


async def state(scope: BudgetScope, *, session: AsyncSession | None = None) -> Budget | None:
    """The scope's cost state: limit, reserve, spent, reserved and the time the players' limit
    was reached (`players_exhausted_at`), for Epic 3's notice and Epic 15's cost view."""
    return await get(scope, session=session)


@dataclass(frozen=True)
class LimitChange:
    """What `set_limit` did: the row after it and the limit before (None: the row was made)."""

    budget: Budget
    previous_limit: Decimal | None
    previous: Budget | None = None
    """The row as it stood under the lock, before the change (None: the row was made)."""

    @property
    def changed(self) -> bool:
        return self.previous_limit != self.budget.limit


async def set_limit(
    scope: BudgetScope, limit: Decimal, *, session: AsyncSession | None = None
) -> LimitChange:
    """Set the scope's cost limit on its one row, under the row's lock, keeping the reserve, the
    spend and `players_exhausted_at` (Story 15.6, FR-69); a missing row is made with the default
    reserve. Raises `BudgetRefused`: `amount_invalid`, `reserve_above_limit` (below the reserve)
    or `limit_below_spent` (below what is spent and held)."""
    limit = _amount("limit", limit)
    async with transaction(session) as s:
        row = (
            await s.execute(select(budgets).where(_where(scope)).with_for_update())
        ).one_or_none()
        if row is None:
            made = await set_budget(scope, limit=limit, session=s)
            return LimitChange(made, None)
        if limit == row.limit_usd:
            return LimitChange(_row(row), row.limit_usd, _row(row))
        if limit < row.reserve_usd:
            raise BudgetRefused(
                "reserve_above_limit", f"the reserve {row.reserve_usd} is larger than {limit}"
            )
        if limit < row.spent_usd + row.reserved_usd:
            raise BudgetRefused(
                "limit_below_spent", f"{row.spent_usd + row.reserved_usd} is spent or held"
            )
        updated = (
            await s.execute(
                update(budgets)
                .where(_where(scope))
                .values(limit_usd=limit, updated_at=func.now())
                .returning(*budgets.c)
            )
        ).one()
    return LimitChange(_row(updated), row.limit_usd, _row(row))


async def class_session_states(
    ids: list[uuid.UUID] | None = None, *, session: AsyncSession | None = None
) -> dict[uuid.UUID, Budget]:
    """The budget rows of these Class sessions (every Class session's when None), by id (Story
    15.6's cost view and the sweep's cost-limit notice)."""
    query = select(budgets).where(budgets.c.scope_kind == "class_session")
    if ids is not None:
        if not ids:
            return {}
        query = query.where(budgets.c.scope_id.in_(ids))
    async with transaction(session) as s:
        rows = (await s.execute(query)).all()
    return {row.scope_id: _row(row) for row in rows}


async def exhausted_class_sessions(*, session: AsyncSession | None = None) -> list[uuid.UUID]:
    """The Class sessions whose players' limit was reached (`players_exhausted_at` set), by id."""
    async with transaction(session) as s:
        rows = await s.execute(
            select(budgets.c.scope_id)
            .where(
                budgets.c.scope_kind == "class_session",
                budgets.c.players_exhausted_at.is_not(None),
            )
            .order_by(budgets.c.scope_id)
        )
    return list(rows.scalars())


async def evaluation_states(*, session: AsyncSession | None = None) -> list[Budget]:
    """Every evaluation budget (simulation runs, AD-22), by model config id."""
    async with transaction(session) as s:
        rows = (
            await s.execute(
                select(budgets)
                .where(budgets.c.scope_kind == "evaluation")
                .order_by(budgets.c.scope_id)
            )
        ).all()
    return [_row(row) for row in rows]


@dataclass(frozen=True)
class Reservation:
    """An amount held on a scope's row until `settle` or `release`."""

    scope: BudgetScope
    amount: Decimal


def _where(scope: BudgetScope) -> Any:
    return (budgets.c.scope_kind == scope.kind) & (budgets.c.scope_id == scope.id)


async def reserve(scope: BudgetScope, amount: Decimal, *, player: bool) -> Reservation | None:
    """Hold `amount` (an attempt's worst-case cost) on the scope's row with one conditional
    `UPDATE`, in its own transaction; None when it does not fit. A player purpose fits only
    within `limit − reserve` and while `players_exhausted_at` is unset; when it does not fit,
    `players_exhausted_at` is set (once) and `ai_cost_limit_reached` is logged after the
    commit."""
    ceiling = budgets.c.limit_usd - budgets.c.reserve_usd if player else budgets.c.limit_usd
    condition = _where(scope) & (budgets.c.spent_usd + budgets.c.reserved_usd + amount <= ceiling)
    if player:
        condition = condition & budgets.c.players_exhausted_at.is_(None)
    reached = False
    async with transaction(None) as session:
        held = (
            await session.execute(
                update(budgets)
                .where(condition)
                .values(reserved_usd=budgets.c.reserved_usd + amount, updated_at=func.now())
                .returning(budgets.c.id)
            )
        ).first()
        if held is None and player:
            reached = (
                await session.execute(
                    update(budgets)
                    .where(_where(scope) & budgets.c.players_exhausted_at.is_(None))
                    .values(players_exhausted_at=func.now(), updated_at=func.now())
                    .returning(budgets.c.id)
                )
            ).first() is not None
    if reached:
        log.warning("ai_cost_limit_reached", scope_kind=scope.kind, scope_id=str(scope.id))
    return None if held is None else Reservation(scope, amount)


async def settle(
    reservation: Reservation | None, scope: BudgetScope, actual: Decimal, *, session: AsyncSession
) -> None:
    """Take the reservation off the row and add the attempt's actual cost to `spent`, in the
    caller's transaction (the gateway writes the attempt's `llm_call` row in the same one)."""
    held = Decimal(0) if reservation is None else reservation.amount
    if not held and not actual:
        return
    if actual > held:
        log.warning(
            "ai_cost_above_reservation",
            scope_kind=scope.kind,
            scope_id=str(scope.id),
            reserved_usd=str(held),
            cost_usd=str(actual),
        )
    await session.execute(
        update(budgets)
        .where(_where(scope))
        .values(
            reserved_usd=budgets.c.reserved_usd - held,
            spent_usd=budgets.c.spent_usd + actual,
            updated_at=func.now(),
        )
    )


@dataclass(frozen=True)
class DailyAlert:
    """The day the AI spend passed `AI_DAILY_ALERT_USD` (Story 15.7, FR-69): the amount and the
    spend when the sweep found it, and when (the sweep's clock)."""

    id: uuid.UUID
    day: date
    alert_usd: Decimal
    spent_usd: Decimal
    alerted_at: datetime


def _alert(row: Any) -> DailyAlert:
    return DailyAlert(row.id, row.day, row.alert_usd, row.spent_usd, row.alerted_at)


async def record_daily_alert(
    day: date, alert_usd: Decimal, spent_usd: Decimal, now: datetime, *, session: AsyncSession
) -> DailyAlert:
    """Record that `day`'s spend passed `alert_usd`, in the caller's transaction; the first record
    of a day stands, so a repeat returns it unchanged."""
    if spent_usd <= alert_usd:
        raise ValueError("a daily alert records a spend above its amount")
    await session.execute(
        insert(spend_alerts)
        .values(id=uuid.uuid7(), day=day, alert_usd=alert_usd, spent_usd=spent_usd, alerted_at=now)
        .on_conflict_do_nothing(constraint="uq_ai_spend_alerts_day")
    )
    row = (await session.execute(select(spend_alerts).where(spend_alerts.c.day == day))).one()
    return _alert(row)


async def daily_alert(
    *,
    day: date | None = None,
    alert_id: uuid.UUID | None = None,
    session: AsyncSession | None = None,
) -> DailyAlert | None:
    """The alert recorded for `day`, or the one with `alert_id`; None when there is none."""
    if (day is None) == (alert_id is None):
        raise ValueError("name the alert by its day or by its id")
    where = spend_alerts.c.day == day if day is not None else spend_alerts.c.id == alert_id
    async with transaction(session) as s:
        row = (await s.execute(select(spend_alerts).where(where))).one_or_none()
    return None if row is None else _alert(row)


async def release(reservation: Reservation) -> None:
    """Give a reservation back without a cost: its attempt made no `llm_call` row (an HTTP 429,
    or the call stopped before the attempt started)."""
    async with transaction(None) as session:
        await settle(reservation, reservation.scope, Decimal(0), session=session)
