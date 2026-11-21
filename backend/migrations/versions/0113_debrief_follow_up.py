"""Bounded follow-up questions about a Student's own Game (Story 9.15, FR-45, AD-6, AD-7, AD-14).

Version 2 of the `narration_templates` content kind: version 1's four narration sentences and the
follow-up's four hint templates (draft copy), which point to where to look and fill only the cited
facts' numbers. `debrief_follow_ups` (owned by `modules/debrief`) holds each answered or declined
question, keyed by `user_id` and Class session with the facts set and the call it cites, stored
once: a trigger refuses every update. `debrief_follow_up_closures` holds the Students whose
follow-up was closed (`debrief.commands.close_follow_up`, when their Individual test opens).

Revision ID: 0113
Revises: 0112
Create Date: 2026-11-21
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0113"
down_revision: str | None = "0112"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Literals, never imported from the app: what version 2 was stays what it was.
NARRATION_TEMPLATES_V2 = {
    "templates": [
        {
            "id": "narration-orders",
            "text": (
                "I Uke {week_1} bestilte du {order_1} da ordren inn var {incoming_order_1}, "
                "og i Uke {week_2} bestilte du {order_2} da ordren inn var {incoming_order_2}."
            ),
        },
        {
            "id": "narration-supply-line",
            "text": "Da du bestilte {order_1} i Uke {week_1}, var {supply_line_1} allerede på vei.",
        },
        {
            "id": "narration-later-cost",
            "text": (
                "Etter Uke {week_1}: i Uke {later_first_week_1} til {later_last_week_1} "
                "kostet leddet ditt {later_cost_1} kr."
            ),
        },
        {
            "id": "narration-weeks",
            "text": "Øyeblikkene dine ligger i Uke {week_1}, {week_2} og {week_3}.",
        },
        {
            "id": "hint-row",
            "text": (
                "Se på raden for Uke {week_1}: der bestilte du {order_1}, "
                "og ordren inn var {incoming_order_1}."
            ),
        },
        {
            "id": "hint-supply-line",
            "text": (
                "Se på kolonnen På vei i Uke {week_1}: {supply_line_1} var allerede på vei "
                "da du bestilte {order_1}."
            ),
        },
        {
            "id": "hint-later",
            "text": (
                "Følg kostnaden etter Uke {week_1}: i Uke {later_first_week_1} til "
                "{later_last_week_1} kostet leddet ditt {later_cost_1} kr."
            ),
        },
        {
            "id": "hint-compare",
            "text": (
                "Sammenlign Uke {week_1} og Uke {week_2}: du bestilte {order_1} og {order_2}, "
                "og ordren inn var {incoming_order_1} og {incoming_order_2}."
            ),
        },
    ]
}


def upgrade() -> None:
    records = sa.table(
        "content_records",
        sa.column("id", sa.Uuid()),
        sa.column("kind", sa.Text()),
        sa.column("version", sa.Integer()),
        sa.column("body", JSONB()),
    )
    op.bulk_insert(
        records,
        [
            {
                "id": uuid.UUID("01a1f9a0-0000-7000-8000-000000000113"),
                "kind": "narration_templates",
                "version": 2,
                "body": NARRATION_TEMPLATES_V2,
            }
        ],
    )
    op.create_table(
        "debrief_follow_ups",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "class_session_id",
            sa.Uuid(),
            sa.ForeignKey("class_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "fact_set_id",
            sa.Uuid(),
            sa.ForeignKey("fact_sets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("llm_call_id", sa.Uuid(), nullable=False),
        sa.Column(
            "asked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "outcome IN ('answered', 'declined')", name="ck_debrief_follow_ups_outcome"
        ),
        sa.CheckConstraint(
            "(outcome = 'answered') = (answer IS NOT NULL)", name="ck_debrief_follow_ups_answer"
        ),
    )
    op.create_index(
        "ix_debrief_follow_ups_user_session",
        "debrief_follow_ups",
        ["user_id", "class_session_id", "asked_at"],
    )
    op.execute(
        """
        CREATE FUNCTION debrief_follow_ups_immutable() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'a Debrief follow-up is stored once'
                USING ERRCODE = 'restrict_violation';
        END $$
        """
    )
    op.execute(
        "CREATE TRIGGER trg_debrief_follow_ups_immutable "
        "BEFORE UPDATE ON debrief_follow_ups "
        "FOR EACH ROW EXECUTE FUNCTION debrief_follow_ups_immutable()"
    )
    op.create_table(
        "debrief_follow_up_closures",
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column(
            "class_session_id",
            sa.Uuid(),
            sa.ForeignKey("class_sessions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "closed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    op.drop_table("debrief_follow_up_closures")
    op.drop_table("debrief_follow_ups")
    op.execute("DROP FUNCTION debrief_follow_ups_immutable()")
    op.execute("DELETE FROM content_records WHERE kind = 'narration_templates' AND version = 2")
