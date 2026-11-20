"""Lab hours of a Class session (Story 5.6, FR-19), owned by `sessions`.

One row per Lab hour: its start and end (UTC), its place, a revision raised by each change, and
`cancelled_at` once the Lecturer removes it. A removed Lab hour is kept so that the cancellation
notice, which holds its id only, can still name it when the digest is sent.

Revision ID: 0035
Revises: 0034
Create Date: 2026-11-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0035"
down_revision: str | None = "0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lab_hours",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "class_session_id",
            sa.Uuid(),
            sa.ForeignKey("class_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("place", sa.Text(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("ends_at > starts_at", name="ck_lab_hours_order"),
        sa.CheckConstraint("char_length(place) BETWEEN 1 AND 120", name="ck_lab_hours_place"),
    )
    op.create_index("ix_lab_hours_class_session_id", "lab_hours", ["class_session_id"])


def downgrade() -> None:
    op.drop_index("ix_lab_hours_class_session_id", table_name="lab_hours")
    op.drop_table("lab_hours")
