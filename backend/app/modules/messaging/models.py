"""Tables owned by `modules/messaging` (AD-9, AD-14)."""

from sqlalchemy import (
    ARRAY,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Table,
    Text,
    Uuid,
    func,
)

from app.platform.db import metadata

MODES = ("immediate", "digest")
SKIP_REASONS = ("no_recipient", "unknown_kind", "send_failed")

mail_deliveries = Table(
    "mail_deliveries",
    metadata,
    Column("id", Uuid, primary_key=True),
    # NULL for a mail to a recipient named by reference (an Invitation's address).
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
    Column("mode", Text, nullable=False),
    Column("notice_ids", ARRAY(Uuid), nullable=False),
    Column("claimed_at", DateTime(timezone=True), nullable=False),
    Column("sent_at", DateTime(timezone=True), nullable=True),
    Column("provider_message_id", Text, nullable=True),
    Column("attempts", Integer, nullable=False, server_default="0"),
    Column("skipped_reason", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(
        f"mode IN ({', '.join(repr(m) for m in MODES)})", name="ck_mail_deliveries_mode"
    ),
    CheckConstraint(
        f"skipped_reason IN ({', '.join(repr(r) for r in SKIP_REASONS)})",
        name="ck_mail_deliveries_skipped_reason",
    ),
    Index("ix_mail_deliveries_user_mode_claimed", "user_id", "mode", "claimed_at"),
    Index(
        "ix_mail_deliveries_unsent",
        "claimed_at",
        postgresql_where="sent_at IS NULL AND skipped_reason IS NULL",
    ),
)
"""One row per mail: the notices it carried, when it was claimed and sent, and the provider's
message id. A `mail` job that finds its row sent (or skipped) sends nothing. Ids only."""
