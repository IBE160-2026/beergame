"""Facts sets and the Detected pattern definitions (Story 9.1, FR-44, AD-7, AD-23).

`content_records` takes a second kind, `detected_patterns`, and version 1 is stored here: the three
patterns of FR-44 with placeholder thresholds, to be reviewed by two lecturers before pilot.
`fact_sets` (owned by `modules/games`) holds one facts set per Seat of a finished Game, written
once by `games.facts.get_or_create`; a trigger refuses every UPDATE.

Revision ID: 0101
Revises: 0050
Create Date: 2026-11-21
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0101"
down_revision: str | None = "0050"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REVIEW = "to be reviewed by two lecturers before pilot"

# A literal, never imported from the app: what version 1 was stays what it was.
DETECTED_PATTERNS_V1 = {
    "following_weeks": 4,
    "patterns": [
        {
            "id": "surge-after-shortage",
            "name": "Stor ordre etter mangel",
            "definition": (
                "En ordre godt over innkommende ordre i en uke med restordre, "
                "eller i en av de to ukene etter."
            ),
            "mechanism": "demand_information_lost",
            "review": REVIEW,
            "lookback_weeks": 2,
            "min_ratio": "1.5",
            "min_excess": 4,
        },
        {
            "id": "large-order-full-supply-line",
            "name": "Stor ordre med mye på vei",
            "definition": (
                "En ordre godt over innkommende ordre mens det som er bestilt og ikke mottatt, "
                "allerede dekker minst seks uker med innkommende ordre."
            ),
            "mechanism": "supply_line",
            "review": REVIEW,
            "min_ratio": "1.5",
            "min_excess": 4,
            "min_cover_weeks": "6",
        },
        {
            "id": "low-after-overshoot",
            "name": "Svært lav ordre etter overskudd",
            "definition": (
                "En ordre på høyst halvparten av innkommende ordre mens lageret dekker "
                "minst fire uker med innkommende ordre."
            ),
            "mechanism": "delay",
            "review": REVIEW,
            "max_ratio": "0.5",
            "min_shortfall": 2,
            "min_cover_weeks": "4",
        },
    ],
}


def upgrade() -> None:
    op.drop_constraint("ck_content_records_kind", "content_records", type_="check")
    op.create_check_constraint(
        "ck_content_records_kind",
        "content_records",
        "kind IN ('starting_task', 'detected_patterns')",
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
                "id": uuid.UUID("01a1f9a0-0000-7000-8000-000000000101"),
                "kind": "detected_patterns",
                "version": 1,
                "body": DETECTED_PATTERNS_V1,
            }
        ],
    )

    op.create_table(
        "fact_sets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("game_id", sa.Uuid(), sa.ForeignKey("games.id"), nullable=False),
        sa.Column("seat_id", sa.Uuid(), sa.ForeignKey("seats.id"), nullable=False),
        sa.Column("analysis_version", sa.Integer(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("analysis_version >= 1", name="ck_fact_sets_analysis_version"),
        sa.UniqueConstraint("game_id", "seat_id", name="uq_fact_sets_game_seat"),
    )
    op.execute(
        """
        CREATE FUNCTION fact_sets_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'a facts set is stored once and never changed'
                USING ERRCODE = 'restrict_violation';
        END $$
        """
    )
    op.execute(
        "CREATE TRIGGER trg_fact_sets_immutable BEFORE UPDATE ON fact_sets "
        "FOR EACH ROW EXECUTE FUNCTION fact_sets_immutable()"
    )


def downgrade() -> None:
    op.drop_table("fact_sets")
    op.execute("DROP FUNCTION fact_sets_immutable()")
    op.execute("DELETE FROM content_records WHERE kind = 'detected_patterns'")
    op.drop_constraint("ck_content_records_kind", "content_records", type_="check")
    op.create_check_constraint(
        "ck_content_records_kind", "content_records", "kind IN ('starting_task')"
    )
