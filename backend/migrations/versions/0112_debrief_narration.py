"""AI narration that only connects computed facts (Story 9.14, FR-44, FR-15, FR-46, AD-7).

`content_records` takes a seventh kind, `narration_templates`, and version 1 is stored here: the
sentences an LLM may connect with fact ids, filled by code (draft copy). `class_sessions` gains
`debrief_ai_text`, the Lecturer's switch for the Debrief's AI text (on by default, frozen at the
lock). `debrief_ai_texts` (owned by `modules/debrief`) holds per facts set the narration and each
quiz question's own-game line, `{text, ai_generated, llm_call_id}`, stored once: a trigger refuses
every update.

Revision ID: 0112
Revises: 0111
Create Date: 2026-11-21
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0112"
down_revision: str | None = "0111"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# A literal, never imported from the app: what version 1 was stays what it was.
NARRATION_TEMPLATES_V1 = {
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
    ]
}

KINDS_BEFORE = (
    "kind IN ('starting_task', 'detected_patterns', 'sentence_templates', "
    "'reflection_questions', 'moment_templates', 'debrief_quiz')"
)
KINDS_AFTER = (
    "kind IN ('starting_task', 'detected_patterns', 'sentence_templates', "
    "'reflection_questions', 'moment_templates', 'debrief_quiz', 'narration_templates')"
)


def upgrade() -> None:
    op.drop_constraint("ck_content_records_kind", "content_records", type_="check")
    op.create_check_constraint("ck_content_records_kind", "content_records", KINDS_AFTER)
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
                "id": uuid.UUID("01a1f9a0-0000-7000-8000-000000000112"),
                "kind": "narration_templates",
                "version": 1,
                "body": NARRATION_TEMPLATES_V1,
            }
        ],
    )
    op.add_column(
        "class_sessions",
        sa.Column("debrief_ai_text", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "debrief_ai_texts",
        sa.Column(
            "fact_set_id",
            sa.Uuid(),
            sa.ForeignKey("fact_sets.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("subject", sa.Text(), primary_key=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("ai_generated", sa.Boolean(), nullable=False),
        sa.Column("llm_call_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "subject = 'narration' OR subject LIKE 'quiz:%'", name="ck_debrief_ai_texts_subject"
        ),
        sa.CheckConstraint(
            "ai_generated = (llm_call_id IS NOT NULL)", name="ck_debrief_ai_texts_marking"
        ),
    )
    op.execute(
        """
        CREATE FUNCTION debrief_ai_texts_immutable() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'a Debrief AI text is stored once'
                USING ERRCODE = 'restrict_violation';
        END $$
        """
    )
    op.execute(
        "CREATE TRIGGER trg_debrief_ai_texts_immutable "
        "BEFORE UPDATE ON debrief_ai_texts "
        "FOR EACH ROW EXECUTE FUNCTION debrief_ai_texts_immutable()"
    )


def downgrade() -> None:
    op.drop_table("debrief_ai_texts")
    op.execute("DROP FUNCTION debrief_ai_texts_immutable()")
    op.drop_column("class_sessions", "debrief_ai_text")
    op.execute("DELETE FROM content_records WHERE kind = 'narration_templates'")
    op.drop_constraint("ck_content_records_kind", "content_records", type_="check")
    op.create_check_constraint("ck_content_records_kind", "content_records", KINDS_BEFORE)
