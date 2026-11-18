"""Tables owned by `app/ai` (AD-6). Only `app.ai.config` and `app.ai.budget` read or write them."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
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
    Column("derived_from", Uuid, ForeignKey("ai_model_configs.id"), nullable=True),
    # Set once by the first Class session or simulation run that pins the row; from then on
    # a trigger refuses every UPDATE and DELETE of it.
    Column("referenced_at", DateTime(timezone=True), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(
        "provider IN ('mock', 'openai_compatible')", name="ck_ai_model_configs_provider"
    ),
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
