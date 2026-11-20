"""The steps a Student has done in a Class session (Story 6.1, AD-16).

`progress_steps` holds one row per User, Class session and step from the closed catalogue; the
unique key makes `progress.record_step` idempotent.

Revision ID: 0045
Revises: 0044
Create Date: 2026-11-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0045"
down_revision: str | None = "0044"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STEPS = (
    "starting_task",
    "class_game",
    "explanation",
    "debrief",
    "quiz_passed",
    "replay",
    "test_submitted",
    "assessment_ready",
)


def upgrade() -> None:
    op.create_table(
        "progress_steps",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "class_session_id",
            sa.Uuid(),
            sa.ForeignKey("class_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step", sa.Text(), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "step IN (" + ", ".join(f"'{step}'" for step in STEPS) + ")",
            name="ck_progress_steps_step",
        ),
        sa.UniqueConstraint("user_id", "class_session_id", "step", name="uq_progress_steps_step"),
    )
    op.create_index("ix_progress_steps_class_session_id", "progress_steps", ["class_session_id"])


def downgrade() -> None:
    op.drop_table("progress_steps")
