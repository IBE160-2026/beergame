"""The Scoring guide and each Class session's Scoring guide in force (Story 11.2, FR-81, FR-18,
AD-23, AD-27).

- `content_records` takes a ninth kind, `scoring_guide`, and version 1 is stored here: placeholder
  guide text marked `status: "draft"` until issue #16 delivers the real text. The same body is
  shipped as `app/modules/content/files/scoring_guide.json` (a test keeps the two equal).
- `content_records.class_session_id`: the Class session a Lecturer's edited Scoring guide was made
  for; NULL for a published default. No foreign key: a copied Class session uses the same version.
- `test_scoring_guides` (owned by `modules/tests`): the Scoring guide version in force for a Class
  session, the default it derives from (`base_id`) and when the Test-deadline lock pinned it. No
  row reads as the latest default. A trigger refuses any change of a pinned row.

Revision ID: 0122
Revises: 0121
Create Date: 2026-11-22
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0122"
down_revision: str | None = "0121"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# A literal, never imported from the app: what version 1 was stays what it was.
SCORING_GUIDE_V1 = {
    "status": "draft",
    "scale": [
        {"step": 0, "label": "Utkast: mangler"},
        {"step": 1, "label": "Utkast: svakt"},
        {"step": 2, "label": "Utkast: delvis"},
        {"step": 3, "label": "Utkast: godt"},
        {"step": 4, "label": "Utkast: svært godt"},
    ],
    "questions": [
        {
            "id": "guide-langsvar-forsinkelse",
            "kind": "long",
            "title": "Utkast: langsvar om forsinkelse",
            "guide": "Utkast: hva oppgaven spør etter.\n"
            "Et sterkt svar: utkast.\n"
            "Et svakt svar: utkast.",
            "criteria": [
                {"code": "F1", "text": "Utkast: kriterium 1", "weight": 20},
                {"code": "F2", "text": "Utkast: kriterium 2", "weight": 20},
                {"code": "F3", "text": "Utkast: kriterium 3", "weight": 20},
                {"code": "F4", "text": "Utkast: kriterium 4", "weight": 20},
                {"code": "F5", "text": "Utkast: kriterium 5", "weight": 20},
            ],
        },
        {
            "id": "guide-langsvar-informasjon",
            "kind": "long",
            "title": "Utkast: langsvar om informasjon i kjeden",
            "guide": "Utkast: hva oppgaven spør etter.\n"
            "Et sterkt svar: utkast.\n"
            "Et svakt svar: utkast.",
            "criteria": [
                {"code": "I1", "text": "Utkast: kriterium 1", "weight": 20},
                {"code": "I2", "text": "Utkast: kriterium 2", "weight": 20},
                {"code": "I3", "text": "Utkast: kriterium 3", "weight": 20},
                {"code": "I4", "text": "Utkast: kriterium 4", "weight": 20},
                {"code": "I5", "text": "Utkast: kriterium 5", "weight": 20},
            ],
        },
        {
            "id": "guide-erstatning-langsvar",
            "kind": "long",
            "title": "Utkast: erstatningsoppgave, langsvar",
            "guide": "Utkast: hva oppgaven spør etter.\n"
            "Et sterkt svar: utkast.\n"
            "Et svakt svar: utkast.",
            "criteria": [
                {"code": "E1", "text": "Utkast: kriterium 1", "weight": 20},
                {"code": "E2", "text": "Utkast: kriterium 2", "weight": 20},
                {"code": "E3", "text": "Utkast: kriterium 3", "weight": 20},
                {"code": "E4", "text": "Utkast: kriterium 4", "weight": 20},
                {"code": "E5", "text": "Utkast: kriterium 5", "weight": 20},
            ],
        },
        {
            "id": "tilpasset-eget-spill",
            "kind": "adapted",
            "title": "Utkast: tilpasset oppgave om eget spill",
            "guide": "Utkast: hva oppgaven spør etter.\n"
            "Et sterkt svar: utkast.\n"
            "Et svakt svar: utkast.",
            "criteria": [
                {"code": "S1", "text": "Utkast: kriterium 1", "weight": 20},
                {"code": "S2", "text": "Utkast: kriterium 2", "weight": 20},
                {"code": "S3", "text": "Utkast: kriterium 3", "weight": 20},
                {"code": "S4", "text": "Utkast: kriterium 4", "weight": 20},
                {"code": "S5", "text": "Utkast: kriterium 5", "weight": 20},
            ],
        },
        {
            "id": "tilpasset-replay",
            "kind": "adapted",
            "title": "Utkast: tilpasset oppgave om Replay",
            "guide": "Utkast: hva oppgaven spør etter.\n"
            "Et sterkt svar: utkast.\n"
            "Et svakt svar: utkast.",
            "criteria": [
                {"code": "R1", "text": "Utkast: kriterium 1", "weight": 20},
                {"code": "R2", "text": "Utkast: kriterium 2", "weight": 20},
                {"code": "R3", "text": "Utkast: kriterium 3", "weight": 20},
                {"code": "R4", "text": "Utkast: kriterium 4", "weight": 20},
                {"code": "R5", "text": "Utkast: kriterium 5", "weight": 20},
            ],
        },
    ],
}

KINDS_BEFORE = (
    "kind IN ('starting_task', 'detected_patterns', 'sentence_templates', "
    "'reflection_questions', 'moment_templates', 'debrief_quiz', 'narration_templates', "
    "'question_set')"
)
KINDS_AFTER = (
    "kind IN ('starting_task', 'detected_patterns', 'sentence_templates', "
    "'reflection_questions', 'moment_templates', 'debrief_quiz', 'narration_templates', "
    "'question_set', 'scoring_guide')"
)


def upgrade() -> None:
    op.drop_constraint("ck_content_records_kind", "content_records", type_="check")
    op.create_check_constraint("ck_content_records_kind", "content_records", KINDS_AFTER)
    op.add_column("content_records", sa.Column("class_session_id", sa.Uuid(), nullable=True))
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
                "id": uuid.UUID("01a1f9a0-0000-7000-8000-000000000122"),
                "kind": "scoring_guide",
                "version": 1,
                "body": SCORING_GUIDE_V1,
            }
        ],
    )
    op.create_table(
        "test_scoring_guides",
        sa.Column(
            "class_session_id",
            sa.Uuid(),
            sa.ForeignKey("class_sessions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "scoring_guide_id",
            sa.Uuid(),
            sa.ForeignKey("content_records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "base_id",
            sa.Uuid(),
            sa.ForeignKey("content_records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pinned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute(
        """
        CREATE FUNCTION test_scoring_guides_pinned() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            -- Only what was pinned is frozen: `updated_by` may still go NULL when the User who
            -- edited it is deleted (its foreign key is ON DELETE SET NULL).
            IF OLD.pinned_at IS NOT NULL AND (
                NEW.scoring_guide_id, NEW.base_id, NEW.pinned_at
            ) IS DISTINCT FROM (OLD.scoring_guide_id, OLD.base_id, OLD.pinned_at) THEN
                RAISE EXCEPTION 'a pinned Scoring guide does not change'
                    USING ERRCODE = 'restrict_violation';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        "CREATE TRIGGER trg_test_scoring_guides_pinned BEFORE UPDATE ON test_scoring_guides "
        "FOR EACH ROW EXECUTE FUNCTION test_scoring_guides_pinned()"
    )


def downgrade() -> None:
    op.drop_table("test_scoring_guides")
    op.execute("DROP FUNCTION test_scoring_guides_pinned()")
    op.execute("DELETE FROM content_records WHERE kind = 'scoring_guide'")
    op.drop_column("content_records", "class_session_id")
    op.drop_constraint("ck_content_records_kind", "content_records", type_="check")
    op.create_check_constraint("ck_content_records_kind", "content_records", KINDS_BEFORE)
