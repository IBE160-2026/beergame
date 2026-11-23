"""Tverrklasse-statistikk (Stories 14.3 and 14.4, FR-65, FR-6, NFR-6, AD-10, AD-12, AD-13, AD-14).

`class_statistics(user, filters)` lists every course Class session of every Class the Lecturer owns
(`sessions.owned_report_sessions` over `authz.classes_visible_to`, archived Classes included,
Control tests never) and reads the shown measures from the stored aggregates only, never the live
tables, so the comparison gives the same answer before and after retention deletes the Student
data. A Class session with no aggregate yet is listed, not compared. The figures take two reads
whatever the number of Class sessions (NFR-3), plus one read per distinct model config to name the
filter options; the list reads each owned Class once, as «Klassene dine» does. No write.

Story 14.4: `compare` (pure) reads each aggregate's stored comparability keys: the filters (one
value per dimension, matched on a hash of the stored key, all given filters must hold), the
options with faceted counts, which Class sessions are compared, what each differs in from the
others' most common value, and whether the Core-only scores are comparable (same question set,
Item weights and Scoring guide version)."""

import hashlib
import json
import uuid
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, get_args

from sqlalchemy import select

from app.engine.settings import GameSettings
from app.modules.reports.aggregates import CHAIN_MEDIAN
from app.modules.reports.class_report import READ
from app.modules.reports.cross_class_schemas import (
    ComparedMeasureOut,
    ComparedSessionOut,
    ComparedValueOut,
    CrossClassOut,
    DiffKey,
    FilterDimension,
    FilterOptionOut,
    FilterOut,
    MeasureUnit,
)
from app.modules.reports.models import class_aggregate_measures, class_aggregates
from app.modules.sessions import service as sessions
from app.platform import authz
from app.platform.db import get_sessionmaker

__all__ = ["DIMENSIONS", "SCORE_MEASURES", "SHOWN", "Comparison", "class_statistics", "compare"]

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

SCORE_MEASURES = frozenset({"core.median"})
"""The test-score measures (Core-only): comparable only on the same question set, Item weights
and Scoring guide version."""

DIMENSIONS: tuple[FilterDimension, ...] = get_args(FilterDimension)
_DIFF_KEYS: tuple[DiffKey, ...] = get_args(DiffKey)
_SCORE_KEYS: tuple[DiffKey, ...] = ("question_set", "item_weights", "scoring_guide")
_STORED: dict[DiffKey, str] = {
    "game_settings": "game_settings",
    "ai_mode": "ai_mode",
    "model": "model_config_id",
    "prompt_versions": "prompt_versions",
    "effort_level": "effort_level",
    "question_set": "question_set_version",
    "item_weights": "item_weights",
    "scoring_guide": "scoring_guide",
}
"""Each difference's key in `class_aggregates.keys` (Story 14.3's `_keys`)."""


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def token(value: object) -> str:
    """A stored key's filter value: the first 16 hex of the SHA-256 of its canonical JSON."""
    return hashlib.sha256(_canonical(value).encode()).hexdigest()[:16]


def _value(keys: Mapping[str, Any], key: DiffKey) -> object:
    """The stored value of a difference key; one absent from an older aggregate reads as None."""
    return keys.get(_STORED[key])


def _classic(settings: object) -> bool:
    if not isinstance(settings, dict):
        return False
    try:
        return sessions.is_classic(GameSettings.model_validate(settings))
    except ValueError:
        return False


@dataclass(frozen=True)
class Comparison:
    """`compare`'s answer: the compared Class sessions in the given order, what each differs in,
    whether the scores are comparable (None under two compared) and the filters."""

    compared: list[uuid.UUID]
    differs: dict[uuid.UUID, list[DiffKey]]
    scores_comparable: bool | None
    filters: list[FilterOut]


