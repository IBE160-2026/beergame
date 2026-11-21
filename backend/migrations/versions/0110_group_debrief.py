"""The Group debrief (Story 9.11, FR-43, AD-21).

`debrief_sessions` gains whether the Debrief session is shared, who opened it and when its current
step opened. `debrief_members` holds the Students who joined a shared Debrief session, and
`debrief_step_marks` each joined Student's «finished» on a shared step after step 1 (step 1 is
finished by the stored Explanation). All owned by `modules/debrief`, written by
`debrief.commands` only.

Revision ID: 0110
Revises: 0109
Create Date: 2026-11-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0110"
down_revision: str | None = "0109"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "debrief_sessions",
        sa.Column("shared", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "debrief_sessions",
        sa.Column(
            "opener_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
    )
    op.add_column(
        "debrief_sessions",
        sa.Column("step_opened_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "debrief_members",
        sa.Column(
            "debrief_id",
            sa.Uuid(),
            sa.ForeignKey("debrief_sessions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "debrief_step_marks",
        sa.Column(
            "debrief_id",
            sa.Uuid(),
            sa.ForeignKey("debrief_sessions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("step", sa.SmallInteger(), primary_key=True),
        sa.Column("done_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("step BETWEEN 2 AND 3", name="ck_debrief_step_marks_step"),
    )


def downgrade() -> None:
    op.drop_table("debrief_step_marks")
    op.drop_table("debrief_members")
    op.drop_column("debrief_sessions", "step_opened_at")
    op.drop_column("debrief_sessions", "opener_id")
    op.drop_column("debrief_sessions", "shared")
