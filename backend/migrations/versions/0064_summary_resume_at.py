"""The agreed time of a paused Class game on the Oversikt (Story 8.7, FR-89, FR-39, AD-25).

`game_summaries.resume_at` holds the Lecturer's agreed time while the Game is `paused`, as
`games.overview.recompute` stores it, so the Oversikt lists the pauses with an agreed time in
«Venter ellers» («Pause i Uke 29, fortsetter to. 19:00») and on the game's row, reading the
summaries only. A paused Game that already has an agreed time when this revision runs gets it
copied from `games`, as a recomputation would give it.

Revision ID: 0064
Revises: 0063
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0064"
down_revision: str | None = "0063"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BACKFILL = """
UPDATE game_summaries gs
SET resume_at = g.resume_at
FROM games g
WHERE g.id = gs.game_id AND gs.status = 'paused' AND g.resume_at IS NOT NULL
"""


def upgrade() -> None:
    op.add_column("game_summaries", sa.Column("resume_at", sa.DateTime(timezone=True)))
    op.execute(BACKFILL)


def downgrade() -> None:
    op.drop_column("game_summaries", "resume_at")
