"""Provider adapters and router preferences (AD-6, FR-68, C-1, AD-17).

`ADAPTERS` maps a config's `provider` to the code that builds its pydantic-ai model, and
`ROUTERS` maps `routing.router` to the request fields that router reads. These two tables are
the only place a provider or router is named in code: everything else (base URL, region,
upstream provider, prices, rate limit) comes from the model config. Adding a provider is one
entry here and one config row.

`openai_compatible` speaks the OpenAI chat API at the config's base URL (for example an EU
in-region router), with the key from the variable the config names and the SDK's own retries
off: the gateway owns attempts and 429 back-off. Tests swap the HTTP transport with
`use_transport`; `tests/conftest.py` installs one that refuses every request.
"""

import asyncio
import math
import os
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any, Literal
from urllib.parse import urlsplit

import httpx2
from openai import AsyncOpenAI
from openai.types import chat
from pydantic_ai import ModelHTTPError
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.ai import config, ratelimit

MOCK_ENVS = ("local", "test", "ci")
"""The environments where the mock answers when no provider key is set (AD-17)."""

UPSTREAM = "upstream_provider"
"""The `provider_details` key holding the upstream provider a router reports."""


# --- Router preferences -------------------------------------------------------------------


def _openrouter(routing: config.Routing) -> dict[str, Any]:
    """OpenRouter's `provider` object: the configured preferences, then the switches that are
    always on. `allow_fallbacks: false` keeps the request on the configured providers,
    `data_collection: deny` and `zdr: true` keep it on endpoints that neither store nor train
    on prompts (FR-68, C-1). No `models` list or `route` is ever sent."""
    preferences = routing.model_dump(exclude_none=True, exclude={"router"})
    return {
        "provider": {
            **preferences,
            "allow_fallbacks": False,
            "data_collection": "deny",
            "zdr": True,
        }
    }


ROUTERS: dict[str, Callable[[config.Routing], dict[str, Any]]] = {"openrouter": _openrouter}

ROUTER_HOSTS: dict[str, tuple[str, ...]] = {"openrouter": ("openrouter.ai",)}
"""The hosts (and their subdomains) of each router: a config whose endpoint is one of them must
carry `routing`, so the switches above are always sent (FR-68, C-1)."""


def router_without_routing(spec: config.ModelConfigSpec) -> str | None:
    """The router a config's endpoint belongs to when the config has no `routing`, else None."""
    if spec.routing is not None:
        return None
    host = (urlsplit(spec.endpoint).hostname or "").lower()
    for router, hosts in ROUTER_HOSTS.items():
        if any(host == known or host.endswith("." + known) for known in hosts):
            return router
    return None


def model_settings(spec: config.ModelConfigSpec, level: config.EffortLevel) -> dict[str, Any]:
    """The model settings of every attempt: seed and temperature from the Effort level where it
    sets them; its other provider params and the router preferences as `extra_body`."""
    params = level.provider_params
    settings: dict[str, Any] = {}
    seed = params.get("seed")
    if isinstance(seed, int) and not isinstance(seed, bool):
        settings["seed"] = seed
    temperature = params.get("temperature")
    if isinstance(temperature, int | float) and not isinstance(temperature, bool):
        settings["temperature"] = float(temperature)
    extra = {
        name: value
        for name, value in params.items()
        if name not in ("seed", "temperature") and name not in config.RESERVED_PARAMS
    }
    if spec.routing is not None:
        extra.update(ROUTERS[spec.routing.router](spec.routing))
    if extra:
        settings["extra_body"] = extra
    return settings


# --- Which model answers --------------------------------------------------------------------


@dataclass(frozen=True)
class Availability:
    """`mock`: the mock answers (`reason` says why); `real`: the adapter calls the endpoint;
    `refused`: no model may answer (`reason` says why)."""

    kind: Literal["mock", "real", "refused"]
    reason: str | None = None
    missing_key: str | None = None
    """The key variable that is not set, when that is the reason."""


