"""The study freeze of a model config (Story 15.5, FR-68, AD-6).

`ai_model_freezes` holds one row per freeze the Admin made for a learning study: the model config,
the Class sessions it was pinned to, and when it was made and lifted. At most one freeze is
active (`lifted_at IS NULL`); while it is, new Class sessions get its config as their default.
Ids and times only: the Admin who made it is in the audit.

Revision ID: 0067
Revises: 0066
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0067"
down_revision: str | None = "0066"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_model_freezes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "model_config_id", sa.Uuid(), sa.ForeignKey("ai_model_configs.id"), nullable=False
        ),
        sa.Column("class_session_ids", postgresql.ARRAY(sa.Uuid()), nullable=False),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lifted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "lifted_at IS NULL OR lifted_at >= frozen_at", name="ck_ai_model_freezes_lifted"
        ),
    )
    op.create_index(
        "uq_ai_model_freezes_active",
        "ai_model_freezes",
        [sa.text("(lifted_at IS NULL)")],
        unique=True,
        postgresql_where=sa.text("lifted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_ai_model_freezes_active", table_name="ai_model_freezes")
    op.drop_table("ai_model_freezes")
