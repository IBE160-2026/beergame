"""Story 2.3: `ai.gateway.run`, the one LLM entry point (AD-6, FR-32, FR-67, AD-17, C-1)."""

import json
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import get_args

import pytest
from pydantic import BaseModel, Field

from app.ai import budget, config, gateway, mock, models
from app.ai.gateway import Failure, GatewayError, Inputs, Result
from app.ai.scrub import PLACEHOLDER
from app.platform import pii
from tests.ai.helpers import mock_config, query

TEMPLATE = "Stock: $stock units. Note: $note"
GAME = uuid.UUID("00000000-0000-7000-8000-000000000001")
SEAT = uuid.UUID("00000000-0000-7000-8000-000000000002")


class Order(BaseModel):
    order: int = Field(ge=0, le=999)


def level(name: str = "standard", **changes: object) -> dict:
    data = {"name": name, "attempt_timeout_s": 4, "order_time_budget_s": 8}
    data.update(changes)
    return data


@pytest.fixture
def template(prompts):
    (prompts / "player_order" / "v1.md").write_text(TEMPLATE, encoding="utf-8")


async def scope_for(*, limit: str = "1", effort_level: str | None = None, **changes):
    data = mock_config(prompts={"player_order": 1}, **changes)
    row = await config.add(config.parse(data))
    scope = budget.BudgetScope.evaluation(row.id, effort_level=effort_level)
    await budget.set_budget(scope, limit=Decimal(limit), reserve=Decimal(0))
    return scope


def inputs(**changes) -> Inputs:
    data = {
        "values": {"stock": 12, "note": "no backlog"},
        "caller": {"game": GAME, "seat": str(SEAT), "week": 3},
        "mock_answer": None,
    }
    data.update(changes)
    return Inputs(**data)


async def call(scope, given: Inputs | None = None, deadline: datetime | None = None):
    return await gateway.run("player_order", scope, given or inputs(), Order, deadline)


def rows(url: str) -> list[dict]:
    names = [c.name for c in models.llm_calls.c]
    found = query(url, f"SELECT {', '.join(names)} FROM llm_call ORDER BY started_at, attempt")
    return [dict(zip(names, row, strict=True)) for row in found]


async def test_a_mock_answer_is_validated_and_logged_with_every_field(ai_db, template):
    scope = await scope_for()
    result = await call(scope, inputs(mock_answer={"order": 4}))
    assert isinstance(result, Result)
    assert result.output == Order(order=4)
    [row] = rows(ai_db)
    assert result.llm_call_ids == (row["id"],)
    assert row["caller_ref"] == {"game": str(GAME), "seat": str(SEAT), "week": 3}
    assert (row["purpose"], row["scope_kind"], row["scope_id"]) == (
        "player_order",
        "evaluation",
        scope.id,
    )
    assert row["model_config_id"] == scope.id
    assert (row["provider"], row["endpoint"], row["model_version"], row["quantisation"]) == (
        "mock",
        "mock://local",
        "mock-1",
        "none",
    )
    assert (row["effort_level"], row["seed"], row["temperature"], row["prompt_version"]) == (
        "standard",
        None,
        None,
        1,
    )
    assert (row["attempt"], row["outcome"], row["error"]) == (1, "ok", None)
    assert row["input_tokens"] > 0 and row["output_tokens"] > 0 and row["reasoning_tokens"] == 0
    expected = (
        row["input_tokens"] * Decimal("0.10") + row["output_tokens"] * Decimal("0.40")
    ) / 1_000_000
    assert row["cost_usd"] == expected.quantize(Decimal("1e-8")) > 0
    assert row["latency_ms"] >= 0 and row["started_at"] <= row["created_at"]
    assert json.loads(row["response"]) == {"order": 4}
    # The prompt is rendered from the values; the caller reference is never rendered or sent.
    request = row["request"]
    assert request["prompt"] == "Stock: 12 units. Note: no backlog"
    assert request["output_schema"] == Order.model_json_schema()
    assert str(GAME) not in json.dumps(request) and str(SEAT) not in json.dumps(request)
    # The attempt's cost is charged to the budget.
    assert (await budget.get(scope)).spent == row["cost_usd"]


async def test_without_a_mock_answer_the_same_inputs_give_the_same_fixed_answer(ai_db, template):
    scope = await scope_for()
    first = await call(scope)
    second = await call(scope)
    assert first.output == second.output == Order(order=0)
    one, two = rows(ai_db)
    assert one["request"] == two["request"] and one["response"] == two["response"]


