"""Story 2.7: the `openai_compatible` adapter, router preferences, availability and HTTP 429
back-off, against a fake HTTP transport (AD-6, FR-68, NFR-3, C-1, AD-17). No test reaches a
real endpoint: `tests/conftest.py` refuses every request a test does not answer itself."""

import json
import uuid
from datetime import timedelta
from decimal import Decimal

import httpx2
import pytest
from pydantic import BaseModel, Field

from app.ai import adapters, budget, config, gateway, models, ratelimit
from app.ai.gateway import Failure, Inputs, Result
from tests.ai.helpers import mock_config, query

ENDPOINT = "https://router.example.test/api/v1"
MODEL = "deepseek/deepseek-v4.1-flash-1017"
KEY_ENV = "OLSPILLET_TEST_KEY"
KEY = "test-key-not-real"
ROUTING = {"router": "openrouter", "order": ["nebius/fp8"], "require_parameters": True}


class Order(BaseModel):
    order: int = Field(ge=0, le=999)


def completion(content: str = '{"order": 7}', **extra: object) -> dict:
    return {
        "id": "gen-1",
        "object": "chat.completion",
        "created": 1_790_000_000,
        "model": MODEL,
        "provider": "Nebius",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 1000, "completion_tokens": 100, "total_tokens": 1100},
        **extra,
    }


class FakeEndpoint:
    """An OpenAI-compatible endpoint: answers each request with the next queued response (a
    status and JSON body, optional headers), then with a valid completion; records requests."""

    def __init__(self, *responses: tuple[int, object, dict[str, str]]) -> None:
        self.responses = list(responses)
        self.requests: list[httpx2.Request] = []
        self.started: list[float] = []

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        self.started.append(ratelimit.clock.monotonic())
        if request.url.path.endswith("/models"):
            return httpx2.Response(200, json={"object": "list", "data": [{"id": MODEL}]})
        status, body, headers = self.responses.pop(0) if self.responses else (200, None, {})
        return httpx2.Response(status, json=body or completion(), headers=headers)

    def bodies(self) -> list[dict]:
        return [json.loads(r.content) for r in self.requests if r.method == "POST"]


@pytest.fixture
def endpoint(monkeypatch):
    monkeypatch.setenv(KEY_ENV, KEY)
    fake = FakeEndpoint()
    with adapters.use_transport(httpx2.MockTransport(fake.handle)):
        yield fake


@pytest.fixture
def template(prompts):
    (prompts / "player_order" / "v1.md").write_text("Stock: $stock units.", encoding="utf-8")


def real_config(**changes: object) -> dict:
    data = {
        "provider": "openai_compatible",
        "endpoint": ENDPOINT,
        "region": "eu",
        "model_version": MODEL,
        "credential_env": KEY_ENV,
        "routing": ROUTING,
        "effort_levels": [
            {
                "name": "standard",
                "provider_params": {"reasoning": {"effort": "low"}, "seed": 3},
                "attempt_timeout_s": 4,
                "order_time_budget_s": 8,
            }
        ],
    }
    data.update(changes)
    data.setdefault("prompts", {"player_order": 1})
    return mock_config(**data)


async def real_scope(**changes: object) -> budget.BudgetScope:
    row = await config.add(config.parse(real_config(**changes)))
    scope = budget.BudgetScope.evaluation(row.id)
    await budget.set_budget(scope, limit=Decimal(1), reserve=Decimal(0))
    return scope


INPUTS = Inputs(values={"stock": 12}, caller={"game": uuid.uuid7(), "week": 2})


async def call(scope, deadline_s: float | None = 8.0):
    deadline = None
    if deadline_s is not None:
        deadline = ratelimit.clock.now() + timedelta(seconds=deadline_s)
    return await gateway.run("player_order", scope, INPUTS, Order, deadline)


def rows(url: str) -> list[dict]:
    names = [c.name for c in models.llm_calls.c]
    found = query(url, f"SELECT {', '.join(names)} FROM llm_call ORDER BY started_at, attempt")
    return [dict(zip(names, row, strict=True)) for row in found]


async def test_a_real_call_sends_the_routing_switches_and_logs_what_served_it(
    ai_db, template, endpoint
):
    scope = await real_scope()
    result = await call(scope)
    assert isinstance(result, Result) and result.output == Order(order=7)
    [request] = endpoint.requests
    assert str(request.url) == f"{ENDPOINT}/chat/completions"
    assert request.headers["authorization"] == f"Bearer {KEY}"
    [body] = endpoint.bodies()
    assert body["model"] == MODEL
    # Router fallback off, zero retention and no data collection, always (FR-68, C-1).
    assert body["provider"] == {
        "order": ["nebius/fp8"],
        "require_parameters": True,
        "allow_fallbacks": False,
        "data_collection": "deny",
        "zdr": True,
    }
    assert "models" not in body and "route" not in body
    assert body["reasoning"] == {"effort": "low"} and body["seed"] == 3
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["schema"]["properties"]["order"]
    [row] = rows(ai_db)
    assert (row["outcome"], row["attempt"]) == ("ok", 1)
    assert (row["served_model"], row["served_by"]) == (MODEL, "Nebius")
    assert (row["input_tokens"], row["output_tokens"]) == (1000, 100)
    assert row["provider"] == "openai_compatible" and row["endpoint"] == ENDPOINT
    # The stored request shows what was sent, routing included; never the key.
    assert row["request"]["model_settings"]["extra_body"]["provider"]["zdr"] is True
    assert KEY not in json.dumps(row, default=str)


