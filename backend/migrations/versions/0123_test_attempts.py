"""The Individual test's attempts and answers (Story 11.3, FR-51, AD-9, AD-10, AD-23).

- `test_attempts` (owned by `modules/tests`): one per Student and Class session, made when the
  Student accepts the own-work statement: the question set version and selection it was opened
  on, its frozen ordered item list, the Student's effective Test deadline and its status. Later
  stories fill `submitted_at` (11.10, 11.11) and `sitting_ends_at` (11.12).
- `test_answers`: one per attempt and item, the stored answer and its revision (Story 11.4 on).

Revision ID: 0123
Revises: 0122
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0123"
down_revision: str | None = "0122"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "test_attempts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "class_session_id",
            sa.Uuid(),
            sa.ForeignKey("class_sessions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("question_set_version", sa.Integer(), nullable=False),
        sa.Column("selection", JSONB(), nullable=False),
        sa.Column("items", JSONB(), nullable=False),
        sa.Column("statement_accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="open"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sitting_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("question_set_version >= 1", name="ck_test_attempts_version"),
        sa.CheckConstraint(
            "status IN ('open', 'submitted', 'auto_submitted')", name="ck_test_attempts_status"
        ),
        sa.CheckConstraint(
            "(status = 'open') = (submitted_at IS NULL)", name="ck_test_attempts_submitted"
        ),
        sa.UniqueConstraint("user_id", "class_session_id", name="uq_test_attempts_user_session"),
    )
    op.create_table(
        "test_answers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "attempt_id",
            sa.Uuid(),
            sa.ForeignKey("test_attempts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("item_id", sa.Text(), nullable=False),
        sa.Column("value", JSONB(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("saved_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("revision >= 1", name="ck_test_answers_revision"),
        sa.UniqueConstraint("attempt_id", "item_id", name="uq_test_answers_item"),
    )


def downgrade() -> None:
    op.drop_table("test_answers")
    op.drop_table("test_attempts")
