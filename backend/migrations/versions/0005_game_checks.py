"""The finished-game check (`game_checks`, Story 1.10), owned by modules/games.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "game_checks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("game_id", sa.Uuid(), sa.ForeignKey("games.id"), nullable=False),
        sa.Column("rules_version", sa.Integer(), nullable=False),
        sa.Column("ok", sa.Boolean(), nullable=False),
        sa.Column("violations", postgresql.JSONB(), nullable=False),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("ok = (jsonb_array_length(violations) = 0)", name="ck_game_checks_ok"),
        sa.UniqueConstraint("game_id", name="uq_game_checks_game"),
    )
    # AD-9: a check result is written once and never changed.
    op.execute(
        """
        CREATE FUNCTION game_checks_append_only() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'game_checks is append-only: % refused', TG_OP
                USING ERRCODE = 'restrict_violation';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER game_checks_append_only
        BEFORE UPDATE OR DELETE ON game_checks
        FOR EACH ROW EXECUTE FUNCTION game_checks_append_only()
        """
    )


def downgrade() -> None:
    op.drop_table("game_checks")
    op.execute("DROP FUNCTION game_checks_append_only()")
