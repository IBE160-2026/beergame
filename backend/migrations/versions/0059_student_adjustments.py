"""A Student's Tilrettelegging in one Class session (Story 8.9, FR-17, AD-14).

`student_adjustments` holds, per Class session and Student, the factor on the Inactivity limit
(«Mer tid før KI tar over»: 1, 1.5, 2 or 3) and the share of Weeks required of that Student (NULL:
the Class session's own). Owned by `modules/sessions`; other modules read it only through
`sessions.service` (`get_adjustment`, `time_factors`). No reason is stored, so no health data. A
User or Class session deleted takes its rows with it.

Revision ID: 0059
Revises: 0058
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0059"
down_revision: str | None = "0058"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "student_adjustments",
        sa.Column(
            "class_session_id",
            sa.Uuid(),
            sa.ForeignKey("class_sessions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("time_factor", sa.Numeric(3, 1), nullable=False),
        sa.Column("share_percent", sa.Integer(), nullable=True),
        sa.Column(
            "updated_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "time_factor IN (1.0, 1.5, 2.0, 3.0)", name="ck_student_adjustments_time_factor"
        ),
        sa.CheckConstraint(
            "share_percent IS NULL OR share_percent BETWEEN 0 AND 100",
            name="ck_student_adjustments_share",
        ),
    )


def downgrade() -> None:
    op.drop_table("student_adjustments")
