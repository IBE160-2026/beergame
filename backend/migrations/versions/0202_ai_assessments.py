"""The AI assessment of an Individual test (Story 12.2, FR-54, AD-6, AD-9, AD-23).

Owned by `modules/assessment`:

- `assessment_switches.model_config_id` / `effort_level`: the model config (and Effort level) the
  Test-deadline lock pins with the switch, the only config an assessment of the Class session
  uses. NULL when no config naming the `assessment` prompt could be pinned.
- `ai_assessments`: one per Test attempt (`attempt_id` unique), its state (`incomplete`, `ready`,
  `failed`), how many job runs it has had, and the pinned versions it was made with.
- `ai_item_scores`: one overall score on the Scoring guide's five-step scale (0 to 4) per
  long-answer or Adapted item, with the versions and the `llm_call` it came from; written once.

Revision ID: 0202
Revises: 0201
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0202"
down_revision: str | None = "0201"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("assessment_switches", sa.Column("model_config_id", sa.Uuid(), nullable=True))
    op.add_column("assessment_switches", sa.Column("effort_level", sa.Text(), nullable=True))
    op.create_table(
        "ai_assessments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "attempt_id",
            sa.Uuid(),
            sa.ForeignKey("test_attempts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "class_session_id",
            sa.Uuid(),
            sa.ForeignKey("class_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("runs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scoring_guide_id", sa.Uuid(), nullable=True),
        sa.Column("question_set_version", sa.Integer(), nullable=False),
        sa.Column("model_config_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("attempt_id", name="uq_ai_assessments_attempt"),
        sa.CheckConstraint(
            "status IN ('incomplete', 'ready', 'failed')", name="ck_ai_assessments_status"
        ),
        sa.CheckConstraint("runs >= 0", name="ck_ai_assessments_runs"),
    )
    op.create_index("ix_ai_assessments_class_session", "ai_assessments", ["class_session_id"])
    op.create_index("ix_ai_assessments_user", "ai_assessments", ["user_id"])
    op.create_table(
        "ai_item_scores",
        sa.Column(
            "assessment_id",
            sa.Uuid(),
            sa.ForeignKey("ai_assessments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("item_id", sa.Text(), nullable=False),
        sa.Column("score", sa.SmallInteger(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("llm_call_id", sa.Uuid(), nullable=True),
        sa.Column("scoring_guide_id", sa.Uuid(), nullable=True),
        sa.Column("question_set_version", sa.Integer(), nullable=False),
        sa.Column("model_config_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("assessment_id", "item_id", name="pk_ai_item_scores"),
        sa.CheckConstraint("score BETWEEN 0 AND 4", name="ck_ai_item_scores_score"),
        sa.CheckConstraint("source IN ('ai', 'blank')", name="ck_ai_item_scores_source"),
        sa.CheckConstraint(
            "(source = 'ai') = (llm_call_id IS NOT NULL)", name="ck_ai_item_scores_call"
        ),
    )


def downgrade() -> None:
    op.drop_table("ai_item_scores")
    op.drop_table("ai_assessments")
    op.drop_column("assessment_switches", "effort_level")
    op.drop_column("assessment_switches", "model_config_id")
