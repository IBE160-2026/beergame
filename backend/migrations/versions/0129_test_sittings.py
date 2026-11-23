"""One timed sitting for the Individual test (Story 11.12, FR-51, FR-17, AD-9).

- `test_sittings`: a Class session's time limit in whole minutes, stored through `tests.service`
  when the Lecturer saves the Klasseøkt; a row means the test is taken in one timed sitting, no
  row means it is not. Who changed it last (`updated_by`) and when.
- `ix_test_attempts_due_sitting`: the finder of `tests.end_sitting` over the open attempts with a
  sitting end (`test_attempts.sitting_ends_at`, a column of revision 0123).

Revision ID: 0129
Revises: 0128
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0129"
down_revision: str | None = "0128"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "test_sittings",
        sa.Column(
            "class_session_id",
            sa.Uuid(),
            sa.ForeignKey("class_sessions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("minutes", sa.Integer(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("minutes > 0", name="ck_test_sittings_minutes"),
    )
    op.create_index(
        "ix_test_attempts_due_sitting",
        "test_attempts",
        ["sitting_ends_at"],
        postgresql_where=sa.text("status = 'open' AND sitting_ends_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_test_attempts_due_sitting", table_name="test_attempts")
    op.drop_table("test_sittings")
