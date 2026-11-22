"""Who triggered a change of a Seat's occupant (Story 8.2, AD-5, AD-14, AD-15).

`seat_occupancy.actor_user_id` is the id of the person behind a row: the staff member of a
`takeover_staff`, the Student who pressed for a `takeover_peer`, the Student of a `reclaim` (set by
the later stories of Epic 8). Rows no person triggers (`initial`, `takeover_inactivity`,
`guard_switch`, `cost_limit`, `playout`, `moved`) never name one: a check constraint keeps it NULL.
The id only, never a name; names are resolved at read time. No foreign key: the rows are
append-only, like `user_id`.

Revision ID: 0054
Revises: 0053
Create Date: 2026-11-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0054"
down_revision: str | None = "0053"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ACTORLESS = "'initial', 'takeover_inactivity', 'guard_switch', 'cost_limit', 'playout', 'moved'"


def upgrade() -> None:
    op.add_column("seat_occupancy", sa.Column("actor_user_id", sa.Uuid(), nullable=True))
    op.create_check_constraint(
        "ck_seat_occupancy_actor",
        "seat_occupancy",
        f"actor_user_id IS NULL OR reason NOT IN ({ACTORLESS})",
    )


def downgrade() -> None:
    op.drop_constraint("ck_seat_occupancy_actor", "seat_occupancy", type_="check")
    op.drop_column("seat_occupancy", "actor_user_id")
