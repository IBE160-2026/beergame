"""Model configs (`ai.config`, AD-6, FR-68, FR-78, NFR-2).

A model config pins one provider, endpoint, region, model version and quantisation, its prices
and rate limit, a `prompts` map from purpose to prompt version, and its Effort levels as data.
A row never changes once a Class session or a simulation run references it (a trigger refuses
it); an edit always writes a new row (`derive`). Credentials are never stored: a config names
only the environment variable that holds the key.

Other modules read and change model configs only through this module (AD-6).

Story 2.12 (FR-68, FR-78, FR-79): `approve_effort` stores the measurement of an Effort level
from a simulation batch's figures, refused unless the batch was real and passed its cost, time
and switched-share lines; `offered_effort_levels` is the one list of levels a Class session may
be offered; `pin` makes a config with an offered level the active default (`active_default`).
Mock measurements come only from the zero-config seed (`app.ai.seed`) and count only in
`local`, `test` and `ci`: with `APP_ENV=production` a database holding only mock measurements
offers no Effort level at all.
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
from app.ai.models import default_pins, effort_measurements, model_configs
from app.platform.config import get_settings

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
    label: str | None = Field(None, min_length=1, max_length=40)
    """The level's name as the Klasseøkt shows it, in Norwegian bokmål (Story 5.5). None: the
    screen shows `name`."""
    effect: str | None = Field(None, min_length=1, max_length=200)
    """One line on the level's effect on speed and cost, in Norwegian bokmål, shown beside the
    level on the Klasseøkt (FR-78, Story 5.5). A placeholder until the prototype (issues #8, #9);
    None for configs stored before the field existed."""


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


# --- Measured Effort levels and the default config (Story 2.12) ------------------------------

PASS_LINE_NAMES = ("cost_per_game_usd", "time_per_order_p95_s", "switched_share")
"""The pass lines an approval needs, each passed (FR-78, FR-79, C-3)."""

MOCK_ENVS = ("local", "test", "ci")
"""Where a mock measurement counts (AD-17); the same set as `adapters.MOCK_ENVS`."""


class ConfigRefused(Exception):
    """An approval or a pin breaks a rule; nothing was stored."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class PassVerdict:
    """One pass line of a batch as its report states it."""

    name: str
    line: Decimal | None
    """None: the batch file has no such line."""
    measured: Decimal | None
    verdict: str
    """`pass`, `miss`, `miss (cut short)`, `n/a` or `no line` (`app.sim_report`)."""


@dataclass(frozen=True)
class EffortFigures:
    """What the simulation runner's report of one batch says (Story 2.11), handed to
    `approve_effort`; built outside `app/ai`, so it carries plain values only (AD-6)."""

    model_config_id: str | None
    effort_levels: tuple[str, ...]
    """The Effort levels the batch's Games froze."""
    mock: bool
    games: int
    cost_per_game_usd: Decimal | None
    time_per_order_median_s: Decimal | None
    time_per_order_p95_s: Decimal | None
    """Retries and back-off included."""
    retries_per_order_mean: Decimal | None
    fallback_share: Decimal | None
    """LLM-path Orders with any fallback over all LLM-path Orders."""
    switched_share: Decimal | None
    """`llm` Seats the Play guard switched over all `llm` Seats."""
    pass_lines: tuple[PassVerdict, ...]


@dataclass(frozen=True)
class EffortMeasurement:
    """One stored `effort_measurements` row."""

    id: uuid.UUID
    model_config_id: uuid.UUID
    effort_level: str
    batch_id: uuid.UUID | None
    mock: bool
    games: int | None
    cost_per_game_usd: Decimal | None
    time_per_order_median_s: Decimal | None
    time_per_order_p95_s: Decimal | None
    retries_per_order_mean: Decimal | None
    fallback_share: Decimal | None
    switched_share: Decimal | None
    pass_lines: dict[str, Any]
    approved_at: datetime


@dataclass(frozen=True)
class OfferedLevel:
    """An Effort level a Class session may be offered, with its measured effect (FR-78)."""

    name: str
    default: bool
    measurement: EffortMeasurement
    """The newest measurement that counts in this environment."""


@dataclass(frozen=True)
class Pinned:
    config: ModelConfig
    offered: list[OfferedLevel]
    evidence: list[EffortMeasurement]
    """The counted measurements of the offered levels, newest first."""


def _measurement(row: Any) -> EffortMeasurement:
    return EffortMeasurement(
        row.id,
        row.model_config_id,
        row.effort_level,
        row.batch_id,
        row.mock,
        row.games,
        row.cost_per_game_usd,
        row.time_per_order_median_s,
        row.time_per_order_p95_s,
        row.retries_per_order_mean,
        row.fallback_share,
        row.switched_share,
        row.pass_lines,
        row.approved_at,
    )


def _pass_problems(figures: EffortFigures) -> tuple[str, list[str]] | None:
    """The refusal code and the problem per line, or None when every line passed."""
    by_name = {verdict.name: verdict for verdict in figures.pass_lines}
    missing = [
        name for name in PASS_LINE_NAMES if name not in by_name or by_name[name].line is None
    ]
    if missing:
        return "pass_line_missing", [f"{name}: no line" for name in missing]
    missed = []
    for name in PASS_LINE_NAMES:
        verdict = by_name[name]
        assert verdict.line is not None
        if verdict.verdict != "pass" or verdict.measured is None or verdict.measured > verdict.line:
            missed.append(
                f"{name}: {verdict.verdict} (measured {verdict.measured}, line {verdict.line})"
            )
    return ("pass_line_missed", missed) if missed else None


def _pass_lines_json(figures: EffortFigures) -> dict[str, Any]:
    return {
        verdict.name: {
            "line": None if verdict.line is None else str(verdict.line),
            "measured": None if verdict.measured is None else str(verdict.measured),
            "verdict": verdict.verdict,
        }
        for verdict in figures.pass_lines
    }


async def approve_effort(
    config_id: uuid.UUID | str,
    level: str,
    batch_id: uuid.UUID | str,
    figures: EffortFigures,
    *,
    session: AsyncSession | None = None,
) -> EffortMeasurement:
    """Store the measurement of `level` from batch `batch_id`'s report figures (FR-78, C-3).
    Refused (`ConfigRefused`, nothing stored) unless the figures are of this config and of
    exactly this level, the batch did not run on the mock, and it passed its cost, time and
    switched-share lines; a batch is approved once. The config row never changes."""
    batch = _uuid(batch_id)
    if batch is None:
        raise ConfigRefused("batch_id_invalid", f"{batch_id!s} is not a batch id")
    async with transaction(session) as s:
        found = await get(config_id, session=s)
        if found is None:
            raise ConfigNotFound(config_id)
        if figures.model_config_id is None or _uuid(figures.model_config_id) != found.id:
            raise ConfigRefused(
                "config_mismatch",
                f"the batch measured model config {figures.model_config_id or '-'}, not {found.id}",
            )
        if found.effort_level(level) is None:
            raise ConfigRefused(
                "effort_level_unknown", f"model config {found.id} has no Effort level {level!r}"
            )
        if figures.mock:
            raise ConfigRefused(
                "mock_batch", "the mock answered this batch: mock numbers are not measurements"
            )
        if figures.effort_levels != (level,):
            played = ", ".join(figures.effort_levels) or "none"
            raise ConfigRefused(
                "effort_level_mismatch", f"the batch played Effort level(s) {played}, not {level}"
            )
        problems = _pass_problems(figures)
        if problems is not None:
            code, lines = problems
            raise ConfigRefused(code, "; ".join(lines))
        taken = (
            await s.execute(
                select(effort_measurements.c.id).where(effort_measurements.c.batch_id == batch)
            )
        ).first()
        if taken is not None:
            raise ConfigRefused(
                "already_approved", f"batch {batch} is already measurement {taken.id}"
            )
        row = (
            await s.execute(
                effort_measurements.insert()
                .values(
                    id=uuid.uuid7(),
                    model_config_id=found.id,
                    effort_level=level,
                    batch_id=batch,
                    mock=False,
                    games=figures.games,
                    cost_per_game_usd=figures.cost_per_game_usd,
                    time_per_order_median_s=figures.time_per_order_median_s,
                    time_per_order_p95_s=figures.time_per_order_p95_s,
                    retries_per_order_mean=figures.retries_per_order_mean,
                    fallback_share=figures.fallback_share,
                    switched_share=figures.switched_share,
                    pass_lines=_pass_lines_json(figures),
                )
                .returning(*effort_measurements.c)
            )
        ).one()
    return _measurement(row)


async def add_mock_measurement(
    config_id: uuid.UUID, level: str, *, session: AsyncSession | None = None
) -> EffortMeasurement:
    """The zero-config seed's measurement (AD-17): marked `mock`, no batch, no figures. It
    makes the level offered in `local`, `test` and `ci` only; `approve_effort` never stores
    one."""
    async with transaction(session) as s:
        row = (
            await s.execute(
                effort_measurements.insert()
                .values(
                    id=uuid.uuid7(),
                    model_config_id=config_id,
                    effort_level=level,
                    batch_id=None,
                    mock=True,
                    pass_lines={},
                )
                .returning(*effort_measurements.c)
            )
        ).one()
    return _measurement(row)


async def measurements(
    config_id: uuid.UUID | str, *, session: AsyncSession | None = None
) -> list[EffortMeasurement]:
    """Every measurement of a config, newest first, mock ones included."""
    key = _uuid(config_id)
    if key is None:
        return []
    async with transaction(session) as s:
        rows = (
            await s.execute(
                select(effort_measurements)
                .where(effort_measurements.c.model_config_id == key)
                .order_by(effort_measurements.c.approved_at.desc(), effort_measurements.c.id.desc())
            )
        ).all()
    return [_measurement(row) for row in rows]


def _counts(measurement: EffortMeasurement, app_env: str) -> bool:
    """A real measurement always counts; a mock one only where the mock may answer."""
    return not measurement.mock or app_env in MOCK_ENVS


def may_answer(found: ModelConfig) -> bool:
    """Whether a model may answer for this config in this environment: the mock where it may,
    else the real endpoint with its key set (AD-17). False in production for the mock config or
    a provider whose key is not set; `sessions.lock` refuses then (`provider_key_missing`)."""
    from app.ai import adapters  # imports this module

    return adapters.availability(found.spec, get_settings().app_env).kind != "refused"


async def offered_effort_levels(
    config_id: uuid.UUID | str, *, session: AsyncSession | None = None
) -> list[OfferedLevel]:
    """The Effort levels of a config a Class session may be offered (FR-78), in the config's
    order: those its endpoint supports in this environment (its calls are not refused) with a
    measurement that counts here, each with its newest such measurement. The first is the
    default. The one source Epic 5's Class session screen reads."""
    from app.ai import adapters  # imports this module

    app_env = get_settings().app_env
    async with transaction(session) as s:
        found = await get(config_id, session=s)
        if found is None:
            raise ConfigNotFound(config_id)
        if adapters.availability(found.spec, app_env).kind == "refused":
            return []
        rows = await measurements(found.id, session=s)
    newest: dict[str, EffortMeasurement] = {}
    for row in rows:
        if _counts(row, app_env):
            newest.setdefault(row.effort_level, row)
    names = [level.name for level in found.spec.effort_levels if level.name in newest]
    return [OfferedLevel(name, index == 0, newest[name]) for index, name in enumerate(names)]


async def pin(config_id: uuid.UUID | str, *, session: AsyncSession | None = None) -> Pinned:
    """Make a config the active default (FR-68): a Class session created from now on receives
    it (Epic 5); scopes created before keep the config id they hold. Refused for the mock
    provider outside `local`, `test` and `ci`, and for a config with no offered Effort level.
    The config is marked referenced, so its content never changes."""
    app_env = get_settings().app_env
    async with transaction(session) as s:
        found = await get(config_id, session=s)
        if found is None:
            raise ConfigNotFound(config_id)
        if found.spec.provider == "mock" and app_env not in MOCK_ENVS:
            raise ConfigRefused(
                "mock_config", f"the mock config can never be pinned with APP_ENV={app_env}"
            )
        offered = await offered_effort_levels(found.id, session=s)
        if not offered:
            raise ConfigRefused(
                "no_offered_level",
                f"model config {found.id} has no measured, approved Effort level its endpoint "
                "supports here",
            )
        found = await mark_referenced(found.id, session=s)
        # The time of the insert, not of the transaction start: the pin made last wins.
        await s.execute(
            default_pins.insert().values(
                id=uuid.uuid7(), model_config_id=found.id, pinned_at=func.clock_timestamp()
            )
        )
        offered_names = {level.name for level in offered}
        evidence = [
            row
            for row in await measurements(found.id, session=s)
            if row.effort_level in offered_names and _counts(row, app_env)
        ]
    return Pinned(found, offered, evidence)


async def active_default(*, session: AsyncSession | None = None) -> ModelConfig | None:
    """The config of the newest pin that offers an Effort level in this environment, or None.
    A pin whose config offers nothing here (the seeded mock config once `APP_ENV=production`,
    a real config whose key is not set) is passed over, so a Class session is never handed a
    default it cannot use."""
    async with transaction(session) as s:
        rows = (
            await s.execute(
                select(default_pins.c.model_config_id).order_by(
                    default_pins.c.pinned_at.desc(), default_pins.c.id.desc()
                )
            )
        ).all()
        checked: set[uuid.UUID] = set()
        for row in rows:
            if row.model_config_id in checked:
                continue
            checked.add(row.model_config_id)
            if await offered_effort_levels(row.model_config_id, session=s):
                return await get(row.model_config_id, session=s)
    return None
