"""The Institution's data processing agreement (Story 15.12, FR-8, PRD §6.1, AD-12).

Owned by `modules/identity`: `institutions.dpa_signed_by` (who signed for the Institution, as the
Admin typed it), `dpa_signed_on` (the day it was signed) and `dpa_recorded_at` (the api's clock
when the Admin recorded it). All three are NULL while no agreement is recorded, or all are set.
`classes` asks `identity.service.has_processing_agreement` before it sends Student Invitations.

Revision ID: 0071
Revises: 0070
Create Date: 2026-11-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0071"
down_revision: str | None = "0070"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("institutions", sa.Column("dpa_signed_by", sa.Text(), nullable=True))
    op.add_column("institutions", sa.Column("dpa_signed_on", sa.Date(), nullable=True))
    op.add_column(
        "institutions", sa.Column("dpa_recorded_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_check_constraint(
        "ck_institutions_processing_agreement",
        "institutions",
        "(dpa_signed_by IS NULL AND dpa_signed_on IS NULL AND dpa_recorded_at IS NULL) OR "
        "(dpa_signed_by IS NOT NULL AND btrim(dpa_signed_by) <> '' AND dpa_signed_on IS NOT NULL "
        "AND dpa_recorded_at IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_institutions_processing_agreement", "institutions", type_="check")
    op.drop_column("institutions", "dpa_recorded_at")
    op.drop_column("institutions", "dpa_signed_on")
    op.drop_column("institutions", "dpa_signed_by")
