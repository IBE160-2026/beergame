"""The Replay walkthrough (Story 10.7, FR-50, AD-7, AD-9).

Two tables owned by `modules/replay`, both written once and never changed (a trigger refuses
every update):

- `replay_narrations`: the line the `llm-batch` job worded for a Replay Seat's facts set, as
  `{text, ai_generated, llm_call_id}` (a rejected or failed call stores the code text).
- `replay_walkthroughs`: a Student's walkthrough of their Replay, stored at their first ready
  view: the two facts sets it cites (the Replay Seat's and the Seat of the game it is compared
  with) and the line fixed at that view.

Revision ID: 0118
Revises: 0117
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0118"
down_revision: str | None = "0117"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

IMMUTABLE = ("replay_narrations", "replay_walkthroughs")


def _fact_set(name: str, nullable: bool = False) -> sa.Column:
    return sa.Column(
        name, sa.Uuid(), sa.ForeignKey("fact_sets.id", ondelete="CASCADE"), nullable=nullable
    )


def upgrade() -> None:
    op.create_table(
        "replay_narrations",
        sa.Column(
            "fact_set_id",
            sa.Uuid(),
            sa.ForeignKey("fact_sets.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("ai_generated", sa.Boolean(), nullable=False),
        sa.Column("llm_call_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "ai_generated = (llm_call_id IS NOT NULL)", name="ck_replay_narrations_marking"
        ),
    )
    op.create_table(
        "replay_walkthroughs",
        sa.Column(
            "replay_game_id",
            sa.Uuid(),
            sa.ForeignKey("games.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "class_session_id",
            sa.Uuid(),
            sa.ForeignKey("class_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        _fact_set("replay_fact_set_id"),
        sa.Column(
            "compared_game_id",
            sa.Uuid(),
            sa.ForeignKey("games.id", ondelete="CASCADE"),
            nullable=False,
        ),
        _fact_set("compared_fact_set_id"),
        sa.Column("narration_text", sa.Text(), nullable=True),
        sa.Column("narration_ai_generated", sa.Boolean(), nullable=False),
        sa.Column("narration_llm_call_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "narration_ai_generated = (narration_llm_call_id IS NOT NULL)",
            name="ck_replay_walkthroughs_marking",
        ),
    )
    for table in IMMUTABLE:
        op.execute(
            f"""
            CREATE FUNCTION {table}_immutable() RETURNS trigger
            LANGUAGE plpgsql AS $$
            BEGIN
                RAISE EXCEPTION 'a {table} row is stored once'
                    USING ERRCODE = 'restrict_violation';
            END $$
            """
        )
        op.execute(
            f"CREATE TRIGGER trg_{table}_immutable BEFORE UPDATE ON {table} "
            f"FOR EACH ROW EXECUTE FUNCTION {table}_immutable()"
        )


def downgrade() -> None:
    for table in reversed(IMMUTABLE):
        op.drop_table(table)
        op.execute(f"DROP FUNCTION {table}_immutable()")
