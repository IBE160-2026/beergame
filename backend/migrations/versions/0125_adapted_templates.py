"""The Adapted item templates (Story 11.7, FR-53, AD-7, AD-23).

`content_records` takes a tenth kind, `adapted_templates`, and version 1 is stored here: the same
templates for every Student, each naming the Game it reads (`game` or `replay`), the kind of fact
it needs (`moment`, `pattern` or `outcome`) and its share of the Adapted total weight; placeholder
text marked `status: "draft"` until issue #16 delivers the real text. The same body is shipped as
`app/modules/content/files/adapted_templates.json` (a test keeps the two equal).

Revision ID: 0125
Revises: 0124
Create Date: 2026-11-22
"""

# ruff: noqa: E501 (the content literal keeps its sentences whole)

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0125"
down_revision: str | None = "0124"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RECORD_ID = uuid.UUID("01a1f9a0-0000-7000-8000-000000000125")

# A literal, never imported from the app: what version 1 was stays what it was.
ADAPTED_TEMPLATES_V1 = {
    "status": "draft",
    "templates": [
        {
            "id": "tilpasset-eget-spill",
            "source": "game",
            "fact": "moment",
            "pick": 1,
            "share": 50,
            "text": "Utkast: I uke {week} av Klassespillet var du {role}. Du fikk inn en ordre "
            "på {incoming_order} enheter, hadde {inventory} enheter på lager, "
            "{backlog} enheter i restordre og {supply_line} enheter på vei, og du "
            "bestilte {order} enheter. Forklar hva du la vekt på da du bestilte, og "
            "hva som skjedde i kjeden de neste ukene.",
        },
        {
            "id": "tilpasset-replay",
            "source": "replay",
            "fact": "outcome",
            "pick": 1,
            "share": 50,
            "text": "Utkast: I Replay var du {role} i {weeks} uker. Kostnaden din ble "
            "{total_cost} kr, {holding_cost} kr for lager og {backorder_cost} kr for "
            "restordre. Sammenlign med Klassespillet og forklar hva du gjorde "
            "annerledes.",
        },
    ],
}

KINDS_BEFORE = (
    "kind IN ('starting_task', 'detected_patterns', 'sentence_templates', "
    "'reflection_questions', 'moment_templates', 'debrief_quiz', 'narration_templates', "
    "'question_set', 'scoring_guide')"
)
KINDS_AFTER = (
    "kind IN ('starting_task', 'detected_patterns', 'sentence_templates', "
    "'reflection_questions', 'moment_templates', 'debrief_quiz', 'narration_templates', "
    "'question_set', 'scoring_guide', 'adapted_templates')"
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
                "id": RECORD_ID,
                "kind": "adapted_templates",
                "version": 1,
                "body": ADAPTED_TEMPLATES_V1,
            }
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM content_records WHERE kind = 'adapted_templates'")
    op.drop_constraint("ck_content_records_kind", "content_records", type_="check")
    op.create_check_constraint("ck_content_records_kind", "content_records", KINDS_BEFORE)
