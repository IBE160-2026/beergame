"""A Class game marked as «I rommet» during a Lab hour (Story 8.11, FR-36, AD-2, AD-9, AD-20).

`games.in_room_minutes`, `in_room_until`, `in_room_lab_hour_id`, `in_room_by` and
`in_room_marked_at` are the mark in force: written by `games.commands.mark_in_room` and cleared by
`end_in_room` (by a person, by the sweep at the Lab hour's end, or when the Lab hour is removed or
moved). The in-room limit replaces the Inactivity limit in `games.rules.turn_times`. Ids only, no
foreign key to `users` or `lab_hours`, like `paused_by`.

`game_summaries` gains `in_room_until`, the wall's «I rommet» mark. No backfill: no Game can be
marked before this revision, so every row `games.overview.recompute` gives equals the stored one
with the new column empty.

Revision ID: 0061
Revises: 0060
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0061"
down_revision: str | None = "0060"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TOGETHER = (
    "(in_room_minutes IS NULL AND in_room_until IS NULL AND in_room_lab_hour_id IS NULL"
    " AND in_room_marked_at IS NULL AND in_room_by IS NULL)"
    " OR (in_room_minutes IS NOT NULL AND in_room_until IS NOT NULL"
    " AND in_room_lab_hour_id IS NOT NULL AND in_room_marked_at IS NOT NULL)"
)


def upgrade() -> None:
    op.add_column("games", sa.Column("in_room_minutes", sa.SmallInteger()))
    op.add_column("games", sa.Column("in_room_until", sa.DateTime(timezone=True)))
    op.add_column("games", sa.Column("in_room_lab_hour_id", sa.Uuid()))
    op.add_column("games", sa.Column("in_room_by", sa.Uuid()))
    op.add_column("games", sa.Column("in_room_marked_at", sa.DateTime(timezone=True)))
    op.create_check_constraint("ck_games_in_room", "games", TOGETHER)
    op.create_check_constraint(
        "ck_games_in_room_minutes",
        "games",
        "in_room_minutes IS NULL OR in_room_minutes BETWEEN 2 AND 120",
    )
    op.add_column("game_summaries", sa.Column("in_room_until", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("game_summaries", "in_room_until")
    op.drop_constraint("ck_games_in_room_minutes", "games", type_="check")
    op.drop_constraint("ck_games_in_room", "games", type_="check")
    for column in (
        "in_room_marked_at",
        "in_room_by",
        "in_room_lab_hour_id",
        "in_room_until",
        "in_room_minutes",
    ):
        op.drop_column("games", column)
