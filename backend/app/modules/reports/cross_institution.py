"""«Tverrinstitusjonell statistikk» (Story 14.7, cut list, FR-65, FR-5, AD-12, AD-14, AD-17).

`institution_statistics(chosen)` reads every stored aggregate (Story 14.3) with the Institution it
was written for (revision 0402), never the live tables: two reads of `class_aggregates` and
`class_aggregate_measures` whatever their number, plus the Institutions' names and the model
configs' names for the filter options. Story 14.4's `cross_class.compare` filters the Class
sessions and labels what differs; `combine` (pure) then groups the compared Class sessions by
Institution. No Class, Class session, Lecturer or Student is named. No write.

Each Institution's figure of a measure is the median of its compared Class sessions' stored,
unwithheld values, every one of which already rests on 10 or more Students. An Institution with
only one compared Class session would show that Class session's own figures: it is listed only
when none of its shown measures was withheld, and otherwise withheld as a whole (the rule holds
after filtering, so a filter cannot single out a small Class session)."""

import statistics
import uuid
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any, get_args

from sqlalchemy import select

from app.modules.identity import service as identity
from app.modules.reports.cross_class import SCORE_MEASURES, SHOWN, compare
from app.modules.reports.cross_class_schemas import DiffKey, FilterDimension
from app.modules.reports.cross_institution_schemas import (
    ComparedInstitutionOut,
    InstitutionMeasureOut,
    InstitutionStatisticsOut,
    InstitutionValueOut,
)
from app.modules.reports.models import class_aggregate_measures, class_aggregates
from app.modules.sessions import service as sessions
from app.platform.collation import nb_sort_key
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker

__all__ = ["READ", "Stored", "combine", "enabled", "institution_statistics"]

READ = "institution_statistics.read"
"""The policy of the view (`platform/authz`): the Admin only in v1."""

_DIFF_KEYS: tuple[DiffKey, ...] = get_args(DiffKey)

Stored = tuple[Decimal | None, bool]
"""A stored measure row: its value and whether it was withheld."""


def enabled() -> bool:
    """`FEATURE_CROSS_INSTITUTION_STATS` (AD-17): whether the view exists at all."""
    return get_settings().feature_cross_institution_stats


def combine(
    compared: Sequence[tuple[uuid.UUID, uuid.UUID]],
    differs: Mapping[uuid.UUID, Sequence[DiffKey]],
    stored: Mapping[tuple[uuid.UUID, str], Stored],
    names: Mapping[uuid.UUID, str],
    scores_comparable: bool | None,
) -> tuple[list[ComparedInstitutionOut], list[InstitutionMeasureOut]]:
    """The compared Class sessions (each with its Institution) grouped by Institution: the
    Institutions in Norwegian name order and each shown measure over them. Pure."""
    by_institution: dict[uuid.UUID, list[uuid.UUID]] = {}
    for session_id, institution_id in compared:
        by_institution.setdefault(institution_id, []).append(session_id)
    order = sorted(by_institution, key=lambda i: (nb_sort_key(names.get(i, "")), str(i)))
    shown = [key for key, _ in SHOWN]
    institutions: list[ComparedInstitutionOut] = []
    withheld: set[uuid.UUID] = set()
    for institution_id in order:
        members = by_institution[institution_id]
        single_withheld = len(members) == 1 and any(
            stored.get((members[0], key), (None, False))[1] for key in shown
        )
        if single_withheld:
            withheld.add(institution_id)
        held = {key for member in members for key in differs.get(member, ())}
        institutions.append(
            ComparedInstitutionOut(
                institution_id=institution_id,
                name=names.get(institution_id, ""),
                sessions=len(members),
                withheld=single_withheld,
                differs=[] if single_withheld else [k for k in _DIFF_KEYS if k in held],
            )
        )
    measures: list[InstitutionMeasureOut] = []
    for key, unit in SHOWN:
        values: list[InstitutionValueOut] = []
        for institution_id in order:
            if institution_id in withheld:
                values.append(
                    InstitutionValueOut(
                        institution_id=institution_id, value=None, withheld=True, sessions=0
                    )
                )
                continue
            rows = [
                stored[(member, key)]
                for member in by_institution[institution_id]
                if (member, key) in stored
            ]
            figures = [value for value, held_back in rows if not held_back and value is not None]
            values.append(
                InstitutionValueOut(
                    institution_id=institution_id,
                    value=Decimal(statistics.median(figures)) if figures else None,
                    withheld=not figures and any(held_back for _, held_back in rows),
                    sessions=len(figures),
                )
            )
        measures.append(
            InstitutionMeasureOut(
                key=key,
                unit=unit,
                values=values,
                comparable=scores_comparable if key in SCORE_MEASURES else None,
            )
        )
    return institutions, measures


async def institution_statistics(
    chosen: Mapping[FilterDimension, str | None] | None = None,
) -> InstitutionStatisticsOut:
    """The view (the module doc) under the chosen filters (Story 14.4's tokens)."""
    institution_of: dict[uuid.UUID, uuid.UUID] = {}
    keys: dict[uuid.UUID, Mapping[str, Any]] = {}
    stored: dict[tuple[uuid.UUID, str], Stored] = {}
    async with get_sessionmaker()() as s:
        # One snapshot for both reads: a job rewriting an aggregate in between never pairs one
        # write's header with another's measures.
        await s.connection(execution_options={"isolation_level": "REPEATABLE READ"})
        for row in await s.execute(
            select(
                class_aggregates.c.class_session_id,
                class_aggregates.c.institution_id,
                class_aggregates.c["keys"].label("stored_keys"),
            ).order_by(class_aggregates.c.class_session_id)
        ):
            institution_of[row.class_session_id] = row.institution_id
            keys[row.class_session_id] = row.stored_keys or {}
        if institution_of:
            for row in await s.execute(
                select(
                    class_aggregate_measures.c.class_session_id,
                    class_aggregate_measures.c.measure,
                    class_aggregate_measures.c.value,
                    class_aggregate_measures.c.withheld,
                ).where(class_aggregate_measures.c.measure.in_([key for key, _ in SHOWN]))
            ):
                stored[(row.class_session_id, row.measure)] = (row.value, row.withheld)
    names = await identity.institution_labels(list(set(institution_of.values())))
    # The Class sessions in the order of their Institution's name, then of creation (UUIDv7):
    # the filter options' first-seen order.
    ready = sorted(
        keys.items(),
        key=lambda item: (nb_sort_key(names.get(institution_of[item[0]], "")), str(item[0])),
    )
    models = {str(k["model_config_id"]) for _, k in ready if k.get("model_config_id")}
    model_names = await sessions.model_names(models) if len(ready) >= 2 else {}
    result = compare(ready, chosen or {}, model_names)
    institutions, measures = combine(
        [(session_id, institution_of[session_id]) for session_id in result.compared],
        result.differs,
        stored,
        names,
        result.scores_comparable,
    )
    return InstitutionStatisticsOut(
        institutions=institutions,
        measures=measures if institutions else [],
        filters=result.filters,
        ready=len(ready),
        compared=len(result.compared),
    )
