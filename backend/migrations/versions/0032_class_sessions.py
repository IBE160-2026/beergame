"""Class sessions (Story 5.1, FR-11, FR-13, AD-4, AD-6), owned by `sessions`.

One row per Class session of a Class: the engine's `GameSettings` as JSONB with its
`schema_version` (the Classic preset with a server-drawn demand seed when created), AI mode,
Debrief mode, Inactivity limit, the obligatory mark, the `ai` model config it uses (no foreign
key into `ai` tables) and when it was created and last saved. Times come from the api's clock.

Revision ID: 0032
Revises: 0031
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0032"
down_revision: str | None = "0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "class_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "class_id",
            sa.Uuid(),
            sa.ForeignKey("classes.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("game_settings", JSONB(), nullable=False),
        sa.Column("ai_mode", sa.Text(), nullable=False),
        sa.Column("debrief_mode", sa.Text(), nullable=False),
        sa.Column("inactivity_limit_hours", sa.Integer(), nullable=False),
        sa.Column("obligatory", sa.Boolean(), nullable=False),
        sa.Column("model_config_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("saved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("ai_mode IN ('llm', 'rule_based')", name="ck_class_sessions_ai_mode"),
        sa.CheckConstraint(
            "debrief_mode IN ('group', 'personal')", name="ck_class_sessions_debrief_mode"
        ),
        sa.CheckConstraint(
            "inactivity_limit_hours >= 20", name="ck_class_sessions_inactivity_limit"
        ),
        sa.CheckConstraint(
            "ai_mode <> 'llm' OR model_config_id IS NOT NULL",
            name="ck_class_sessions_llm_has_config",
        ),
    )


def downgrade() -> None:
    op.drop_table("class_sessions")
