"""A Student's Oppfølgingsspill (Story 13.4, FR-17, FR-20, AD-13).

- `makeup_games` (owned by `modules/reports`): names each Student's one Oppfølgingsspill in a
  Class session, the `makeup` Game a Lecturer gave them, who gave it and when. The Game itself,
  its Seats and its Weeks are `games` tables, written only by `games.commands`. One per Student
  and Class session, so two presses at once make one Game.

Revision ID: 0302
Revises: 0301
Create Date: 2026-11-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0302"
down_revision: str | None = "0301"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "makeup_games",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "class_session_id",
            sa.Uuid(),
            sa.ForeignKey("class_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "game_id", sa.Uuid(), sa.ForeignKey("games.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("given_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("given_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "class_session_id", name="uq_makeup_games_student"),
        sa.UniqueConstraint("game_id", name="uq_makeup_games_game"),
    )
    op.create_index("ix_makeup_games_class_session_id", "makeup_games", ["class_session_id"])


def downgrade() -> None:
    op.drop_index("ix_makeup_games_class_session_id", table_name="makeup_games")
    op.drop_table("makeup_games")
