"""Near-optimal reference Order (Story 2.9): the second reference on turns and Decision log rows,
with the version of the algorithm that computed it (FR-67, FR-79, AD-5, AD-15).

Rows written before this revision have neither value, so both columns are nullable; a check
keeps them set together. The `seat_turns` trigger also keeps both once they are set: the
reference is computed once, when the Week opens.

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("seat_turns", "seat_weeks")


def _keep_opening(near_optimal: bool) -> str:
    """The trigger function as 0009 left it, with the near-optimal rule when `near_optimal`."""
    keep_reference = (
        """OR (OLD.near_optimal_reference_order IS NOT NULL
                   AND NEW.near_optimal_reference_order
                       IS DISTINCT FROM OLD.near_optimal_reference_order)
               OR (OLD.near_optimal_algorithm_version IS NOT NULL
                   AND NEW.near_optimal_algorithm_version
                       IS DISTINCT FROM OLD.near_optimal_algorithm_version)"""
        if near_optimal
        else ""
    )
    return f"""
        CREATE OR REPLACE FUNCTION seat_turns_keep_opening() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE'
               OR NEW.game_id IS DISTINCT FROM OLD.game_id
               OR NEW.seat_id IS DISTINCT FROM OLD.seat_id
               OR NEW.week IS DISTINCT FROM OLD.week
               OR NEW.opened_at IS DISTINCT FROM OLD.opened_at
               OR NEW.rule_based_reference_order IS DISTINCT FROM OLD.rule_based_reference_order
               OR (OLD.ordered_at IS NOT NULL AND NEW.ordered_at IS DISTINCT FROM OLD.ordered_at)
               OR (OLD.ai_deadline_at IS NOT NULL
                   AND NEW.ai_deadline_at IS DISTINCT FROM OLD.ai_deadline_at)
               {keep_reference}
            THEN
                RAISE EXCEPTION 'seat_turns keeps its opening values: % refused', TG_OP
                    USING ERRCODE = 'restrict_violation';
            END IF;
            RETURN NEW;
        END;
        $$
        """


def upgrade() -> None:
    for table in TABLES:
        op.add_column(table, sa.Column("near_optimal_reference_order", sa.Integer))
        op.add_column(table, sa.Column("near_optimal_algorithm_version", sa.Text))
        op.create_check_constraint(
            f"ck_{table}_near_optimal_order", table, "near_optimal_reference_order >= 0"
        )
        op.create_check_constraint(
            f"ck_{table}_near_optimal_pair",
            table,
            "(near_optimal_reference_order IS NULL) = (near_optimal_algorithm_version IS NULL)",
        )
    op.execute(_keep_opening(near_optimal=True))


def downgrade() -> None:
    op.execute(_keep_opening(near_optimal=False))
    for table in reversed(TABLES):
        op.drop_constraint(f"ck_{table}_near_optimal_pair", table, type_="check")
        op.drop_constraint(f"ck_{table}_near_optimal_order", table, type_="check")
        op.drop_column(table, "near_optimal_algorithm_version")
        op.drop_column(table, "near_optimal_reference_order")
