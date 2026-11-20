"""The Start-date lock of a Class session (Story 5.11, FR-12, AD-4).

`class_sessions.locked_at` is set by `sessions.service.lock` together with `snapshot`, the frozen
`GameSettings`, demand series, seed, `rules_version` and `SessionRuntime` every Class game takes
(Story 5.12). `ck_class_sessions_lock` keeps the two set together.

Revision ID: 0040
Revises: 0039
Create Date: 2026-11-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0040"
down_revision: str | None = "0039"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("class_sessions", sa.Column("locked_at", sa.DateTime(timezone=True)))
    op.add_column("class_sessions", sa.Column("snapshot", postgresql.JSONB()))
    op.create_check_constraint(
        "ck_class_sessions_lock", "class_sessions", "(locked_at IS NULL) = (snapshot IS NULL)"
    )


def downgrade() -> None:
    op.drop_constraint("ck_class_sessions_lock", "class_sessions", type_="check")
    op.drop_column("class_sessions", "snapshot")
    op.drop_column("class_sessions", "locked_at")
