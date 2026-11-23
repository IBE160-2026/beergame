"""The Student report's request and snapshot (Story 13.7, FR-57, AD-9, AD-14, AD-18).

- `report_requests` (owned by `modules/reports`): each press of «Lag Studentrapport»: the
  Student, who asked, the variant, the status (`pending`, `ready`, `failed`), the PDF's object
  path and a failure code. One pending render per Student, Class session and variant.
- `report_snapshots`: the assembled report for one render, with the SHA-256 of its single-use
  render token and its 5-minute expiry; deleted when the render ends.

Revision ID: 0304
Revises: 0303
Create Date: 2026-11-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0304"
down_revision: str | None = "0303"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "report_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "class_session_id",
            sa.Uuid(),
            sa.ForeignKey("class_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("requested_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("variant", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("object_path", sa.Text()),
        sa.Column("failure", sa.Text()),
        sa.CheckConstraint(
            "status IN ('pending', 'ready', 'failed')", name="ck_report_requests_status"
        ),
        sa.CheckConstraint("variant IN ('standard')", name="ck_report_requests_variant"),
    )
    op.create_index(
        "ix_report_requests_student",
        "report_requests",
        ["class_session_id", "user_id", "requested_at"],
    )
    op.create_index(
        "uq_report_requests_pending",
        "report_requests",
        ["class_session_id", "user_id", "variant"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_table(
        "report_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "request_id",
            sa.Uuid(),
            sa.ForeignKey("report_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.LargeBinary(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column("data", postgresql.JSONB(), nullable=False),
    )
    op.create_index("ix_report_snapshots_request_id", "report_snapshots", ["request_id"])


def downgrade() -> None:
    op.drop_index("ix_report_snapshots_request_id", table_name="report_snapshots")
    op.drop_table("report_snapshots")
    op.drop_index("uq_report_requests_pending", table_name="report_requests")
    op.drop_index("ix_report_requests_student", table_name="report_requests")
    op.drop_table("report_requests")
