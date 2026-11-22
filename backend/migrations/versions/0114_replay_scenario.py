"""The Replay scenario choice of a Class session (Story 10.1, FR-49, AD-4).

`class_sessions` gains `replay_scenario`, the Lecturer's choice of Replay scenario. Story 10.1
knows one value, `default`: the template is derived from the session's Game settings on every
read and pinned at the lock, never stored here. Story 10.2 widens the check for an own scenario.

Revision ID: 0114
Revises: 0113
Create Date: 2026-11-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0114"
down_revision: str | None = "0113"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "class_sessions",
        sa.Column("replay_scenario", sa.Text(), nullable=False, server_default="default"),
    )
    op.create_check_constraint(
        "ck_class_sessions_replay_scenario", "class_sessions", "replay_scenario IN ('default')"
    )


def downgrade() -> None:
    op.drop_constraint("ck_class_sessions_replay_scenario", "class_sessions", type_="check")
    op.drop_column("class_sessions", "replay_scenario")
