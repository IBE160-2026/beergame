"""Why a Game ended without its last Week (Story 10.6, AD-2, AD-13).

`games.end_reason` is set by `games.commands.close` together with `lifecycle = finished`: the only
value is `test_deadline` (an unfinished Replay closed at its Student's Test deadline). Every other
Game keeps it NULL, also one that finished through `finish`.

Revision ID: 0117
Revises: 0116
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0117"
down_revision: str | None = "0116"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("games", sa.Column("end_reason", sa.Text(), nullable=True))
    op.create_check_constraint("ck_games_end_reason", "games", "end_reason IN ('test_deadline')")
    op.create_check_constraint(
        "ck_games_end_reason_finished", "games", "end_reason IS NULL OR lifecycle = 'finished'"
    )


def downgrade() -> None:
    op.drop_constraint("ck_games_end_reason_finished", "games", type_="check")
    op.drop_constraint("ck_games_end_reason", "games", type_="check")
    op.drop_column("games", "end_reason")
