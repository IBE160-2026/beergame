"""Simulation batches (Story 2.11, AD-22, FR-78): one row per `python -m app.sim run`, the
batch's Games linked by `games.batch_id`, and the Effort level on Decision log rows.

`simulation_batches` holds the batch file, its pass lines, whether it ran on the mock provider
and its start time. A trigger refuses UPDATE and DELETE, so the pass lines can never change
once a Game of the batch exists. Both new columns are nullable: Games and Decision log rows
written before this revision have neither value.

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "simulation_batches",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("batch_file", postgresql.JSONB, nullable=False),
        sa.Column("pass_lines", postgresql.JSONB, nullable=False),
        sa.Column("mock", sa.Boolean, nullable=False),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.execute(
        """
        CREATE FUNCTION simulation_batches_append_only() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'simulation_batches is append-only: % refused', TG_OP
                USING ERRCODE = 'restrict_violation';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER simulation_batches_append_only
        BEFORE UPDATE OR DELETE ON simulation_batches
        FOR EACH ROW EXECUTE FUNCTION simulation_batches_append_only()
        """
    )
    op.add_column(
        "games",
        sa.Column("batch_id", sa.Uuid, sa.ForeignKey("simulation_batches.id"), nullable=True),
    )
    op.create_index("ix_games_batch_id", "games", ["batch_id"])
    op.add_column("seat_weeks", sa.Column("effort_level", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("seat_weeks", "effort_level")
    op.drop_index("ix_games_batch_id", table_name="games")
    op.drop_column("games", "batch_id")
    op.execute("DROP TRIGGER simulation_batches_append_only ON simulation_batches")
    op.execute("DROP FUNCTION simulation_batches_append_only()")
    op.drop_table("simulation_batches")
