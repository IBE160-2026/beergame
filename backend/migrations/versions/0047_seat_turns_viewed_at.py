"""When a Student opened a Guided Week (Story 6.10, FR-24, AD-20).

`seat_turns.viewed_at` is set once, by `games.commands.view_week`, on a Student-held Seat's turn
in a Guided Week: viewing counts as ordering there (founder decision 2026-11-12). The
`seat_turns` trigger keeps it once set, like `ordered_at`.

Revision ID: 0047
Revises: 0046
Create Date: 2026-11-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0047"
down_revision: str | None = "0046"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _keep_opening(viewed: bool) -> str:
    """The trigger function as 0012 left it, with the `viewed_at` rule when `viewed`."""
    keep_viewed = (
        "OR (OLD.viewed_at IS NOT NULL AND NEW.viewed_at IS DISTINCT FROM OLD.viewed_at)"
        if viewed
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
               {keep_viewed}
            THEN
                RAISE EXCEPTION 'seat_turns keeps its opening values: % refused', TG_OP
                    USING ERRCODE = 'restrict_violation';
            END IF;
            RETURN NEW;
        END;
        $$
        """


def upgrade() -> None:
    op.add_column("seat_turns", sa.Column("viewed_at", sa.DateTime(timezone=True)))
    op.execute(_keep_opening(viewed=True))


def downgrade() -> None:
    op.execute(_keep_opening(viewed=False))
    op.drop_column("seat_turns", "viewed_at")
