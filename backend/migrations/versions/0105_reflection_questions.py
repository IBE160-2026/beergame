"""The reflection questions (Story 9.6, FR-45, AD-14, AD-23).

`content_records` takes a fourth kind, `reflection_questions`, and version 1 is stored here: three
placeholder questions, feelings, then evidence, then structure, until issue #16 delivers the real
ones. `debrief_reflection_answers` (owned by `modules/debrief`) holds a Student's answer to one
question in a Class session, stored once as typed and never changed: a trigger refuses every
update.

Revision ID: 0105
Revises: 0104
Create Date: 2026-11-21
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0105"
down_revision: str | None = "0104"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# A literal, never imported from the app: what version 1 was stays what it was.
REFLECTION_QUESTIONS_V1 = {
    "questions": [
        {
            "id": "feelings",
            "kind": "feelings",
            "prompt": (
                "Hvordan opplevde du det å bestille uke for uke uten å vite hva kundene ville "
                "bestille?"
            ),
            "hint": None,
        },
        {
            "id": "evidence",
            "kind": "evidence",
            "prompt": (
                "Hva i tallene fra hele kjeden viser at svingningene vokste oppover i kjeden?"
            ),
            "hint": None,
        },
        {
            "id": "structure",
            "kind": "structure",
            "prompt": "Hvorfor svinger nesten alle kjeder slik, uansett hvem som spiller dem?",
            "hint": "Struktur gir atferd, derfor spør vi hvorfor og ikke hvem.",
        },
    ]
}

KINDS_BEFORE = "kind IN ('starting_task', 'detected_patterns', 'sentence_templates')"


def upgrade() -> None:
    op.drop_constraint("ck_content_records_kind", "content_records", type_="check")
    op.create_check_constraint(
        "ck_content_records_kind",
        "content_records",
        "kind IN ('starting_task', 'detected_patterns', 'sentence_templates', "
        "'reflection_questions')",
    )
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
                "id": uuid.UUID("01a1f9a0-0000-7000-8000-000000000105"),
                "kind": "reflection_questions",
                "version": 1,
                "body": REFLECTION_QUESTIONS_V1,
            }
        ],
    )
    op.create_table(
        "debrief_reflection_answers",
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
        sa.Column("question_id", sa.Text(), primary_key=True),
        sa.Column(
            "game_id",
            sa.Uuid(),
            sa.ForeignKey("games.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("questions_version", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("length", sa.Integer(), nullable=False),
        sa.Column("saved_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length = char_length(text) AND length BETWEEN 1 AND 2000",
            name="ck_debrief_reflection_answers_length",
        ),
    )
    op.execute(
        """
        CREATE FUNCTION debrief_reflection_answers_immutable() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'a reflection answer is stored once and never changed'
                USING ERRCODE = 'restrict_violation';
        END $$
        """
    )
    op.execute(
        "CREATE TRIGGER trg_debrief_reflection_answers_immutable "
        "BEFORE UPDATE ON debrief_reflection_answers "
        "FOR EACH ROW EXECUTE FUNCTION debrief_reflection_answers_immutable()"
    )


def downgrade() -> None:
    op.drop_table("debrief_reflection_answers")
    op.execute("DROP FUNCTION debrief_reflection_answers_immutable()")
    op.execute("DELETE FROM content_records WHERE kind = 'reflection_questions'")
    op.drop_constraint("ck_content_records_kind", "content_records", type_="check")
    op.create_check_constraint("ck_content_records_kind", "content_records", KINDS_BEFORE)
