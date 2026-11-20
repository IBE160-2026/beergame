"""The required share of Weeks of a Class session (Story 5.7, FR-17), owned by `sessions`.

A whole percent from 1 to 100, stored with the obligatory mark and read by other modules only
through `sessions.service.required_share`. Rows stored before this column get 80, the placeholder
default (`COMPLETION_DEFAULT_SHARE_PERCENT`); new rows always get the configured value from the api.

Revision ID: 0036
Revises: 0035
Create Date: 2026-11-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0036"
down_revision: str | None = "0035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "class_sessions",
        sa.Column("required_share_percent", sa.Integer(), nullable=False, server_default="80"),
    )
    op.alter_column("class_sessions", "required_share_percent", server_default=None)
    op.create_check_constraint(
        "ck_class_sessions_required_share",
        "class_sessions",
        "required_share_percent BETWEEN 1 AND 100",
    )


def downgrade() -> None:
    op.drop_constraint("ck_class_sessions_required_share", "class_sessions", type_="check")
    op.drop_column("class_sessions", "required_share_percent")
