"""Natural wording of Adapted items (Story 11.8, FR-53, FR-34, AD-6, AD-7, AD-9).

- Version 2 of `adapted_templates`: the templates of version 1, each with approved `wordings`, plain
  phrasings of the same question with the same slots, of which an LLM may only choose one
  (`adapted_item_wording`). Placeholder text marked `status: "draft"` until issue #16. The same
  body is shipped as `app/modules/content/files/adapted_templates.json` (a test keeps the two
  equal).
- `test_prepared_items` (owned by `modules/tests`): one prepared set of a Student's Adapted (or
  replacement) items per Class session, stored once by the `tests.prepare_adapted` job before the
  Student opens the test; `open_attempt` freezes it. Holds the Student's id and text rendered from
  their own game's facts (personal data).

Revision ID: 0126
Revises: 0125
Create Date: 2026-11-22
"""

# ruff: noqa: E501 (the content literal keeps its sentences whole)

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0126"
down_revision: str | None = "0125"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RECORD_ID = uuid.UUID("01a1f9a0-0000-7000-8000-000000000126")

# A literal, never imported from the app: what version 2 was stays what it was.
ADAPTED_TEMPLATES_V2 = {
    "status": "draft",
    "templates": [
        {
            "id": "tilpasset-eget-spill",
            "source": "game",
            "fact": "moment",
            "pick": 1,
            "share": 50,
            "text": "Utkast: I uke {week} av Klassespillet var du {role}. Du fikk inn en "
            "ordre på {incoming_order} enheter, hadde {inventory} enheter på "
            "lager, {backlog} enheter i restordre og {supply_line} enheter på "
            "vei, og du bestilte {order} enheter. Forklar hva du la vekt på da du "
            "bestilte, og hva som skjedde i kjeden de neste ukene.",
            "wordings": [
                {
                    "id": "tilpasset-eget-spill-sporsmal",
                    "text": "Utkast: Du var {role} i Klassespillet. Hva la du vekt "
                    "på da du bestilte {order} enheter i uke {week}, med en "
                    "ordre inn på {incoming_order} enheter, {inventory} "
                    "enheter på lager, {backlog} enheter i restordre og "
                    "{supply_line} enheter på vei? Hva skjedde i kjeden de "
                    "neste ukene?",
                },
                {
                    "id": "tilpasset-eget-spill-vei",
                    "text": "Utkast: I uke {week} av Klassespillet hadde du som "
                    "{role} {supply_line} enheter på vei, {inventory} "
                    "enheter på lager og {backlog} enheter i restordre, og "
                    "ordren inn var {incoming_order} enheter. Du bestilte "
                    "{order} enheter. Hva la du vekt på, og hva skjedde i "
                    "kjeden de neste ukene?",
                },
            ],
        },
        {
            "id": "tilpasset-replay",
            "source": "replay",
            "fact": "outcome",
            "pick": 1,
            "share": 50,
            "text": "Utkast: I Replay var du {role} i {weeks} uker. Kostnaden din ble "
            "{total_cost} kr, {holding_cost} kr for lager og {backorder_cost} kr "
            "for restordre. Sammenlign med Klassespillet og forklar hva du gjorde "
            "annerledes.",
            "wordings": [
                {
                    "id": "tilpasset-replay-sporsmal",
                    "text": "Utkast: Du var {role} i Replay i {weeks} uker, og "
                    "kostnaden din ble {total_cost} kr: {holding_cost} kr "
                    "for lager og {backorder_cost} kr for restordre. Hva "
                    "gjorde du annerledes enn i Klassespillet?",
                },
                {
                    "id": "tilpasset-replay-fordelt",
                    "text": "Utkast: Hva gjorde du annerledes i Replay enn i "
                    "Klassespillet? Der var du {role} i {weeks} uker, med "
                    "{holding_cost} kr i lagerkostnad og {backorder_cost} "
                    "kr i restordrekostnad, til sammen {total_cost} kr.",
                },
            ],
        },
    ],
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
                "id": RECORD_ID,
                "kind": "adapted_templates",
                "version": 2,
                "body": ADAPTED_TEMPLATES_V2,
            }
        ],
    )
    op.create_table(
        "test_prepared_items",
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "class_session_id",
            sa.Uuid(),
            sa.ForeignKey("class_sessions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("question_set_version", sa.Integer(), nullable=False),
        sa.Column("adapted_weight", sa.Integer(), nullable=False),
        sa.Column("items", JSONB(), nullable=False),
        sa.Column(
            "prepared_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("user_id", "class_session_id", name="pk_test_prepared_items"),
        sa.CheckConstraint("question_set_version >= 1", name="ck_test_prepared_items_version"),
        sa.CheckConstraint(
            "adapted_weight BETWEEN 0 AND 100", name="ck_test_prepared_items_adapted_weight"
        ),
    )


def downgrade() -> None:
    op.drop_table("test_prepared_items")
    op.execute("DELETE FROM content_records WHERE kind = 'adapted_templates' AND version = 2")
