"""The ZIP of all Student reports of a Class session (Story 13.13, FR-59, AD-9, AD-14, AD-18).

- `report_zips`: each press of «Last ned alle Studentrapporter (ZIP)», its status and the ZIP's
  object path; one pending per Class session.
- `report_snapshots` gains a second owner, `zip_id`: a snapshot belongs to one single report's
  request or to one ZIP, exactly one of the two, so the print route stays one path.

Revision ID: 0308
Revises: 0307
Create Date: 2026-11-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0308"
down_revision: str | None = "0307"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "report_zips",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "class_session_id",
            sa.Uuid(),
            sa.ForeignKey("class_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("requested_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("object_path", sa.Text()),
        sa.Column("failure", sa.Text()),
        sa.Column("students", sa.Integer()),
        sa.CheckConstraint(
            "status IN ('pending', 'ready', 'failed')", name="ck_report_zips_status"
        ),
    )
    op.create_index("ix_report_zips_session", "report_zips", ["class_session_id", "requested_at"])
    op.create_index(
        "uq_report_zips_pending",
        "report_zips",
        ["class_session_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.add_column(
        "report_snapshots",
        sa.Column("zip_id", sa.Uuid(), sa.ForeignKey("report_zips.id", ondelete="CASCADE")),
    )
    op.create_index("ix_report_snapshots_zip_id", "report_snapshots", ["zip_id"])
    op.alter_column("report_snapshots", "request_id", nullable=True)
    op.create_check_constraint(
        "ck_report_snapshots_owner",
        "report_snapshots",
        "(request_id IS NULL) <> (zip_id IS NULL)",
    )


def downgrade() -> None:
    # A ZIP's snapshots live only while its job renders; they go with the table.
    op.execute("DELETE FROM report_snapshots WHERE zip_id IS NOT NULL")
    op.drop_constraint("ck_report_snapshots_owner", "report_snapshots", type_="check")
    op.alter_column("report_snapshots", "request_id", nullable=False)
    op.drop_index("ix_report_snapshots_zip_id", table_name="report_snapshots")
    op.drop_column("report_snapshots", "zip_id")
    op.drop_index("uq_report_zips_pending", table_name="report_zips")
    op.drop_index("ix_report_zips_session", table_name="report_zips")
    op.drop_table("report_zips")
