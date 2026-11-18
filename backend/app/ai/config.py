"""Model configs (`ai.config`, AD-6, FR-68, FR-78, NFR-2).

A model config pins one provider, endpoint, region, model version and quantisation, its prices
and rate limit, a `prompts` map from purpose to prompt version, and its Effort levels as data.
A row never changes once a Class session or a simulation run references it (a trigger refuses
it); an edit always writes a new row (`derive`). Credentials are never stored: a config names
only the environment variable that holds the key.

Other modules read and change model configs only through this module (AD-6).
"""

import re
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Any, Literal
from urllib.parse import parse_qsl, urlsplit

from pydantic import BaseModel, ConfigDict, Field, StrictInt, ValidationError
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.db import transaction
from app.ai.models import model_configs

PROMPTS_DIR = Path(__file__).parent / "prompts"
"""Prompt files live at `prompts/<purpose>/v<N>.md` (AD-6)."""

PURPOSE_PATTERN = r"^[a-z][a-z0-9_]*$"

# A key with one of these names (after lower-casing and `-` → `_`), or ending in one of the
# suffixes, holds a credential; a string value with one of the prefixes is a credential.
CREDENTIAL_KEYS = frozenset(
    {"key", "api_key", "apikey", "secret", "token", "password", "authorization", "bearer"}
)
CREDENTIAL_SUFFIXES = ("api_key", "secret_key", "access_key", "_secret", "_token", "_password")
CREDENTIAL_PREFIXES = ("sk-", "sk_", "bearer ", "basic ")
# The scan is a heuristic against pasting a key into the file, not a proof that none is there.

Money = Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=8)]
Seconds = Annotated[float, Field(gt=0, le=3600, allow_inf_nan=False, strict=True)]
Purpose = Annotated[str, Field(pattern=PURPOSE_PATTERN)]
Version = Annotated[StrictInt, Field(ge=1)]


class _Spec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Prices(_Spec):
    """USD per million tokens; reasoning tokens are billed as output."""

    input_usd_per_mtok: Money
    output_usd_per_mtok: Money


class EffortLevel(_Spec):
    """One Effort level as data (FR-78, NFR-2). `placeholder` marks values that the prototype
    has not set yet (issues #8, #9); a level counts as a placeholder unless it says otherwise."""

    name: str = Field(min_length=1, pattern=PURPOSE_PATTERN)
    provider_params: dict[str, Any] = Field(default_factory=dict)
    attempt_timeout_s: Seconds
    order_time_budget_s: Seconds
    max_output_tokens: Annotated[StrictInt, Field(ge=1, le=1_000_000)] = 4096
    """The most output tokens (reasoning included) one attempt may produce, sent as
    `max_tokens`; with the prices it bounds the cost each attempt reserves (Story 2.8). The
    default is a placeholder until the prototype (issue #8)."""
    placeholder: bool = True


RESERVED_PARAMS = frozenset(
    {
        "max_tokens",
        "max_completion_tokens",
        "provider",
        "models",
        "route",
        "model",
        "messages",
        "response_format",
        "stream",
        "n",
        "tools",
        "tool_choice",
    }
)
"""Request fields an Effort level may not set: router preferences come from `routing` only, a
model list or route would let the router fall back to another model (FR-68), the output token
bound comes from `max_output_tokens` (it bounds the reservation), and the others would override
the pinned model, the prompt or the output schema."""


class Routing(_Spec):
    """Router preferences (Story 2.7). The adapter always adds the switches that turn router
    fallback off and ask for zero retention and no data collection (`adapters.ROUTERS`); a
    config may state them only with those values."""

    router: str = Field(min_length=1)
    """A key of `adapters.ROUTERS`."""
    order: list[Annotated[str, Field(min_length=1)]] | None = None
    only: list[Annotated[str, Field(min_length=1)]] | None = None
    ignore: list[Annotated[str, Field(min_length=1)]] | None = None
    quantizations: list[Annotated[str, Field(min_length=1)]] | None = None
    require_parameters: bool | None = None
    sort: Literal["price", "throughput", "latency"] | None = None
    allow_fallbacks: Literal[False] | None = None
    data_collection: Literal["deny"] | None = None
    zdr: Literal[True] | None = None