def availability(
    spec: config.ModelConfigSpec, app_env: str, environ: Mapping[str, str] | None = None
) -> Availability:
    environ = os.environ if environ is None else environ
    key_set = bool(spec.credential_env and environ.get(spec.credential_env))
    if app_env in MOCK_ENVS:
        if spec.provider == "mock":
            return Availability("mock", "the config's provider is the mock")
        if not key_set:
            return Availability("mock", f"{spec.credential_env} is not set", spec.credential_env)
    elif spec.provider == "mock":
        return Availability("refused", f"the mock provider is never used with APP_ENV={app_env}")
    elif not key_set:
        return Availability(
            "refused", f"the key variable {spec.credential_env} is not set", spec.credential_env
        )
    if spec.provider not in ADAPTERS:
        return Availability("refused", f"no adapter for provider {spec.provider}")
    router = router_without_routing(spec)
    if router is not None:
        # A row stored before routing existed: never send it without the switches.
        return Availability("refused", f"the endpoint is a {router} router but has no routing")
    return Availability("real")


# --- openai_compatible -----------------------------------------------------------------------


_transport: httpx2.AsyncBaseTransport | None = None
_clients: dict[tuple[object, ...], AsyncOpenAI] = {}


@contextmanager
def use_transport(transport: httpx2.AsyncBaseTransport | None) -> Iterator[None]:
    """Send every adapter request through `transport` while the block runs (tests)."""
    global _transport
    before, _transport = _transport, transport
    try:
        yield
    finally:
        _transport = before


def _client(spec: config.ModelConfigSpec) -> AsyncOpenAI:
    assert spec.credential_env is not None  # `config.parse` requires it for this adapter
    key = os.environ.get(spec.credential_env, "")
    cache_key = (spec.endpoint, key, id(_transport), id(asyncio.get_running_loop()))
    client = _clients.get(cache_key)
    if client is None:
        http_client = None if _transport is None else httpx2.AsyncClient(transport=_transport)
        client = AsyncOpenAI(
            base_url=spec.endpoint, api_key=key, max_retries=0, http_client=http_client
        )
        _clients[cache_key] = client
    return client


class _ChatModel(OpenAIChatModel):
    """The OpenAI chat model, also keeping the upstream provider a router reports."""

    def _process_provider_details(self, response: chat.ChatCompletion) -> dict[str, Any] | None:
        details = dict(super()._process_provider_details(response) or {})
        upstream = (response.model_extra or {}).get("provider")
        if isinstance(upstream, str) and upstream:
            details[UPSTREAM] = upstream
        return details or None


def _openai_compatible(spec: config.ModelConfigSpec) -> Model:
    provider = OpenAIProvider(openai_client=_client(spec))
    return _ChatModel(spec.model_version, provider=provider)


ADAPTERS: dict[str, Callable[[config.ModelConfigSpec], Model]] = {
    "openai_compatible": _openai_compatible
}


def build_model(spec: config.ModelConfigSpec) -> Model:
    """The real model of a config whose availability is `real`."""
    return ADAPTERS[spec.provider](spec)


async def list_models(spec: config.ModelConfigSpec) -> list[str]:
    """The model ids the endpoint lists (`GET {endpoint}/models`), for the endpoint probe."""
    page = await _client(spec).models.list()
    return [item.id for item in page.data]


def endpoint_key(spec: config.ModelConfigSpec) -> tuple[str, str]:
    """The limiter key: one schedule per base URL and key variable."""
    return spec.endpoint, spec.credential_env or ""


# --- HTTP 429 ---------------------------------------------------------------------------------


def rate_limited(exc: BaseException) -> bool:
    return isinstance(exc, ModelHTTPError) and exc.status_code == 429


RETRYABLE_4XX = frozenset({408, 409, 425, 429})


def final(exc: BaseException) -> bool:
    """An HTTP error that asking again cannot fix (a bad key, a bad request, no endpoint for
    the routing): the call stops instead of using up its attempts."""
    return (
        isinstance(exc, ModelHTTPError)
        and 400 <= exc.status_code < 500
        and exc.status_code not in RETRYABLE_4XX
    )


def retry_after(exc: ModelHTTPError) -> float | None:
    """Seconds the endpoint asked to wait (`Retry-After`, seconds or an HTTP date), if any."""
    if exc.retry_after is not None:
        seconds = float(exc.retry_after)
        return max(seconds, 0.0) if math.isfinite(seconds) else None
    value = (exc.headers or {}).get("retry-after")
    if not value:
        return None
    try:
        seconds = float(value)
    except ValueError:
        pass
    else:
        return max(seconds, 0.0) if math.isfinite(seconds) else None
    try:
        when = parsedate_to_datetime(value)
    except TypeError, ValueError:
        return None
    return max((when - ratelimit.clock.now()).total_seconds(), 0.0)
