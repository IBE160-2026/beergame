"""When the sweep saw a Lecturer's agreed Pause time pass (Story 8.7, FR-89, AD-8, AD-9).

`games.agreed_time_reached_at` is set once by `games.commands.reach_agreed_time` when the sweep
crosses `resume_at`: the Pause goes on and no AI player takes a Seat, but the Game's version rises
and its events are emitted once, so every open view reads it again and the right to put in an AI
player can show. `pause`, `set_agreed_time` and `resume` clear it with the agreed time, and a
Student's Order that ends the Pause clears it too. The check keeps it NULL without an agreed time.
No backfill: no Game has an agreed time before this revision.

Revision ID: 0057
Revises: 0056
Create Date: 2026-11-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0057"
down_revision: str | None = "0056"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("games", sa.Column("agreed_time_reached_at", sa.DateTime(timezone=True)))
    op.create_check_constraint(
        "ck_games_agreed_time_reached",
        "games",
        "agreed_time_reached_at IS NULL OR resume_at IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint("ck_games_agreed_time_reached", "games", type_="check")
    op.drop_column("games", "agreed_time_reached_at")
