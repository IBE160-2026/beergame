"""The session version of a User (Story 3.10, AD-11, Issue #73).

The session cookie carries the version it was issued at; every request checks it against
`users.session_version`. Deactivating a User and confirming a password reset raise it, so every
session the User had before ends, also after a reactivation. Tokens issued before this migration
carry no version and read as 0, which is every User's version here.

Revision ID: 0020
Revises: 0019
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("session_version", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )


def downgrade() -> None:
    op.drop_column("users", "session_version")
