"""`run`: the only way to make an LLM call (AD-6, FR-32, FR-67, FR-68, AD-17, C-1).

One call resolves the scope's model config and the purpose's prompt version from it, scrubs
free text, renders the prompt, and makes up to the purpose's number of attempts inside the
deadline. Each attempt is timed and written as its own `llm_call` row with the caller
reference, tokens, cost and outcome, in its own transaction, which also settles the worst-case
cost the attempt reserved on the budget before it started (Story 2.8). A real endpoint's
requests wait on its rate limiter, and an HTTP 429 is back-off inside
the deadline, not an attempt (Story 2.7). pydantic-ai validates the answer against the output
schema with its own output retries set to 0: the retry loop is this module's.

The caller gets a validated `Result` or a typed `Failure`; no provider exception reaches it.
`GatewayError` is raised only for a mistake of the caller or the config, before any attempt.
`preview` returns the request `run` would send (prompt, output schema, model settings) without
calling a model, for `python -m app.sim prompt` and the recognition probe.
"""

import asyncio
import json
import string
import time
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import ROUND_CEILING, Decimal
from typing import Any, Literal

import pydantic_ai
import structlog
from pydantic import BaseModel
from pydantic_ai import (
    Agent,
    ModelHTTPError,
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

from app.ai import adapters, budget, config, mock, prompt_files, purposes, ratelimit
from app.ai.db import transaction
from app.ai.models import llm_calls
from app.ai.scrub import OffsetMap, scrub
from app.platform import pii
from app.platform.config import get_settings

pydantic_ai.BANNER_ENABLED = False  # never print to a CLI's stdout

FailureKind = Literal["timeout", "invalid_output", "budget_exhausted", "provider_error"]
Outcome = Literal["ok", "invalid_output", "timeout", "provider_error", "cancelled"]
Scalar = str | int | float | Decimal | bool

log = structlog.get_logger(__name__)

MOCK_ENVS = adapters.MOCK_ENVS
"""The environments where the mock answers when no provider key is set (AD-17)."""

BACK_OFF_MIN_S = 0.25
"""The shortest back-off after a 429, also when Retry-After says 0."""

BACK_OFF_MAX_S = 30.0
"""The longest back-off after a 429 (1, 2, 4 ... seconds without `Retry-After`; a longer
`Retry-After` is cut to this)."""

RATE_LIMITED_MAX = 10
"""Consecutive 429s after which a call without a deadline gives up (`provider_error`)."""

NO_RETRIES = {"tools": 0, "output": 0}
"""pydantic-ai's own retries (its `output_retries`) stay at 0: this module retries (AD-6)."""

ERROR_LIMIT = 500
"""Characters of an error message kept on a row."""


class _Cancelled(BaseException):
    """The caller cancelled the call during an attempt; carries that attempt to be logged."""

    def __init__(self, attempt: _Attempt, original: asyncio.CancelledError) -> None:
        self.attempt = attempt
        self.original = original
        super().__init__("cancelled")


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
    served_model: str | None = None
    served_by: str | None = None
    rate_limited: bool = False
    """The endpoint answered 429: not an attempt, nothing is logged (Story 2.7)."""
    retry_after_s: float | None = None
    final: bool = False
    """An HTTP error asking again cannot fix (401, 400, 404 ...): the call stops after it."""


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


def _players_stopped(state: budget.Budget, purpose: purposes.Purpose) -> bool:
    """The scope reached the players' cost limit: a player purpose makes no attempt at all. Every
    other limit is decided by the reservation before each attempt (`budget.reserve`)."""
    return purpose.player and state.players_exhausted_at is not None


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
    if _players_stopped(state, purpose):
        return Failure("budget_exhausted", (), f"budget {scope.kind} {scope.id} is spent")
    terms = pii.terms(scope)
    prompt, offset_maps = _render(purpose, version, template, inputs, terms)
    settings = adapters.model_settings(model_config.spec, level)
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
        model_config, level, version = await _resolve(budget_scope, checked)
        terms = pii.terms(budget_scope)
        settings = adapters.model_settings(model_config.spec, level)
    prompt, _ = _render(checked, version, _template(checked, version), inputs, terms)
    return Preview(version, _request(prompt, output_schema, settings))


def _model(call: _Call, inputs: Inputs, output_schema: type[BaseModel]) -> tuple[Model, bool] | str:
    """The model for the attempts and whether it is a real endpoint (paced by the rate
    limiter), or why no model may be used (a `provider_error`)."""
    spec = call.config.spec
    found = adapters.availability(spec, get_settings().app_env)
    if found.kind == "mock":
        return mock.model(inputs.mock_answer, output_schema, spec.model_version), False
    if found.kind == "refused":
        return found.reason or "no model may answer"
    return adapters.build_model(spec), True


def _usage(response: ModelResponse | None) -> tuple[int, int, int, str | None]:
    if response is None:
        return 0, 0, 0, None
    text = "".join(part.content for part in response.parts if isinstance(part, TextPart))
    usage = response.usage
    return usage.input_tokens, usage.output_tokens, usage.output_reasoning_tokens, text


def _served(response: ModelResponse | None) -> tuple[str | None, str | None]:
    """The model id the response reports and, behind a router, the upstream provider."""
    if response is None:
        return None, None
    upstream = (response.provider_details or {}).get(adapters.UPSTREAM)
    return response.model_name or None, upstream if isinstance(upstream, str) else None


async def _attempt(
    call: _Call, model: Model, output_schema: type[BaseModel], seconds: float
) -> _Attempt:
    started_at = datetime.now(UTC)
    clock = time.perf_counter()
    output: BaseModel | None = None
    outcome: Outcome = "ok"
    error: str | None = None
    cancelled: asyncio.CancelledError | None = None
    rate_limited = False
    retry_after_s: float | None = None
    stop = False
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
        except ModelHTTPError as exc:
            outcome, error = "provider_error", f"{type(exc).__name__}: {exc}"
            if adapters.rate_limited(exc):
                rate_limited, retry_after_s = True, adapters.retry_after(exc)
            stop = adapters.final(exc)
        except UnexpectedModelBehavior as exc:
            outcome, error = "invalid_output", str(exc)
        except Exception as exc:  # every other provider failure becomes a typed failure
            outcome, error = "provider_error", f"{type(exc).__name__}: {exc}"
        except asyncio.CancelledError as exc:
            # Stopped from outside (a job killed mid-call, Issue #52): the attempt still gets
            # its row, then the same cancellation goes on (`run`).
            outcome, error, cancelled = "cancelled", "the caller cancelled the attempt", exc
    latency_ms = round((time.perf_counter() - clock) * 1000)
    response = next((m for m in reversed(messages) if isinstance(m, ModelResponse)), None)
    input_tokens, output_tokens, reasoning_tokens, text = _usage(response)
    served_model, served_by = _served(response)
    if text is not None:
        text = scrub(text, call.terms).text
    attempt = _Attempt(
        outcome,
        output,
        None if error is None else scrub(error, call.terms).text[:ERROR_LIMIT],
        text,
        input_tokens,
        output_tokens,
        reasoning_tokens,
        latency_ms,
        started_at,
        served_model,
        served_by,
        rate_limited,
        retry_after_s,
        stop,
    )
    if cancelled is not None:
        raise _Cancelled(attempt, cancelled)
    return attempt


def cost(
    spec: config.ModelConfigSpec, input_tokens: int, output_tokens: int, *, rounding: str = ""
) -> Decimal:
    """USD at the config's prices; reasoning tokens are part of the output tokens. A
    reservation rounds up (`rounding=ROUND_CEILING`) so it never falls below the true cost."""
    prices = spec.prices
    total = input_tokens * prices.input_usd_per_mtok + output_tokens * prices.output_usd_per_mtok
    quantum = Decimal("1e-8")
    if rounding:
        return (total / Decimal(1_000_000)).quantize(quantum, rounding=rounding)
    return (total / Decimal(1_000_000)).quantize(quantum)


INPUT_OVERHEAD_TOKENS = 256
"""Tokens a request may add around its content (message framing, the chat template)."""


def worst_case(call: _Call) -> Decimal:
    """The most one attempt of `call` can cost (Story 2.8): every byte of the request it sends
    (prompt, output schema, settings) as one input token — a byte-level tokenizer never makes
    more tokens than bytes — plus `INPUT_OVERHEAD_TOKENS`, and the Effort level's
    `max_output_tokens`, which the request sends as `max_tokens`."""
    sent = len(json.dumps(call.request, default=str).encode("utf-8"))
    return cost(
        call.config.spec,
        sent + INPUT_OVERHEAD_TOKENS,
        call.level.max_output_tokens,
        rounding=ROUND_CEILING,
    )


async def _log(
    call: _Call, number: int, attempt: _Attempt, held: budget.Reservation | None = None
) -> uuid.UUID:
    """Write the attempt's row and settle its reservation to its actual cost, in one
    transaction."""
    spec = call.config.spec
    amount = cost(spec, attempt.input_tokens, attempt.output_tokens)
    row_id = uuid.uuid7()
    try:
        await _write(call, number, attempt, held, row_id, amount)
    except Exception:
        # The row and the settle rolled back together: give the reservation back, so a
        # failed write never keeps budget held (Story 2.8).
        if held is not None:
            await budget.release(held)
        raise
    return row_id


async def _write(
    call: _Call,
    number: int,
    attempt: _Attempt,
    held: budget.Reservation | None,
    row_id: uuid.UUID,
    amount: Decimal,
) -> None:
    spec = call.config.spec
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
                served_model=attempt.served_model,
                served_by=attempt.served_by,
                started_at=attempt.started_at,
            )
        )
        await budget.settle(held, call.scope, amount, session=session)


