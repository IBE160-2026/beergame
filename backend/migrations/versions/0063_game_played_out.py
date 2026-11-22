"""When the Play deadline playout took a Game over (Story 8.14, FR-38, AD-2, AD-9).

`games.played_out_at` is set once by `games.commands.playout`, in the transaction that sets
`lifecycle = playing_out`, and kept after `finish`: «Spillet er ferdig» says the game ended at the
Spillfrist, a person's command answers `play_deadline_passed`, and the sweep logs a Game still
playing out past the allowed time. A partial index serves that finder.

Revision ID: 0063
Revises: 0062
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0063"
down_revision: str | None = "0062"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("games", sa.Column("played_out_at", sa.DateTime(timezone=True)))
    op.create_index(
        "ix_games_playing_out",
        "games",
        ["played_out_at"],
        postgresql_where=sa.text("lifecycle = 'playing_out'"),
    )


def downgrade() -> None:
    op.drop_index("ix_games_playing_out", table_name="games")
    op.drop_column("games", "played_out_at")
