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

RECIPIENT_KINDS = ("student", "class_game", "class_session", "list", "requirement_not_met")
"""Whom a Message was written to (Story 7.9): one Student, a Class game, a whole Class session,
a list of Students a calling module passed (Epic 13), or the Students of an Obligatory class
session who had not met the requirement when it was sent (Story 13.6)."""

messages = Table(
    "messages",
    metadata,
    Column("id", Uuid, primary_key=True),
    # The client-made key of the send: a repeated request finds its Message and sends nothing.
    Column("key", Uuid, nullable=False, unique=True),
    Column("class_session_id", Uuid, ForeignKey("class_sessions.id"), nullable=False),
    Column("sender_id", Uuid, ForeignKey("users.id"), nullable=False),
    Column("recipient_kind", Text, nullable=False),
    Column("recipient_game_id", Uuid, ForeignKey("games.id"), nullable=True),
    Column("recipient_user_id", Uuid, ForeignKey("users.id"), nullable=True),
    Column("text", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(
        f"recipient_kind IN ({', '.join(repr(k) for k in RECIPIENT_KINDS)})",
        name="ck_messages_recipient_kind",
    ),
    CheckConstraint(
        "(recipient_kind = 'class_game') = (recipient_game_id IS NOT NULL) "
        "OR recipient_kind = 'student'",
        name="ck_messages_recipient_game",
    ),
    CheckConstraint(
        "(recipient_kind = 'student') = (recipient_user_id IS NOT NULL)",
        name="ck_messages_recipient_user",
    ),
    Index(
        "ix_messages_recipient",
        "class_session_id",
        "recipient_kind",
        "recipient_game_id",
        "recipient_user_id",
    ),
)
"""One row per Message a staff member sent (Story 7.9, AD-14): the text, its Class session, the
sender and whom it was written to, by id. No name or address is copied here. A Message to one
Student may name the Class game it was written from (`recipient_game_id`), for its title."""

message_recipients = Table(
    "message_recipients",
    metadata,
    Column(
        "message_id",
        Uuid,
        ForeignKey("messages.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Index("ix_message_recipients_user", "user_id"),
)
"""One row per Student a Message went to, resolved when it was sent (Story 7.9)."""
