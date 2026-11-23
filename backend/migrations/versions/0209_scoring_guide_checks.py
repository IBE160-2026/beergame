"""Mark a Scoring guide version as checked for a model config (Story 12.10, FR-81, AD-27).

Owned by `modules/content`:

- `scoring_guide_checks`: one row per Scoring guide version and model config that a Control test
  has checked (every named scorer scored every listed answer), with the Control test and the time.
  `content.service.is_checked` reads it, `mark_checked` writes it (called only by `assessment`).
  The first check of a pair stays; a trigger refuses every update. `control_test_id` has no
  foreign key: the check outlives the Control test, as an edited guide outlives its Class
  session. No personal data.

Revision ID: 0209
Revises: 0208
Create Date: 2026-11-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0209"
down_revision: str | None = "0208"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scoring_guide_checks",
        sa.Column(
            "scoring_guide_id",
            sa.Uuid(),
            sa.ForeignKey("content_records.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        # No foreign key: only `app/ai` owns the model config table (AD-6), as for
        # `class_sessions.model_config_id`; a referenced config never changes or goes.
        sa.Column("model_config_id", sa.Uuid(), nullable=False),
        sa.Column("control_test_id", sa.Uuid(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "scoring_guide_id", "model_config_id", name="pk_scoring_guide_checks"
        ),
    )
    op.execute(
        """
        CREATE FUNCTION scoring_guide_checks_immutable() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'a Scoring guide check does not change';
        END;
        $$
        """
    )
    op.execute(
        "CREATE TRIGGER trg_scoring_guide_checks_immutable BEFORE UPDATE ON scoring_guide_checks "
        "FOR EACH ROW EXECUTE FUNCTION scoring_guide_checks_immutable()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_scoring_guide_checks_immutable ON scoring_guide_checks")
    op.execute("DROP FUNCTION scoring_guide_checks_immutable()")
    op.drop_table("scoring_guide_checks")
