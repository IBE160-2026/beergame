"""`run`: the only way to make an LLM call (AD-6, FR-32, FR-67, FR-68, AD-17, C-1).

One call resolves the scope's model config and the purpose's prompt version from it, scrubs
free text, renders the prompt, and makes up to the purpose's number of attempts inside the
deadline. Each attempt is timed and written as its own `llm_call` row with the caller
reference, tokens, cost and outcome, in its own transaction, and its cost is added to the
budget. pydantic-ai validates the answer against the output schema with its own output
retries set to 0: the retry loop is this module's.

The caller gets a validated `Result` or a typed `Failure`; no provider exception reaches it.
`GatewayError` is raised only for a mistake of the caller or the config, before any attempt.
`preview` returns the request `run` would send (prompt, output schema, model settings) without
calling a model, for `python -m app.sim prompt` and the recognition probe.
"""

import asyncio
import os
import string
import time
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal

import pydantic_ai
from pydantic import BaseModel
from pydantic_ai import (
    Agent,
    ModelRequestTimeout,
    ModelResponse,
    ModelTimeoutError,
    NativeOutput,
    TextPart,
    UnexpectedModelBehavior,
    capture_run_messages,
)
from pydantic_ai.exceptions import ContentFilterError, IncompleteToolCall
from pydantic_ai.models import Model

from app.ai import budget, config, mock, prompt_files, purposes
from app.ai.db import transaction
from app.ai.models import llm_calls
from app.ai.scrub import OffsetMap, scrub
from app.platform import pii
from app.platform.config import get_settings

pydantic_ai.BANNER_ENABLED = False  # never print to a CLI's stdout

FailureKind = Literal["timeout", "invalid_output", "budget_exhausted", "provider_error"]
Outcome = Literal["ok", "invalid_output", "timeout", "provider_error"]
Scalar = str | int | float | Decimal | bool

MOCK_ENVS = ("local", "test", "ci")
"""The environments where the mock answers when no provider key is set (AD-17)."""

NO_RETRIES = {"tools": 0, "output": 0}
"""pydantic-ai's own retries (its `output_retries`) stay at 0: this module retries (AD-6)."""

ERROR_LIMIT = 500
"""Characters of an error message kept on a row."""