def compare(
    ready: Sequence[tuple[uuid.UUID, Mapping[str, Any]]],
    chosen: Mapping[FilterDimension, str | None],
    names: Mapping[str, sessions.ModelName] | None = None,
) -> Comparison:
    """The comparison of the Class sessions with an aggregate (`ready`, each with its stored keys,
    in the page's order) under the chosen filters (a token per dimension; one no ready Class
    session holds is ignored). Pure."""
    names = names or {}
    tokens = {
        session_id: {dimension: token(_value(keys, dimension)) for dimension in DIMENSIONS}
        for session_id, keys in ready
    }
    held = {dimension: {t[dimension] for t in tokens.values()} for dimension in DIMENSIONS}
    active = {
        dimension: value
        for dimension, value in chosen.items()
        if value is not None and value in held.get(dimension, set())
    }

    def matches(session_id: uuid.UUID, *, but: FilterDimension | None = None) -> bool:
        return all(
            tokens[session_id][dimension] == value
            for dimension, value in active.items()
            if dimension != but
        )

    compared = [session_id for session_id, _ in ready if matches(session_id)]
    keys_of = dict(ready)
    differs: dict[uuid.UUID, list[DiffKey]] = {session_id: [] for session_id in compared}
    for key in _DIFF_KEYS:
        values = {
            session_id: _canonical(_value(keys_of[session_id], key)) for session_id in compared
        }
        counted = Counter(values.values()).most_common()
        if len(counted) < 2:
            continue
        reference = counted[0][0] if counted[0][1] > counted[1][1] else None
        for session_id in compared:
            if reference is None or values[session_id] != reference:
                differs[session_id].append(key)
    scores: bool | None = None
    if len(compared) >= 2:
        # A key no aggregate stored proves nothing: the scores are then not comparable.
        scores = all(
            _value(keys_of[session_id], key) is not None
            for session_id in compared
            for key in _SCORE_KEYS
        ) and all(
            len({_canonical(_value(keys_of[session_id], key)) for session_id in compared}) == 1
            for key in _SCORE_KEYS
        )
    filters: list[FilterOut] = []
    if len(ready) >= 2:
        for dimension in DIMENSIONS:
            others = [session_id for session_id, _ in ready if matches(session_id, but=dimension)]
            options: list[FilterOptionOut] = []
            seen: dict[str, FilterOptionOut] = {}
            unnamed = 0
            for session_id, keys in ready:
                value_token = tokens[session_id][dimension]
                if value_token in seen:
                    continue
                stored = _value(keys, dimension)
                label = _label(dimension, stored, keys, names)
                if dimension == "game_settings" and label is None:
                    unnamed += 1
                option = FilterOptionOut(
                    value=value_token,
                    label=label,
                    ordinal=unnamed if dimension == "game_settings" and label is None else 0,
                    count=sum(1 for other in others if tokens[other][dimension] == value_token),
                    selected=active.get(dimension) == value_token,
                )
                seen[value_token] = option
                options.append(option)
            filters.append(FilterOut(dimension=dimension, all_count=len(others), options=options))
    return Comparison(compared, differs, scores, filters)


def _label(
    dimension: FilterDimension,
    stored: object,
    keys: Mapping[str, Any],
    names: Mapping[str, sessions.ModelName],
) -> str | None:
    """A filter option's label: data the web app names, never copy (`FilterOptionOut`)."""
    if stored is None:
        return None
    if dimension == "game_settings":
        return "classic" if _classic(stored) else None
    if dimension == "model":
        found = names.get(str(stored))
        return found.name if found else str(stored)
    if dimension == "prompt_versions":
        if not isinstance(stored, dict) or not stored:
            return None
        return ", ".join(f"{purpose} {version}" for purpose, version in sorted(stored.items()))
    if dimension == "effort_level":
        found = names.get(str(keys.get("model_config_id")))
        return found.levels.get(str(stored), str(stored)) if found else str(stored)
    return str(stored)


async def class_statistics(
    user: authz.Principal, chosen: Mapping[FilterDimension, str | None] | None = None
) -> CrossClassOut:
    listed = await sessions.owned_report_sessions(user, READ)
    ids = [found.id for found in listed]
    written: dict[uuid.UUID, object] = {}
    keys: dict[uuid.UUID, Mapping[str, Any]] = {}
    stored: dict[tuple[uuid.UUID, str], tuple[Decimal | None, bool]] = {}
    if ids:
        async with get_sessionmaker()() as s:
            for row in await s.execute(
                select(
                    class_aggregates.c.class_session_id,
                    class_aggregates.c.written_at,
                    class_aggregates.c["keys"].label("stored_keys"),
                ).where(class_aggregates.c.class_session_id.in_(ids))
            ):
                written[row.class_session_id] = row.written_at
                keys[row.class_session_id] = row.stored_keys or {}
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
    ready = [(found.id, keys[found.id]) for found in listed if found.id in written]
    models = {str(k["model_config_id"]) for _, k in ready if k.get("model_config_id")}
    names = await sessions.model_names(models) if len(ready) >= 2 else {}
    result = compare(ready, chosen or {}, names)
    compared = set(result.compared)
    return CrossClassOut(
        sessions=[
            ComparedSessionOut(
                class_session_id=found.id,
                class_name=found.class_name,
                session_number=found.number,
                archived=found.archived,
                written_at=written.get(found.id),  # type: ignore[arg-type]
                compared=found.id in compared,
                differs=result.differs.get(found.id, []),
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
                    for session_id in result.compared
                ],
                comparable=result.scores_comparable if key in SCORE_MEASURES else None,
            )
            for key, unit in SHOWN
        ]
        if ready
        else [],
        filters=result.filters,
    )
