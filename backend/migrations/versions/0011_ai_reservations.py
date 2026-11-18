"""AI budget reservations (Story 2.8): the open reservations of a budget row (AD-6, FR-69).

Each attempt reserves its worst-case cost against the row with one conditional `UPDATE` and
settles to its actual cost when its `llm_call` row is written.

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ai_budgets",
        sa.Column("reserved_usd", sa.Numeric(18, 8), nullable=False, server_default=sa.text("0")),
    )
    op.create_check_constraint("ck_ai_budgets_reserved", "ai_budgets", "reserved_usd >= 0")


def downgrade() -> None:
    op.drop_constraint("ck_ai_budgets_reserved", "ai_budgets", type_="check")
    op.drop_column("ai_budgets", "reserved_usd")
