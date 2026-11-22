"""The sentence templates (Story 9.4, FR-44, AD-7, AD-23).

`content_records` takes a third kind, `sentence_templates`, and version 1 is stored here: the five
variants of the Debrief's step-2 heading, rendered by code from the Game's customer demand series.
Draft copy, to be reviewed with the rest of the Debrief copy (Issue #31).

Revision ID: 0104
Revises: 0103
Create Date: 2026-11-21
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0104"
down_revision: str | None = "0103"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# A literal, never imported from the app: what version 1 was stays what it was.
SENTENCE_TEMPLATES_V1 = {
    "templates": [
        {"id": "demand-flat", "text": "Kundene bestilte {level} hver uke. Det endret seg aldri."},
        {
            "id": "demand-step",
            "text": "Kundene bestilte {before}, så {after}. Etter det endret de seg aldri.",
        },
        {
            "id": "demand-step-noise",
            "text": (
                "Kundene bestilte rundt {before}, så rundt {after} fra Uke {change_week}. "
                "Hver uke lå de mellom {low} og {high}."
            ),
        },
        {
            "id": "demand-random",
            "text": (
                "Kundene bestilte rundt {level} hver uke, aldri under {low} og aldri over {high}."
            ),
        },
        {
            "id": "demand-varied",
            "text": (
                "Kundene bestilte {first} i Uke 1, og siden aldri under {low} eller over {high}."
            ),
        },
    ]
}


def upgrade() -> None:
    op.drop_constraint("ck_content_records_kind", "content_records", type_="check")
    op.create_check_constraint(
        "ck_content_records_kind",
        "content_records",
        "kind IN ('starting_task', 'detected_patterns', 'sentence_templates')",
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
                "id": uuid.UUID("01a1f9a0-0000-7000-8000-000000000104"),
                "kind": "sentence_templates",
                "version": 1,
                "body": SENTENCE_TEMPLATES_V1,
            }
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM content_records WHERE kind = 'sentence_templates'")
    op.drop_constraint("ck_content_records_kind", "content_records", type_="check")
    op.create_check_constraint(
        "ck_content_records_kind",
        "content_records",
        "kind IN ('starting_task', 'detected_patterns')",
    )
