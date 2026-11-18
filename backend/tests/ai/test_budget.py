"""Story 2.2: budgets (`ai.budget`)."""

import asyncio
import uuid
from decimal import Decimal

import pytest
from structlog.testing import capture_logs

from app.ai import budget, config
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker
from tests.ai.helpers import MOCK, query


async def test_an_evaluation_budget_is_one_row_with_the_default_reserve(ai_db):
    row = await config.add(config.parse(MOCK))
    scope = budget.BudgetScope.evaluation(row.id)
    first = await budget.set_budget(scope, limit=Decimal("2"))
    assert (first.limit, first.reserve, first.spent, first.players_exhausted_at) == (
        Decimal("2.00000000"),
        get_settings().ai_budget_reserve_usd,
        Decimal("0E-8"),
        None,
    )
    # Trailing zeros past 8 places are still an exact amount.
    again = await budget.set_budget(scope, limit=Decimal("3.000000000"), reserve=Decimal("0.5"))
    assert (again.limit, again.reserve, again.spent) == (Decimal(3), Decimal("0.5"), 0)
    assert query(ai_db, "SELECT count(*), min(scope_kind) FROM ai_budgets") == [(1, "evaluation")]
    assert await budget.get(scope) == again


async def test_a_second_set_keeps_spent_and_the_cost_limit_state(ai_db):
    row = await config.add(config.parse(MOCK))
    scope = budget.BudgetScope.evaluation(row.id)
    await budget.set_budget(scope, limit=Decimal("2"))
    query(  # what the gateway's reservations (Story 2.8) will write
        ai_db,
        "UPDATE ai_budgets SET spent_usd = 1.5, players_exhausted_at = now() RETURNING id",
    )
    again = await budget.set_budget(scope, limit=Decimal("4"))
    assert again.spent == Decimal("1.5") and again.players_exhausted_at is not None


async def test_a_class_session_budget_defaults_its_limit(ai_db, monkeypatch):
    monkeypatch.setenv("AI_DEFAULT_SESSION_BUDGET_USD", "7.25")
    get_settings.cache_clear()
    scope = budget.BudgetScope.class_session(uuid.uuid7())
    row = await budget.set_budget(scope)
    assert (row.scope, row.limit, row.reserve) == (scope, Decimal("7.25"), Decimal("1.00"))


@pytest.mark.parametrize(
    ("limit", "reserve", "code"),
    [
        (None, None, "limit_required"),
        (Decimal("0.5"), None, "reserve_above_limit"),
        (Decimal("1"), Decimal("2"), "reserve_above_limit"),
        (Decimal("-1"), Decimal("0"), "amount_invalid"),
        (Decimal("1.000000001"), Decimal("0"), "amount_invalid"),
        (Decimal("NaN"), Decimal("0"), "amount_invalid"),
        (Decimal("10000000000"), Decimal("0"), "amount_invalid"),
    ],
)
async def test_refused_budgets_store_nothing(ai_db, limit, reserve, code):
    row = await config.add(config.parse(MOCK))
    with pytest.raises(budget.BudgetRefused) as caught:
        await budget.set_budget(budget.BudgetScope.evaluation(row.id), limit=limit, reserve=reserve)
    assert caught.value.code == code
    assert query(ai_db, "SELECT count(*) FROM ai_budgets") == [(0,)]


async def test_an_evaluation_budget_needs_a_stored_config(ai_db):
    with pytest.raises(budget.BudgetRefused) as caught:
        await budget.set_budget(budget.BudgetScope.evaluation(uuid.uuid7()), limit=Decimal(1))
    assert caught.value.code == "config_not_found"


# --- Story 2.8: reservations ------------------------------------------------------------------


async def evaluation(limit: str, reserve: str = "0") -> budget.BudgetScope:
    row = await config.add(config.parse(MOCK))
    scope = budget.BudgetScope.evaluation(row.id)
    await budget.set_budget(scope, limit=Decimal(limit), reserve=Decimal(reserve))
    return scope


async def test_parallel_reservations_never_take_the_row_past_its_limit(ai_db):
    """AD-6: each reservation is one conditional UPDATE; 20 at once on a row that fits 10."""
    scope = await evaluation("1")
    held = await asyncio.gather(
        *(budget.reserve(scope, Decimal("0.1"), player=False) for _ in range(20))
    )
    assert sum(item is not None for item in held) == 10
    state = await budget.state(scope)
    assert (state.spent, state.reserved) == (0, Decimal("1"))
    # Settling takes each reservation off and adds the actual cost.
    for item in filter(None, held):
        async with get_sessionmaker().begin() as session:
            await budget.settle(item, scope, Decimal("0.02"), session=session)
    state = await budget.state(scope)
    assert (state.spent, state.reserved) == (Decimal("0.2"), 0)


async def test_a_player_may_not_spend_the_reserve_and_sets_the_cost_limit_once(ai_db):
    scope = await evaluation("1", reserve="0.6")
    assert await budget.reserve(scope, Decimal("0.4"), player=True) is not None
    with capture_logs() as logs:
        assert await budget.reserve(scope, Decimal("0.1"), player=True) is None
        reached = (await budget.state(scope)).players_exhausted_at
        assert await budget.reserve(scope, Decimal("0.01"), player=True) is None
    assert reached is not None and (await budget.state(scope)).players_exhausted_at == reached
    assert [entry for entry in logs if entry["event"] == "ai_cost_limit_reached"] == [
        {
            "event": "ai_cost_limit_reached",
            "log_level": "warning",
            "scope_kind": "evaluation",
            "scope_id": str(scope.id),
        }
    ]
    # Other purposes may still spend the reserve, up to the limit.
    other = await budget.reserve(scope, Decimal("0.6"), player=False)
    assert other is not None
    assert await budget.reserve(scope, Decimal("0.00000001"), player=False) is None
    await budget.release(other)
    state = await budget.state(scope)
    assert (state.limit, state.reserve, state.spent, state.reserved) == (
        1,
        Decimal("0.6"),
        0,
        Decimal("0.4"),
    )


async def test_a_non_player_reservation_that_does_not_fit_leaves_the_players_alone(ai_db):
    scope = await evaluation("0.1")
    assert await budget.reserve(scope, Decimal("0.2"), player=False) is None
    assert (await budget.state(scope)).players_exhausted_at is None
    assert (
        await budget.reserve(budget.BudgetScope.evaluation(uuid.uuid7()), Decimal(0), player=True)
        is None
    )


async def test_a_cost_above_its_reservation_is_recorded_and_logged(ai_db):
    scope = await evaluation("1")
    held = await budget.reserve(scope, Decimal("0.01"), player=True)
    with capture_logs() as logs:
        async with get_sessionmaker().begin() as session:
            await budget.settle(held, scope, Decimal("0.03"), session=session)
    state = await budget.state(scope)
    assert (state.spent, state.reserved) == (Decimal("0.03"), 0)
    assert [entry["event"] for entry in logs] == ["ai_cost_above_reservation"]
