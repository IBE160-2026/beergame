"""Each Student's Replay in a Class session (Story 10.3, FR-48, AD-13).

`replays` (owned by `modules/replay`) names the one `replay` Game made for a Student in a Class
session. The unique key on Student and Class session makes two starts at once one Replay.

Revision ID: 0116
Revises: 0115
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0116"
down_revision: str | None = "0115"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "replays",
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
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("user_id", "class_session_id", name="uq_replays_student"),
        sa.UniqueConstraint("game_id", name="uq_replays_game"),
    )
    op.create_index("ix_replays_class_session_id", "replays", ["class_session_id"])


def downgrade() -> None:
    op.drop_table("replays")
