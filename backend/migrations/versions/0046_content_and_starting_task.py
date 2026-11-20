"""Versioned content and the Starting task answers (Story 6.3, AD-23, FR-85).

`content_records` holds immutable, versioned content (a trigger refuses UPDATE); version 1 of the
Starting task is stored here: placeholder items until issue #16 delivers the final ones as a new
version. `starting_task_answers` (owned by `modules/tests`) holds each Student's answers once per
Class session, with the content version.

Revision ID: 0046
Revises: 0045
Create Date: 2026-11-20
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0046"
down_revision: str | None = "0045"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# A literal, never imported from the app: what version 1 was stays what it was.
STARTING_TASK_V1 = {
    "items": [
        {
            "id": "to-ship",
            "prompt": "Hvor mange enheter skal Grossisten sende i alt denne uka?",
            "hint": "Å sende = Restordre før + Ordre inn",
            "column": "Uke 11",
            "rows": [
                {"key": "backlog-before", "label": "Restordre før", "value": 9},
                {"key": "incoming-order", "label": "Ordre inn", "value": 8},
            ],
            "asked_label": "Å sende",
            "terms": [{"row": "backlog-before", "sign": 1}, {"row": "incoming-order", "sign": 1}],
        },
        {
            "id": "backlog",
            "prompt": "Regn restordren etter uka.",
            "hint": "Restordre = Restordre før + Ordre inn − Sendt",
            "column": "Uke 11",
            "rows": [
                {"key": "backlog-before", "label": "Restordre før", "value": 9},
                {"key": "incoming-order", "label": "Ordre inn", "value": 8},
                {"key": "shipped", "label": "Sendt", "value": 4},
            ],
            "asked_label": "Restordre",
            "terms": [
                {"row": "backlog-before", "sign": 1},
                {"row": "incoming-order", "sign": 1},
                {"row": "shipped", "sign": -1},
            ],
        },
        {
            "id": "position",
            "prompt": "Regn posisjonen for én Uke.",
            "hint": "Posisjon = Lager − Restordre + På vei",
            "column": "Uke 11",
            "rows": [
                {"key": "inventory", "label": "Lager", "value": 0},
                {"key": "backlog", "label": "Restordre", "value": 13},
                {"key": "on-order", "label": "På vei", "value": 16},
            ],
            "asked_label": "Posisjon",
            "terms": [
                {"row": "inventory", "sign": 1},
                {"row": "backlog", "sign": -1},
                {"row": "on-order", "sign": 1},
            ],
        },
    ]
}

CHOICES = ("yes", "no", "unknown", "skipped")


def upgrade() -> None:
    op.create_table(
        "content_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("body", JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("kind IN ('starting_task')", name="ck_content_records_kind"),
        sa.CheckConstraint("version >= 1", name="ck_content_records_version"),
        sa.UniqueConstraint("kind", "version", name="uq_content_records_kind_version"),
    )
    op.execute(
        """
        CREATE FUNCTION content_records_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'content records are immutable: publish a new version'
                USING ERRCODE = 'restrict_violation';
        END $$
        """
    )
    op.execute(
        "CREATE TRIGGER trg_content_records_immutable BEFORE UPDATE ON content_records "
        "FOR EACH ROW EXECUTE FUNCTION content_records_immutable()"
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
                "id": uuid.UUID("01a1f9a0-0000-7000-8000-000000000001"),
                "kind": "starting_task",
                "version": 1,
                "body": STARTING_TASK_V1,
            }
        ],
    )

    op.create_table(
        "starting_task_answers",
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
        sa.Column("content_version", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Text(), nullable=False),
        sa.Column("answer", sa.Integer(), nullable=True),
        sa.Column("correct", sa.Boolean(), nullable=True),
        sa.Column("choice", sa.Text(), nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(item_id = 'played_before' AND answer IS NULL AND correct IS NULL "
            "AND choice IN (" + ", ".join(f"'{c}'" for c in CHOICES) + ")) OR "
            "(item_id <> 'played_before' AND answer IS NOT NULL AND correct IS NOT NULL "
            "AND choice IS NULL)",
            name="ck_starting_task_answers_kind",
        ),
        sa.UniqueConstraint(
            "user_id", "class_session_id", "item_id", name="uq_starting_task_answers_item"
        ),
    )
    op.create_index(
        "ix_starting_task_answers_class_session_id", "starting_task_answers", ["class_session_id"]
    )


def downgrade() -> None:
    op.drop_table("starting_task_answers")
    op.drop_table("content_records")
    op.execute("DROP FUNCTION content_records_immutable()")
