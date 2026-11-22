"""Who started a Game and when (Story 8.10, FR-22, AD-2, AD-15).

`games.started_at` and `started_by` are written once by `games.commands.start`: the transaction's
clock, and the Student or Lecturer who pressed «Start spillet» (NULL when no person did, as a
simulation). A Lecturer's start that loses the race to a Student reads them for its `acted_by`.
Ids only, no foreign key to `users`, like `paused_by`. No backfill: a Game started before this
revision reads as started by no one, at no known time.

Revision ID: 0060
Revises: 0059
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0060"
down_revision: str | None = "0059"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("games", sa.Column("started_at", sa.DateTime(timezone=True)))
    op.add_column("games", sa.Column("started_by", sa.Uuid()))
    op.create_check_constraint(
        "ck_games_started", "games", "started_by IS NULL OR started_at IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_constraint("ck_games_started", "games", type_="check")
    op.drop_column("games", "started_by")
    op.drop_column("games", "started_at")
