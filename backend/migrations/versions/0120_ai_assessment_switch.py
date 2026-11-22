"""The «KI-vurdering» switch of a Class session and the Test-deadline lock (Story 12.1, FR-61,
AD-9).

- `assessment_switches` (owned by `modules/assessment`): the switch per Class session, on by
  default (no row reads as on), and when the Test-deadline lock pinned it. A trigger refuses any
  update of a pinned row.
- `class_sessions.test_locked_at` (owned by `modules/sessions`): when `sessions.lock_test` ran for
  the session's original Test deadline; NULL until then.

Revision ID: 0120
Revises: 0119
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0120"
down_revision: str | None = "0119"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "class_sessions", sa.Column("test_locked_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_table(
        "assessment_switches",
        sa.Column(
            "class_session_id",
            sa.Uuid(),
            sa.ForeignKey("class_sessions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("pinned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.execute(
        """
        CREATE FUNCTION assessment_switches_pinned() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.pinned_at IS NOT NULL THEN
                RAISE EXCEPTION 'a pinned assessment switch does not change'
                    USING ERRCODE = 'restrict_violation';
            END IF;
            RETURN NEW;
        END $$
        """
    )
    op.execute(
        "CREATE TRIGGER trg_assessment_switches_pinned BEFORE UPDATE ON assessment_switches "
        "FOR EACH ROW EXECUTE FUNCTION assessment_switches_pinned()"
    )


def downgrade() -> None:
    op.drop_table("assessment_switches")
    op.execute("DROP FUNCTION assessment_switches_pinned()")
    op.drop_column("class_sessions", "test_locked_at")
