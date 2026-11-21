"""When the game began to wait for a Seat in its open Week (Story 6.14, FR-25, AD-20).

`seat_turns.wait_started_at` is set once, by `games.commands` only (`place_order` for a Student's
own Order, `view_week` in a Guided Week), on the open Week's turns that have not ordered when the
first Student orders or views: the clock every wait is counted from. The `seat_turns` trigger
keeps it once set, like `viewed_at`.

Revision ID: 0048
Revises: 0047
Create Date: 2026-11-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0048"
down_revision: str | None = "0047"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _keep_opening(waits: bool) -> str:
    """The trigger function as 0047 left it, with the `wait_started_at` rule when `waits`."""
    keep_wait = (
        "OR (OLD.wait_started_at IS NOT NULL"
        " AND NEW.wait_started_at IS DISTINCT FROM OLD.wait_started_at)"
        if waits
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
               OR (OLD.near_optimal_reference_order IS NOT NULL
                   AND NEW.near_optimal_reference_order
                       IS DISTINCT FROM OLD.near_optimal_reference_order)
               OR (OLD.near_optimal_algorithm_version IS NOT NULL
                   AND NEW.near_optimal_algorithm_version
                       IS DISTINCT FROM OLD.near_optimal_algorithm_version)
               OR (OLD.viewed_at IS NOT NULL AND NEW.viewed_at IS DISTINCT FROM OLD.viewed_at)
               {keep_wait}
            THEN
                RAISE EXCEPTION 'seat_turns keeps its opening values: % refused', TG_OP
                    USING ERRCODE = 'restrict_violation';
            END IF;
            RETURN NEW;
        END;
        $$
        """


def upgrade() -> None:
    op.add_column("seat_turns", sa.Column("wait_started_at", sa.DateTime(timezone=True)))
    op.execute(_keep_opening(waits=True))


def downgrade() -> None:
    op.execute(_keep_opening(waits=False))
    op.drop_column("seat_turns", "wait_started_at")