class ModelConfigSpec(_Spec):
    """The content of a model config file and of a row."""

    name: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    """`mock` or a key of `adapters.ADAPTERS`."""
    endpoint: str = Field(min_length=1)
    region: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    quantisation: str = Field(min_length=1)
    credential_env: str | None = Field(None, pattern=r"^[A-Z][A-Z0-9_]*$")
    prices: Prices
    rate_limit_rpm: StrictInt = Field(gt=0, le=1_000_000)
    prompts: dict[Purpose, Version]
    effort_levels: list[EffortLevel] = Field(min_length=1)
    routing: Routing | None = None


@dataclass(frozen=True)
class FieldError:
    code: str
    field: str
    message: str


class ConfigInvalid(Exception):
    """A config file or an edit breaks a rule; nothing was stored."""

    def __init__(self, errors: Sequence[FieldError]) -> None:
        self.errors = list(errors)
        super().__init__("; ".join(f"{e.code} {e.field}: {e.message}" for e in self.errors))


class ConfigNotFound(Exception):
    def __init__(self, config_id: object) -> None:
        self.code = "config_not_found"
        self.message = f"no model config {config_id!s}"
        super().__init__(self.message)


@dataclass(frozen=True)
class ModelConfig:
    """One stored row."""

    id: uuid.UUID
    spec: ModelConfigSpec
    derived_from: uuid.UUID | None
    referenced_at: datetime | None
    created_at: datetime

    @property
    def referenced(self) -> bool:
        return self.referenced_at is not None

    def effort_level(self, name: str) -> EffortLevel | None:
        return next((level for level in self.spec.effort_levels if level.name == name), None)


def prompt_path(purpose: str, version: int) -> Path:
    return PROMPTS_DIR / purpose / f"v{version}.md"


def _credential_name(key: object) -> bool:
    name = str(key).lower().replace("-", "_")
    return name in CREDENTIAL_KEYS or name.endswith(CREDENTIAL_SUFFIXES)


def _url_credentials(value: str) -> bool:
    """A user, a password or a key-like query parameter in a URL."""
    try:
        parts = urlsplit(value.strip())
        query = parse_qsl(parts.query, keep_blank_values=True)
        return bool(parts.username or parts.password) or any(
            _credential_name(name) for name, _ in query
        )
    except ValueError:
        return False


def _credentials(value: object, path: str) -> list[FieldError]:
    found: list[FieldError] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            field = f"{path}.{key}" if path else str(key)
            if path == "prompts":
                continue  # purpose names map to version numbers; checked by the schema
            if _credential_name(key):
                found.append(
                    FieldError(
                        "credential_in_file",
                        field,
                        "a config never holds a credential; name its environment variable in "
                        "credential_env",
                    )
                )
            else:
                found += _credentials(item, field)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found += _credentials(item, f"{path}.{index}" if path else str(index))
    elif isinstance(value, str) and value.strip().lower().startswith(CREDENTIAL_PREFIXES):
        found.append(FieldError("credential_in_file", path, "the value looks like a provider key"))
    elif isinstance(value, str) and "://" in value and _url_credentials(value):
        found.append(FieldError("credential_in_file", path, "the URL carries a credential"))
    return found


