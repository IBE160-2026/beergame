"""Where a staged Roster came from (Story 4.3, FR-7): an uploaded file or pasted addresses.

Expand-only: existing stagings are files.

Revision ID: 0025
Revises: 0024
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "roster_uploads",
        sa.Column("source", sa.Text(), nullable=False, server_default="file"),
    )
    op.create_check_constraint(
        "ck_roster_uploads_source", "roster_uploads", "source IN ('file', 'paste')"
    )


def downgrade() -> None:
    op.drop_constraint("ck_roster_uploads_source", "roster_uploads", type_="check")
    op.drop_column("roster_uploads", "source")
