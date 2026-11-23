"""Show the Indicative letter where it is allowed (Story 12.6, FR-56, FR-3, AD-12).

Owned by `modules/assessment`:

- `assessment_switches.letter_setting`: `all` (shown to everyone in the Class session),
  `student_choice` (the default: each Student may turn it on for their own view) or
  `unavailable`; `letter_thresholds`: the lower bounds of A to E in whole percent, NULL for the
  configured defaults until the Test-deadline pin stores the ones in force. The pin trigger now
  refuses a change to these two after the pin as well.
- `ai_assessments.letter_chosen`: the Student turned the letter on for their own view.

Owned by `modules/identity`:

- `institutions.no_letter`: the Institution's data protection officer requires that no letter is
  shown; the Admin switches it on the Institution list.

Revision ID: 0206
Revises: 0205
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0206"
down_revision: str | None = "0205"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TRIGGER = """
CREATE OR REPLACE FUNCTION assessment_switches_pinned() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.pinned_at IS NOT NULL AND (
        NEW.class_session_id, NEW.enabled, NEW.pinned_at, NEW.model_config_id, NEW.effort_level
        {extra_new}
    ) IS DISTINCT FROM (
        OLD.class_session_id, OLD.enabled, OLD.pinned_at, OLD.model_config_id, OLD.effort_level
        {extra_old}
    ) THEN
        RAISE EXCEPTION 'a pinned assessment switch does not change'
            USING ERRCODE = 'restrict_violation';
    END IF;
    RETURN NEW;
END $$
"""


def upgrade() -> None:
    op.add_column(
        "assessment_switches",
        sa.Column("letter_setting", sa.Text(), nullable=False, server_default="student_choice"),
    )
    op.add_column("assessment_switches", sa.Column("letter_thresholds", JSONB(), nullable=True))
    op.create_check_constraint(
        "ck_assessment_switches_letter_setting",
        "assessment_switches",
        "letter_setting IN ('all', 'student_choice', 'unavailable')",
    )
    # A switch pinned before this revision pins the bounds in force now (the configured
    # placeholders), so a later change of the configuration never moves its letters. The 0204
    # trigger does not guard this new column yet; the new trigger below does.
    op.execute(
        "UPDATE assessment_switches SET letter_thresholds = "
        '\'{"A": 90, "B": 80, "C": 60, "D": 50, "E": 40}\'::jsonb '
        "WHERE pinned_at IS NOT NULL AND letter_thresholds IS NULL"
    )
    op.add_column(
        "ai_assessments",
        sa.Column("letter_chosen", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "institutions",
        sa.Column("no_letter", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute(
        _TRIGGER.format(
            extra_new=", NEW.letter_setting, NEW.letter_thresholds",
            extra_old=", OLD.letter_setting, OLD.letter_thresholds",
        )
    )


def downgrade() -> None:
    op.execute(_TRIGGER.format(extra_new="", extra_old=""))
    op.drop_column("institutions", "no_letter")
    op.drop_column("ai_assessments", "letter_chosen")
    op.drop_constraint(
        "ck_assessment_switches_letter_setting", "assessment_switches", type_="check"
    )
    op.drop_column("assessment_switches", "letter_thresholds")
    op.drop_column("assessment_switches", "letter_setting")
