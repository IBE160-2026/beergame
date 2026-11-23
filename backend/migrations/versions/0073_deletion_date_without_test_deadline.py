"""A deletion date for a Class session without a Test deadline (Epic 15 close-out, FR-77, AD-9).

`platform.retention.deletion_base`: a Class session with no Test deadline now counts its retention
period from the latest of its other dates (Debrieffrist, Spillfrist, Startdato), so its Student
data is deleted too. Existing rows with no Test deadline and at least one other date are filled
with their Institution's period, or the placeholder six months (`RETENTION_MONTHS`) where it has
none; Postgres clamps a day past the month's end as `platform.retention.add_months` does.

Revision ID: 0073
Revises: 0072
Create Date: 2026-11-23
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0073"
down_revision: str | None = "0072"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE class_sessions AS cs
        SET deletion_date = (
            (
                greatest(cs.debrief_deadline, cs.play_deadline, cs.start_at)
                AT TIME ZONE 'Europe/Oslo'
            )::date
            + make_interval(months => coalesce(i.retention_months, 6))
        )::date
        FROM classes AS c
        LEFT JOIN institutions AS i ON i.id = c.institution_id
        WHERE c.id = cs.class_id
          AND cs.test_deadline IS NULL
          AND cs.deletion_date IS NULL
          AND cs.data_deleted_at IS NULL
          AND greatest(cs.debrief_deadline, cs.play_deadline, cs.start_at) IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute(
        "UPDATE class_sessions SET deletion_date = NULL "
        "WHERE test_deadline IS NULL AND data_deleted_at IS NULL"
    )
