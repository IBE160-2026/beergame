"""The Debrief quiz and its attempts (Story 9.9, FR-46, AD-16, AD-23).

`content_records` takes a sixth kind, `debrief_quiz`, and version 1 is stored here: three
placeholder questions, marked `placeholder: true`, until issue #16 delivers the real quiz.
`quiz_attempts` (owned by `modules/debrief`) holds one row per scored attempt of a Student in a
Class session, with the answers, the result and the quiz version, stored once and never changed:
a trigger refuses every update.

Revision ID: 0108
Revises: 0107
Create Date: 2026-11-21
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0108"
down_revision: str | None = "0107"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# A literal, never imported from the app: what version 1 was stays what it was.
DEBRIEF_QUIZ_V1 = {
    "placeholder": True,
    "questions": [
        {
            "id": "posisjon",
            "prompt": "Du har 0 på lager, 13 i restordre og 16 på vei. Hva er posisjonen din?",
            "choices": [
                {"id": "netto", "text": "−13"},
                {"id": "posisjon", "text": "3"},
                {"id": "sum", "text": "29"},
            ],
            "answer": "posisjon",
            "explanation": (
                "Posisjonen er lager − restordre + på vei: 0 − 13 + 16 = 3. −13 er netto lager, "
                "uten det som er på vei."
            ),
            "in_your_game": (
                "Ditt første øyeblikk var Uke {first_moment_week}. "
                "Det står i kolonne {first_moment_week} i din egen tabell."
            ),
        },
        {
            "id": "forsinkelse",
            "prompt": "Du øker ordren din i én uke. Når kommer varene fram?",
            "choices": [
                {"id": "samme-uke", "text": "Samme uke"},
                {"id": "uka-etter", "text": "Uka etter"},
                {"id": "flere-uker", "text": "Først etter flere uker"},
            ],
            "answer": "flere-uker",
            "explanation": (
                "Det går uker fra en ordre sendes til varene er framme. Imens står de i På vei, "
                "og de hører med i posisjonen."
            ),
            "in_your_game": (
                "Din første ordre på 10 eller mer kom i Uke {own_first_large_order_week}. "
                "Det står i kolonne {own_first_large_order_week} i din egen tabell."
            ),
        },
        {
            "id": "forsterkning",
            "prompt": "Hvor i kjeden svinger ordrene mest?",
            "choices": [
                {"id": "detaljist", "text": "Hos Detaljisten"},
                {"id": "like-mye", "text": "Like mye i alle ledd"},
                {"id": "fabrikk", "text": "Hos Fabrikken"},
            ],
            "answer": "fabrikk",
            "explanation": (
                "Oppover i kjeden ser hvert ledd bare ordrene fra leddet under, ikke hva kundene "
                "bestilte. Svingningene vokser fra Detaljist til Fabrikk."
            ),
            "in_your_game": (
                "I ditt spill var Forsterkningen hos Fabrikken {factory_amplification}."
            ),
        },
    ],
}

KINDS_BEFORE = (
    "kind IN ('starting_task', 'detected_patterns', 'sentence_templates', "
    "'reflection_questions', 'moment_templates')"
)


def upgrade() -> None:
    op.drop_constraint("ck_content_records_kind", "content_records", type_="check")
    op.create_check_constraint(
        "ck_content_records_kind",
        "content_records",
        "kind IN ('starting_task', 'detected_patterns', 'sentence_templates', "
        "'reflection_questions', 'moment_templates', 'debrief_quiz')",
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
                "id": uuid.UUID("01a1f9a0-0000-7000-8000-000000000108"),
                "kind": "debrief_quiz",
                "version": 1,
                "body": DEBRIEF_QUIZ_V1,
            }
        ],
    )
    op.create_table(
        "quiz_attempts",
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
            "game_id", sa.Uuid(), sa.ForeignKey("games.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("quiz_version", sa.Integer(), nullable=False),
        sa.Column("answers", JSONB(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "user_id", "class_session_id", "number", name="uq_quiz_attempts_user_session_number"
        ),
        sa.CheckConstraint("number >= 1", name="ck_quiz_attempts_number"),
    )
    op.execute(
        """
        CREATE FUNCTION quiz_attempts_immutable() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'a quiz attempt is stored once and never changed'
                USING ERRCODE = 'restrict_violation';
        END $$
        """
    )
    op.execute(
        "CREATE TRIGGER trg_quiz_attempts_immutable "
        "BEFORE UPDATE ON quiz_attempts "
        "FOR EACH ROW EXECUTE FUNCTION quiz_attempts_immutable()"
    )


def downgrade() -> None:
    op.drop_table("quiz_attempts")
    op.execute("DROP FUNCTION quiz_attempts_immutable()")
    op.execute("DELETE FROM content_records WHERE kind = 'debrief_quiz'")
    op.drop_constraint("ck_content_records_kind", "content_records", type_="check")
    op.create_check_constraint("ck_content_records_kind", "content_records", KINDS_BEFORE)
