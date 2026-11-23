"""A Message to the Students who have not met the requirement (Story 13.6, FR-17, FR-40, AD-9).

- `messages.recipient_kind` may be `requirement_not_met`: the Students of an Obligatory class
  session who had not met the requirement when the Message was sent, resolved then through
  `reports.service`. Like a Message to the whole Class session it names no game and no Student;
  its recipients are its `message_recipients` rows.

Revision ID: 0303
Revises: 0302
Create Date: 2026-11-23
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0303"
down_revision: str | None = "0302"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BEFORE = "recipient_kind IN ('student', 'class_game', 'class_session', 'list')"
AFTER = (
    "recipient_kind IN ('student', 'class_game', 'class_session', 'list', 'requirement_not_met')"
)


def upgrade() -> None:
    op.drop_constraint("ck_messages_recipient_kind", "messages", type_="check")
    op.create_check_constraint("ck_messages_recipient_kind", "messages", AFTER)


def downgrade() -> None:
    # Such a Message is kept as a list of Students: its `message_recipients` rows say whom.
    op.execute(
        "UPDATE messages SET recipient_kind = 'list' WHERE recipient_kind = 'requirement_not_met'"
    )
    op.drop_constraint("ck_messages_recipient_kind", "messages", type_="check")
    op.create_check_constraint("ck_messages_recipient_kind", "messages", BEFORE)
