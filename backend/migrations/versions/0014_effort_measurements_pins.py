"""Effort measurements and the default model config (Story 2.12, AD-6, AD-17, FR-68, FR-78).

`effort_measurements` holds one approved measurement of a model config's Effort level: the batch
it rests on and the batch's figures, or (`mock`, no batch, no figures) the zero-config seed's
mock measurement. A trigger refuses UPDATE and DELETE, so the evidence never changes.
`ai_default_pins` holds one row per pin; the newest row is the active default model config.
Both tables are owned by `app/ai`.

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FIGURES = (
    "games",
    "cost_per_game_usd",
    "time_per_order_median_s",
    "time_per_order_p95_s",
    "retries_per_order_mean",
    "fallback_share",
    "switched_share",
)


def upgrade() -> None:
    op.create_table(
        "effort_measurements",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("model_config_id", sa.Uuid, sa.ForeignKey("ai_model_configs.id"), nullable=False),
        sa.Column("effort_level", sa.Text, nullable=False),
        sa.Column("batch_id", sa.Uuid, nullable=True),
        sa.Column("mock", sa.Boolean, nullable=False),
        sa.Column("games", sa.Integer, nullable=True),
        sa.Column("cost_per_game_usd", sa.Numeric(18, 8), nullable=True),
        sa.Column("time_per_order_median_s", sa.Numeric, nullable=True),
        sa.Column("time_per_order_p95_s", sa.Numeric, nullable=True),
        sa.Column("retries_per_order_mean", sa.Numeric, nullable=True),
        sa.Column("fallback_share", sa.Numeric, nullable=True),
        sa.Column("switched_share", sa.Numeric, nullable=True),
        sa.Column("pass_lines", postgresql.JSONB, nullable=False),
        sa.Column(
            "approved_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("mock = (batch_id IS NULL)", name="ck_effort_measurements_source"),
        sa.CheckConstraint(
            "mock OR (" + " AND ".join(f"{name} IS NOT NULL" for name in FIGURES) + ")",
            name="ck_effort_measurements_figures",
        ),
        sa.UniqueConstraint("batch_id", name="uq_effort_measurements_batch"),
    )
    op.create_index("ix_effort_measurements_config", "effort_measurements", ["model_config_id"])
    op.execute(
        """
        CREATE FUNCTION effort_measurements_append_only() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'effort_measurements is append-only: % refused', TG_OP
                USING ERRCODE = 'restrict_violation';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER effort_measurements_append_only
        BEFORE UPDATE OR DELETE ON effort_measurements
        FOR EACH ROW EXECUTE FUNCTION effort_measurements_append_only()
        """
    )
    op.create_table(
        "ai_default_pins",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("model_config_id", sa.Uuid, sa.ForeignKey("ai_model_configs.id"), nullable=False),
        sa.Column(
            "pinned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    op.drop_table("ai_default_pins")
    op.execute("DROP TRIGGER effort_measurements_append_only ON effort_measurements")
    op.execute("DROP FUNCTION effort_measurements_append_only()")
    op.drop_index("ix_effort_measurements_config", table_name="effort_measurements")
    op.drop_table("effort_measurements")