async def test_an_invalid_real_answer_is_an_attempt_like_any_other(ai_db, template, endpoint):
    endpoint.responses = [(200, completion('{"order": "seven"}'), {})]
    scope = await real_scope()
    result = await call(scope)
    assert isinstance(result, Result)
    assert [row["outcome"] for row in rows(ai_db)] == ["invalid_output", "ok"]


async def test_a_429_is_back_off_not_an_attempt(ai_db, template, endpoint):
    endpoint.responses = [(429, {"error": {"message": "rate limited"}}, {"retry-after": "2"})]
    scope = await real_scope()
    result = await call(scope)
    assert isinstance(result, Result)
    [row] = rows(ai_db)
    assert (row["attempt"], row["outcome"]) == (1, "ok")
    first, second = endpoint.started
    assert second - first >= 2  # waited the endpoint's Retry-After, in virtual time
    assert ratelimit.limiter.stats(adapters.endpoint_key(config.parse(real_config())))[0] == 1


async def test_429s_until_the_deadline_end_in_timeout_with_no_row(ai_db, template, endpoint):
    endpoint.responses = [(429, {"error": {"message": "busy"}}, {})] * 20
    scope = await real_scope()
    result = await call(scope, deadline_s=8.0)
    assert isinstance(result, Failure) and result.kind == "timeout"
    assert result.llm_call_ids == () and rows(ai_db) == []
    assert len(endpoint.requests) == 4  # waits of 1, 2 and 4 s; the next 8 s does not fit


async def test_429s_without_a_deadline_give_up_as_a_provider_error(ai_db, template, endpoint):
    endpoint.responses = [(429, {"error": {"message": "busy"}}, {})] * 20
    scope = await real_scope()
    result = await call(scope, deadline_s=None)
    assert isinstance(result, Failure) and result.kind == "provider_error"
    assert result.detail == f"rate limited {gateway.RATE_LIMITED_MAX} times"
    assert rows(ai_db) == [] and len(endpoint.requests) == gateway.RATE_LIMITED_MAX


async def test_the_endpoints_model_list_is_read_with_the_key(endpoint):
    spec = config.parse(real_config())
    assert await adapters.list_models(spec) == [MODEL]
    [request] = endpoint.requests
    assert str(request.url) == f"{ENDPOINT}/models"
    assert request.headers["authorization"] == f"Bearer {KEY}"


@pytest.mark.parametrize(
    ("routing", "field"),
    [
        ({**ROUTING, "allow_fallbacks": True}, "routing.allow_fallbacks"),
        ({**ROUTING, "data_collection": "allow"}, "routing.data_collection"),
        ({**ROUTING, "zdr": False}, "routing.zdr"),
        ({**ROUTING, "models": ["other/model"]}, "routing.models"),
        ({**ROUTING, "router": "elsewhere"}, "routing.router"),
    ],
)
def test_routing_that_would_allow_fallback_or_retention_is_refused(routing, field):
    with pytest.raises(config.ConfigInvalid) as caught:
        config.parse(real_config(routing=routing))
    assert field in [error.field for error in caught.value.errors]


def test_the_forced_switches_may_be_stated_and_reserved_params_are_refused(prompts):
    stated = {**ROUTING, "allow_fallbacks": False, "data_collection": "deny", "zdr": True}
    assert config.parse(real_config(routing=stated)).routing.zdr is True
    level = {"name": "x", "attempt_timeout_s": 1, "order_time_budget_s": 2}
    reserved = ("provider", "models", "route", "model", "messages", "response_format")
    for param in (*reserved, "max_tokens", "max_completion_tokens"):
        with pytest.raises(config.ConfigInvalid) as caught:
            config.parse(real_config(effort_levels=[{**level, "provider_params": {param: 1}}]))
        assert [e.code for e in caught.value.errors] == ["param_reserved"]
    with pytest.raises(config.ConfigInvalid) as caught:
        config.parse(mock_config(routing=ROUTING))
    assert [e.code for e in caught.value.errors] == ["routing_unused"]


