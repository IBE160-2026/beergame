"""Class games and the confirmed allocation (Story 5.9, FR-20, AD-2, AD-4, AD-5).

`games`: the five snapshot columns may be NULL together, on a Game whose policy takes its
snapshot at the Class session's lock; `class_session_id` and `game_number` name a Class game's
Class session and its number in it, unique together. `seat_occupancy.user_id`: the Student of a
`student` occupant, ids only (AD-14). Neither has a foreign key: `games` sits below `sessions`, and
occupancy rows are append-only. `allocation_drafts.confirmed_at` and `confirmed_by`: the draft
the Lecturer confirmed.

Revision ID: 0038
Revises: 0037
Create Date: 2026-11-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0038"
down_revision: str | None = "0037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SNAPSHOT = ("settings", "demand_series", "demand_seed", "rules_version", "session_runtime")


def upgrade() -> None:
    for column in SNAPSHOT:
        op.alter_column("games", column, nullable=True)
    op.add_column("games", sa.Column("class_session_id", sa.Uuid(), nullable=True))
    op.add_column("games", sa.Column("game_number", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_games_snapshot", "games", f"num_nulls({', '.join(SNAPSHOT)}) IN (0, {len(SNAPSHOT)})"
    )
    op.create_check_constraint(
        "ck_games_class_session", "games", "(class_session_id IS NULL) = (game_number IS NULL)"
    )
    op.create_check_constraint("ck_games_game_number", "games", "game_number >= 1")
    op.create_unique_constraint(
        "uq_games_class_session_number", "games", ["class_session_id", "game_number"]
    )
    op.add_column("seat_occupancy", sa.Column("user_id", sa.Uuid(), nullable=True))
    op.create_check_constraint(
        "ck_seat_occupancy_user_student",
        "seat_occupancy",
        "occupant_kind = 'student' OR user_id IS NULL",
    )
    op.add_column(
        "allocation_drafts", sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "allocation_drafts",
        sa.Column(
            "confirmed_by",
            sa.Uuid(),
            sa.ForeignKey(
                "users.id", ondelete="SET NULL", name="fk_allocation_drafts_confirmed_by"
            ),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("allocation_drafts", "confirmed_by")
    op.drop_column("allocation_drafts", "confirmed_at")
    op.drop_constraint("ck_seat_occupancy_user_student", "seat_occupancy", type_="check")
    op.drop_column("seat_occupancy", "user_id")
    # A Class game without its snapshot makes the NOT NULL below fail: its occupancy rows are
    # append-only, so the downgrade does not delete it.
    op.drop_constraint("uq_games_class_session_number", "games", type_="unique")
    op.drop_constraint("ck_games_game_number", "games", type_="check")
    op.drop_constraint("ck_games_class_session", "games", type_="check")
    op.drop_constraint("ck_games_snapshot", "games", type_="check")
    op.drop_column("games", "game_number")
    op.drop_column("games", "class_session_id")
    for column in SNAPSHOT:
        op.alter_column("games", column, nullable=False)
