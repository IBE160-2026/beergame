"""The Individual test's question set and each Class session's selection of it (Story 11.1,
FR-52, FR-53, FR-80, AD-23).

- `content_records` takes an eighth kind, `question_set`, and version 1 is stored here: placeholder
  items marked `status: "draft"` until issue #16 delivers the real questions. The same body is
  shipped as `app/modules/content/files/question_set.json`, which `python -m app.modules.content
  load` publishes only when it differs (a test keeps the two equal).
- `test_selections` (owned by `modules/tests`): a Class session's selection, the question set
  version it was made on, the items taken out, the Item weights and the Adapted total weight. No
  row reads as the latest version's defaults.
- `class_sessions.lock_refused_reason` (owned by `modules/sessions`): why the sweep last refused
  the lock (`provider_key_missing`, `question_set_draft`); NULL otherwise.

Revision ID: 0121
Revises: 0120
Create Date: 2026-11-22
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

revision: str = "0121"
down_revision: str | None = "0120"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# A literal, never imported from the app: what version 1 was stays what it was.
QUESTION_SET_V1 = {
    "status": "draft",
    "adapted_weight": 30,
    "items": [
        {
            "id": "startoppgave-sende",
            "type": "number",
            "title": "Utkast: Startoppgaven, enheter å sende",
            "weight": 3,
            "options": [],
            "answer_key": None,
            "scoring_rule": "starting-task-sum",
            "tags": ["quantity"],
            "starting_task_item": "to-ship",
        },
        {
            "id": "startoppgave-restordre",
            "type": "number",
            "title": "Utkast: Startoppgaven, restordre etter uka",
            "weight": 3,
            "options": [],
            "answer_key": None,
            "scoring_rule": "starting-task-sum",
            "tags": ["quantity"],
            "starting_task_item": "backlog",
        },
        {
            "id": "startoppgave-posisjon",
            "type": "number",
            "title": "Utkast: Startoppgaven, posisjonen for én uke",
            "weight": 4,
            "options": [],
            "answer_key": None,
            "scoring_rule": "starting-task-sum",
            "tags": ["quantity"],
            "starting_task_item": "position",
        },
        {
            "id": "flervalg-forklaring",
            "type": "choice",
            "title": "Utkast: flervalg med ordene fra Forklaringen",
            "weight": 5,
            "options": ["a", "b", "c"],
            "answer_key": "b",
            "scoring_rule": None,
            "tags": ["explanation-wording"],
            "starting_task_item": None,
        },
        {
            "id": "flervalg-arsaker",
            "type": "choice",
            "title": "Utkast: flervalg om årsaker",
            "weight": 5,
            "options": ["a", "b", "c", "d"],
            "answer_key": "c",
            "scoring_rule": None,
            "tags": [],
            "starting_task_item": None,
        },
        {
            "id": "tabell-nytt-monster",
            "type": "table",
            "title": "Utkast: tabell med et etterspørselsmønster du ikke har sett",
            "weight": 10,
            "options": [],
            "answer_key": None,
            "scoring_rule": "units-balance",
            "tags": ["unseen-demand", "quantity"],
            "starting_task_item": None,
        },
        {
            "id": "tabell-annen-bransje",
            "type": "table",
            "title": "Utkast: tabell fra en annen bransje",
            "weight": 10,
            "options": [],
            "answer_key": None,
            "scoring_rule": "stock-flow",
            "tags": ["other-business", "quantity"],
            "starting_task_item": None,
        },
        {
            "id": "tall-annen-bransje",
            "type": "number",
            "title": "Utkast: tall fra en annen bransje",
            "weight": 10,
            "options": [],
            "answer_key": None,
            "scoring_rule": "units-balance",
            "tags": ["other-business"],
            "starting_task_item": None,
        },
        {
            "id": "langsvar-forsinkelse",
            "type": "long",
            "title": "Utkast: langsvar om forsinkelse",
            "weight": 10,
            "options": [],
            "answer_key": None,
            "scoring_rule": "guide-langsvar-forsinkelse",
            "tags": [],
            "starting_task_item": None,
        },
        {
            "id": "langsvar-informasjon",
            "type": "long",
            "title": "Utkast: langsvar om informasjon i kjeden",
            "weight": 10,
            "options": [],
            "answer_key": None,
            "scoring_rule": "guide-langsvar-informasjon",
            "tags": [],
            "starting_task_item": None,
        },
    ],
    "replacements": [
        {
            "id": "erstatning-tabell",
            "type": "table",
            "title": "Utkast: erstatningsoppgave, tabell",
            "weight": 15,
            "options": [],
            "answer_key": None,
            "scoring_rule": "units-balance",
            "tags": ["quantity"],
            "starting_task_item": None,
        },
        {
            "id": "erstatning-langsvar",
            "type": "long",
            "title": "Utkast: erstatningsoppgave, langsvar",
            "weight": 15,
            "options": [],
            "answer_key": None,
            "scoring_rule": "guide-erstatning-langsvar",
            "tags": [],
            "starting_task_item": None,
        },
    ],
}

KINDS_BEFORE = (
    "kind IN ('starting_task', 'detected_patterns', 'sentence_templates', "
    "'reflection_questions', 'moment_templates', 'debrief_quiz', 'narration_templates')"
)
KINDS_AFTER = (
    "kind IN ('starting_task', 'detected_patterns', 'sentence_templates', "
    "'reflection_questions', 'moment_templates', 'debrief_quiz', 'narration_templates', "
    "'question_set')"
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
                "id": uuid.UUID("01a1f9a0-0000-7000-8000-000000000121"),
                "kind": "question_set",
                "version": 1,
                "body": QUESTION_SET_V1,
            }
        ],
    )
    op.create_table(
        "test_selections",
        sa.Column(
            "class_session_id",
            sa.Uuid(),
            sa.ForeignKey("class_sessions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("question_set_version", sa.Integer(), nullable=False),
        sa.Column("excluded", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("weights", JSONB(), nullable=False),
        sa.Column("adapted_weight", sa.Integer(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("question_set_version >= 1", name="ck_test_selections_version"),
        sa.CheckConstraint(
            "adapted_weight BETWEEN 0 AND 100", name="ck_test_selections_adapted_weight"
        ),
    )
    op.add_column("class_sessions", sa.Column("lock_refused_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("class_sessions", "lock_refused_reason")
    op.drop_table("test_selections")
    op.execute("DELETE FROM content_records WHERE kind = 'question_set'")
    op.drop_constraint("ck_content_records_kind", "content_records", type_="check")
    op.create_check_constraint("ck_content_records_kind", "content_records", KINDS_BEFORE)
