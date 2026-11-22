"""Be told when the AI assessment is ready (Story 12.4, FR-54, FR-55, FR-61, FR-69, AD-9).

Owned by `modules/assessment`:

- `ai_assessments.due_at`: the attempt's `effective_deadline`, stored when `tests.close_attempt`
  creates the row and defers the job; the sweep's `assessment.overdue` action counts the 24-hour
  target from it (rows made before this migration take their attempt's deadline here).
  `overdue_at`: when that action logged the assessment as overdue (once).
- `assessment_switches.stopped_at` / `stopped_by`: the stop mark of `stop_for_session` (the
  cost limit, or the Admin's choice), cleared by `resume_for_session`. The pin trigger of 0120 now
  refuses a change to the pinned columns only, so the mark can be set and cleared after the pin.

Revision ID: 0204
Revises: 0203
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0204"
down_revision: str | None = "0203"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PINNED_ONLY = """
CREATE OR REPLACE FUNCTION assessment_switches_pinned() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.pinned_at IS NOT NULL AND (
        NEW.class_session_id, NEW.enabled, NEW.pinned_at, NEW.model_config_id, NEW.effort_level
    ) IS DISTINCT FROM (
        OLD.class_session_id, OLD.enabled, OLD.pinned_at, OLD.model_config_id, OLD.effort_level
    ) THEN
        RAISE EXCEPTION 'a pinned assessment switch does not change'
            USING ERRCODE = 'restrict_violation';
    END IF;
    RETURN NEW;
END $$
"""

ANY_CHANGE = """
CREATE OR REPLACE FUNCTION assessment_switches_pinned() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.pinned_at IS NOT NULL THEN
        RAISE EXCEPTION 'a pinned assessment switch does not change'
            USING ERRCODE = 'restrict_violation';
    END IF;
    RETURN NEW;
END $$
"""


def upgrade() -> None:
    op.add_column("ai_assessments", sa.Column("due_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "ai_assessments", sa.Column("overdue_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.execute(
        "UPDATE ai_assessments a SET due_at = t.effective_deadline "
        "FROM test_attempts t WHERE t.id = a.attempt_id AND a.due_at IS NULL"
    )
    op.create_index(
        "ix_ai_assessments_unsettled",
        "ai_assessments",
        ["due_at"],
        postgresql_where=sa.text("status = 'incomplete'"),
    )
    op.add_column(
        "assessment_switches", sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "assessment_switches",
        sa.Column(
            "stopped_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
    )
    op.execute(PINNED_ONLY)


def downgrade() -> None:
    op.execute(ANY_CHANGE)
    op.drop_column("assessment_switches", "stopped_by")
    op.drop_column("assessment_switches", "stopped_at")
    op.drop_index("ix_ai_assessments_unsettled", table_name="ai_assessments")
    op.drop_column("ai_assessments", "overdue_at")
    op.drop_column("ai_assessments", "due_at")
