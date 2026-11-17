"""Stored Week states and open turns (Story 1.8), owned by modules/games.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "game_weeks",
        sa.Column("game_id", sa.Uuid(), sa.ForeignKey("games.id"), primary_key=True),
        sa.Column("week", sa.Integer(), primary_key=True),
        sa.Column("state", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("week >= 1", name="ck_game_weeks_week"),
    )
    op.create_table(
        "seat_turns",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("game_id", sa.Uuid(), sa.ForeignKey("games.id"), nullable=False),
        sa.Column("seat_id", sa.Uuid(), sa.ForeignKey("seats.id"), nullable=False),
        sa.Column("week", sa.Integer(), nullable=False),
        sa.Column(
            "opened_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("ordered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rule_based_reference_order", sa.Integer(), nullable=False),
        sa.CheckConstraint("week >= 1", name="ck_seat_turns_week"),
        sa.CheckConstraint("rule_based_reference_order >= 0", name="ck_seat_turns_reference_order"),
        sa.UniqueConstraint("game_id", "week", "seat_id", name="uq_seat_turns_game_week_seat"),
    )
    # AD-5 / AD-20: the reference Order is computed once when the Week opens and never again.
    op.execute(
        """
        CREATE FUNCTION seat_turns_keep_opening() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE'
               OR NEW.game_id IS DISTINCT FROM OLD.game_id
               OR NEW.seat_id IS DISTINCT FROM OLD.seat_id
               OR NEW.week IS DISTINCT FROM OLD.week
               OR NEW.opened_at IS DISTINCT FROM OLD.opened_at
               OR NEW.rule_based_reference_order IS DISTINCT FROM OLD.rule_based_reference_order
            THEN
                RAISE EXCEPTION 'seat_turns keeps its opening values: % refused', TG_OP
                    USING ERRCODE = 'restrict_violation';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER seat_turns_keep_opening
        BEFORE UPDATE OR DELETE ON seat_turns
        FOR EACH ROW EXECUTE FUNCTION seat_turns_keep_opening()
        """
    )


def downgrade() -> None:
    op.drop_table("seat_turns")
    op.execute("DROP FUNCTION seat_turns_keep_opening()")
    op.drop_table("game_weeks")
