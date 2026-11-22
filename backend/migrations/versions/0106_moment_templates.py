"""The own moments' templates and the facts set each Student's moments cite (Story 9.7, FR-44,
AD-7, AD-23).

`content_records` takes a fifth kind, `moment_templates`, and version 1 is stored here: the
templates code fills from a stored facts set for Debrief step 4 (draft copy, Issue #31).
`debrief_fact_sets` (owned by `modules/debrief`) holds, per Student and Class session, the facts
set their moments were rendered from, stored once and never changed: a trigger refuses every
update.

Revision ID: 0106
Revises: 0105
Create Date: 2026-11-21
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0106"
down_revision: str | None = "0105"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# A literal, never imported from the app: what version 1 was stays what it was.
MOMENT_TEMPLATES_V1 = {
    "templates": [
        {
            "id": "moments-heading",
            "text": (
                "Ditt øyeblikk: Uke {week}. Du bestilte {order} med {supply_line} på vei. "
                "Og hva det kostet kjeden."
            ),
        },
        {
            "id": "moment-heading",
            "text": "Uke {week}. Du bestilte {order} med {supply_line} på vei.",
        },
        {
            "id": "moment-position",
            "text": (
                "Posisjon {inventory} − {backlog} + {supply_line} = {position}. "
                "Med {order} ble den {position_after}."
            ),
        },
        {
            "id": "moment-later",
            "text": "I Uke {first_week} til {last_week} kostet leddet ditt {later_cost} kr.",
        },
        {
            "id": "moment-later-one",
            "text": "I Uke {first_week} kostet leddet ditt {later_cost} kr.",
        },
        {
            "id": "moment-later-none",
            "text": "Dette var spillets siste uke. Ingen senere uke kostet noe.",
        },
        {"id": "moment-pattern", "text": "Mønster: {name}. {definition}"},
        {
            "id": "mechanism-delay",
            "text": (
                "Mønsteret hører til mekanismen forsinkelse: det går uker fra en ordre sendes "
                "til varene er framme."
            ),
        },
        {
            "id": "mechanism-supply-line",
            "text": (
                "Mønsteret hører til mekanismen varene på vei: det som er bestilt og ikke kommet, "
                "hører med i posisjonen."
            ),
        },
        {
            "id": "mechanism-demand-information-lost",
            "text": (
                "Mønsteret hører til mekanismen etterspørsel som går tapt i ordrene: oppover i "
                "kjeden ser hvert ledd bare ordrer, ikke hva kundene bestilte."
            ),
        },
        {
            "id": "moment-gap-above",
            "text": (
                "Ingen av mønstrene passer denne uka. "
                "Du bestilte {gap} mer enn ordren inn, som var {incoming_order}."
            ),
        },
        {
            "id": "moment-gap-below",
            "text": (
                "Ingen av mønstrene passer denne uka. "
                "Du bestilte {gap} mindre enn ordren inn, som var {incoming_order}."
            ),
        },
        {
            "id": "moment-gap-equal",
            "text": (
                "Ingen av mønstrene passer denne uka. "
                "Du bestilte det samme som ordren inn, {incoming_order}."
            ),
        },
    ]
}

KINDS_BEFORE = (
    "kind IN ('starting_task', 'detected_patterns', 'sentence_templates', 'reflection_questions')"
)


def upgrade() -> None:
    op.drop_constraint("ck_content_records_kind", "content_records", type_="check")
    op.create_check_constraint(
        "ck_content_records_kind",
        "content_records",
        "kind IN ('starting_task', 'detected_patterns', 'sentence_templates', "
        "'reflection_questions', 'moment_templates')",
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
                "id": uuid.UUID("01a1f9a0-0000-7000-8000-000000000106"),
                "kind": "moment_templates",
                "version": 1,
                "body": MOMENT_TEMPLATES_V1,
            }
        ],
    )
    op.create_table(
        "debrief_fact_sets",
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
        sa.Column(
            "game_id",
            sa.Uuid(),
            sa.ForeignKey("games.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "fact_set_id",
            sa.Uuid(),
            sa.ForeignKey("fact_sets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute(
        """
        CREATE FUNCTION debrief_fact_sets_immutable() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'the facts set of a Student''s moments is stored once'
                USING ERRCODE = 'restrict_violation';
        END $$
        """
    )
    op.execute(
        "CREATE TRIGGER trg_debrief_fact_sets_immutable "
        "BEFORE UPDATE ON debrief_fact_sets "
        "FOR EACH ROW EXECUTE FUNCTION debrief_fact_sets_immutable()"
    )


def downgrade() -> None:
    op.drop_table("debrief_fact_sets")
    op.execute("DROP FUNCTION debrief_fact_sets_immutable()")
    op.execute("DELETE FROM content_records WHERE kind = 'moment_templates'")
    op.drop_constraint("ck_content_records_kind", "content_records", type_="check")
    op.create_check_constraint("ck_content_records_kind", "content_records", KINDS_BEFORE)
