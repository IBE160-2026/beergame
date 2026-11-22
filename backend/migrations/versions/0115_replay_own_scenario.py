"""An own Replay scenario on a Class session (Story 10.2, FR-49, AD-4).

`class_sessions.replay_scenario` may now be `own`, and `replay_template` holds the Lecturer's own
`engine.ReplayTemplate` as JSON, there exactly when the choice is `own`. The default is still never
stored: it is derived from the Game settings until the lock pins it.

Revision ID: 0115
Revises: 0114
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0115"
down_revision: str | None = "0114"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_class_sessions_replay_scenario", "class_sessions", type_="check")
    op.create_check_constraint(
        "ck_class_sessions_replay_scenario",
        "class_sessions",
        "replay_scenario IN ('default', 'own')",
    )
    op.add_column("class_sessions", sa.Column("replay_template", JSONB(), nullable=True))
    op.create_check_constraint(
        "ck_class_sessions_replay_template",
        "class_sessions",
        "(replay_scenario = 'own') = (replay_template IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_class_sessions_replay_template", "class_sessions", type_="check")
    op.execute(
        "UPDATE class_sessions SET replay_scenario = 'default' WHERE replay_scenario = 'own'"
    )
    op.drop_column("class_sessions", "replay_template")
    op.drop_constraint("ck_class_sessions_replay_scenario", "class_sessions", type_="check")
    op.create_check_constraint(
        "ck_class_sessions_replay_scenario", "class_sessions", "replay_scenario IN ('default')"
    )
