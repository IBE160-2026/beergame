"""Per-session error counts (Story 15.8, NFR-8, AD-14).

`error_events` holds one row per counted error: its source (the finished-game check, a job that
failed for good, an api answer of 5xx), a fixed code, the Class session when one is known and the
request or job id. Ids and codes only, written by `ops.service.record_error`; the rows are kept at
retention, since they hold no personal data.

Revision ID: 0069
Revises: 0068
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0069"
down_revision: str | None = "0068"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "error_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("class_session_id", sa.Uuid(), nullable=True),
        sa.Column("request_id", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "source IN ('conservation_check', 'job_failed', 'api_error')",
            name="ck_error_events_source",
        ),
        sa.CheckConstraint("code ~ '^[a-z0-9_.:-]{1,80}$'", name="ck_error_events_code"),
        sa.CheckConstraint(
            "request_id IS NULL OR length(request_id) <= 64", name="ck_error_events_request_id"
        ),
    )
    op.create_index(
        "ix_error_events_session_time", "error_events", ["class_session_id", "occurred_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_error_events_session_time", table_name="error_events")
    op.drop_table("error_events")
