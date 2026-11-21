"""Continue alone when the group is not there (Story 9.12, FR-43, AD-21).

`debrief_members` gains `last_seen_at`, written on each SSE heartbeat of a joined Student
(`debrief.commands.touch`). `debrief_alone` holds each Student of a shared Debrief session who goes
on as a Personal debrief: by leaving, by dropping out (two minutes without a heartbeat), by the
48-hour fallback, or because the group finished its shared steps without them (`missed`), with
the shared step they were on. `debrief_sessions` gains the fallback's due time,
computed from the Game's finish time, and when it ran. All owned by `modules/debrief`, written by
`debrief.commands` only.

Revision ID: 0111
Revises: 0110
Create Date: 2026-11-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0111"
down_revision: str | None = "0110"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "debrief_members",
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_debrief_members_user_id", "debrief_members", ["user_id"])
    op.add_column(
        "debrief_sessions",
        sa.Column("fallback_due_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "debrief_sessions",
        sa.Column("fallback_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "debrief_alone",
        sa.Column(
            "debrief_id",
            sa.Uuid(),
            sa.ForeignKey("debrief_sessions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("step", sa.SmallInteger(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("since", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "reason IN ('left', 'dropout', 'fallback', 'missed')", name="ck_debrief_alone_reason"
        ),
        sa.CheckConstraint("step BETWEEN 1 AND 3", name="ck_debrief_alone_step"),
    )
    # Shared sessions opened before this revision fall back 48 hours after their Game finished
    # (its finished Week state), or after their open when that state is missing.
    op.execute(
        "UPDATE debrief_sessions s SET fallback_due_at = coalesce("
        "(SELECT w.created_at FROM game_weeks w WHERE w.game_id = s.game_id AND w.finished),"
        " s.opened_at) + interval '48 hours' WHERE s.shared"
    )


def downgrade() -> None:
    op.drop_table("debrief_alone")
    op.drop_column("debrief_sessions", "fallback_at")
    op.drop_column("debrief_sessions", "fallback_due_at")
    op.drop_index("ix_debrief_members_user_id", table_name="debrief_members")
    op.drop_column("debrief_members", "last_seen_at")
