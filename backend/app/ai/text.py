"""AI text with a code fallback (Story 9.14, FR-44, AD-6, AD-7): `worded`.

The shared helper every facts-only text goes through (the Debrief's narration and quiz lines,
later the follow-up answers, the Replay walkthrough and Adapted items). It makes one call through
`gateway.run` and hands the validated output to the caller's `validate`, which renders it by code
and returns the text, or None to reject it. Every other outcome — a `GatewayError` (a config
without the purpose's prompt, no budget row), a typed `Failure` (`timeout`, `invalid_output`,
`budget_exhausted`, `provider_error`), a rejection or any other exception — gives the caller's
`fallback` text with `ai_generated` false and no `llm_call_id`. The call is never retried here.

The caller passes its own validator and fallback renderer, so this module imports only `platform`
and `app.ai` (AD-6). `can_word` (Story 9.15) says whether a purpose could be answered at all on a
model config, for a caller that shows a field only then (the follow-up questions).
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

import structlog
from pydantic import BaseModel

from app.ai import adapters, budget, config, gateway, mock
from app.platform.config import get_settings

__all__ = ["AiText", "can_word", "provider_failing", "worded"]

log = structlog.get_logger(__name__)

provider_failing = mock.outage_here
"""Local dev and tests only: while the block runs, the mock provider fails every attempt made in
the calling task (a `provider_error`), so a caller's fallback text is what `worded` gives; calls
other requests make meanwhile are not affected (Story 9.15). A real provider is never affected
(AD-17)."""


@dataclass(frozen=True)
class AiText:
    """`{text, ai_generated, llm_call_id}`: how AI text travels (AD-7). `ai_generated` alone
    decides the «KI-generert, kan ta feil:» marking."""

    text: str
    ai_generated: bool
    llm_call_id: uuid.UUID | None


async def can_word(purpose: str, model_config_id: uuid.UUID | str | None) -> bool:
    """Whether a call of `purpose` on that model config could be made at all (Story 9.15, FR-15):
    the config exists, names a prompt for the purpose, and a provider may answer here (the mock in
    local, test and ci; a real provider only with its key set). A caller that shows a field only
    when an answer is possible asks this first; it says nothing about the budget."""
    if model_config_id is None:
        return False
    try:
        found = await config.get(uuid.UUID(str(model_config_id)))
    except ValueError:
        return False
    if found is None or purpose not in found.spec.prompts:
        return False
    return adapters.availability(found.spec, get_settings().app_env).kind != "refused"


async def worded[T: BaseModel](
    purpose: str,
    budget_scope: budget.BudgetScope,
    inputs: gateway.Inputs,
    output_schema: type[T],
    *,
    validate: Callable[[T], str | None],
    fallback: Callable[[], str],
    deadline: datetime | None = None,
) -> AiText:
    """The LLM's text when the call succeeds and `validate` accepts its output (the text
    `validate` rendered, with the id of the call's last `llm_call` row), else `fallback()`."""
    try:
        result = await gateway.run(purpose, budget_scope, inputs, output_schema, deadline)
    except gateway.GatewayError as exc:
        log.warning("ai_text_not_prepared", purpose=purpose, code=exc.code)
        return AiText(fallback(), False, None)
    except Exception as exc:  # the type only: never raised to the caller, never retried
        log.error("ai_text_call_failed", purpose=purpose, exc_type=type(exc).__name__)
        return AiText(fallback(), False, None)
    if isinstance(result, gateway.Failure):
        log.info("ai_text_fallback", purpose=purpose, kind=result.kind)
        return AiText(fallback(), False, None)
    try:
        text = validate(result.output)
    except Exception as exc:
        log.error("ai_text_validation_failed", purpose=purpose, exc_type=type(exc).__name__)
        text = None
    if text is None:
        log.info("ai_text_rejected", purpose=purpose)
        return AiText(fallback(), False, None)
    return AiText(text, True, result.llm_call_ids[-1])
