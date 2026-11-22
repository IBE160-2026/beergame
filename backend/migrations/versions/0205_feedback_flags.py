"""Flag feedback, and read assessments as staff (Story 12.5, FR-55, AD-12).

Owned by `modules/assessment`:

- `ai_feedback_flags`: one row per piece of written feedback the Student marked as wrong
  («Marker som feil»), keyed by its assessment and item; «Angre» deletes it. The composite foreign
  key to `ai_item_scores` makes a flag exist only on a stored item score, and removes it with the
  score or the assessment. The Student is the assessment's `user_id`; nothing they wrote is
  stored here.

Revision ID: 0205
Revises: 0204
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0205"
down_revision: str | None = "0204"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_feedback_flags",
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Text(), nullable=False),
        sa.Column("flagged_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("assessment_id", "item_id", name="pk_ai_feedback_flags"),
        sa.ForeignKeyConstraint(
            ["assessment_id", "item_id"],
            ["ai_item_scores.assessment_id", "ai_item_scores.item_id"],
            name="fk_ai_feedback_flags_item_score",
            ondelete="CASCADE",
        ),
    )


def downgrade() -> None:
    op.drop_table("ai_feedback_flags")