def test_a_config_without_routing_sends_no_provider_object(prompts):
    spec = config.parse(real_config(routing=None))
    assert adapters.model_settings(spec, spec.effort_levels[0]) == {
        "max_tokens": 4096,
        "seed": 3,
        "extra_body": {"reasoning": {"effort": "low"}},
    }


@pytest.mark.parametrize(
    ("provider", "app_env", "key", "expected"),
    [
        ("mock", "local", None, ("mock", "the config's provider is the mock")),
        ("real", "test", None, ("mock", f"{KEY_ENV} is not set")),
        ("real", "ci", "k", ("real", None)),
        ("real", "production", "k", ("real", None)),
        ("real", "production", None, ("refused", f"the key variable {KEY_ENV} is not set")),
        (
            "mock",
            "production",
            None,
            ("refused", "the mock provider is never used with APP_ENV=production"),
        ),  # noqa: E501
    ],
)
def test_availability(prompts, provider, app_env, key, expected):
    spec = config.parse(mock_config() if provider == "mock" else real_config())
    environ = {} if key is None else {KEY_ENV: key}
    found = adapters.availability(spec, app_env, environ)
    assert (found.kind, found.reason) == expected


def test_retry_after_reads_seconds_and_http_dates():
    from pydantic_ai import ModelHTTPError

    def error(value: str | None) -> ModelHTTPError:
        return ModelHTTPError(429, MODEL, headers=None if value is None else {"retry-after": value})

    assert adapters.retry_after(error("3")) == 3.0
    assert adapters.retry_after(error(None)) is None
    assert adapters.retry_after(error("soon")) is None
    assert adapters.retry_after(error("inf")) is None and adapters.retry_after(error("nan")) is None
    later = ratelimit.clock.now() + timedelta(seconds=30)
    stamp = later.strftime("%a, %d %b %Y %H:%M:%S GMT")
    assert 28 <= adapters.retry_after(error(stamp)) <= 30


async def test_a_long_retry_after_is_cut_to_the_back_off_maximum(ai_db, template, endpoint):
    endpoint.responses = [(429, {"error": {"message": "busy"}}, {"retry-after": "3600"})]
    scope = await real_scope()
    result = await call(scope, deadline_s=None)
    assert isinstance(result, Result)
    first, second = endpoint.started
    assert round(second - first) == gateway.BACK_OFF_MAX_S


async def test_an_error_asking_again_cannot_fix_stops_the_call(ai_db, template, endpoint):
    endpoint.responses = [(401, {"error": {"message": "no auth"}}, {})] * 3
    scope = await real_scope()
    result = await call(scope)
    assert isinstance(result, Failure) and result.kind == "provider_error"
    [row] = rows(ai_db)
    assert (row["attempt"], row["outcome"]) == (1, "provider_error")
    endpoint.responses = [(500, {"error": {"message": "down"}}, {})]
    assert isinstance(await call(scope), Result)  # a 5xx is an attempt; the next one answers


async def test_a_paced_retry_waits_for_its_slot_only_when_a_whole_attempt_still_fits(
    ai_db, template, endpoint
):
    """The retry rule (NFR-2) holds for the rate limiter's wait: attempt 2 needs its slot
    plus its whole 4 s timeout before the deadline."""
    endpoint.responses = [(200, completion('{"order": "seven"}'), {})]
    scope = await real_scope(rate_limit_rpm=10)  # one request per 6 s
    result = await call(scope, deadline_s=8.0)  # slot at 6 s leaves 2 s < 4 s
    [row] = rows(ai_db)
    assert result == Failure("timeout", (row["id"],), "no request slot before the deadline")
    assert len(endpoint.requests) == 1


async def test_a_429_on_a_retry_needs_room_for_a_whole_attempt(ai_db, template, endpoint):
    endpoint.responses = [
        (200, completion('{"order": "seven"}'), {}),
        (429, {"error": {"message": "busy"}}, {"retry-after": "5"}),
    ]
    scope = await real_scope()
    result = await call(scope, deadline_s=8.0)  # a 5 s wait leaves under 4 s
    [row] = rows(ai_db)
    assert result == Failure("timeout", (row["id"],), "rate limited until the deadline")
    assert len(endpoint.requests) == 2


def test_a_router_endpoint_without_routing_is_refused(prompts):
    with pytest.raises(config.ConfigInvalid) as caught:
        config.parse(real_config(endpoint="https://eu.openrouter.ai/api/v1", routing=None))
    assert [(e.code, e.field) for e in caught.value.errors] == [("routing_missing", "routing")]
    # A row stored before routing existed is never sent without the switches.
    stored = config.parse(real_config(routing=None)).model_copy(
        update={"endpoint": "https://openrouter.ai/api/v1"}
    )
    found = adapters.availability(stored, "production", {KEY_ENV: "k"})
    assert (found.kind, found.reason) == (
        "refused",
        "the endpoint is a openrouter router but has no routing",
    )
