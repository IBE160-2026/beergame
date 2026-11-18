"""Story 2.2: budgets (`ai.budget`)."""

import uuid
from decimal import Decimal

import pytest

from app.ai import budget, config
from app.platform.config import get_settings
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
