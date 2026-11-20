"""The Effort level of a Class session (Story 5.5, FR-78), owned by `sessions`.

The name of an Effort level of the session's model config, as `ai.config.offered_effort_levels`
offers it. NULL while the AI mode is Rule-based: no level is in force then. Rows with LLM players
stored before this column read the config's default level.

Revision ID: 0034
Revises: 0033
Create Date: 2026-11-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0034"
down_revision: str | None = "0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("class_sessions", sa.Column("effort_level", sa.Text(), nullable=True))
    op.create_check_constraint(
        "ck_class_sessions_effort_level_llm_only",
        "class_sessions",
        "ai_mode = 'llm' OR effort_level IS NULL",
    )


def downgrade() -> None:
    op.drop_constraint("ck_class_sessions_effort_level_llm_only", "class_sessions", type_="check")
    op.drop_column("class_sessions", "effort_level")
