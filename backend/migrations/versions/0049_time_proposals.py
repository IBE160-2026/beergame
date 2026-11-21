"""The scheduling aid of a Class game (Story 6.19, FR-22, AD-2, AD-20).

`time_proposals` holds a Game's one open proposal of a time to play (a date and a time, no free
text), `time_acceptances` who accepted it. Only `games.commands.propose_time` and `accept_time`
write them; a new proposal replaces the old one and its acceptances. Neither table is an input of
`games.rules.turn_times`.

Revision ID: 0049
Revises: 0048
Create Date: 2026-11-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0049"
down_revision: str | None = "0048"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "time_proposals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("game_id", sa.Uuid(), sa.ForeignKey("games.id"), nullable=False),
        sa.Column("proposed_by", sa.Uuid(), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("game_id", name="uq_time_proposals_game"),
    )
    op.create_table(
        "time_acceptances",
        sa.Column(
            "proposal_id",
            sa.Uuid(),
            sa.ForeignKey("time_proposals.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("user_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "accepted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("time_acceptances")
    op.drop_table("time_proposals")
