"""The Roster and Student Invitations (Story 4.4, FR-7, FR-8, AD-14, AD-24), owned by `identity`.

`roster_entries` holds one row per address on a Class's Roster. `invitations` gains a kind:
`role` (every existing row, Story 3.7) or `student`, which names its Class and Roster entry and
offers no account role, so `role` becomes nullable.

Expand-only: existing Invitations are `role` Invitations and keep their role.

Revision ID: 0026
Revises: 0025
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "roster_entries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "class_id",
            sa.Uuid(),
            sa.ForeignKey("classes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("registration", sa.Text(), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "email = lower(btrim(email))", name="ck_roster_entries_email_normalised"
        ),
        sa.CheckConstraint(
            "registration IN ('invited', 'registered')", name="ck_roster_entries_registration"
        ),
    )
    op.create_index(
        "uq_roster_entries_class_email", "roster_entries", ["class_id", "email"], unique=True
    )

    op.alter_column("invitations", "role", existing_type=sa.Text(), nullable=True)
    op.add_column(
        "invitations", sa.Column("kind", sa.Text(), nullable=False, server_default="role")
    )
    op.add_column(
        "invitations",
        sa.Column(
            "class_id", sa.Uuid(), sa.ForeignKey("classes.id", ondelete="CASCADE"), nullable=True
        ),
    )
    op.add_column(
        "invitations",
        sa.Column(
            "roster_entry_id",
            sa.Uuid(),
            sa.ForeignKey("roster_entries.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index("ix_invitations_roster_entry_id", "invitations", ["roster_entry_id"])
    op.create_check_constraint("ck_invitations_kind", "invitations", "kind IN ('role', 'student')")
    op.create_check_constraint(
        "ck_invitations_kind_fields",
        "invitations",
        "(kind = 'role') = (role IS NOT NULL) "
        "AND (kind = 'student') = (class_id IS NOT NULL AND roster_entry_id IS NOT NULL)",
    )
    op.create_index(
        "uq_invitations_open_roster_entry",
        "invitations",
        ["roster_entry_id"],
        unique=True,
        postgresql_where=sa.text(
            "roster_entry_id IS NOT NULL AND accepted_at IS NULL AND voided_at IS NULL"
        ),
    )


def downgrade() -> None:
    op.execute("DELETE FROM invitations WHERE kind <> 'role'")
    op.drop_index("uq_invitations_open_roster_entry", table_name="invitations")
    op.drop_constraint("ck_invitations_kind_fields", "invitations", type_="check")
    op.drop_constraint("ck_invitations_kind", "invitations", type_="check")
    op.drop_index("ix_invitations_roster_entry_id", table_name="invitations")
    op.drop_column("invitations", "roster_entry_id")
    op.drop_column("invitations", "class_id")
    op.drop_column("invitations", "kind")
    op.alter_column("invitations", "role", existing_type=sa.Text(), nullable=False)
    op.drop_index("uq_roster_entries_class_email", table_name="roster_entries")
    op.drop_table("roster_entries")
