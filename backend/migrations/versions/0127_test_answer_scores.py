"""Computed scores on the Individual test's answers (Story 11.10, FR-51, AD-16, AD-23).

- `test_answers.score`: the computed score `tests.commands.submit` stores on a saved answer when
  the attempt is handed in (`{answered, credit, criteria: [{code, weight, met, explanation}]}`);
  null for an answer no computed rule scores (long answers, Adapted items: Epic 12).
- `test_answers.scored_version`: the question set version the score was computed with.

Revision ID: 0127
Revises: 0126
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0127"
down_revision: str | None = "0126"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("test_answers", sa.Column("score", JSONB(), nullable=True))
    op.add_column("test_answers", sa.Column("scored_version", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_test_answers_scored_version",
        "test_answers",
        "score IS NULL OR scored_version IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint("ck_test_answers_scored_version", "test_answers", type_="check")
    op.drop_column("test_answers", "scored_version")
    op.drop_column("test_answers", "score")
