"""When the Test-deadline close ran for an Individual test attempt (Story 11.11, FR-51, AD-9).

- `test_attempts.closed_at`: set once by `tests.commands.close_attempt`, the sweep's
  `tests.close_attempt` due action after `sessions.lock_test`, for every attempt at its
  `effective_deadline`, handed in or not (an open one is auto-submitted there). NULL until then.
- `ck_test_attempts_closed`: a closed attempt is never `open`.
- `ix_test_attempts_due_close`: the finder's partial index over the attempts not yet closed.

Revision ID: 0128
Revises: 0127
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0128"
down_revision: str | None = "0127"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "test_attempts", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_check_constraint(
        "ck_test_attempts_closed", "test_attempts", "closed_at IS NULL OR status <> 'open'"
    )
    op.create_index(
        "ix_test_attempts_due_close",
        "test_attempts",
        ["effective_deadline"],
        postgresql_where=sa.text("closed_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_test_attempts_due_close", table_name="test_attempts")
    op.drop_constraint("ck_test_attempts_closed", "test_attempts", type_="check")
    op.drop_column("test_attempts", "closed_at")
