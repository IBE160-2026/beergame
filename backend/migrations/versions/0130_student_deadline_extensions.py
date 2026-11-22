"""One Student's own Test deadline (Story 11.13, FR-18, AD-9).

- `student_deadline_extensions` (owned by `modules/sessions`): a Student's own Test deadline in a
  Class session, later than the Class session's, and their Debrief deadline moved by the same
  amount (NULL when the Class session has none). Who saved it last (`updated_by`) and when. No
  reason is stored.
- `deadline_reminders.user_id`: NULL for the reminder of the Class session's deadline to its
  Students (Story 5.14); a Student's id for the reminder of their own deadline. The unique key
  takes the user, NULLs not distinct, so the Class reminder is still one per deadline time.

Revision ID: 0130
Revises: 0129
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0130"
down_revision: str | None = "0129"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "student_deadline_extensions",
        sa.Column(
            "class_session_id",
            sa.Uuid(),
            sa.ForeignKey("class_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("test_deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("debrief_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("class_session_id", "user_id"),
    )
    op.add_column(
        "deadline_reminders",
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True
        ),
    )
    op.drop_constraint("uq_deadline_reminders_deadline", "deadline_reminders", type_="unique")
    op.create_unique_constraint(
        "uq_deadline_reminders_deadline",
        "deadline_reminders",
        ["class_session_id", "deadline", "deadline_at", "user_id"],
        postgresql_nulls_not_distinct=True,
    )


def downgrade() -> None:
    op.execute("DELETE FROM deadline_reminders WHERE user_id IS NOT NULL")
    op.drop_constraint("uq_deadline_reminders_deadline", "deadline_reminders", type_="unique")
    op.create_unique_constraint(
        "uq_deadline_reminders_deadline",
        "deadline_reminders",
        ["class_session_id", "deadline", "deadline_at"],
    )
    op.drop_column("deadline_reminders", "user_id")
    op.drop_table("student_deadline_extensions")