def _rules(spec: ModelConfigSpec) -> list[FieldError]:
    errors: list[FieldError] = []
    from app.ai.adapters import ADAPTERS, ROUTERS, router_without_routing  # imports this module

    if spec.provider != "mock" and spec.provider not in ADAPTERS:
        errors.append(
            FieldError("provider_unknown", "provider", f"mock or one of: {', '.join(ADAPTERS)}")
        )
    elif spec.provider != "mock":
        if not spec.endpoint.startswith("https://"):
            errors.append(FieldError("endpoint_not_https", "endpoint", "must start https://"))
        router = router_without_routing(spec)
        if router is not None:
            errors.append(
                FieldError(
                    "routing_missing",
                    "routing",
                    f"the endpoint is a {router} router: routing turns its fallback off",
                )
            )

        if spec.routing is not None and spec.routing.router not in ROUTERS:
            errors.append(
                FieldError(
                    "router_unknown",
                    "routing.router",
                    f"one of: {', '.join(sorted(ROUTERS))}",
                )
            )
        if spec.credential_env is None:
            errors.append(
                FieldError(
                    "missing",
                    "credential_env",
                    f"{spec.provider} needs the name of the variable holding the key",
                )
            )
    else:
        if spec.credential_env is not None:
            errors.append(
                FieldError(
                    "credential_env_unused", "credential_env", "the mock provider has no key"
                )
            )
        if spec.routing is not None:
            errors.append(
                FieldError("routing_unused", "routing", "the mock provider has no router")
            )
    seen: set[str] = set()
    for index, level in enumerate(spec.effort_levels):
        if level.name in seen:
            errors.append(
                FieldError(
                    "duplicate_name", f"effort_levels.{index}.name", f"{level.name!r} repeats"
                )
            )
        seen.add(level.name)
        for param in sorted(RESERVED_PARAMS & set(level.provider_params)):
            errors.append(
                FieldError(
                    "param_reserved",
                    f"effort_levels.{index}.provider_params.{param}",
                    "router preferences belong in routing; a model list or route is never sent",
                )
            )
        if level.attempt_timeout_s > level.order_time_budget_s:
            errors.append(
                FieldError(
                    "timeout_above_budget",
                    f"effort_levels.{index}.attempt_timeout_s",
                    "the per-attempt timeout cannot exceed the per-Order time budget",
                )
            )
    for purpose, version in spec.prompts.items():
        if not prompt_path(purpose, version).is_file():
            errors.append(
                FieldError(
                    "prompt_missing",
                    f"prompts.{purpose}",
                    f"no prompt file app/ai/prompts/{purpose}/v{version}.md",
                )
            )
    return errors


def parse(data: object) -> ModelConfigSpec:
    """Validate a config file's JSON value; raise `ConfigInvalid` naming the bad fields. The
    checks run in three stages (credentials, schema, rules); the first stage that finds a
    problem reports every bad field it found, and the later stages do not run."""
    if not isinstance(data, Mapping):
        raise ConfigInvalid([FieldError("not_an_object", "", "a config is one JSON object")])
    credentials = _credentials(data, "")
    if credentials:
        raise ConfigInvalid(credentials)
    try:
        spec = ModelConfigSpec.model_validate(data)
    except ValidationError as exc:
        raise ConfigInvalid(
            [
                FieldError(e["type"], ".".join(str(part) for part in e["loc"]), e["msg"])
                for e in exc.errors()
            ]
        ) from None
    errors = _rules(spec)
    if errors:
        raise ConfigInvalid(errors)
    return spec


def parse_prompt(text: str) -> tuple[str, int]:
    """`<purpose>=<version>` (version `N` or `vN`) from the `--prompt` option."""
    match = re.fullmatch(r"([a-z][a-z0-9_]*)=v?([1-9][0-9]*)", text.strip())
    if match is None:
        raise ValueError(f"{text!r} is not <purpose>=<version>")
    return match[1], int(match[2])


def _uuid(value: uuid.UUID | str) -> uuid.UUID | None:
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