async def test_an_invalid_answer_is_retried_and_each_attempt_logged(ai_db, template):
    scope = await scope_for()
    with mock.script(mock.INVALID, '{"order": 1000}'):
        result = await call(scope, inputs(mock_answer={"order": 7}))
    assert result.output == Order(order=7)
    found = rows(ai_db)
    assert [(r["attempt"], r["outcome"]) for r in found] == [
        (1, "invalid_output"),
        (2, "invalid_output"),
        (3, "ok"),
    ]
    assert result.llm_call_ids == tuple(r["id"] for r in found)
    assert found[0]["response"] == "not json"
    spent = (await budget.get(scope)).spent
    assert spent == sum(r["cost_usd"] for r in found)


async def test_invalid_answers_end_in_invalid_output_after_six_attempts(ai_db, template):
    scope = await scope_for()
    result = await call(scope, inputs(mock_answer={"order": -1}))
    assert isinstance(result, Failure)
    assert result.kind == "invalid_output"
    found = rows(ai_db)
    assert [r["outcome"] for r in found] == ["invalid_output"] * 6
    assert [r["attempt"] for r in found] == [1, 2, 3, 4, 5, 6]
    assert result.llm_call_ids == tuple(r["id"] for r in found)


async def test_provider_errors_are_typed_failures_never_exceptions(ai_db, template):
    scope = await scope_for()
    with mock.script(*[mock.ERROR] * 6):
        result = await call(scope)
    assert isinstance(result, Failure) and result.kind == "provider_error"
    found = rows(ai_db)
    assert [r["outcome"] for r in found] == ["provider_error"] * 6
    assert found[0]["error"].startswith("ModelHTTPError")
    assert (found[0]["input_tokens"], found[0]["cost_usd"]) == (0, 0)


async def test_a_timed_out_attempt_is_logged_and_the_next_one_runs(ai_db, template):
    scope = await scope_for(effort_levels=[level(attempt_timeout_s=0.05)])
    with mock.script(mock.TIMEOUT):
        result = await call(scope, inputs(mock_answer={"order": 2}))
    assert result.output == Order(order=2)
    first, second = rows(ai_db)
    assert (first["outcome"], second["outcome"]) == ("timeout", "ok")
    assert first["latency_ms"] >= 40 and first["response"] is None


async def test_the_deadline_bounds_every_attempt(ai_db, template):
    scope = await scope_for()
    past = datetime.now(UTC) - timedelta(seconds=1)
    result = await call(scope, deadline=past)
    assert result == Failure("timeout", (), "the deadline passed")
    assert rows(ai_db) == []

    soon = datetime.now(UTC) + timedelta(seconds=0.1)
    with mock.script(*[mock.TIMEOUT] * 6):
        result = await call(scope, deadline=soon)
    assert isinstance(result, Failure) and result.kind == "timeout"
    found = rows(ai_db)
    # The 4 s attempt timeout is cut to the deadline. The loop clock and the wall clock may
    # differ by a hair, so a last sliver of an attempt may follow; all of it ends by 0.5 s.
    assert {r["outcome"] for r in found} == {"timeout"}
    assert sum(r["latency_ms"] for r in found) < 500
    with pytest.raises(GatewayError) as caught:
        await call(scope, deadline=datetime.now())
    assert caught.value.code == "inputs_invalid"


async def test_a_retry_starts_only_when_its_whole_timeout_fits_before_the_deadline(ai_db, template):
    """Story 2.6: after a timed-out attempt, the next one starts only if it can finish inside
    the deadline; otherwise the call ends as `timeout`."""
    scope = await scope_for(effort_levels=[level(attempt_timeout_s=0.3)])
    # After the first 0.3 s attempt about 0.15 s are left: less than a whole attempt.
    tight = datetime.now(UTC) + timedelta(seconds=0.45)
    with mock.script(mock.TIMEOUT):
        result = await call(scope, inputs(mock_answer={"order": 2}), deadline=tight)
    [only] = rows(ai_db)
    assert result == Failure("timeout", (only["id"],), "no time left for another attempt")
    assert only["outcome"] == "timeout"

    quick = await scope_for(effort_levels=[level(attempt_timeout_s=0.05)])
    roomy = datetime.now(UTC) + timedelta(seconds=2)
    with mock.script(mock.TIMEOUT):
        result = await call(quick, inputs(mock_answer={"order": 2}), deadline=roomy)
    assert result.output == Order(order=2)
    assert [r["outcome"] for r in rows(ai_db)[1:]] == ["timeout", "ok"]


async def test_without_a_deadline_the_attempt_limit_and_timeout_still_apply(ai_db, template):
    scope = await scope_for(effort_levels=[level(attempt_timeout_s=0.02)])
    with mock.script(*[mock.TIMEOUT] * 6):
        result = await call(scope, deadline=None)
    assert isinstance(result, Failure) and result.kind == "timeout"
    assert [r["outcome"] for r in rows(ai_db)] == ["timeout"] * 6


