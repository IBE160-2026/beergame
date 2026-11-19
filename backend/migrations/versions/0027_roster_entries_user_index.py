"""The Classes a Student is in (Story 4.5, AD-12): `authz.classes_enrolled_by` reads Roster
entries by `user_id` on every Student request, so the column gets an index.

Expand-only.

Revision ID: 0027
Revises: 0026
Create Date: 2026-11-19
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0027"
down_revision: str | None = "0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_roster_entries_user_id", "roster_entries", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_roster_entries_user_id", table_name="roster_entries")
