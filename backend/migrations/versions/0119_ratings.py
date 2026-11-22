"""Rate how believable the AI players were (Story 10.8, FR-70, FR-50, AD-13, AD-15).

Two tables, each written once (a trigger refuses every update):

- `believability_ratings` (owned by `games`): a Student's answer, 1 to 5, on how believable the
  AI players' ordering felt in a Game, one per Student and Game, with the Game's purpose and the
  AI mode its snapshot froze. The Student by id only, never a name.
- `replay_another_round` (owned by `replay`): whether the Student would have wanted to play
  another round, one per Student and Class session.

Revision ID: 0119
Revises: 0118
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0119"
down_revision: str | None = "0118"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

IMMUTABLE = ("believability_ratings", "replay_another_round")
PURPOSES = "'class', 'replay', 'makeup', 'lecturer_test', 'simulation'"


def _created_at() -> sa.Column:
    return sa.Column(
        "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


def upgrade() -> None:
    op.create_table(
        "believability_ratings",
        sa.Column(
            "game_id",
            sa.Uuid(),
            sa.ForeignKey("games.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("user_id", sa.Uuid(), primary_key=True),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("ai_mode", sa.Text(), nullable=False),
        sa.Column("rating", sa.SmallInteger(), nullable=False),
        _created_at(),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_believability_ratings_rating"),
        sa.CheckConstraint(f"purpose IN ({PURPOSES})", name="ck_believability_ratings_purpose"),
        sa.CheckConstraint(
            "ai_mode IN ('llm', 'rule_based')", name="ck_believability_ratings_ai_mode"
        ),
    )
    op.create_table(
        "replay_another_round",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "class_session_id",
            sa.Uuid(),
            sa.ForeignKey("class_sessions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("answer", sa.Boolean(), nullable=False),
        _created_at(),
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
