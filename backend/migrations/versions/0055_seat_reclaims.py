"""A Student's queued Reclaim of their Seat (Story 8.4, FR-37, AD-2, AD-5).

`seat_reclaims` holds at most one request per Seat: the Student whose Seat an AI player took over
pressed «Ta tilbake setet». It changes no occupancy; the command that opens the next Week appends
the `reclaim` occupancy row and deletes the request. Ids only, never a name (AD-14); no foreign key
to `users`, like `seat_occupancy.user_id`.

Revision ID: 0055
Revises: 0054
Create Date: 2026-11-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0055"
down_revision: str | None = "0054"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "seat_reclaims",
        sa.Column("seat_id", sa.Uuid(), sa.ForeignKey("seats.id"), primary_key=True),
        sa.Column("game_id", sa.Uuid(), sa.ForeignKey("games.id"), nullable=False, index=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    op.drop_table("seat_reclaims")
