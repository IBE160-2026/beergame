"""Version 2 of the Individual test's question set (Story 11.5, FR-80, FR-52, AD-23).

Every table item and every number item that is not a Starting task item gets its own table and
computed rule (`interactive`: prompt, rows, given columns, asked label, whether a value may be
negative, and coded criteria scored by `analysis.scoring.score_interactive`). Still placeholder
items marked `status: "draft"` until issue #16 delivers the real questions; the same body is
shipped as `app/modules/content/files/question_set.json` (a test keeps the two equal). Version 1
stays as it was: Class sessions pinned to it keep it.

Revision ID: 0124
Revises: 0123
Create Date: 2026-11-22
"""

# ruff: noqa: E501 (the content literal keeps its sentences whole)

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0124"
down_revision: str | None = "0123"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RECORD_ID = uuid.UUID("01a1f9a0-0000-7000-8000-000000000124")

# A literal, never imported from the app: what version 2 was stays what it was.
QUESTION_SET_V2 = {
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
            "interactive": None,
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
            "interactive": None,
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
            "interactive": None,
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
            "interactive": None,
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
            "interactive": None,
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
            "interactive": {
                "prompt": "Utkast: Etterspørselen følger et mønster du ikke har sett. Fyll inn hvor mange enheter som mangler ved slutten av hver uke.",
                "hint": None,
                "caption": "Utkast: Etterspørsel, levert og mangler per uke, i enheter",
                "rows": ["Uke 1", "Uke 2", "Uke 3", "Uke 4", "Uke 5", "Uke 6"],
                "given": [
                    {"key": "ettersporsel", "label": "Etterspørsel", "values": [4, 4, 8, 8, 4, 4]},
                    {"key": "levert", "label": "Levert", "values": [4, 4, 4, 4, 8, 8]},
                ],
                "asked": "Mangler",
                "negative": False,
                "criteria": [
                    {
                        "code": "K1",
                        "weight": 50,
                        "check": {
                            "kind": "flow",
                            "inflow": "ettersporsel",
                            "outflow": "levert",
                            "start": 0,
                        },
                    },
                    {"code": "K2", "weight": 25, "check": {"kind": "cell", "row": 3, "value": 8}},
                    {"code": "K3", "weight": 25, "check": {"kind": "cell", "row": 5, "value": 0}},
                ],
            },
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
            "interactive": {
                "prompt": "Utkast: Et bakeri har 10 enheter på lager før uke 1. Fyll inn lageret ved slutten av hver uke.",
                "hint": None,
                "caption": "Utkast: Bakeriets lager per uke, i enheter",
                "rows": ["Uke 1", "Uke 2", "Uke 3", "Uke 4", "Uke 5"],
                "given": [
                    {"key": "inn", "label": "Inn", "values": [20, 20, 25, 25, 20]},
                    {"key": "ut", "label": "Ut", "values": [22, 24, 20, 18, 25]},
                ],
                "asked": "Lager",
                "negative": False,
                "criteria": [
                    {
                        "code": "K1",
                        "weight": 60,
                        "check": {"kind": "flow", "inflow": "inn", "outflow": "ut", "start": 10},
                    },
                    {"code": "K2", "weight": 40, "check": {"kind": "cell", "row": 4, "value": 11}},
                ],
            },
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
            "interactive": {
                "prompt": "Utkast: Et verksted mangler deler i fire uker. Hvor mange enheter må legges til for å dekke alt som mangler?",
                "hint": None,
                "caption": "Utkast: Mangler per uke, i enheter",
                "rows": ["Uke 1", "Uke 2", "Uke 3", "Uke 4"],
                "given": [{"key": "mangler", "label": "Mangler", "values": [3, 5, 2, 6]}],
                "asked": "Legg til",
                "negative": False,
                "criteria": [
                    {
                        "code": "K1",
                        "weight": 100,
                        "check": {"kind": "balance", "added": "answer", "missing": "mangler"},
                    }
                ],
            },
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
            "interactive": None,
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
            "interactive": None,
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
            "interactive": {
                "prompt": "Utkast: Fyll inn hvor mange enheter som mangler ved slutten av hver uke.",
                "hint": None,
                "caption": "Utkast: Bestilt, mottatt og mangler per uke, i enheter",
                "rows": ["Uke 1", "Uke 2", "Uke 3", "Uke 4"],
                "given": [
                    {"key": "bestilt", "label": "Bestilt", "values": [5, 5, 5, 5]},
                    {"key": "mottatt", "label": "Mottatt", "values": [3, 4, 6, 7]},
                ],
                "asked": "Mangler",
                "negative": False,
                "criteria": [
                    {
                        "code": "K1",
                        "weight": 50,
                        "check": {
                            "kind": "flow",
                            "inflow": "bestilt",
                            "outflow": "mottatt",
                            "start": 0,
                        },
                    },
                    {"code": "K2", "weight": 50, "check": {"kind": "cell", "row": 3, "value": 0}},
                ],
            },
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
            "interactive": None,
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
    # The next version of the kind: 2 on every database the app made (a load never published a
    # second question set before this file changed).
    newest = op.get_bind().scalar(
        sa.text("SELECT max(version) FROM content_records WHERE kind = 'question_set'")
    )
    op.bulk_insert(
        records,
        [
            {
                "id": RECORD_ID,
                "kind": "question_set",
                "version": (newest or 0) + 1,
                "body": QUESTION_SET_V2,
            }
        ],
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM content_records WHERE id = :id").bindparams(id=RECORD_ID))
