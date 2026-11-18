"""Model configs and budgets (`ai_model_configs`, `ai_budgets`, Story 2.2), owned by app/ai.

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MONEY = sa.Numeric(18, 8)


def upgrade() -> None:
    op.create_table(
        "ai_model_configs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("region", sa.Text(), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=False),
        sa.Column("quantisation", sa.Text(), nullable=False),
        sa.Column("credential_env", sa.Text(), nullable=True),
        sa.Column("input_usd_per_mtok", MONEY, nullable=False),
        sa.Column("output_usd_per_mtok", MONEY, nullable=False),
        sa.Column("rate_limit_rpm", sa.Integer(), nullable=False),
        sa.Column("prompts", postgresql.JSONB(), nullable=False),
        sa.Column("effort_levels", postgresql.JSONB(), nullable=False),
        sa.Column("derived_from", sa.Uuid(), sa.ForeignKey("ai_model_configs.id"), nullable=True),
        sa.Column("referenced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "provider IN ('mock', 'openai_compatible')", name="ck_ai_model_configs_provider"
        ),
        sa.CheckConstraint("rate_limit_rpm > 0", name="ck_ai_model_configs_rate_limit"),
        sa.CheckConstraint(
            "input_usd_per_mtok >= 0 AND output_usd_per_mtok >= 0",
            name="ck_ai_model_configs_prices",
        ),
    )
    # AD-6: a config that a Class session or a simulation run references never changes; an
    # edit writes a new row. Setting `referenced_at` the first time is the one allowed update;
    # an UPDATE that changes any other column is refused even before that.
    op.execute(
        """
        CREATE FUNCTION ai_model_configs_immutable() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.referenced_at IS NOT NULL THEN
                RAISE EXCEPTION 'ai_model_configs row % is referenced: % refused', OLD.id, TG_OP
                    USING ERRCODE = 'restrict_violation';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            IF (to_jsonb(NEW) - 'referenced_at') IS DISTINCT FROM (to_jsonb(OLD) - 'referenced_at')
            THEN
                RAISE EXCEPTION 'ai_model_configs row %: only referenced_at may be set', OLD.id
                    USING ERRCODE = 'restrict_violation';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER ai_model_configs_immutable
        BEFORE UPDATE OR DELETE ON ai_model_configs
        FOR EACH ROW EXECUTE FUNCTION ai_model_configs_immutable()
        """
    )
    op.create_table(
        "ai_budgets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("scope_kind", sa.Text(), nullable=False),
        sa.Column("scope_id", sa.Uuid(), nullable=False),
        sa.Column("limit_usd", MONEY, nullable=False),
        sa.Column("reserve_usd", MONEY, nullable=False),
        sa.Column("spent_usd", MONEY, nullable=False, server_default=sa.text("0")),
        sa.Column("players_exhausted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "scope_kind IN ('evaluation', 'class_session')", name="ck_ai_budgets_scope_kind"
        ),
        sa.CheckConstraint(
            "limit_usd >= 0 AND reserve_usd >= 0 AND spent_usd >= 0", name="ck_ai_budgets_money"
        ),
        sa.CheckConstraint("reserve_usd <= limit_usd", name="ck_ai_budgets_reserve"),
        sa.UniqueConstraint("scope_kind", "scope_id", name="uq_ai_budgets_scope"),
    )


def downgrade() -> None:
    op.drop_table("ai_budgets")
    op.drop_table("ai_model_configs")
    op.execute("DROP FUNCTION ai_model_configs_immutable()")
