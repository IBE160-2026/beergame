"""The staff's variants of the Student report (Story 13.12, FR-59, FR-58, FR-56).

- `report_requests.variant` gains `staff` (made by the staff of the Class, no AI data) and
  `staff_ai` (with the AI assessment section, never the Indicative letter). The staff's PDFs are
  their own requests, pending locks and objects, apart from the Student's own.

Revision ID: 0307
Revises: 0306
Create Date: 2026-11-23
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0307"
down_revision: str | None = "0306"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_report_requests_variant", "report_requests", type_="check")
    op.create_check_constraint(
        "ck_report_requests_variant",
        "report_requests",
        "variant IN ('standard', 'ai', 'ai_letter', 'staff', 'staff_ai')",
    )


def downgrade() -> None:
    # The staff's PDFs go with their rows; their objects expire with the retention.
    op.execute("DELETE FROM report_requests WHERE variant IN ('staff', 'staff_ai')")
    op.drop_constraint("ck_report_requests_variant", "report_requests", type_="check")
    op.create_check_constraint(
        "ck_report_requests_variant",
        "report_requests",
        "variant IN ('standard', 'ai', 'ai_letter')",
    )
