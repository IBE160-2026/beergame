"""The request for a new Invitation (Story 3.8, FR-1).

`invitations.renewal_requested_at` is set when the holder of an expired or voided link asks for a
new one from «Du er invitert». The Admin's list shows it (Story 3.10), and a resend clears it.

Revision ID: 0019
Revises: 0018
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "invitations",
        sa.Column("renewal_requested_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("invitations", "renewal_requested_at")
