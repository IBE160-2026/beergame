"""Score Control test answers blind (Story 12.9, FR-82, AD-12, AD-27).

Owned by `modules/assessment`:

- `control_test_scorers`: the Users the Admin named to score one Control test's answers (who
  named them and when). Personal data (a User's role in a Control test), deleted with the User.
- `human_scores`: one score per answer and scorer on the Scoring guide's five-step scale, written
  once. A trigger refuses every update: a score is never changed afterwards. Personal data (a
  User's judgement), deleted with the scorer.

Revision ID: 0208
Revises: 0207
Create Date: 2026-11-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0208"
down_revision: str | None = "0207"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "control_test_scorers",
        sa.Column(
            "class_session_id",
            sa.Uuid(),
            sa.ForeignKey("class_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "named_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("named_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("class_session_id", "user_id", name="pk_control_test_scorers"),
    )
    op.create_index("ix_control_test_scorers_user", "control_test_scorers", ["user_id"])
    op.create_table(
        "human_scores",
        sa.Column(
            "answer_id",
            sa.Uuid(),
            sa.ForeignKey("test_answers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "scorer_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("score", sa.SmallInteger(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("answer_id", "scorer_id", name="pk_human_scores"),
        sa.CheckConstraint("score BETWEEN 0 AND 4", name="ck_human_scores_score"),
    )
    op.create_index("ix_human_scores_scorer", "human_scores", ["scorer_id"])
    # AD-27: a human score is written once and never changed.
    op.execute(
        """
        CREATE FUNCTION human_scores_immutable() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'a human score does not change';
        END;
        $$
        """
    )
    op.execute(
        "CREATE TRIGGER trg_human_scores_immutable BEFORE UPDATE ON human_scores "
        "FOR EACH ROW EXECUTE FUNCTION human_scores_immutable()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_human_scores_immutable ON human_scores")
    op.execute("DROP FUNCTION human_scores_immutable()")
    op.drop_index("ix_human_scores_scorer", table_name="human_scores")
    op.drop_table("human_scores")
    op.drop_index("ix_control_test_scorers_user", table_name="control_test_scorers")
    op.drop_table("control_test_scorers")
