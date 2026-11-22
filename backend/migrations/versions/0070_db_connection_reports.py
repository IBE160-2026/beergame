"""The connections each process says it holds (Story 15.9, NFR-3, NFR-4, AD-24).

`db_connection_reports` holds one row per process start: the process (`backend`, `worker-ai`,
`worker-batch`) and the database connections it is configured to hold (its SQLAlchemy pool, its
procrastinate pool, its LISTEN connection). «Drift» sums the latest row per process against the
written connection budget (`docs/ops/connection-budget.md`). Counts only; the newest ten rows per
process are kept.

Revision ID: 0070
Revises: 0069
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0070"
down_revision: str | None = "0069"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "db_connection_reports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("process", sa.Text(), nullable=False),
        sa.Column("sqlalchemy_pool", sa.SmallInteger(), nullable=False),
        sa.Column("job_pool", sa.SmallInteger(), nullable=False),
        sa.Column("listen", sa.SmallInteger(), nullable=False),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "process IN ('backend', 'worker-ai', 'worker-batch')",
            name="ck_db_connection_reports_process",
        ),
        sa.CheckConstraint(
            "sqlalchemy_pool >= 0 AND job_pool >= 0 AND listen >= 0",
            name="ck_db_connection_reports_counts",
        ),
    )
    op.create_index(
        "ix_db_connection_reports_process_time",
        "db_connection_reports",
        ["process", "reported_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_db_connection_reports_process_time", table_name="db_connection_reports")
    op.drop_table("db_connection_reports")