class GatewayError(Exception):
    """The caller or the config is wrong; no attempt was made and nothing was logged."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class Inputs:
    """`values` are what the prompt is rendered from (every string is free text and is
    scrubbed); `caller` holds ids only (for a player Order the Game, Seat and Week), stored on
    every row and never rendered; `mock_answer` is read by the mock provider only."""

    values: Mapping[str, Scalar] = field(default_factory=dict)
    caller: Mapping[str, uuid.UUID | int | str] = field(default_factory=dict)
    mock_answer: Any = None


@dataclass(frozen=True)
class Result[T: BaseModel]:
    output: T
    llm_call_ids: tuple[uuid.UUID, ...]
    offset_maps: Mapping[str, OffsetMap]
    """For each string value, the map from its scrubbed text back to the original."""


@dataclass(frozen=True)
class Failure:
    kind: FailureKind
    llm_call_ids: tuple[uuid.UUID, ...]
    detail: str


@dataclass(frozen=True)
class _Call:
    purpose: purposes.Purpose
    scope: budget.BudgetScope
    config: config.ModelConfig
    level: config.EffortLevel
    prompt_version: int
    prompt: str
    caller: dict[str, str | int]
    terms: list[str]
    offset_maps: dict[str, OffsetMap]
    settings: dict[str, Any]
    request: dict[str, Any]


@dataclass(frozen=True)
class _Attempt:
    outcome: Outcome
    output: BaseModel | None
    error: str | None
    response: str | None
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    latency_ms: int
    started_at: datetime


def _caller(caller: Mapping[str, object]) -> dict[str, str | int]:
    stored: dict[str, str | int] = {}
    for name, value in caller.items():
        if not isinstance(name, str):
            raise GatewayError("inputs_invalid", "caller reference names must be strings")
        if isinstance(value, uuid.UUID):
            stored[name] = str(value)
        elif isinstance(value, int) and not isinstance(value, bool):
            stored[name] = value
        elif isinstance(value, str):
            try:
                stored[name] = str(uuid.UUID(value))
            except ValueError:
                raise GatewayError(
                    "inputs_invalid", f"caller reference {name!r} is not an id"
                ) from None
        else:
            raise GatewayError("inputs_invalid", f"caller reference {name!r} is not an id")
    return stored


def _settings(level: config.EffortLevel) -> dict[str, Any]:
    """Seed and temperature from the Effort level, where it sets them."""
    params = level.provider_params
    settings: dict[str, Any] = {}
    seed = params.get("seed")
    if isinstance(seed, int) and not isinstance(seed, bool):
        settings["seed"] = seed
    temperature = params.get("temperature")
    if isinstance(temperature, int | float) and not isinstance(temperature, bool):
        settings["temperature"] = float(temperature)
    return settings


def _exhausted(state: budget.Budget | None, purpose: purposes.Purpose) -> bool:
    """The budget allows no further attempt (until Story 2.8's reservations)."""
    if state is None:
        return True
    return state.spent >= state.limit or (purpose.player and state.players_exhausted_at is not None)


def _checked(purpose_name: str, inputs: Inputs) -> tuple[purposes.Purpose, dict[str, str | int]]:
    """The purpose and the stored caller reference; refuses a caller mistake."""
    purpose = purposes.get(purpose_name)
    if purpose is None:
        raise GatewayError("unknown_purpose", f"no purpose {purpose_name!r}")
    if not isinstance(inputs, Inputs):
        raise GatewayError("inputs_invalid", "inputs must be an Inputs")
    for name, value in inputs.values.items():
        if not isinstance(name, str) or not isinstance(value, Scalar):
            raise GatewayError("inputs_invalid", f"render value {name!r} is not a scalar")
    return purpose, _caller(inputs.caller)


async def _resolve(
    scope: budget.BudgetScope, purpose: purposes.Purpose
) -> tuple[config.ModelConfig, config.EffortLevel, int]:
    """The scope's model config, its Effort level and the purpose's prompt version."""
    if scope.kind != "evaluation":
        # A Class session's config comes from its binding, which Epic 5 adds.
        raise GatewayError("scope_unresolved", f"no model config is bound to {scope.kind}")
    model_config = await config.get(scope.id)
    if model_config is None:
        raise GatewayError("config_not_found", f"no model config {scope.id}")
    if scope.effort_level is None:
        level = model_config.spec.effort_levels[0]
    else:
        found = model_config.effort_level(scope.effort_level)
        if found is None:
            raise GatewayError(
                "effort_level_unknown", f"config {scope.id} has no level {scope.effort_level!r}"
            )
        level = found
    version = model_config.spec.prompts.get(purpose.name)
    if version is None:
        raise GatewayError(
            "prompt_not_in_config", f"config {scope.id} names no prompt for {purpose.name}"
        )
    return model_config, level, version


def _template(purpose: purposes.Purpose, version: int) -> str:
    template = prompt_files.load(purpose.name, version)
    if template is None:
        raise GatewayError("prompt_missing", f"no prompt file {purpose.name}/v{version}.md")
    return template


def _render(
    purpose: purposes.Purpose, version: int, template: str, inputs: Inputs, terms: list[str]
) -> tuple[str, dict[str, OffsetMap]]:
    """The prompt rendered from the scrubbed values, and each string value's offset map."""
    scrubbed = {
        name: scrub(value, terms) for name, value in inputs.values.items() if isinstance(value, str)
    }
    rendered = {
        name: scrubbed[name].text if name in scrubbed else str(value)
        for name, value in inputs.values.items()
    }
    try:
        prompt = string.Template(template).substitute(rendered)
    except (KeyError, ValueError) as exc:
        raise GatewayError("render_failed", f"prompt {purpose.name}/v{version}: {exc}") from None
    return prompt, {name: item.offsets for name, item in scrubbed.items()}


def _request(
    prompt: str, output_schema: type[BaseModel], settings: dict[str, Any]
) -> dict[str, Any]:
    """What is handed to the model layer and stored on every row: the scrubbed prompt, the
    output JSON schema and the model settings. Ids and the mock answer are never in it."""
    return {
        "prompt": prompt,
        "output_schema": output_schema.model_json_schema(),
        "model_settings": settings,
    }


async def _prepare(
    purpose_name: str,
    scope: budget.BudgetScope,
    inputs: Inputs,
    output_schema: type[BaseModel],
) -> _Call | Failure:
    purpose, caller = _checked(purpose_name, inputs)
    model_config, level, version = await _resolve(scope, purpose)
    template = _template(purpose, version)
    state = await budget.get(scope)
    if state is None:
        raise GatewayError("budget_not_found", f"no budget for {scope.kind} {scope.id}")
    if _exhausted(state, purpose):
        return Failure("budget_exhausted", (), f"budget {scope.kind} {scope.id} is spent")
    terms = pii.terms(scope)
    prompt, offset_maps = _render(purpose, version, template, inputs, terms)
    settings = _settings(level)
    return _Call(
        purpose=purpose,
        scope=scope,
        config=model_config,
        level=level,
        prompt_version=version,
        prompt=prompt,
        caller=caller,
        terms=terms,
        offset_maps=offset_maps,
        settings=settings,
        request=_request(prompt, output_schema, settings),
    )


@dataclass(frozen=True)
class Preview:
    """What `run` would send for these inputs: the prompt version and the request (the scrubbed
    prompt, the output JSON schema and the model settings), exactly as a row stores it."""

    prompt_version: int
    request: Mapping[str, Any]


async def preview(
    purpose: str,
    inputs: Inputs,
    output_schema: type[BaseModel],
    budget_scope: budget.BudgetScope | None = None,
) -> Preview:
    """The request `run` would make, without a model, a budget check or a row.

    With a scope it is resolved as `run` resolves it (config, Effort level, prompt version,
    scrubbing terms). Without one, the newest prompt file of the purpose is rendered with no
    terms and no model settings. Raises `GatewayError` like `run`."""
    checked, _ = _checked(purpose, inputs)
    if budget_scope is None:
        version = prompt_files.latest(checked.name)
        if version is None:
            raise GatewayError("prompt_missing", f"no prompt file for {checked.name}")
        terms: list[str] = []
        settings: dict[str, Any] = {}
    else:
        _, level, version = await _resolve(budget_scope, checked)
        terms = pii.terms(budget_scope)
        settings = _settings(level)
    prompt, _ = _render(checked, version, _template(checked, version), inputs, terms)
    return Preview(version, _request(prompt, output_schema, settings))


def _model(call: _Call, inputs: Inputs, output_schema: type[BaseModel]) -> Model | str:
    """The model for the attempts, or why none may be used (a `provider_error`)."""
    spec = call.config.spec
    app_env = get_settings().app_env
    key_set = bool(spec.credential_env and os.environ.get(spec.credential_env))
    if app_env in MOCK_ENVS and (spec.provider == "mock" or not key_set):
        return mock.model(inputs.mock_answer, output_schema, spec.model_version)
    if spec.provider == "mock":
        return f"the mock provider is never used with APP_ENV={app_env}"
    if not key_set:
        return f"the key variable {spec.credential_env} is not set"
    return f"no adapter for provider {spec.provider} yet"  # Story 2.7 adds openai_compatible


def _usage(response: ModelResponse | None) -> tuple[int, int, int, str | None]:
    if response is None:
        return 0, 0, 0, None
    text = "".join(part.content for part in response.parts if isinstance(part, TextPart))
    usage = response.usage
    return usage.input_tokens, usage.output_tokens, usage.output_reasoning_tokens, text


async def _attempt(
    call: _Call, model: Model, output_schema: type[BaseModel], seconds: float
) -> _Attempt:
    started_at = datetime.now(UTC)
    clock = time.perf_counter()
    output: BaseModel | None = None
    outcome: Outcome = "ok"
    error: str | None = None
    with capture_run_messages() as messages:
        try:
            agent = Agent(model, output_type=NativeOutput(output_schema), retries=NO_RETRIES)
            async with asyncio.timeout(seconds):
                result = await agent.run(call.prompt, model_settings=call.settings or None)
            output = result.output
        except TimeoutError, ModelTimeoutError, ModelRequestTimeout:
            outcome, error = "timeout", f"no answer within {seconds:.3f} s"
        except ContentFilterError, IncompleteToolCall:
            outcome, error = "provider_error", "the provider refused or cut off the answer"
        except UnexpectedModelBehavior as exc:
            outcome, error = "invalid_output", str(exc)
        except Exception as exc:  # every other provider failure becomes a typed failure
            outcome, error = "provider_error", f"{type(exc).__name__}: {exc}"
    latency_ms = round((time.perf_counter() - clock) * 1000)
    response = next((m for m in reversed(messages) if isinstance(m, ModelResponse)), None)
    input_tokens, output_tokens, reasoning_tokens, text = _usage(response)
    if text is not None:
        text = scrub(text, call.terms).text
    return _Attempt(
        outcome,
        output,
        None if error is None else scrub(error, call.terms).text[:ERROR_LIMIT],
        text,
        input_tokens,
        output_tokens,
        reasoning_tokens,
        latency_ms,
        started_at,
    )


def cost(spec: config.ModelConfigSpec, input_tokens: int, output_tokens: int) -> Decimal:
    """USD at the config's prices; reasoning tokens are part of the output tokens."""
    prices = spec.prices
    total = input_tokens * prices.input_usd_per_mtok + output_tokens * prices.output_usd_per_mtok
    return (total / Decimal(1_000_000)).quantize(Decimal("1e-8"))


async def _log(call: _Call, number: int, attempt: _Attempt) -> uuid.UUID:
    spec = call.config.spec
    amount = cost(spec, attempt.input_tokens, attempt.output_tokens)
    row_id = uuid.uuid7()
    async with transaction(None) as session:
        await session.execute(
            llm_calls.insert().values(
                id=row_id,
                purpose=call.purpose.name,
                scope_kind=call.scope.kind,
                scope_id=call.scope.id,
                caller_ref=call.caller,
                model_config_id=call.config.id,
                provider=spec.provider,
                endpoint=spec.endpoint,
                model_version=spec.model_version,
                quantisation=spec.quantisation,
                effort_level=call.level.name,
                seed=call.settings.get("seed"),
                temperature=call.settings.get("temperature"),
                prompt_version=call.prompt_version,
                attempt=number,
                input_tokens=attempt.input_tokens,
                output_tokens=attempt.output_tokens,
                reasoning_tokens=attempt.reasoning_tokens,
                cost_usd=amount,
                latency_ms=attempt.latency_ms,
                outcome=attempt.outcome,
                error=attempt.error,
                request=call.request,
                response=attempt.response,
                started_at=attempt.started_at,
            )
        )
        if amount:
            await budget.charge(call.scope, amount, session=session)
    return row_id


def _no_model(error: str) -> _Attempt:
    return _Attempt("provider_error", None, error, None, 0, 0, 0, 0, datetime.now(UTC))


async def run[T: BaseModel](
    purpose: str,
    budget_scope: budget.BudgetScope,
    inputs: Inputs,
    output_schema: type[T],
    deadline: datetime | None,
) -> Result[T] | Failure:
    """Make one validated LLM call. `deadline` (timezone-aware) bounds all attempts; `None`
    leaves only the attempt limit and the per-attempt timeout (Epic 8's playout)."""
    if deadline is not None and deadline.tzinfo is None:
        raise GatewayError("inputs_invalid", "the deadline must be timezone-aware")
    call = await _prepare(purpose, budget_scope, inputs, output_schema)
    if isinstance(call, Failure):
        return call
    model = _model(call, inputs, output_schema)
    if isinstance(model, str):
        return Failure("provider_error", (await _log(call, 1, _no_model(model)),), model)
    ids: list[uuid.UUID] = []
    last: _Attempt | None = None
    for number in range(1, call.purpose.attempt_limit + 1):
        timeout = call.level.attempt_timeout_s
        if deadline is not None:
            left = (deadline - datetime.now(UTC)).total_seconds()
            if left <= 0:
                return Failure("timeout", tuple(ids), "the deadline passed")
            timeout = min(timeout, left)
        if number > 1 and _exhausted(await budget.get(call.scope), call.purpose):
            # Each attempt's cost is charged as it ends, so a call stops once it is spent.
            return Failure("budget_exhausted", tuple(ids), "the budget was spent during the call")
        last = await _attempt(call, model, output_schema, timeout)
        ids.append(await _log(call, number, last))
        if last.output is not None:
            return Result(last.output, tuple(ids), call.offset_maps)  # type: ignore[arg-type]
    assert last is not None and last.outcome != "ok"
    return Failure(last.outcome, tuple(ids), last.error or last.outcome)
