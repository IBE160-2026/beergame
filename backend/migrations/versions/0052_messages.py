"""Messages from staff to Students (Story 7.9, FR-40, AD-9, AD-14): `messages` and
`message_recipients`, owned by `modules/messaging`. Ids, text and times only.

Revision ID: 0052
Revises: 0051
Create Date: 2026-11-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0052"
down_revision: str | None = "0051"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("key", sa.Uuid(), nullable=False, unique=True),
        sa.Column(
            "class_session_id", sa.Uuid(), sa.ForeignKey("class_sessions.id"), nullable=False
        ),
        sa.Column("sender_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("recipient_kind", sa.Text(), nullable=False),
        sa.Column("recipient_game_id", sa.Uuid(), sa.ForeignKey("games.id"), nullable=True),
        sa.Column("recipient_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "recipient_kind IN ('student', 'class_game', 'class_session', 'list')",
            name="ck_messages_recipient_kind",
        ),
        sa.CheckConstraint(
            "(recipient_kind = 'class_game') = (recipient_game_id IS NOT NULL) "
            "OR recipient_kind = 'student'",
            name="ck_messages_recipient_game",
        ),
        sa.CheckConstraint(
            "(recipient_kind = 'student') = (recipient_user_id IS NOT NULL)",
            name="ck_messages_recipient_user",
        ),
    )
    op.create_index(
        "ix_messages_recipient",
        "messages",
        ["class_session_id", "recipient_kind", "recipient_game_id", "recipient_user_id"],
    )
    op.create_table(
        "message_recipients",
        sa.Column(
            "message_id",
            sa.Uuid(),
            sa.ForeignKey("messages.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
        ),
    )
    op.create_index("ix_message_recipients_user", "message_recipients", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_message_recipients_user", table_name="message_recipients")
    op.drop_table("message_recipients")
    op.drop_index("ix_messages_recipient", table_name="messages")
    op.drop_table("messages")
