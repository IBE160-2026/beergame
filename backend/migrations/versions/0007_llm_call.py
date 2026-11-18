"""One `llm_call` row per LLM attempt (Story 2.3, FR-67, AD-6), owned by app/ai.

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_call",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("scope_kind", sa.Text(), nullable=False),
        sa.Column("scope_id", sa.Uuid(), nullable=False),
        sa.Column("caller_ref", postgresql.JSONB(), nullable=False),
        sa.Column(
            "model_config_id", sa.Uuid(), sa.ForeignKey("ai_model_configs.id"), nullable=False
        ),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=False),
        sa.Column("quantisation", sa.Text(), nullable=False),
        sa.Column("effort_level", sa.Text(), nullable=False),
        sa.Column("seed", sa.BigInteger(), nullable=True),
        sa.Column("temperature", sa.Double(), nullable=True),
        sa.Column("prompt_version", sa.Integer(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("reasoning_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(18, 8), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("request", postgresql.JSONB(), nullable=False),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "scope_kind IN ('evaluation', 'class_session')", name="ck_llm_call_scope_kind"
        ),
        sa.CheckConstraint(
            "outcome IN ('ok', 'invalid_output', 'timeout', 'provider_error')",
            name="ck_llm_call_outcome",
        ),
        sa.CheckConstraint(
            "attempt >= 1 AND input_tokens >= 0 AND output_tokens >= 0 AND reasoning_tokens >= 0 "
            "AND cost_usd >= 0 AND latency_ms >= 0",
            name="ck_llm_call_counts",
        ),
    )
    op.create_index("ix_llm_call_scope", "llm_call", ["scope_kind", "scope_id"])


def downgrade() -> None:
    op.drop_index("ix_llm_call_scope", table_name="llm_call")
    op.drop_table("llm_call")
