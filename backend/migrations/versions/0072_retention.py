"""Retention (Story 15.3, FR-77, FR-3, AD-9, AD-14).

`institutions.retention_months` (owned by `modules/identity`): the Institution's retention period
in whole calendar months, set by the Admin; NULL means the configured placeholder
(`RETENTION_MONTHS`). `class_sessions.data_deleted_at` (owned by `modules/sessions`): when the
sweep's retention finished deleting the Class session's Student data; NULL until then.

Revision ID: 0072
Revises: 0071
Create Date: 2026-11-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0072"
down_revision: str | None = "0071"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("institutions", sa.Column("retention_months", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_institutions_retention_months",
        "institutions",
        "retention_months IS NULL OR (retention_months >= 1 AND retention_months <= 120)",
    )
    op.add_column(
        "class_sessions", sa.Column("data_deleted_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("class_sessions", "data_deleted_at")
    op.drop_constraint("ck_institutions_retention_months", "institutions", type_="check")
    op.drop_column("institutions", "retention_months")
