"""A User may have no password yet (Story 4.8, FR-9), owned by `identity`.

A Lecturer's manual registration creates the Student's User without a password; the Student sets
the first one through a single-use «Nytt passord» link. Until then the account cannot log in.

Expand-only: no existing row changes. The downgrade gives every User still without a password
the unusable hash `'!'`, which never verifies, so it stays locked out as before.

Revision ID: 0030
Revises: 0029
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0030"
down_revision: str | None = "0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("users", "password_hash", existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    op.execute("UPDATE users SET password_hash = '!' WHERE password_hash IS NULL")
    op.alter_column("users", "password_hash", existing_type=sa.Text(), nullable=False)
