"""Written feedback on an AI-assessed item (Story 12.3, FR-54, AD-7).

Owned by `modules/assessment`: `ai_item_scores.feedback` holds the item's feedback as it travels
(`{text, ai_generated, llm_call_id, parts}`, the quotes as spans over the Student's original
answer) when the validator accepted it; `feedback_note` is `dropped` when the feedback was rejected
twice and left out, the score kept. Both stay NULL for an item scored by a score-only prompt
(`assessment/v1`) and for an empty answer (step 0 by code).

Revision ID: 0203
Revises: 0202
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0203"
down_revision: str | None = "0202"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ai_item_scores", sa.Column("feedback", postgresql.JSONB(), nullable=True))
    op.add_column("ai_item_scores", sa.Column("feedback_note", sa.Text(), nullable=True))
    op.create_check_constraint(
        "ck_ai_item_scores_feedback_note",
        "ai_item_scores",
        "feedback_note IS NULL OR feedback_note = 'dropped'",
    )
    op.create_check_constraint(
        "ck_ai_item_scores_feedback",
        "ai_item_scores",
        "source = 'ai' OR (feedback IS NULL AND feedback_note IS NULL)",
    )
    op.create_check_constraint(
        "ck_ai_item_scores_feedback_one",
        "ai_item_scores",
        "feedback IS NULL OR feedback_note IS NULL",
    )


def downgrade() -> None:
    op.drop_constraint("ck_ai_item_scores_feedback_one", "ai_item_scores", type_="check")
    op.drop_constraint("ck_ai_item_scores_feedback", "ai_item_scores", type_="check")
    op.drop_constraint("ck_ai_item_scores_feedback_note", "ai_item_scores", type_="check")
    op.drop_column("ai_item_scores", "feedback_note")
    op.drop_column("ai_item_scores", "feedback")
