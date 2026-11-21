"""A Class game's Pause (Story 8.6, FR-89, FR-36, FR-39, AD-2, AD-25).

`games.paused_at`, `paused_by` and `resume_at` are the Pause in force: set by
`games.commands.pause`, cleared by a Student's Order (`place_order`), and later by `resume` (Story
8.7, which also writes `resume_at`, the Lecturer's agreed time). `pause_ended_at` and
`pause_ended_by` keep who ended the last Pause by ordering, so every Student of the game reads
«Pausen er over. Sara har bestilt.» until the next Week opens. Ids only, never a name (AD-14); no
foreign key to `users`, like `seat_occupancy.user_id`.

`game_summaries` gains the Pause in force, and its status check `paused`
(`games.rules.game_status`). No backfill: no Game can be paused before this revision, so every row
`games.overview.recompute` would give equals the stored one with the new columns empty, and
revision 0051's backfill stays as it is.

Revision ID: 0056
Revises: 0055
Create Date: 2026-11-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0056"
down_revision: str | None = "0055"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATUSES_BEFORE = "status IN ('not_started', 'running', 'waiting', 'finished')"
STATUSES = "status IN ('not_started', 'running', 'waiting', 'paused', 'finished')"


def upgrade() -> None:
    op.add_column("games", sa.Column("paused_at", sa.DateTime(timezone=True)))
    op.add_column("games", sa.Column("paused_by", sa.Uuid()))
    op.add_column("games", sa.Column("resume_at", sa.DateTime(timezone=True)))
    op.add_column("games", sa.Column("pause_ended_at", sa.DateTime(timezone=True)))
    op.add_column("games", sa.Column("pause_ended_by", sa.Uuid()))
    op.create_check_constraint(
        "ck_games_pause",
        "games",
        "(paused_by IS NULL AND resume_at IS NULL) OR paused_at IS NOT NULL",
    )
    op.add_column("game_summaries", sa.Column("paused_at", sa.DateTime(timezone=True)))
    op.add_column("game_summaries", sa.Column("paused_by", sa.Uuid()))
    op.drop_constraint("ck_game_summaries_status", "game_summaries", type_="check")
    op.create_check_constraint("ck_game_summaries_status", "game_summaries", STATUSES)


def downgrade() -> None:
    op.execute("UPDATE game_summaries SET status = 'running' WHERE status = 'paused'")
    op.drop_constraint("ck_game_summaries_status", "game_summaries", type_="check")
    op.create_check_constraint("ck_game_summaries_status", "game_summaries", STATUSES_BEFORE)
    op.drop_column("game_summaries", "paused_by")
    op.drop_column("game_summaries", "paused_at")
    op.drop_constraint("ck_games_pause", "games", type_="check")
    for column in ("pause_ended_by", "pause_ended_at", "resume_at", "paused_by", "paused_at"):
        op.drop_column("games", column)
