"""Games, Seats and Seat occupancy (Story 1.7), owned by modules/games.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def upgrade() -> None:
    op.create_table(
        "games",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("lifecycle", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("settings", postgresql.JSONB(), nullable=False),
        sa.Column("demand_series", postgresql.JSONB(), nullable=False),
        sa.Column("demand_seed", sa.BigInteger(), nullable=False),
        sa.Column("rules_version", sa.Integer(), nullable=False),
        sa.Column("session_runtime", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            _in("purpose", ("class", "replay", "makeup", "lecturer_test", "simulation")),
            name="ck_games_purpose",
        ),
        sa.CheckConstraint(
            _in("lifecycle", ("not_started", "running", "playing_out", "finished")),
            name="ck_games_lifecycle",
        ),
        sa.CheckConstraint("version >= 0", name="ck_games_version"),
    )
    op.create_table(
        "seats",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("game_id", sa.Uuid(), sa.ForeignKey("games.id"), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.UniqueConstraint("game_id", "role", name="uq_seats_game_role"),
        sa.UniqueConstraint("game_id", "position", name="uq_seats_game_position"),
    )
    op.create_table(
        "seat_occupancy",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("seat_id", sa.Uuid(), sa.ForeignKey("seats.id"), nullable=False),
        sa.Column("from_week", sa.Integer(), nullable=False),
        sa.Column("occupant_kind", sa.Text(), nullable=False),
        sa.Column("policy_id", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("from_week >= 1", name="ck_seat_occupancy_from_week"),
        sa.CheckConstraint(
            _in("occupant_kind", ("student", "llm", "rule_based", "scripted")),
            name="ck_seat_occupancy_kind",
        ),
        sa.CheckConstraint(
            _in(
                "reason",
                (
                    "initial",
                    "takeover_inactivity",
                    "takeover_staff",
                    "takeover_peer",
                    "reclaim",
                    "guard_switch",
                    "cost_limit",
                    "playout",
                ),
            ),
            name="ck_seat_occupancy_reason",
        ),
    )
    op.create_index("ix_seat_occupancy_seat_id", "seat_occupancy", ["seat_id"])
    # AD-5: occupancy is a history; rows are appended, never changed or removed.
    op.execute(
        """
        CREATE FUNCTION seat_occupancy_append_only() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'seat_occupancy is append-only: % refused', TG_OP
                USING ERRCODE = 'restrict_violation';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER seat_occupancy_append_only
        BEFORE UPDATE OR DELETE ON seat_occupancy
        FOR EACH ROW EXECUTE FUNCTION seat_occupancy_append_only()
        """
    )


def downgrade() -> None:
    op.drop_table("seat_occupancy")
    op.execute("DROP FUNCTION seat_occupancy_append_only()")
    op.drop_table("seats")
    op.drop_table("games")
