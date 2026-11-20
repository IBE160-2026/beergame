"""The allocation draft of a Class session (Story 5.8, FR-20), owned by `sessions`.

One current draft per Class session: its id, a revision that starts at 1, the seed it was drawn
with, the assignments as `user_id`, game number and Role (ids only, AD-14), and who drew it. A new
draw replaces the row under a new id.

Revision ID: 0037
Revises: 0036
Create Date: 2026-11-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0037"
down_revision: str | None = "0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "allocation_drafts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "class_session_id",
            sa.Uuid(),
            sa.ForeignKey("class_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("seed", sa.BigInteger(), nullable=False),
        sa.Column("assignments", postgresql.JSONB(), nullable=False),
        sa.Column(
            "drawn_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("drawn_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("revision >= 1", name="ck_allocation_drafts_revision"),
        sa.UniqueConstraint("class_session_id", name="uq_allocation_drafts_class_session"),
    )


def downgrade() -> None:
    op.drop_table("allocation_drafts")
