"""Story 9.14: `ai.text.worded`, AI text with the caller's validator and code fallback (AD-6, AD-7).

One call through the gateway with the mock provider: an accepted output gives the validator's text
marked `ai_generated` with its `llm_call` id; every typed failure, a rejection, a validator that
raises and a call the gateway refuses to prepare give the fallback text, unmarked, with no id, and
the call is never made twice."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import BaseModel

from app.ai import budget, config, gateway, mock
from app.ai.text import AiText, worded
from tests.ai.helpers import mock_config, query

FALLBACK = "Koden sin tekst."


class Line(BaseModel):
    template_id: str


async def scope_for(*, limit: str = "1", prompts: dict | None = None) -> budget.BudgetScope:
    """A Class session scope naming a mock config with the Debrief's prompt, and its budget."""
    row = await config.add(config.parse(mock_config(prompts=prompts or {"debrief_narration": 1})))
    scope = budget.BudgetScope.class_session(uuid.uuid4(), model_config_id=row.id)
    await budget.set_budget(scope, limit=Decimal(limit), reserve=Decimal(0))
    return scope


def inputs(answer: object = None) -> gateway.Inputs:
    return gateway.Inputs(values={}, caller={"game_id": uuid.uuid4()}, mock_answer=answer)


def accept(output: Line) -> str | None:
    return (
        f"Tekst fra {output.template_id}." if output.template_id.startswith("narration") else None
    )


async def run(scope, answer: object = None, **changes) -> AiText:
    options = {"validate": accept, "fallback": lambda: FALLBACK, **changes}
    return await worded("debrief_narration", scope, inputs(answer), Line, **options)


def calls(url: str) -> list[tuple]:
    return query(url, "SELECT id, purpose, scope_kind, model_config_id, outcome FROM llm_call")


async def test_an_accepted_output_is_the_validators_text_marked_with_its_call(ai_db):
    scope = await scope_for()
    shown = await run(scope, {"template_id": "narration-orders"})
    [(call_id, purpose, kind, config_id, outcome)] = calls(ai_db)
    assert shown == AiText("Tekst fra narration-orders.", True, call_id)
    # A Class session scope uses the model config its caller named (Story 9.14).
    assert (purpose, kind, config_id, outcome) == (
        "debrief_narration",
        "class_session",
        scope.model_config_id,
        "ok",
    )


async def test_a_rejected_output_gives_the_fallback_unmarked(ai_db):
    scope = await scope_for()
    assert await run(scope, {"template_id": "invented"}) == AiText(FALLBACK, False, None)
    assert len(calls(ai_db)) == 1  # one call, never asked again


async def test_a_validator_that_raises_gives_the_fallback(ai_db):
    def broken(output: Line) -> str | None:
        raise KeyError(output.template_id)

    shown = await run(await scope_for(), {"template_id": "narration-orders"}, validate=broken)
    assert shown == AiText(FALLBACK, False, None)


@pytest.mark.parametrize("kind", ["timeout", "invalid_output", "provider_error"])
async def test_every_typed_failure_gives_the_fallback_after_one_attempt(ai_db, kind):
    scope = await scope_for()
    step = {"timeout": mock.TIMEOUT, "invalid_output": mock.INVALID, "provider_error": mock.ERROR}
    deadline = datetime.now(UTC) + timedelta(seconds=0.3)
    with mock.script(step[kind]):
        shown = await run(scope, {"template_id": "narration-orders"}, deadline=deadline)
    assert shown == AiText(FALLBACK, False, None)
    assert [row[4] for row in calls(ai_db)] == [kind]


async def test_a_spent_budget_gives_the_fallback_without_a_call(ai_db):
    scope = await scope_for(limit="0")
    assert await run(scope, {"template_id": "narration-orders"}) == AiText(FALLBACK, False, None)
    assert calls(ai_db) == []


async def test_any_other_exception_of_the_call_gives_the_fallback(ai_db, monkeypatch):
    async def broken(*args, **kwargs):
        raise RuntimeError("the database went away")

    monkeypatch.setattr(gateway, "run", broken)
    assert await run(await scope_for()) == AiText(FALLBACK, False, None)


async def test_a_call_the_gateway_cannot_prepare_gives_the_fallback(ai_db):
    # The config names no prompt for the purpose (a config made before Story 9.14), and a Class
    # session scope without a config.
    scope = await scope_for(prompts={"player_order": 1})
    assert await run(scope) == AiText(FALLBACK, False, None)
    unbound = budget.BudgetScope.class_session(uuid.uuid4())
    assert await run(unbound) == AiText(FALLBACK, False, None)
    assert calls(ai_db) == []


async def test_a_default_mock_config_without_the_debriefs_prompts_gets_a_derived_row(ai_db):
    """Zero-config (AD-17): a database seeded before Story 9.14 gets the `config edit … --prompt`
    row: derived from the default, measured as mock and pinned; once only."""
    from app.ai import seed

    old = await config.add(
        config.parse(mock_config(prompts={"player_order": 1, "recognition_probe": 1}))
    )
    await config.add_mock_measurement(old.id, "standard")
    await config.pin(old.id)
    new_id = await seed.ensure_zero_config()
    assert new_id is not None and new_id != str(old.id)
    found = await config.active_default()
    assert found is not None and str(found.id) == new_id
    assert found.spec.prompts == seed.MOCK_SPEC["prompts"]
    assert (await config.get(old.id)).spec.prompts == {"player_order": 1, "recognition_probe": 1}
    assert await seed.ensure_zero_config() is None


async def test_can_word_needs_the_config_its_prompt_and_a_provider_that_may_answer(
    ai_db, monkeypatch
):
    """Story 9.15 (FR-15): the follow-up field shows only when an answer is possible at all."""
    from app.ai.text import can_word
    from app.platform.config import Settings, get_settings

    row = await config.add(config.parse(mock_config(prompts={"debrief_follow_up": 1})))
    assert await can_word("debrief_follow_up", row.id) is True
    assert await can_word("debrief_follow_up", str(row.id)) is True
    assert await can_word("debrief_narration", row.id) is False  # no prompt for it
    assert await can_word("debrief_follow_up", None) is False
    assert await can_word("debrief_follow_up", "not-an-id") is False
    assert await can_word("debrief_follow_up", uuid.uuid4()) is False
    # In production the mock never answers: no provider, no field.
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setattr(Settings, "production_problems", lambda self: [])
    get_settings.cache_clear()
    try:
        assert await can_word("debrief_follow_up", row.id) is False
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


async def test_the_dev_outage_fails_only_the_calling_tasks_attempts(ai_db):
    """Story 9.15: the local dev narration's outage (`provider_failing`) never fails a call that
    another request makes in the same process meanwhile."""
    import asyncio

    from app.ai.text import provider_failing

    scope = await scope_for(limit="5")
    go = asyncio.Event()

    async def elsewhere() -> AiText:
        await go.wait()
        return await run(scope, {"template_id": "narration-orders"})

    other = asyncio.create_task(elsewhere())
    with provider_failing():
        failed = await run(scope, {"template_id": "narration-orders"})
        go.set()
        answered = await other
    assert failed == AiText(FALLBACK, False, None)
    assert answered.ai_generated is True
