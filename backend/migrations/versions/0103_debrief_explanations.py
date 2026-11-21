"""The Explanation before the reveal (Story 9.3, FR-41, AD-14).

`debrief_explanations` (owned by `modules/debrief`) holds one Explanation per Student per Class
session, stored once as typed with its length in characters and its time, and never changed: a
trigger refuses every update.

Revision ID: 0103
Revises: 0102
Create Date: 2026-11-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0103"
down_revision: str | None = "0102"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "debrief_explanations",
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
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("length", sa.Integer(), nullable=False),
        sa.Column("saved_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length = char_length(text) AND length BETWEEN 1 AND 5000",
            name="ck_debrief_explanations_length",
        ),
    )
    op.execute(
        """
        CREATE FUNCTION debrief_explanations_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'an Explanation is stored once and never changed'
                USING ERRCODE = 'restrict_violation';
        END $$
        """
    )
    op.execute(
        "CREATE TRIGGER trg_debrief_explanations_immutable BEFORE UPDATE ON debrief_explanations "
        "FOR EACH ROW EXECUTE FUNCTION debrief_explanations_immutable()"
    )


def downgrade() -> None:
    op.drop_table("debrief_explanations")
    op.execute("DROP FUNCTION debrief_explanations_immutable()")
