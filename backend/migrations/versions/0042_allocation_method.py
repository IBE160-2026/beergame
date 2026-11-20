"""The allocation method of a Class session (Story 5.17).

`class_sessions.allocation_method` is `random` (Stories 5.8 to 5.13, every existing row) or
`student_choice` (behind `FEATURE_STUDENT_CHOICE`): the Students take a Class game and a Seat
themselves before the Start date.

Revision ID: 0042
Revises: 0041
Create Date: 2026-11-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0042"
down_revision: str | None = "0041"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "class_sessions",
        sa.Column("allocation_method", sa.Text(), nullable=False, server_default="random"),
    )
    op.create_check_constraint(
        "ck_class_sessions_allocation_method",
        "class_sessions",
        "allocation_method IN ('random', 'student_choice')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_class_sessions_allocation_method", "class_sessions", type_="check")
    op.drop_column("class_sessions", "allocation_method")
