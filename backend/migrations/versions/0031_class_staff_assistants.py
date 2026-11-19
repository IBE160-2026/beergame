"""Assistant lecturers and their Invitations (Story 4.9, FR-10, AD-12).

`class_staff.role` gains `assistant` (co-owners are `owner` rows). `invitations.kind` gains
`assistant`: an Invitation that names its Class and no Roster entry or account role. At most one
`assistant` Invitation is open per Class and address.

Expand-only: no existing row changes. The downgrade deletes Assistant rows and Invitations.

Revision ID: 0031
Revises: 0030
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0031"
down_revision: str | None = "0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

KIND_FIELDS_OLD = (
    "(kind = 'role') = (role IS NOT NULL) "
    "AND (kind = 'student') = (class_id IS NOT NULL AND roster_entry_id IS NOT NULL)"
)
KIND_FIELDS_NEW = (
    KIND_FIELDS_OLD
    + " AND (kind = 'assistant') = (class_id IS NOT NULL AND roster_entry_id IS NULL)"
)


def upgrade() -> None:
    op.drop_constraint("ck_class_staff_role", "class_staff", type_="check")
    op.create_check_constraint(
        "ck_class_staff_role", "class_staff", "role IN ('owner', 'assistant')"
    )
    op.drop_constraint("ck_invitations_kind", "invitations", type_="check")
    op.create_check_constraint(
        "ck_invitations_kind", "invitations", "kind IN ('role', 'student', 'assistant')"
    )
    op.drop_constraint("ck_invitations_kind_fields", "invitations", type_="check")
    op.create_check_constraint("ck_invitations_kind_fields", "invitations", KIND_FIELDS_NEW)
    op.create_index(
        "uq_invitations_open_assistant",
        "invitations",
        ["class_id", "email"],
        unique=True,
        postgresql_where=sa.text(
            "kind = 'assistant' AND accepted_at IS NULL AND voided_at IS NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index("uq_invitations_open_assistant", table_name="invitations")
    op.execute("DELETE FROM invitations WHERE kind = 'assistant'")
    op.drop_constraint("ck_invitations_kind_fields", "invitations", type_="check")
    op.create_check_constraint("ck_invitations_kind_fields", "invitations", KIND_FIELDS_OLD)
    op.drop_constraint("ck_invitations_kind", "invitations", type_="check")
    op.create_check_constraint("ck_invitations_kind", "invitations", "kind IN ('role', 'student')")
    op.execute("DELETE FROM class_staff WHERE role = 'assistant'")
    op.drop_constraint("ck_class_staff_role", "class_staff", type_="check")
    op.create_check_constraint("ck_class_staff_role", "class_staff", "role IN ('owner')")
