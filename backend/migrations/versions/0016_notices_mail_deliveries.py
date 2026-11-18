"""Notices and mail deliveries (Story 3.5, AD-9, AD-14).

`notices` is owned by `platform/notify`: one row per request to tell someone, unique on
`dedupe_key`, ids only. `mail_deliveries` is owned by `messaging`: one row per mail, with the
notices it carried, the send time and the provider's message id.

Revision ID: 0016
Revises: 0015
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notices",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("user_id", sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("kind", sa.Text, nullable=False),
        sa.Column("dedupe_key", sa.Text, nullable=False, unique=True),
        sa.Column("ref", sa.Uuid, nullable=True),
        sa.Column("not_before", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("user_id IS NOT NULL OR ref IS NOT NULL", name="ck_notices_recipient"),
    )
    op.create_index(
        "ix_notices_unclaimed",
        "notices",
        ["kind", "not_before"],
        postgresql_where=sa.text("claimed_at IS NULL"),
    )
    op.create_table(
        "mail_deliveries",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("user_id", sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("mode", sa.Text, nullable=False),
        sa.Column("notice_ids", postgresql.ARRAY(sa.Uuid), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_message_id", sa.Text, nullable=True),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("skipped_reason", sa.Text, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("mode IN ('immediate', 'digest')", name="ck_mail_deliveries_mode"),
        sa.CheckConstraint(
            "skipped_reason IN ('no_recipient', 'unknown_kind', 'send_failed')",
            name="ck_mail_deliveries_skipped_reason",
        ),
    )
    op.create_index(
        "ix_mail_deliveries_user_mode_claimed",
        "mail_deliveries",
        ["user_id", "mode", "claimed_at"],
    )
    op.create_index(
        "ix_mail_deliveries_unsent",
        "mail_deliveries",
        ["claimed_at"],
        postgresql_where=sa.text("sent_at IS NULL AND skipped_reason IS NULL"),
    )


def downgrade() -> None:
    op.drop_table("mail_deliveries")
    op.drop_table("notices")
