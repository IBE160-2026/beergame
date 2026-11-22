"""When the sweep announced that a Seat's insert time had passed (Story 8.8, FR-89, AD-8, AD-9).

`seat_turns.insert_announced_at` is set once by `games.commands.announce_insert_time` when the
sweep crosses the turn's `insert_allowed_at`: the Game's version rises and its events are emitted
once, so «Sett inn KI-spiller for …» shows on every open view without a reload. A Lecturer's
Pause command that moves the insert time clears it. No backfill: the finder reads only the open
Week of running Games, where an insert time already passed is announced once at the next sweep.

Revision ID: 0058
Revises: 0057
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0058"
down_revision: str | None = "0057"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("seat_turns", sa.Column("insert_announced_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("seat_turns", "insert_announced_at")
