"""The four dates of a Class session (Story 5.2, FR-18), owned by `sessions`.

Start date, Play deadline, Debrief deadline and Test deadline, each `timestamptz` (UTC) and NULL
until the Lecturer sets it. Every pair that is set keeps the order start < play < debrief < test.

Revision ID: 0033
Revises: 0032
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0033"
down_revision: str | None = "0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DATES = ("start_at", "play_deadline", "debrief_deadline", "test_deadline")


def upgrade() -> None:
    for name in DATES:
        op.add_column("class_sessions", sa.Column(name, sa.DateTime(timezone=True), nullable=True))
    pairs = [
        f"({a} IS NULL OR {b} IS NULL OR {a} < {b})"
        for i, a in enumerate(DATES)
        for b in DATES[i + 1 :]
    ]
    op.create_check_constraint(
        "ck_class_sessions_date_order", "class_sessions", " AND ".join(pairs)
    )


def downgrade() -> None:
    op.drop_constraint("ck_class_sessions_date_order", "class_sessions", type_="check")
    for name in reversed(DATES):
        op.drop_column("class_sessions", name)
