"""AI deadlines (Story 2.6): `ai_deadline_at` on turns and Decision log rows, the index the
`worker-ai` rescue loop reads, and the `cancelled` outcome of an attempt (AD-5, AD-6, AD-20,
NFR-2).

The `seat_turns` trigger also keeps an `ai_deadline_at` once it is set: a deadline is written
when the Week opens (or, from Epic 8, when an LLM player takes the Seat) and never moved.

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OUTCOMES = ("ok", "invalid_output", "timeout", "provider_error")


def _outcome_check(values: Sequence[str]) -> str:
    return f"outcome IN ({', '.join(repr(value) for value in values)})"


def _keep_opening(deadline: bool) -> str:
    """The trigger function as 0004 left it, with the deadline rule when `deadline`."""
    keep_deadline = (
        "OR (OLD.ai_deadline_at IS NOT NULL "
        "AND NEW.ai_deadline_at IS DISTINCT FROM OLD.ai_deadline_at)"
        if deadline
        else ""
    )
    return f"""
        CREATE OR REPLACE FUNCTION seat_turns_keep_opening() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE'
               OR NEW.game_id IS DISTINCT FROM OLD.game_id
               OR NEW.seat_id IS DISTINCT FROM OLD.seat_id
               OR NEW.week IS DISTINCT FROM OLD.week
               OR NEW.opened_at IS DISTINCT FROM OLD.opened_at
               OR NEW.rule_based_reference_order IS DISTINCT FROM OLD.rule_based_reference_order
               OR (OLD.ordered_at IS NOT NULL AND NEW.ordered_at IS DISTINCT FROM OLD.ordered_at)
               {keep_deadline}
            THEN
                RAISE EXCEPTION 'seat_turns keeps its opening values: % refused', TG_OP
                    USING ERRCODE = 'restrict_violation';
            END IF;
            RETURN NEW;
        END;
        $$
        """


def upgrade() -> None:
    op.add_column("seat_turns", sa.Column("ai_deadline_at", sa.DateTime(timezone=True)))
    op.add_column("seat_weeks", sa.Column("ai_deadline_at", sa.DateTime(timezone=True)))
    op.create_index(
        "ix_seat_turns_ai_deadline",
        "seat_turns",
        ["ai_deadline_at"],
        postgresql_where=sa.text("ordered_at IS NULL AND ai_deadline_at IS NOT NULL"),
    )
    op.execute(_keep_opening(deadline=True))
    op.drop_constraint("ck_llm_call_outcome", "llm_call", type_="check")
    op.create_check_constraint(
        "ck_llm_call_outcome", "llm_call", _outcome_check([*OUTCOMES, "cancelled"])
    )


def downgrade() -> None:
    # Rows with outcome `cancelled` break the narrower check: such a database cannot go below
    # 0009 (`llm_call` keeps every attempt).
    op.drop_constraint("ck_llm_call_outcome", "llm_call", type_="check")
    op.create_check_constraint("ck_llm_call_outcome", "llm_call", _outcome_check(OUTCOMES))
    op.execute(_keep_opening(deadline=False))
    op.drop_index("ix_seat_turns_ai_deadline", table_name="seat_turns")
    op.drop_column("seat_weeks", "ai_deadline_at")
    op.drop_column("seat_turns", "ai_deadline_at")
