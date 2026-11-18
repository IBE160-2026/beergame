"""Invitations and the audit log (Story 3.7, FR-1, FR-3, AD-11, AD-15).

`invitations` is owned by `identity`: one row per Invitation to the Lecturer or Admin role,
holding the address, the role, only the SHA-256 of its token, the expiry, and when it was accepted
or voided. A partial unique index keeps one open Invitation per address and role.

`audit_events` is owned by `platform/audit`: one row per Admin or system action, ids and codes
only. A trigger refuses UPDATE and DELETE.

Revision ID: 0018
Revises: 0017
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "invitations",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("email", sa.Text, nullable=False),
        sa.Column("role", sa.Text, nullable=False),
        sa.Column("token_hash", sa.Text, nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "invited_by", sa.Uuid, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.CheckConstraint("email = lower(btrim(email))", name="ck_invitations_email_normalised"),
        sa.CheckConstraint("role IN ('admin', 'lecturer')", name="ck_invitations_role"),
    )
    op.create_index("ix_invitations_email", "invitations", ["email"])
    op.create_index(
        "uq_invitations_open",
        "invitations",
        ["email", "role"],
        unique=True,
        postgresql_where=sa.text("accepted_at IS NULL AND voided_at IS NULL"),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("actor_user_id", sa.Uuid, nullable=True),
        sa.Column("action", sa.Text, nullable=False),
        sa.Column("target_ids", JSONB, nullable=False),
        sa.Column("change", JSONB, nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_occurred_at", "audit_events", ["occurred_at"])
    # AD-15: the audit log is a history; rows are appended, never changed or removed.
    op.execute(
        """
        CREATE FUNCTION audit_events_append_only() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'audit_events is append-only: % refused', TG_OP
                USING ERRCODE = 'restrict_violation';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_events_append_only
        BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION audit_events_append_only()
        """
    )


def downgrade() -> None:
    op.drop_table("audit_events")
    op.execute("DROP FUNCTION audit_events_append_only()")
    op.drop_table("invitations")