async def test_a_cancelled_call_logs_the_attempt_in_flight(ai_db, template):
    """Issue #52: a job stopped mid-call still leaves the attempt's row, then the
    cancellation goes on."""
    import asyncio

    scope = await scope_for()
    with mock.script(mock.TIMEOUT):
        task = asyncio.create_task(call(scope))
        await asyncio.sleep(0.1)  # the call first reads the config and budget
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    [row] = rows(ai_db)
    assert (row["outcome"], row["attempt"]) == ("cancelled", 1)
    assert row["error"] == "the caller cancelled the attempt"
    assert row["caller_ref"] == {"game": str(GAME), "seat": str(SEAT), "week": 3}
    assert row["latency_ms"] >= 30


async def test_production_never_uses_the_mock(ai_db, template, monkeypatch):
    scope = await scope_for()
    monkeypatch.setenv("APP_ENV", "production")
    from app.platform.config import get_settings

    get_settings.cache_clear()
    with mock.script("left alone"):
        result = await call(scope, inputs(mock_answer={"order": 4}))
        assert list(mock._steps) == ["left alone"]
    assert isinstance(result, Failure) and result.kind == "provider_error"
    assert "never used with APP_ENV=production" in result.detail
    [row] = rows(ai_db)
    assert (row["outcome"], row["attempt"], row["cost_usd"]) == ("provider_error", 1, 0)


async def test_a_real_provider_without_a_key_gets_the_mock_outside_production(
    ai_db, template, monkeypatch
):
    real = {
        "provider": "openai_compatible",
        "endpoint": "https://eu.example.test/api/v1",
        "credential_env": "OLSPILLET_TEST_KEY",
    }
    scope = await scope_for(**real)
    monkeypatch.delenv("OLSPILLET_TEST_KEY", raising=False)
    result = await call(scope, inputs(mock_answer={"order": 5}))
    assert result.output == Order(order=5)
    # With a key set, the adapter calls the endpoint and no mock stands in (the tests' transport
    # refuses every request, so this is a provider error).
    monkeypatch.setenv("OLSPILLET_TEST_KEY", "not-a-real-key")
    result = await call(scope, inputs(mock_answer={"order": 5}))
    assert isinstance(result, Failure) and result.kind == "provider_error"
    assert "Connection" in result.detail
    # In production a missing key is a provider error too, never the mock.
    monkeypatch.delenv("OLSPILLET_TEST_KEY")
    monkeypatch.setenv("APP_ENV", "production")
    from app.platform.config import get_settings

    get_settings.cache_clear()
    result = await call(scope, inputs(mock_answer={"order": 5}))
    assert result.detail == "the key variable OLSPILLET_TEST_KEY is not set"
    assert "not-a-real-key" not in json.dumps([str(v) for r in rows(ai_db) for v in r.values()])


async def test_a_spent_budget_makes_no_attempt(ai_db, template):
    scope = await scope_for(limit="0")
    result = await call(scope)
    assert isinstance(result, Failure) and (result.kind, result.llm_call_ids) == (
        "budget_exhausted",
        (),
    )
    await budget.set_budget(scope, limit=Decimal(1), reserve=Decimal(0))
    query(ai_db, "UPDATE ai_budgets SET players_exhausted_at = now() RETURNING id")
    assert (await call(scope)).kind == "budget_exhausted"
    assert rows(ai_db) == []


async def test_a_call_stops_when_its_attempts_spend_the_budget(ai_db, template):
    scope = await scope_for(limit="0.00000001")
    result = await call(scope, inputs(mock_answer={"order": -1}))
    [row] = rows(ai_db)
    assert result == Failure(
        "budget_exhausted", (row["id"],), "the budget was spent during the call"
    )


async def test_free_text_is_scrubbed_before_it_is_sent_or_stored(ai_db, template, monkeypatch):
    scope = await scope_for()
    monkeypatch.setattr(pii, "terms", lambda scope: ["Ola Nordmann"])
    note = "ola nordmann asked for more"
    with mock.script('{"order": 3} Ola Nordmann'):
        await call(scope, inputs(values={"stock": 1, "note": note}))
    result = await call(scope, inputs(values={"stock": 1, "note": note}))
    found = rows(ai_db)
    assert found[-1]["request"]["prompt"] == f"Stock: 1 units. Note: {PLACEHOLDER} asked for more"
    assert "nordmann" not in json.dumps([r["request"] for r in found]).lower()
    assert found[0]["response"] == f'{{"order": 3}} {PLACEHOLDER}'
    # An error text is scrubbed too (a provider may echo text back in it).

    def failing(*args, **kwargs):
        raise RuntimeError("upstream said: Ola  Nordmann")

    monkeypatch.setattr(gateway, "Agent", failing)
    failure = await call(scope, inputs(values={"stock": 1, "note": note}))
    assert failure.kind == "provider_error"
    assert failure.detail == f"RuntimeError: upstream said: {PLACEHOLDER}"
    assert rows(ai_db)[-1]["error"] == failure.detail
    start = len(PLACEHOLDER) + 1
    assert result.offset_maps["note"].original_span(0, start + 5) == (0, len("ola nordmann ") + 5)
    assert set(result.offset_maps) == {"note"}


