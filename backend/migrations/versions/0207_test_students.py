"""Invite test students who consent before they take part (Story 12.8, FR-82, AD-13, AD-27).

Owned by `modules/identity`:

- `users.is_test_student`: set when a User is created from a Control test's Roster (an accepted
  Invitation or a manual registration); a Control test Roster takes only such Users and an
  ordinary Roster none of them.
- `test_student_consents`: one row per decision a test student takes on Hjem (`given` or
  `declined`), with the version of the text they read and the time. Personal data (a User's
  decision): written and read through `identity.service` only, deleted with the User.

Revision ID: 0207
Revises: 0206
Create Date: 2026-11-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0207"
down_revision: str | None = "0206"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_test_student", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "test_student_consents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("text_version", sa.Text(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "decision IN ('given', 'declined')", name="ck_test_student_consents_decision"
        ),
        sa.CheckConstraint("text_version <> ''", name="ck_test_student_consents_text_version"),
    )
    op.create_index("ix_test_student_consents_user_id", "test_student_consents", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_test_student_consents_user_id", table_name="test_student_consents")
    op.drop_table("test_student_consents")
    op.drop_column("users", "is_test_student")
