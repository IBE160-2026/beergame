"""The deadline reminders of a Class session (Story 5.14).

`deadline_reminders` holds one row per deadline time the Students were reminded of, 24 hours
ahead: the sweep's `sessions.send_deadline_reminder` skips a deadline with a row at its current
time, and each `deadline_reminder` notice names its row as `ref`.

Revision ID: 0041
Revises: 0040
Create Date: 2026-11-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0041"
down_revision: str | None = "0040"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "deadline_reminders",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "class_session_id",
            sa.Uuid(),
            sa.ForeignKey("class_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("deadline", sa.Text(), nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "deadline IN ('play_deadline', 'debrief_deadline', 'test_deadline')",
            name="ck_deadline_reminders_deadline",
        ),
        sa.UniqueConstraint(
            "class_session_id", "deadline", "deadline_at", name="uq_deadline_reminders_deadline"
        ),
    )


def downgrade() -> None:
    op.drop_table("deadline_reminders")
