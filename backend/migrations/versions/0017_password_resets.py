"""Password resets (Story 3.6, FR-4, AD-11).

`password_resets` is owned by `identity`: one row per reset link, holding only the SHA-256 of
its token, with expiry, use and void times. `mail_deliveries` may now be skipped as `stale`, when
a link is no longer usable by the time its mail would leave.

Revision ID: 0017
Revises: 0016
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SKIP_CHECK = "ck_mail_deliveries_skipped_reason"


def upgrade() -> None:
    op.create_table(
        "password_resets",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column(
            "user_id", sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("token_hash", sa.Text, nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_password_resets_user_id", "password_resets", ["user_id"])
    op.drop_constraint(SKIP_CHECK, "mail_deliveries", type_="check")
    op.create_check_constraint(
        SKIP_CHECK,
        "mail_deliveries",
        "skipped_reason IN ('no_recipient', 'unknown_kind', 'send_failed', 'stale')",
    )


def downgrade() -> None:
    op.execute(
        "UPDATE mail_deliveries SET skipped_reason = 'no_recipient' WHERE skipped_reason = 'stale'"
    )
    op.drop_constraint(SKIP_CHECK, "mail_deliveries", type_="check")
    op.create_check_constraint(
        SKIP_CHECK,
        "mail_deliveries",
        "skipped_reason IN ('no_recipient', 'unknown_kind', 'send_failed')",
    )
    op.drop_table("password_resets")
