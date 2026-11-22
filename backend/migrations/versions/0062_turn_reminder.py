"""The turn reminder's due time on each turn (Story 8.13, FR-27, AD-9, AD-20).

`seat_turns.reminder_due_at` is when the Student holding the Seat is reminded by mail that the
game waits for them: set with `wait_started_at` by `games.commands` from `games.rules.turn_times`.
`reminder_queued_at` is when the sweep's `games.queue_turn_reminder` queued the reminder, or found
the Seat no longer waited for, so it acts once. A partial index serves the sweep's finder.

No backfill: a turn whose wait started before this revision gets no reminder.

Revision ID: 0062
Revises: 0061
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0062"
down_revision: str | None = "0061"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("seat_turns", sa.Column("reminder_due_at", sa.DateTime(timezone=True)))
    op.add_column("seat_turns", sa.Column("reminder_queued_at", sa.DateTime(timezone=True)))
    op.create_index(
        "ix_seat_turns_reminder_due",
        "seat_turns",
        ["reminder_due_at"],
        postgresql_where=sa.text("reminder_queued_at IS NULL AND reminder_due_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_seat_turns_reminder_due", table_name="seat_turns")
    op.drop_column("seat_turns", "reminder_queued_at")
    op.drop_column("seat_turns", "reminder_due_at")
