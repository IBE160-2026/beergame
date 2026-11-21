"""The Debrief opens (Story 9.2, FR-42, AD-21, AD-25).

`class_sessions.debrief_release` (owned by `modules/sessions`) holds the Lecturer's choice:
`open`, each Student's Debrief opens when their own Class game has finished (the default), or
`hold`, every Debrief waits until all Class games have finished. `debrief_sessions` (owned by
`modules/debrief`) holds one Debrief session per Game with its step pointer, and
`debrief_releases` the once-only release of a held Class session by the sweep.

Revision ID: 0102
Revises: 0101
Create Date: 2026-11-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0102"
down_revision: str | None = "0101"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "class_sessions",
        sa.Column("debrief_release", sa.Text(), nullable=False, server_default="open"),
    )
    op.create_check_constraint(
        "ck_class_sessions_debrief_release",
        "class_sessions",
        "debrief_release IN ('open', 'hold')",
    )
    op.create_table(
        "debrief_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "game_id",
            sa.Uuid(),
            sa.ForeignKey("games.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "class_session_id",
            sa.Uuid(),
            sa.ForeignKey("class_sessions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("step", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("game_id", name="uq_debrief_sessions_game"),
        sa.CheckConstraint("step BETWEEN 1 AND 5", name="ck_debrief_sessions_step"),
    )
    op.create_table(
        "debrief_releases",
        sa.Column(
            "class_session_id",
            sa.Uuid(),
            sa.ForeignKey("class_sessions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("debrief_releases")
    op.drop_table("debrief_sessions")
    op.drop_constraint("ck_class_sessions_debrief_release", "class_sessions", type_="check")
    op.drop_column("class_sessions", "debrief_release")