def _row(row: Any) -> ModelConfig:
    spec = ModelConfigSpec.model_validate(
        {
            "name": row.name,
            "provider": row.provider,
            "endpoint": row.endpoint,
            "region": row.region,
            "model_version": row.model_version,
            "quantisation": row.quantisation,
            "credential_env": row.credential_env,
            "prices": {
                "input_usd_per_mtok": row.input_usd_per_mtok,
                "output_usd_per_mtok": row.output_usd_per_mtok,
            },
            "rate_limit_rpm": row.rate_limit_rpm,
            "prompts": row.prompts,
            "effort_levels": row.effort_levels,
            "routing": row.routing,
        }
    )
    return ModelConfig(row.id, spec, row.derived_from, row.referenced_at, row.created_at)


def _values(spec: ModelConfigSpec) -> dict[str, object]:
    data = spec.model_dump(mode="json")
    return {
        "name": spec.name,
        "provider": spec.provider,
        "endpoint": spec.endpoint,
        "region": spec.region,
        "model_version": spec.model_version,
        "quantisation": spec.quantisation,
        "credential_env": spec.credential_env,
        "input_usd_per_mtok": spec.prices.input_usd_per_mtok,
        "output_usd_per_mtok": spec.prices.output_usd_per_mtok,
        "rate_limit_rpm": spec.rate_limit_rpm,
        "prompts": data["prompts"],
        "effort_levels": data["effort_levels"],
        "routing": None if spec.routing is None else spec.routing.model_dump(exclude_none=True),
    }


async def _insert(
    session: AsyncSession, spec: ModelConfigSpec, derived_from: uuid.UUID | None
) -> ModelConfig:
    row = (
        await session.execute(
            model_configs.insert()
            .values(id=uuid.uuid7(), derived_from=derived_from, **_values(spec))
            .returning(*model_configs.c)
        )
    ).one()
    return _row(row)


async def add(spec: ModelConfigSpec, *, session: AsyncSession | None = None) -> ModelConfig:
    """Store a new config row. `spec` comes from `parse`, so its prompt files exist."""
    async with transaction(session) as s:
        return await _insert(s, spec, None)


async def get(
    config_id: uuid.UUID | str, *, session: AsyncSession | None = None
) -> ModelConfig | None:
    key = _uuid(config_id)
    if key is None:
        return None
    async with transaction(session) as s:
        row = (
            await s.execute(select(model_configs).where(model_configs.c.id == key))
        ).one_or_none()
    return None if row is None else _row(row)


async def list_all(*, session: AsyncSession | None = None) -> list[ModelConfig]:
    """Every row, oldest first."""
    async with transaction(session) as s:
        rows = (
            await s.execute(
                select(model_configs).order_by(model_configs.c.created_at, model_configs.c.id)
            )
        ).all()
    return [_row(row) for row in rows]


async def derive(
    config_id: uuid.UUID | str,
    *,
    prompts: Mapping[str, int] | None = None,
    spec: ModelConfigSpec | None = None,
    session: AsyncSession | None = None,
) -> ModelConfig:
    """An edit: a new row from `spec` (default: the source row's content) with `prompts` added
    to or moved in its `prompts` map, `derived_from` the source. The source never changes."""
    async with transaction(session) as s:
        source = await get(config_id, session=s)
        if source is None:
            raise ConfigNotFound(config_id)
        base = (spec or source.spec).model_dump(mode="json")
        base["prompts"] = {**base["prompts"], **(prompts or {})}
        return await _insert(s, parse(base), source.id)


async def mark_referenced(
    config_id: uuid.UUID | str, *, session: AsyncSession | None = None
) -> ModelConfig:
    """Freeze a row: called by whatever pins it (a simulation run, `sessions.lock`). From then
    on the row can never be updated or deleted. Calling it again changes nothing."""
    key = _uuid(config_id)
    async with transaction(session) as s:
        if key is not None:
            await s.execute(
                update(model_configs)
                .where(model_configs.c.id == key, model_configs.c.referenced_at.is_(None))
                .values(referenced_at=func.now())
            )
        config = await get(config_id, session=s)
        if config is None:
            raise ConfigNotFound(config_id)
        return config
