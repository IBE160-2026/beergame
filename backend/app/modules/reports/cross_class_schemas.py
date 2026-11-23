"""Tverrklasse-statistikk's response (Story 14.3, FR-65, AD-10, AD-14).

Every figure is a stored aggregate's (`reports.aggregates`), sent as a decimal string, so the web
app only formats it (AD-10). Class sessions are named by their Class and number only: no Student,
Seat or Game is named, and a withheld figure has no value (AD-14)."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

__all__ = ["ComparedMeasureOut", "ComparedSessionOut", "ComparedValueOut", "CrossClassOut"]

MeasureUnit = Literal["kroner", "ratio", "percent", "points"]


class ComparedSessionOut(BaseModel):
    """A Class session the Lecturer may compare: its Class, number and whether the Class is
    archived; `written_at` is when its aggregate was written, None while it is not (not ready for
    comparison)."""

    class_session_id: uuid.UUID
    class_name: str
    session_number: int
    archived: bool
    written_at: datetime | None


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


class CrossClassOut(BaseModel):
    """Tverrklasse-statistikk: every Class session of the Lecturer's own Classes (archived ones
    included, Control tests never), by Class and number, and the shown measures over those with a
    written aggregate. «Samme mål, samme regnestykke.»"""

    sessions: list[ComparedSessionOut]
    measures: list[ComparedMeasureOut]