async def test_the_effort_level_comes_from_the_scope(ai_db, template):
    levels = [level(), level("careful", provider_params={"seed": 7, "temperature": 0.2})]
    scope = await scope_for(effort_levels=levels, effort_level="careful")
    await call(scope)
    [row] = rows(ai_db)
    assert (row["effort_level"], row["seed"], row["temperature"]) == ("careful", 7, 0.2)
    assert row["request"]["model_settings"] == {"seed": 7, "temperature": 0.2}
    assert mock.last_model_settings == {"seed": 7, "temperature": 0.2}  # sent, not only logged

    # A scope that names no level gets the config's first one.
    default = budget.BudgetScope.evaluation(scope.id)
    await call(default)
    assert rows(ai_db)[-1]["effort_level"] == "standard"
    assert mock.last_model_settings == {}


async def test_caller_and_config_mistakes_raise_before_any_attempt(ai_db, template, prompts):
    scope = await scope_for()

    async def code(purpose="player_order", target=scope, given=None) -> str:
        with pytest.raises(GatewayError) as caught:
            await gateway.run(purpose, target, given or inputs(), Order, None)
        return caught.value.code

    assert await code(purpose="chat") == "unknown_purpose"
    assert await code(target=budget.BudgetScope.class_session(uuid.uuid4())) == "scope_unresolved"
    assert await code(target=budget.BudgetScope.evaluation(uuid.uuid4())) == "config_not_found"
    level_scope = budget.BudgetScope.evaluation(scope.id, effort_level="turbo")
    assert await code(target=level_scope) == "effort_level_unknown"
    assert await code(given=inputs(caller={"game": "Ola"})) == "inputs_invalid"
    assert await code(given=inputs(caller={"week": True})) == "inputs_invalid"
    assert await code(given=inputs(values={"stock": [1]})) == "inputs_invalid"
    assert await code(given=inputs(values={"stock": 1})) == "render_failed"
    no_prompt = await config.add(config.parse(mock_config()))
    assert await code(target=budget.BudgetScope.evaluation(no_prompt.id)) == "prompt_not_in_config"
    no_budget = await config.add(config.parse(mock_config(prompts={"player_order": 1})))
    assert await code(target=budget.BudgetScope.evaluation(no_budget.id)) == "budget_not_found"
    (prompts / "player_order" / "v1.md").unlink()
    assert await code() == "prompt_missing"
    assert rows(ai_db) == []


def test_the_outcomes_match_the_table_check():
    assert set(get_args(gateway.Outcome)) == set(models.OUTCOMES)
    failures = set(get_args(gateway.FailureKind))
    # `cancelled` (Story 2.6) never reaches a caller: the cancellation goes on.
    assert failures - {"budget_exhausted"} == set(models.OUTCOMES) - {"ok", "cancelled"}


async def test_preview_resolves_a_scope_as_run_does_and_uses_the_newest_file_without_one(
    ai_db, template, prompts
):
    """Story 2.4: `preview` with a scope takes the config's prompt version and Effort level
    settings, and equals what `run` stores; without one, the newest file and no settings."""
    (prompts / "player_order" / "v2.md").write_text("Newer: $stock $note", encoding="utf-8")
    seeded = level(provider_params={"seed": 1, "temperature": 0.2})
    scope = await scope_for(effort_levels=[seeded])
    scoped = await gateway.preview("player_order", inputs(), Order, scope)
    assert scoped.prompt_version == 1
    assert scoped.request["prompt"] == "Stock: 12 units. Note: no backlog"
    assert scoped.request["model_settings"] == {"seed": 1, "temperature": 0.2}
    bare = await gateway.preview("player_order", inputs(), Order)
    assert bare.prompt_version == 2 and bare.request["model_settings"] == {}
    assert bare.request["prompt"] == "Newer: 12 no backlog"
    await call(scope, inputs(mock_answer={"order": 4}))
    [row] = rows(ai_db)
    assert row["request"] == json.loads(json.dumps(scoped.request))
    assert rows(ai_db)[0]["outcome"] == "ok"
    with pytest.raises(GatewayError) as caught:
        await gateway.preview("debrief", inputs(), Order)
    assert caught.value.code == "unknown_purpose"
