"""The Debrief summary each Student stores by finishing the Debrief (Story 9.8, FR-47, AD-7,
AD-16).

`debrief_summaries` (owned by `modules/debrief`) holds, per Student and Class session, the key
moments by fact id, the reflection answers, the facts set they cite and the completion time,
stored once and never changed: a trigger refuses every update.

Revision ID: 0107
Revises: 0106
Create Date: 2026-11-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0107"
down_revision: str | None = "0106"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "debrief_summaries",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "class_session_id",
            sa.Uuid(),
            sa.ForeignKey("class_sessions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "game_id",
            sa.Uuid(),
            sa.ForeignKey("games.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "fact_set_id",
            sa.Uuid(),
            sa.ForeignKey("fact_sets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("moment_ids", JSONB(), nullable=False),
        sa.Column("reflection", JSONB(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute(
        """
        CREATE FUNCTION debrief_summaries_immutable() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'a Debrief summary is stored once'
                USING ERRCODE = 'restrict_violation';
        END $$
        """
    )
    op.execute(
        "CREATE TRIGGER trg_debrief_summaries_immutable "
        "BEFORE UPDATE ON debrief_summaries "
        "FOR EACH ROW EXECUTE FUNCTION debrief_summaries_immutable()"
    )


def downgrade() -> None:
    op.drop_table("debrief_summaries")
    op.execute("DROP FUNCTION debrief_summaries_immutable()")