async def _reserve(call: _Call, amount: Decimal) -> budget.Reservation | None:
    """`budget.reserve`, shielded: a cancel while it runs lets it finish, gives back what it
    held and then goes on, so no reservation is left behind."""
    task = asyncio.ensure_future(budget.reserve(call.scope, amount, player=call.purpose.player))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        while not task.done():  # a second cancel (shutdown) still waits for the reservation
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                continue
        held = None if task.cancelled() or task.exception() else task.result()
        if held is not None:
            await asyncio.shield(budget.release(held))
        raise


def _no_model(error: str) -> _Attempt:
    return _Attempt("provider_error", None, error, None, 0, 0, 0, 0, datetime.now(UTC))


async def run[T: BaseModel](
    purpose: str,
    budget_scope: budget.BudgetScope,
    inputs: Inputs,
    output_schema: type[T],
    deadline: datetime | None,
) -> Result[T] | Failure:
    """Make one validated LLM call. `deadline` (timezone-aware) bounds all attempts: each
    attempt's timeout is cut to the time left, a retry starts only when its whole per-attempt
    timeout fits before the deadline, and a passed deadline gives `timeout`. `None` leaves only
    the attempt limit and the per-attempt timeout (Epic 8's playout).

    A real endpoint's request waits for its rate limiter's slot first; a wait past the deadline
    gives `timeout` at once. An HTTP 429 gets no row and uses up no attempt: the endpoint pauses
    for its `Retry-After` (else 1, 2, 4 ... s) and the same attempt is made again while the
    deadline allows (`timeout` when it does not; `provider_error` after `RATE_LIMITED_MAX` in a
    row without a deadline).

    Each attempt first reserves its worst-case cost on the scope's budget row (`worst_case`,
    `budget.reserve`) and settles it to the actual cost with its row; a reservation that does
    not fit ends the call with `budget_exhausted` (for a player purpose it also sets the
    scope's cost-limit state).

    Cancelling the call (a job stopped mid-call) logs the attempt in flight with outcome
    `cancelled` and then raises `CancelledError`."""
    if deadline is not None and deadline.tzinfo is None:
        raise GatewayError("inputs_invalid", "the deadline must be timezone-aware")
    call = await _prepare(purpose, budget_scope, inputs, output_schema)
    if isinstance(call, Failure):
        return call
    found = _model(call, inputs, output_schema)
    if isinstance(found, str):
        return Failure("provider_error", (await _log(call, 1, _no_model(found)),), found)
    model, paced = found
    spec = call.config.spec
    key = adapters.endpoint_key(spec)
    clock = ratelimit.clock
    worst = worst_case(call)
    ids: list[uuid.UUID] = []
    last: _Attempt | None = None
    number = 1
    limited = 0  # consecutive 429 answers since the last attempt that counted
    while number <= call.purpose.attempt_limit:
        timeout = call.level.attempt_timeout_s
        left: float | None = None
        if deadline is not None:
            left = (deadline - clock.now()).total_seconds()
            if left <= 0:
                return Failure("timeout", tuple(ids), "the deadline passed")
            if number > 1 and left < timeout:
                # A retry starts only when it can finish inside the deadline (NFR-2); the first
                # attempt takes the time that is left.
                return Failure("timeout", tuple(ids), "no time left for another attempt")
        if paced:
            # The longest wait that still lets this attempt start under the rules above.
            allowed = None if left is None else left - (timeout if number > 1 else 0)
            if not await ratelimit.limiter.acquire(key, spec.rate_limit_rpm, allowed):
                return Failure("timeout", tuple(ids), "no request slot before the deadline")
        if deadline is not None:
            timeout = min(timeout, (deadline - clock.now()).total_seconds())
            if timeout <= 0:
                return Failure("timeout", tuple(ids), "the deadline passed")
        # Every attempt first holds its worst-case cost on the budget row (Story 2.8).
        held = await _reserve(call, worst)
        if held is None:
            detail = (
                "the budget was spent during the call"
                if number > 1
                else f"budget {call.scope.kind} {call.scope.id} is spent"
            )
            return Failure("budget_exhausted", tuple(ids), detail)
        try:
            last = await _attempt(call, model, output_schema, timeout)
        except _Cancelled as cancelled:
            try:
                # Shielded: a second cancel (shutdown) does not roll the row back.
                await asyncio.shield(_log(call, number, cancelled.attempt, held))
            finally:
                raise cancelled.original
        except BaseException:
            await asyncio.shield(budget.release(held))
            raise
        if last.rate_limited:
            # Back-off inside the deadline, not an attempt: no row, the number is not used up,
            # and the reservation is given back.
            await asyncio.shield(budget.release(held))
            limited += 1
            wait = last.retry_after_s
            if wait is None:
                wait = 2.0 ** (limited - 1)
            wait = min(max(wait, BACK_OFF_MIN_S), BACK_OFF_MAX_S)
            log.warning("llm_rate_limited", endpoint=spec.endpoint, wait_s=wait, attempt=number)
            if deadline is None and limited >= RATE_LIMITED_MAX:
                return Failure("provider_error", tuple(ids), f"rate limited {limited} times")
            if deadline is not None:
                left = (deadline - clock.now()).total_seconds()
                if wait >= left - (call.level.attempt_timeout_s if number > 1 else 0):
                    return Failure("timeout", tuple(ids), "rate limited until the deadline")
            if paced:
                ratelimit.limiter.back_off(key, spec.rate_limit_rpm, wait)
            else:
                await clock.sleep(wait)
            continue
        limited = 0
        ids.append(await asyncio.shield(_log(call, number, last, held)))
        if last.output is not None:
            return Result(last.output, tuple(ids), call.offset_maps)  # type: ignore[arg-type]
        if last.final:
            break
        number += 1
    assert last is not None and last.outcome != "ok"
    return Failure(last.outcome, tuple(ids), last.error or last.outcome)
