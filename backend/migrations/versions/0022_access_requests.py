"""Requests for lecturer access from the public Landing (Story 3.13, FR-1), owned by `identity`.

A request is `open` until the Admin invites from it (`invited`, with the Invitation) or dismisses
it (`dismissed`). At most one request is open per address (`uq_access_requests_open`). Times come
from the api's clock. A request never creates a User or an Invitation by itself.

Revision ID: 0022
Revises: 0021
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "access_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("institution", sa.Text(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="open"),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "closed_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column(
            "invitation_id",
            sa.Uuid(),
            sa.ForeignKey("invitations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "email = lower(btrim(email))", name="ck_access_requests_email_normalised"
        ),
        sa.CheckConstraint(
            "status IN ('open', 'invited', 'dismissed')", name="ck_access_requests_status"
        ),
    )
    op.create_index(
        "uq_access_requests_open",
        "access_requests",
        ["email"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
    )


def downgrade() -> None:
    op.drop_index("uq_access_requests_open", table_name="access_requests")
    op.drop_table("access_requests")
