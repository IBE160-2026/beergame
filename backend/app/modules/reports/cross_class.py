"""Tverrklasse-statistikk (Story 14.3, FR-65, FR-6, AD-10, AD-12, AD-13, AD-14).

`class_statistics(user)` lists every course Class session of every Class the Lecturer owns
(`sessions.owned_report_sessions` over `authz.classes_visible_to`, archived Classes included,
Control tests never) and reads the shown measures from the stored aggregates only, never the live
tables, so the comparison gives the same answer before and after retention deletes the Student
data. A Class session with no aggregate yet is listed, not compared. The figures take two reads
whatever the number of Class sessions (NFR-3); the list reads each owned Class once, as
«Klassene dine» does. No write."""

import uuid
from decimal import Decimal

from sqlalchemy import select

from app.modules.reports.aggregates import CHAIN_MEDIAN
from app.modules.reports.class_report import READ
from app.modules.reports.cross_class_schemas import (
    ComparedMeasureOut,
    ComparedSessionOut,
    ComparedValueOut,
    CrossClassOut,
    MeasureUnit,
)
from app.modules.reports.models import class_aggregate_measures, class_aggregates
from app.modules.sessions import service as sessions
from app.platform import authz
from app.platform.db import get_sessionmaker

__all__ = ["SHOWN", "class_statistics"]

_ROLES_FABRIKK_FIRST = ("factory", "distributor", "wholesaler", "retailer")

SHOWN: tuple[tuple[str, MeasureUnit], ...] = (
    (CHAIN_MEDIAN, "kroner"),
    *((f"cost.{role}.median", "kroner") for role in _ROLES_FABRIKK_FIRST),
    *((f"amplification.{role}.median", "ratio") for role in _ROLES_FABRIKK_FIRST),
    ("ai.seats_percent", "percent"),
    ("learning.submitted_percent", "percent"),
    ("core.median", "points"),
)
"""The measures the page compares, in its order (Role lists put Fabrikk at the top)."""


async def class_statistics(user: authz.Principal) -> CrossClassOut:
    listed = await sessions.owned_report_sessions(user, READ)
    ids = [found.id for found in listed]
    written: dict[uuid.UUID, object] = {}
    stored: dict[tuple[uuid.UUID, str], tuple[Decimal | None, bool]] = {}
    if ids:
        async with get_sessionmaker()() as s:
            for row in await s.execute(
                select(class_aggregates.c.class_session_id, class_aggregates.c.written_at).where(
                    class_aggregates.c.class_session_id.in_(ids)
                )
            ):
                written[row.class_session_id] = row.written_at
            for row in await s.execute(
                select(
                    class_aggregate_measures.c.class_session_id,
                    class_aggregate_measures.c.measure,
                    class_aggregate_measures.c.value,
                    class_aggregate_measures.c.withheld,
                ).where(
                    class_aggregate_measures.c.class_session_id.in_(list(written)),
                    class_aggregate_measures.c.measure.in_([key for key, _ in SHOWN]),
                )
            ):
                stored[(row.class_session_id, row.measure)] = (row.value, row.withheld)
    ready = [found.id for found in listed if found.id in written]
    return CrossClassOut(
        sessions=[
            ComparedSessionOut(
                class_session_id=found.id,
                class_name=found.class_name,
                session_number=found.number,
                archived=found.archived,
                written_at=written.get(found.id),  # type: ignore[arg-type]
            )
            for found in listed
        ],
        measures=[
            ComparedMeasureOut(
                key=key,
                unit=unit,
                values=[
                    ComparedValueOut(
                        class_session_id=session_id,
                        value=stored.get((session_id, key), (None, False))[0],
                        withheld=stored.get((session_id, key), (None, False))[1],
                    )
                    for session_id in ready
                ],
            )
            for key, unit in SHOWN
        ]
        if ready
        else [],
    )
