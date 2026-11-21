"""A Lecturer's test Game belongs to its Class session without a game number (Story 6.20).

`ck_games_class_session` held a Class session id and a game number together. A test Game
(`purpose = lecturer_test`) carries its Class session id, so its AI calls are charged to that
session's budget, but no number: it is never one of the session's Class games. The check now only
says a game number needs a Class session.

Revision ID: 0050
Revises: 0049
Create Date: 2026-11-21
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0050"
down_revision: str | None = "0049"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_games_class_session", "games", type_="check")
    op.create_check_constraint(
        "ck_games_class_session", "games", "game_number IS NULL OR class_session_id IS NOT NULL"
    )


def downgrade() -> None:
    # Test Games stored meanwhile keep their rows: the old check returns `NOT VALID`, so it holds
    # for every new row and leaves them as they are.
    op.drop_constraint("ck_games_class_session", "games", type_="check")
    op.execute(
        "ALTER TABLE games ADD CONSTRAINT ck_games_class_session "
        "CHECK ((class_session_id IS NULL) = (game_number IS NULL)) NOT VALID"
    )
