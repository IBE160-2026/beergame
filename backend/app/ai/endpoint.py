"""Checking a real endpoint by hand (Story 2.7): `python -m app.sim endpoint` builds the
requests from stored Seat states and prints what `probe` returns.

`probe` makes a few real calls through the gateway (each logged and charged to the config's
evaluation budget like any other) and reports whether the endpoint lists the model, what model
and upstream provider served each answer, whether the answers were valid Orders, latency, cost,
and how the rate limiter and HTTP 429 behaved under a burst of calls at once.
"""

import asyncio
import json
import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from pydantic import BaseModel

from app.ai import adapters, budget, calls, config, gateway, ratelimit
from app.platform.config import get_settings

Request = tuple[gateway.Inputs, type[BaseModel]]
"""One call's gateway inputs and output schema."""


async def availability(config_id: str) -> adapters.Availability | None:
    """Whether the config's calls go to the mock, to the endpoint, or nowhere, in this
    environment; None when there is no such config."""
    found = await config.get(config_id)
    if found is None:
        return None
    return adapters.availability(found.spec, get_settings().app_env)


def served_matches(model_version: str, served: str | None) -> bool:
    """The served model id is the pinned one: the same id, or the same model whose dated
    snapshot ends with the pinned suffix (`…-1017` served as `…-20261017`)."""
    if served is None:
        return False
    if served == model_version:
        return True
    base, _, suffix = model_version.rpartition("-")
    served_base, _, served_suffix = served.rpartition("-")
    if not base or served_base != base or not suffix.isdigit():
        return False
    # A dated snapshot: the pinned MMDD served as YYYYMMDD.
    return len(suffix) == 4 and len(served_suffix) == 8 and served_suffix[4:] == suffix


@dataclass(frozen=True)
class _Outcome:
    result: gateway.Result | gateway.Failure
    attempts: list[calls.Attempt]


async def _one(scope: budget.BudgetScope, request: Request, budget_s: float) -> _Outcome:
    inputs, schema = request
    deadline = ratelimit.clock.now() + timedelta(seconds=budget_s)
    result = await gateway.run("player_order", scope, inputs, schema, deadline)
    return _Outcome(result, await calls.get(result.llm_call_ids))


def _line(index: int, outcome: _Outcome) -> str:
    last = outcome.attempts[-1] if outcome.attempts else None
    head = f"order {index}"
    if isinstance(outcome.result, gateway.Failure):
        head += f" failure {outcome.result.kind}: {outcome.result.detail}"
    else:
        head += f" ok order={getattr(outcome.result.output, 'order', '?')}"
    if last is None:
        return head + " attempts=0"
    cost = sum((a.cost_usd for a in outcome.attempts), Decimal(0))
    return (
        f"{head} attempts={len(outcome.attempts)} served={last.served_model or '-'} "
        f"by={last.served_by or '-'} latency_ms={last.latency_ms} "
        f"tokens={last.input_tokens}/{last.output_tokens} cost_usd={cost}"
    )


async def probe(config_id: str, requests: Sequence[Request], burst: int) -> tuple[bool, list[str]]:
    """Run the checks; returns whether all passed and the report lines. `requests` are sent
    one after another; then `burst` calls (cycling through `requests`) are sent at once.
    Raises `gateway.GatewayError` when a call cannot be prepared (no budget, no prompt)."""
    found = await config.get(config_id)
    if found is None:
        raise gateway.GatewayError("config_not_found", f"no model config {config_id}")
    spec = found.spec
    level = spec.effort_levels[0]
    scope = budget.BudgetScope.evaluation(found.id)
    settings = adapters.model_settings(spec, level)
    routing = settings.get("extra_body", {}).get("provider")
    lines = [
        f"config {found.id} {spec.name}",
        f"endpoint {spec.endpoint} region {spec.region} model {spec.model_version} "
        f"quantisation {spec.quantisation}",
        f"routing {json.dumps(routing, sort_keys=True) if routing else 'none'}",
        f"rate_limit_rpm {spec.rate_limit_rpm} effort_level {level.name} "
        f"attempt_timeout_s {level.attempt_timeout_s} order_time_budget_s "
        f"{level.order_time_budget_s}",
    ]
    problems: list[str] = []
    try:
        listed = await adapters.list_models(spec)
    except Exception as exc:  # any failure of the listing is reported, not raised
        lines.append(f"model_listed error {type(exc).__name__}: {str(exc)[:200]}")
        problems.append("model list not read")
    else:
        ok = spec.model_version in listed
        lines.append(f"model_listed {'yes' if ok else 'no'} ({len(listed)} models)")
        if not ok:
            problems.append("model not listed")

    outcomes: list[_Outcome] = []
    for index, request in enumerate(requests, start=1):
        outcome = await _one(scope, request, level.order_time_budget_s)
        outcomes.append(outcome)
        lines.append(_line(index, outcome))
    key = adapters.endpoint_key(spec)
    limited_before, _ = ratelimit.limiter.stats(key)
    burst_outcomes = await asyncio.gather(
        *(_one(scope, requests[i % len(requests)], level.order_time_budget_s) for i in range(burst))
    )
    limited_after, longest_wait = ratelimit.limiter.stats(key)
    burst_ok = sum(isinstance(o.result, gateway.Result) for o in burst_outcomes)
    lines.append(
        f"burst {burst} ok={burst_ok} rate_limited={limited_after - limited_before} "
        f"longest_slot_wait_s={longest_wait:.1f} (whole run)"
    )

    every = [*outcomes, *burst_outcomes]
    failed = sum(isinstance(o.result, gateway.Failure) for o in every)
    if failed:
        problems.append(f"{failed} of {len(every)} calls failed")
    attempts = [a for o in every for a in o.attempts]
    served = {a.served_model for a in attempts if a.outcome == "ok"}
    wrong = sorted(str(s) for s in served if not served_matches(spec.model_version, s))
    lines.append(
        "served_model "
        + (", ".join(sorted(str(s) for s in served)) or "-")
        + (" (differs from the config)" if wrong else "")
    )
    lines.append("served_by " + (", ".join(sorted({a.served_by or "-" for a in attempts})) or "-"))
    if wrong:
        problems.append("served model differs")
    latencies = [a.latency_ms for a in attempts if a.outcome == "ok"]
    if latencies:
        lines.append(
            f"latency_ms median={statistics.median(latencies):.0f} max={max(latencies)} "
            f"(ok attempts {len(latencies)})"
        )
    total = sum((a.cost_usd for a in attempts), Decimal(0))
    tokens_in = sum(a.input_tokens for a in attempts)
    tokens_out = sum(a.output_tokens for a in attempts)
    lines.append(f"cost_usd total={total} attempts={len(attempts)} tokens={tokens_in}/{tokens_out}")
    lines.append("endpoint ok" if not problems else "endpoint failed: " + "; ".join(problems))
    return not problems, lines
