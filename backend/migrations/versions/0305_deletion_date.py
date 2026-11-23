"""The Class session's deletion date (Story 13.9, FR-77, FR-57, AD-9).

- `class_sessions.deletion_date`: the day its Student data is deleted, the latest effective Test
  deadline (its own or the latest Student extension, Story 11.13) on the Europe/Oslo calendar
  plus the retention period; NULL without a Test deadline. Existing rows are filled with the
  placeholder period of six months (`RETENTION_MONTHS`), the rule of `platform.retention`:
  Postgres clamps a day past the month's end the same way.
- `class_sessions.deletion_reminded_at`: when the sweep reminded its Students.

Revision ID: 0305
Revises: 0304
Create Date: 2026-11-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0305"
down_revision: str | None = "0304"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("class_sessions", sa.Column("deletion_date", sa.Date(), nullable=True))
    op.add_column(
        "class_sessions",
        sa.Column("deletion_reminded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        """
        UPDATE class_sessions AS cs
        SET deletion_date = (
            (
                greatest(
                    cs.test_deadline,
                    (
                        SELECT max(e.test_deadline)
                        FROM student_deadline_extensions AS e
                        WHERE e.class_session_id = cs.id
                    )
                ) AT TIME ZONE 'Europe/Oslo'
            )::date
            + interval '6 months'
        )::date
        WHERE cs.test_deadline IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_column("class_sessions", "deletion_reminded_at")
    op.drop_column("class_sessions", "deletion_date")
