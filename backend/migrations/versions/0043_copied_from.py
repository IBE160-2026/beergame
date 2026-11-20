"""Where a copied Class session came from (Story 5.18).

`class_sessions.copied_from` names the Class session it was copied from (`FEATURE_RERUN`), NULL
for every other row and once that session is gone. `effort_level_replaced` holds the source's
Effort level when the new model config did not offer it, so the Klasseøkt can say so.

Revision ID: 0043
Revises: 0042
Create Date: 2026-11-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0043"
down_revision: str | None = "0042"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "class_sessions",
        sa.Column(
            "copied_from",
            sa.Uuid(),
            sa.ForeignKey(
                "class_sessions.id", ondelete="SET NULL", name="fk_class_sessions_copied_from"
            ),
            nullable=True,
        ),
    )
    op.add_column("class_sessions", sa.Column("effort_level_replaced", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("class_sessions", "effort_level_replaced")
    op.drop_column("class_sessions", "copied_from")
