"""The Student report's variants with the AI assessment section (Story 13.11, FR-58, FR-56).

- `report_requests.variant`: `standard` (no AI data), `ai` (the AI assessment section) or
  `ai_letter` (the section with the Indicative letter the Student's own view shows). Each variant
  is its own request, pending lock and stored PDF, so a download without the section never
  serves a PDF with it.

Revision ID: 0306
Revises: 0305
Create Date: 2026-11-23
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0306"
down_revision: str | None = "0305"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_report_requests_variant", "report_requests", type_="check")
    op.create_check_constraint(
        "ck_report_requests_variant",
        "report_requests",
        "variant IN ('standard', 'ai', 'ai_letter')",
    )


def downgrade() -> None:
    # The PDFs with the AI section go with their rows; their objects expire with the retention.
    op.execute("DELETE FROM report_requests WHERE variant <> 'standard'")
    op.drop_constraint("ck_report_requests_variant", "report_requests", type_="check")
    op.create_check_constraint(
        "ck_report_requests_variant", "report_requests", "variant IN ('standard')"
    )
