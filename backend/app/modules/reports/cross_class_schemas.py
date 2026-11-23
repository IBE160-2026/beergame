"""Tverrklasse-statistikk's response (Stories 14.3 and 14.4, FR-65, NFR-6, AD-10, AD-14).

Every figure is a stored aggregate's (`reports.aggregates`), sent as a decimal string, so the web
app only formats it (AD-10). Class sessions are named by their Class and number only: no Student,
Seat or Game is named, and a withheld figure has no value (AD-14). Story 14.4: the filters, which
Class sessions are compared, what each differs in and whether the scores are comparable are the
api's, from the stored comparability keys; the web app only names them from `nb.ts`."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

__all__ = [
    "ComparedMeasureOut",
    "ComparedSessionOut",
    "ComparedValueOut",
    "CrossClassOut",
    "DiffKey",
    "FilterDimension",
    "FilterOptionOut",
    "FilterOut",
]

MeasureUnit = Literal["kroner", "ratio", "percent", "points"]

FilterDimension = Literal["game_settings", "ai_mode", "model", "prompt_versions", "effort_level"]
"""What the Lecturer may filter the comparison by (Story 14.4)."""

DiffKey = Literal[
    "game_settings",
    "ai_mode",
    "model",
    "prompt_versions",
    "effort_level",
    "question_set",
    "item_weights",
    "scoring_guide",
]
"""What two compared Class sessions may differ in (Story 14.4): the filter dimensions and the
three keys a score comparison holds equal."""


class ComparedSessionOut(BaseModel):
    """A Class session the Lecturer may compare: its Class, number and whether the Class is
    archived; `written_at` is when its aggregate was written, None while it is not (not ready for
    comparison)."""

    class_session_id: uuid.UUID
    class_name: str
    session_number: int
    archived: bool
    written_at: datetime | None
    compared: bool = False
    """Story 14.4: written and matching every filter, so it is in the measures."""
    differs: list[DiffKey] = []
    """Story 14.4: what this compared Class session differs in from the others' most common
    value (every compared session, for a key with no single most common value); empty for one
    not compared."""


class ComparedValueOut(BaseModel):
    """One Class session's figure of a measure: `withheld` when its group held fewer than 10
    Students (no value); neither a value nor withheld when the measure was not measured (no
    finished game, the AI assessment off)."""

    class_session_id: uuid.UUID
    value: Decimal | None
    withheld: bool


class ComparedMeasureOut(BaseModel):
    """One measure across the ready Class sessions, in their order: `key` is the stored measure
    code the page names from `nb.ts`, `unit` how it is formatted."""

    key: str
    unit: MeasureUnit
    values: list[ComparedValueOut]
    comparable: bool | None = None
    """Story 14.4, a score measure only: whether the compared Class sessions hold the same
    question set, Item weights and Scoring guide version; None for any other measure and with
    fewer than two compared."""


class FilterOptionOut(BaseModel):
    """One value of a filter dimension among the Class sessions with an aggregate. `value` is the
    token the query sends back (a hash of the stored key). `label` is data, never copy: for Game
    settings `classic` or None (then named by `ordinal`), the AI mode's code, the model config's
    name, the prompt versions as «purpose version» pairs, the Effort level's label; None when the
    Class session had none (no model for rule-based players). `count` is the Class sessions
    holding it that match the other dimensions' filters."""

    value: str
    label: str | None
    ordinal: int
    count: int
    selected: bool


class FilterOut(BaseModel):
    """A filter dimension: its options, and `all_count`, the Class sessions «Alle» would compare
    (those matching the other dimensions' filters)."""

    dimension: FilterDimension
    all_count: int
    options: list[FilterOptionOut]


class CrossClassOut(BaseModel):
    """Tverrklasse-statistikk: every Class session of the Lecturer's own Classes (archived ones
    included, Control tests never), by Class and number, and the shown measures over those with a
    written aggregate. «Samme mål, samme regnestykke.»"""

    sessions: list[ComparedSessionOut]
    measures: list[ComparedMeasureOut]
    filters: list[FilterOut] = []
    """Story 14.4: one per dimension once two Class sessions have an aggregate."""
