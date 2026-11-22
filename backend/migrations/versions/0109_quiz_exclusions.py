"""Debrief quiz exclusions (Story 9.10, FR-46, AD-23).

`quiz_exclusions` (owned by `modules/debrief`) holds one row per Debrief quiz question a Lecturer
has taken out of a Class session's quiz: a Class session row, never an edit of the `content`
record. Lifting an exclusion deletes its row; both are recorded through `platform/audit`.

Revision ID: 0109
Revises: 0108
Create Date: 2026-11-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0109"
down_revision: str | None = "0108"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "quiz_exclusions",
        sa.Column(
            "class_session_id",
            sa.Uuid(),
            sa.ForeignKey("class_sessions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("question_id", sa.Text(), primary_key=True),
        sa.Column("quiz_version", sa.Integer(), nullable=False),
        sa.Column("excluded_by", sa.Uuid(), nullable=True),
        sa.Column("excluded_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("quiz_exclusions")
