"""«Tverrinstitusjonell statistikk»'s response (Story 14.7, cut list, FR-65, FR-5, AD-12, AD-14).

The stored aggregates of Story 14.3 grouped by Institution: every figure is a statistic of stored
figures that each rest on 10 or more Students, sent as a decimal string, so the web app only
formats it (AD-10). Institutions are the only thing named: no Class, Class session, Lecturer,
Student, Seat or Game is named, and only Class sessions are counted. The filters and the
difference labels are Story 14.4's, from the stored comparability keys."""

import uuid
from decimal import Decimal

from pydantic import BaseModel

from app.modules.reports.cross_class_schemas import DiffKey, FilterOut, MeasureUnit

__all__ = [
    "InstitutionMeasureOut",
    "ComparedInstitutionOut",
    "InstitutionStatisticsOut",
    "InstitutionValueOut",
]


class ComparedInstitutionOut(BaseModel):
    """An Institution with at least one compared Class session: its name, how many of its Class
    sessions are compared, and what its compared Class sessions differ in from the most common
    setup. `withheld` when its one compared Class session has a shown measure over fewer than 10
    Students: then it shows no figure and no difference."""

    institution_id: uuid.UUID
    name: str
    sessions: int
    withheld: bool
    differs: list[DiffKey]


class InstitutionValueOut(BaseModel):
    """One Institution's figure of a measure: the median of its compared Class sessions' stored,
    unwithheld values (`sessions` of them). `withheld` with no value when only withheld figures
    were stored (or the Institution is withheld); neither when the measure was not measured."""

    institution_id: uuid.UUID
    value: Decimal | None
    withheld: bool
    sessions: int


class InstitutionMeasureOut(BaseModel):
    """One measure across the listed Institutions, in their order (Story 14.3's codes and units);
    `comparable` on a score measure as in Story 14.4."""

    key: str
    unit: MeasureUnit
    values: list[InstitutionValueOut]
    comparable: bool | None = None


class InstitutionStatisticsOut(BaseModel):
    """The Institutions in Norwegian name order, the shown measures over them, and the filters
    (one per dimension once two Class sessions have an aggregate). `ready` counts the Class
    sessions with an aggregate, `compared` those matching the filters."""

    institutions: list[ComparedInstitutionOut]
    measures: list[InstitutionMeasureOut]
    filters: list[FilterOut]
    ready: int
    compared: int
