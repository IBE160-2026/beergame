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
SKIP_REASONS = ("no_recipient", "unknown_kind", "send_failed", "stale")
DELIVERY_STATES = ("delayed", "delivered", "bounced")
"""What the provider last reported of a sent mail (Story 4.6), in the order a state may move: a
later report never moves it back, so a replayed or late event changes nothing."""
BOUNCE_CLASSES = ("hard", "soft")
"""A permanent bounce is `hard`, every other `soft`; `hard` is never turned back into `soft`."""

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
    # What the provider's webhook reported (Story 4.6): the state, a bounce's class, and the id of
    # the last event stored, so a repeated event is recognised.
    Column("delivery_state", Text, nullable=True),
    Column("bounce_class", Text, nullable=True),
    Column("last_event_id", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(
        f"mode IN ({', '.join(repr(m) for m in MODES)})", name="ck_mail_deliveries_mode"
    ),
    CheckConstraint(
        f"skipped_reason IN ({', '.join(repr(r) for r in SKIP_REASONS)})",
        name="ck_mail_deliveries_skipped_reason",
    ),
    CheckConstraint(
        f"delivery_state IN ({', '.join(repr(s) for s in DELIVERY_STATES)})",
        name="ck_mail_deliveries_delivery_state",
    ),
    CheckConstraint(
        f"bounce_class IN ({', '.join(repr(c) for c in BOUNCE_CLASSES)})",
        name="ck_mail_deliveries_bounce_class",
    ),
    CheckConstraint(
        "(delivery_state IS NOT DISTINCT FROM 'bounced') = (bounce_class IS NOT NULL)",
        name="ck_mail_deliveries_bounce_fields",
    ),
    Index("ix_mail_deliveries_provider_message_id", "provider_message_id"),
    Index("ix_mail_deliveries_user_mode_claimed", "user_id", "mode", "claimed_at"),
    Index(
        "ix_mail_deliveries_unsent",
        "claimed_at",
        postgresql_where="sent_at IS NULL AND skipped_reason IS NULL",
    ),
)
"""One row per mail: the notices it carried, when it was claimed and sent, and the provider's
message id, and what the provider reported of it later (Story 4.6). A `mail` job that finds its
row sent (or skipped) sends nothing. Ids only."""
