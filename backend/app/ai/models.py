"""Tables owned by `app/ai` (AD-6). Only modules of `app/ai` read or write them."""

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.platform.db import metadata

MONEY = Numeric(18, 8)
"""USD amounts and prices (AD-6)."""

SCOPE_KINDS = ("evaluation", "class_session")

model_configs = Table(
    "ai_model_configs",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("name", Text, nullable=False),
    Column("provider", Text, nullable=False),
    Column("endpoint", Text, nullable=False),
    Column("region", Text, nullable=False),
    Column("model_version", Text, nullable=False),
    Column("quantisation", Text, nullable=False),
    # The name of the environment variable that holds the key, never the key itself.
    Column("credential_env", Text, nullable=True),
    Column("input_usd_per_mtok", MONEY, nullable=False),
    Column("output_usd_per_mtok", MONEY, nullable=False),
    Column("rate_limit_rpm", Integer, nullable=False),
    Column("prompts", JSONB, nullable=False),
    Column("effort_levels", JSONB, nullable=False),
    # Router preferences (Story 2.7); NULL for an endpoint that is not a router.
    Column("routing", JSONB(none_as_null=True), nullable=True),
    Column("derived_from", Uuid, ForeignKey("ai_model_configs.id"), nullable=True),
    # Set once by the first Class session or simulation run that pins the row; from then on
    # a trigger refuses every UPDATE and DELETE of it.
    Column("referenced_at", DateTime(timezone=True), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("rate_limit_rpm > 0", name="ck_ai_model_configs_rate_limit"),
    CheckConstraint(
        "input_usd_per_mtok >= 0 AND output_usd_per_mtok >= 0", name="ck_ai_model_configs_prices"
    ),
)

budgets = Table(
    "ai_budgets",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("scope_kind", Text, nullable=False),
    Column("scope_id", Uuid, nullable=False),
    Column("limit_usd", MONEY, nullable=False),
    Column("reserve_usd", MONEY, nullable=False),
    Column("spent_usd", MONEY, nullable=False, server_default=text("0")),
    Column("players_exhausted_at", DateTime(timezone=True), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(
        f"scope_kind IN ({', '.join(repr(kind) for kind in SCOPE_KINDS)})",
        name="ck_ai_budgets_scope_kind",
    ),
    CheckConstraint(
        "limit_usd >= 0 AND reserve_usd >= 0 AND spent_usd >= 0", name="ck_ai_budgets_money"
    ),
    CheckConstraint("reserve_usd <= limit_usd", name="ck_ai_budgets_reserve"),
    UniqueConstraint("scope_kind", "scope_id", name="uq_ai_budgets_scope"),
)

OUTCOMES = ("ok", "invalid_output", "timeout", "provider_error", "cancelled")
"""How one attempt ended (FR-67); `cancelled`: the caller stopped the call during the attempt."""

llm_calls = Table(
    "llm_call",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("purpose", Text, nullable=False),
    Column("scope_kind", Text, nullable=False),
    Column("scope_id", Uuid, nullable=False),
    # Ids only (for a player Order the Game, Seat and Week); stored, never rendered.
    Column("caller_ref", JSONB, nullable=False),
    Column("model_config_id", Uuid, ForeignKey("ai_model_configs.id"), nullable=False),
    Column("provider", Text, nullable=False),
    Column("endpoint", Text, nullable=False),
    Column("model_version", Text, nullable=False),
    Column("quantisation", Text, nullable=False),
    Column("effort_level", Text, nullable=False),
    Column("seed", BigInteger, nullable=True),
    Column("temperature", Double, nullable=True),
    Column("prompt_version", Integer, nullable=False),
    Column("attempt", Integer, nullable=False),
    Column("input_tokens", Integer, nullable=False),
    Column("output_tokens", Integer, nullable=False),
    # Part of output_tokens; stored on its own (FR-78).
    Column("reasoning_tokens", Integer, nullable=False),
    Column("cost_usd", MONEY, nullable=False),
    Column("latency_ms", Integer, nullable=False),
    Column("outcome", Text, nullable=False),
    Column("error", Text, nullable=True),
    # The scrubbed request and response (AD-6, C-1).
    Column("request", JSONB, nullable=False),
    Column("response", Text, nullable=True),
    # What the response reports: the model id and, behind a router, the upstream provider.
    Column("served_model", Text, nullable=True),
    Column("served_by", Text, nullable=True),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(
        f"scope_kind IN ({', '.join(repr(kind) for kind in SCOPE_KINDS)})",
        name="ck_llm_call_scope_kind",
    ),
    CheckConstraint(
        f"outcome IN ({', '.join(repr(outcome) for outcome in OUTCOMES)})",
        name="ck_llm_call_outcome",
    ),
    CheckConstraint(
        "attempt >= 1 AND input_tokens >= 0 AND output_tokens >= 0 AND reasoning_tokens >= 0 "
        "AND cost_usd >= 0 AND latency_ms >= 0",
        name="ck_llm_call_counts",
    ),
    Index("ix_llm_call_scope", "scope_kind", "scope_id"),
)
