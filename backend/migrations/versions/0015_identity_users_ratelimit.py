"""Accounts and login rate limits (Story 3.2, AD-11, AD-14, AD-24).

`users` and `user_roles` are the `identity` module's first tables: names and e-mails live only
here. E-mails are stored trimmed and lower-cased, so the unique constraint is case-insensitive.
`rate_limit_counters` is owned by `platform/ratelimit` and holds hashed keys only.

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("email", sa.Text, nullable=False, unique=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("email = lower(btrim(email))", name="ck_users_email_normalised"),
    )
    op.create_table(
        "user_roles",
        sa.Column(
            "user_id",
            sa.Uuid,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("role", sa.Text, primary_key=True),
        sa.Column(
            "granted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("role IN ('admin', 'lecturer')", name="ck_user_roles_role"),
    )
    op.create_table(
        "rate_limit_counters",
        sa.Column("bucket", sa.Text, primary_key=True),
        sa.Column("key_hash", sa.Text, primary_key=True),
        sa.Column("window_start", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("count", sa.Integer, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("rate_limit_counters")
    op.drop_table("user_roles")
    op.drop_table("users")
