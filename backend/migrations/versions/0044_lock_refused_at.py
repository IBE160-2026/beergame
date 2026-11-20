"""When the lock of a Class session was first refused (Story 5.11 follow-up, GitHub issue 109).

`class_sessions.lock_refused_at` is set by the sweep the first time the lock is refused for a
missing provider key, and left as it is after. The Klasseøkt tells a refused lock from one waiting
for the next minute's sweep while `locked_at` is NULL, and the sweep stops retrying a refused
session of an archived Class.

Revision ID: 0044
Revises: 0043
Create Date: 2026-11-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0044"
down_revision: str | None = "0043"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "class_sessions", sa.Column("lock_refused_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("class_sessions", "lock_refused_at")
