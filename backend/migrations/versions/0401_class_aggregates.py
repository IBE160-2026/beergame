"""The aggregates of Cross-class statistics (Story 14.3, FR-65, AD-9, AD-14).

`class_aggregates` (owned by `modules/reports`): one header per Class session with when
`reports.write_aggregate` wrote it, its group sizes and the keys a comparison must hold equal.
`class_aggregate_measures`: one scalar figure per measure code, or the mark that its group held
fewer than 10 Students (`withheld`, no value). No `user_id`, `seat_id`, Game id, name or free
text: the rows survive the deletion of the Student data (Story 15.3).

Revision ID: 0401
Revises: 0073
Create Date: 2026-11-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0401"
down_revision: str | None = "0073"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "class_aggregates",
        sa.Column("class_session_id", sa.Uuid(), nullable=False),
        sa.Column("written_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("students", sa.Integer(), nullable=False),
        sa.Column("game_students", sa.Integer(), nullable=False),
        sa.Column("games_finished", sa.Integer(), nullable=False),
        sa.Column("keys", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint(
            "students >= 0 AND game_students >= 0 AND games_finished >= 0",
            name="ck_class_aggregates_counts",
        ),
        sa.ForeignKeyConstraint(["class_session_id"], ["class_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("class_session_id"),
    )
    op.create_table(
        "class_aggregate_measures",
        sa.Column("class_session_id", sa.Uuid(), nullable=False),
        sa.Column("measure", sa.Text(), nullable=False),
        sa.Column("group_size", sa.Integer(), nullable=False),
        sa.Column("value", sa.Numeric(), nullable=True),
        sa.Column("withheld", sa.Boolean(), nullable=False),
        sa.CheckConstraint("group_size >= 0", name="ck_class_aggregate_measures_group"),
        sa.CheckConstraint(
            "NOT withheld OR value IS NULL", name="ck_class_aggregate_measures_withheld"
        ),
        sa.ForeignKeyConstraint(
            ["class_session_id"], ["class_aggregates.class_session_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("class_session_id", "measure", name="pk_class_aggregate_measures"),
    )


def downgrade() -> None:
    op.drop_table("class_aggregate_measures")
    op.drop_table("class_aggregates")
