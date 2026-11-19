"""A Roster entry may be registered manually (Story 4.7, FR-9), owned by `identity`.

`ck_roster_entries_registration` gains `registered_manually`, the status Story 4.8's manual
registration writes and Story 4.7's status list and totals («Manuelt») read.

Expand-only: no existing row changes. The downgrade turns manual registrations into plain ones.

Revision ID: 0029
Revises: 0028
Create Date: 2026-11-19
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0029"
down_revision: str | None = "0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_roster_entries_registration", "roster_entries", type_="check")
    op.create_check_constraint(
        "ck_roster_entries_registration",
        "roster_entries",
        "registration IN ('invited', 'registered', 'registered_manually')",
    )


def downgrade() -> None:
    op.execute(
        "UPDATE roster_entries SET registration = 'registered' "
        "WHERE registration = 'registered_manually'"
    )
    op.drop_constraint("ck_roster_entries_registration", "roster_entries", type_="check")
    op.create_check_constraint(
        "ck_roster_entries_registration",
        "roster_entries",
        "registration IN ('invited', 'registered')",
    )
