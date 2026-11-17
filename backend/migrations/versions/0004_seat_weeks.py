"""The Decision log (`seat_weeks`) and the finished Week state (Story 1.9), owned by
modules/games.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DECIDED_BY = ("student", "llm", "rule_based", "scripted", "guided")
FALLBACK = ("none",)
OCCUPANT_KIND = ("student", "llm", "rule_based", "scripted")
REASON = (
    "initial",
    "takeover_inactivity",
    "takeover_staff",
    "takeover_peer",
    "reclaim",
    "guard_switch",
    "cost_limit",
    "playout",
)


def _in(column: str, values: Sequence[str]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


_TURNS_FUNCTION = """
CREATE OR REPLACE FUNCTION seat_turns_keep_opening() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE'
       OR NEW.game_id IS DISTINCT FROM OLD.game_id
       OR NEW.seat_id IS DISTINCT FROM OLD.seat_id
       OR NEW.week IS DISTINCT FROM OLD.week
       OR NEW.opened_at IS DISTINCT FROM OLD.opened_at
       OR NEW.rule_based_reference_order IS DISTINCT FROM OLD.rule_based_reference_order
       {ordered_at}
    THEN
        RAISE EXCEPTION 'seat_turns keeps its opening values: % refused', TG_OP
            USING ERRCODE = 'restrict_violation';
    END IF;
    RETURN NEW;
END;
$$
"""


def _append_only(table: str) -> None:
    op.execute(
        f"""
        CREATE FUNCTION {table}_append_only() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION '{table} is append-only: % refused', TG_OP
                USING ERRCODE = 'restrict_violation';
        END;
        $$
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER {table}_append_only
        BEFORE UPDATE OR DELETE ON {table}
        FOR EACH ROW EXECUTE FUNCTION {table}_append_only()
        """
    )


def upgrade() -> None:
    op.create_table(
        "seat_weeks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("game_id", sa.Uuid(), sa.ForeignKey("games.id"), nullable=False),
        sa.Column("seat_id", sa.Uuid(), sa.ForeignKey("seats.id"), nullable=False),
        sa.Column("week", sa.Integer(), nullable=False),
        sa.Column("state_seen", postgresql.JSONB(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("decided_by", sa.Text(), nullable=False),
        sa.Column("fallback", sa.Text(), nullable=False),
        sa.Column("occupant_kind", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ordered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rule_based_reference_order", sa.Integer(), nullable=False),
        sa.CheckConstraint("week >= 1", name="ck_seat_weeks_week"),
        sa.CheckConstraint('"order" >= 0', name="ck_seat_weeks_order"),
        sa.CheckConstraint("rule_based_reference_order >= 0", name="ck_seat_weeks_reference_order"),
        sa.CheckConstraint(_in("decided_by", DECIDED_BY), name="ck_seat_weeks_decided_by"),
        sa.CheckConstraint(_in("fallback", FALLBACK), name="ck_seat_weeks_fallback"),
        sa.CheckConstraint(_in("occupant_kind", OCCUPANT_KIND), name="ck_seat_weeks_occupant_kind"),
        sa.CheckConstraint(_in("reason", REASON), name="ck_seat_weeks_reason"),
        sa.UniqueConstraint("game_id", "week", "seat_id", name="uq_seat_weeks_game_week_seat"),
    )
    # AD-15: a Decision log row is written once and never changed.
    _append_only("seat_weeks")

    # The finished state carries the last Week's number; it is stored next to the opened Weeks.
    op.add_column(
        "game_weeks",
        sa.Column("finished", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.drop_constraint("game_weeks_pkey", "game_weeks", type_="primary")
    op.create_primary_key("game_weeks_pkey", "game_weeks", ["game_id", "week", "finished"])
    _append_only("game_weeks")

    # An `ordered_at` that is set stays as it is.
    op.execute(
        _TURNS_FUNCTION.format(
            ordered_at="OR (OLD.ordered_at IS NOT NULL "
            "AND NEW.ordered_at IS DISTINCT FROM OLD.ordered_at)"
        )
    )


def downgrade() -> None:
    op.execute(_TURNS_FUNCTION.format(ordered_at=""))
    op.execute("DROP TRIGGER game_weeks_append_only ON game_weeks")
    op.execute("DROP FUNCTION game_weeks_append_only()")
    op.execute("DELETE FROM game_weeks WHERE finished")  # 0003 keeps opened Weeks only
    op.drop_constraint("game_weeks_pkey", "game_weeks", type_="primary")
    op.drop_column("game_weeks", "finished")
    op.create_primary_key("game_weeks_pkey", "game_weeks", ["game_id", "week"])
    op.drop_table("seat_weeks")
    op.execute("DROP FUNCTION seat_weeks_append_only()")
