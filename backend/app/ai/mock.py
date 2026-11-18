"""The deterministic mock provider (AD-17).

Used with no provider key in `local`, `test` and `ci`, never in `production`. It answers with
the caller's mock answer (for a player Order, the stored Rule-based reference Order) as JSON,
or else with a fixed answer built from the output schema, so the same inputs always give the
same output. Tests script misbehaviour with `script(...)`: each step is used by one attempt.
"""

import asyncio
import json
from collections import deque
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from pydantic import BaseModel
from pydantic_ai import ModelHTTPError, ModelResponse, TextPart
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models.function import AgentInfo, FunctionModel

TIMEOUT = "timeout"
"""Step: the attempt hangs until the gateway's timeout cancels it."""
INVALID = "invalid"
"""Step: the answer is not JSON."""
ERROR = "error"
"""Step: the provider fails (HTTP 500)."""

_steps: deque[str] = deque()

last_model_settings: dict[str, Any] | None = None
"""The model settings (seed, temperature) the last mock attempt received, for tests."""


@contextmanager
def script(*steps: str) -> Iterator[None]:
    """Make the next attempts follow `steps` in order (`TIMEOUT`, `INVALID`, `ERROR`, or any
    other text, sent as the raw answer); after the last step the mock answers normally."""
    _steps.clear()
    _steps.extend(steps)
    try:
        yield
    finally:
        _steps.clear()


def _resolve(schema: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    ref = node.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/$defs/"):
        return _resolve(schema, schema.get("$defs", {})[ref.removeprefix("#/$defs/")])
    return node


def _value(schema: dict[str, Any], node: dict[str, Any]) -> Any:
    node = _resolve(schema, node)
    if "const" in node:
        return node["const"]
    if node.get("enum"):
        return node["enum"][0]
    for combinator in ("anyOf", "oneOf", "allOf"):
        if node.get(combinator):
            return _value(schema, node[combinator][0])
    kind = node.get("type")
    if isinstance(kind, list):
        kind = next((k for k in kind if k != "null"), "null")
    if kind in ("integer", "number"):
        low = node.get("minimum", node.get("exclusiveMinimum"))
        if low is None:
            return 0
        if "exclusiveMinimum" in node and "minimum" not in node:
            return int(low) + 1 if kind == "integer" else low + 1
        return low
    if kind == "string":
        return "x" * node.get("minLength", 0)
    if kind == "boolean":
        return False
    if kind == "array":
        return [_value(schema, node.get("items", {})) for _ in range(node.get("minItems", 0))]
    if kind == "object" or "properties" in node:
        properties = node.get("properties", {})
        return {name: _value(schema, properties[name]) for name in node.get("required", [])}
    return None


def fixed_answer(output_schema: type[BaseModel]) -> dict[str, Any]:
    """A deterministic answer that fits the schema of the usual kind (required fields only)."""
    schema = output_schema.model_json_schema()
    return _value(schema, schema)


def model(mock_answer: Any, output_schema: type[BaseModel], model_name: str) -> FunctionModel:
    """The mock as a pydantic-ai model for one attempt."""
    if isinstance(mock_answer, BaseModel):
        answer = mock_answer.model_dump_json()
    elif mock_answer is not None:
        answer = json.dumps(mock_answer, default=str)
    else:
        answer = json.dumps(fixed_answer(output_schema))

    async def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        global last_model_settings
        last_model_settings = dict(info.model_settings or {})
        step = _steps.popleft() if _steps else None
        if step == TIMEOUT:
            await asyncio.Event().wait()  # never set: only the gateway's timeout ends it
        if step == ERROR:
            raise ModelHTTPError(500, model_name, body={"error": "mock provider error"})
        if step == INVALID:
            return ModelResponse(parts=[TextPart("not json")])
        return ModelResponse(parts=[TextPart(answer if step is None else step)])

    return FunctionModel(respond, model_name=model_name)
