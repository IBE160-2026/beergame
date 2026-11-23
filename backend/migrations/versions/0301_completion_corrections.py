"""A Lecturer's correction of one step of a Student's Completion status (Story 13.3, FR-17,
AD-15, AD-16).

- `completion_corrections` (owned by `modules/progress`): one row per correction, never changed
  (a trigger refuses UPDATE, except the actor set to NULL when that User is deleted); a later
  correction of the same step is a new row and the latest applies. The Student, the Class
  session, the step, the new status, the reason, who corrected it and when. The reason is the
  Lecturer's free text about the Student: personal data.

Revision ID: 0301
Revises: 0209
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0301"
down_revision: str | None = "0209"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STEPS = ("class_game", "debrief", "quiz_passed", "replay", "test_submitted")


def upgrade() -> None:
    op.create_table(
        "completion_corrections",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "class_session_id",
            sa.Uuid(),
            sa.ForeignKey("class_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step", sa.Text(), nullable=False),
        sa.Column("done", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "step IN (" + ", ".join(f"'{step}'" for step in STEPS) + ")",
            name="ck_completion_corrections_step",
        ),
        sa.CheckConstraint(
            "char_length(btrim(reason)) BETWEEN 1 AND 1000",
            name="ck_completion_corrections_reason",
        ),
    )
    op.create_index(
        "ix_completion_corrections_student",
        "completion_corrections",
        ["class_session_id", "user_id"],
    )
    op.execute(
        """
        CREATE FUNCTION completion_corrections_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            -- The one change allowed: the actor's foreign key set to NULL when that User is
            -- deleted (ON DELETE SET NULL); everything else stays as stored.
            IF NEW.actor_user_id IS NULL
                AND (to_jsonb(NEW) - 'actor_user_id') = (to_jsonb(OLD) - 'actor_user_id') THEN
                RETURN NEW;
            END IF;
            RAISE EXCEPTION 'a correction is stored once and never changed'
                USING ERRCODE = 'restrict_violation';
        END $$
        """
    )
    op.execute(
        "CREATE TRIGGER trg_completion_corrections_immutable BEFORE UPDATE ON "
        "completion_corrections FOR EACH ROW EXECUTE FUNCTION completion_corrections_immutable()"
    )


def downgrade() -> None:
    op.drop_table("completion_corrections")
    op.execute("DROP FUNCTION completion_corrections_immutable()")
