"""The shape of a User's own stored data for «Mine data» (Story 15.1, FR-75, AD-12, AD-14).

Each owning module's `service.py` has an own-data reader, `own_records(user_id)`, that reads its
tables for that User only and answers `{category: [OwnRecord, ...]}`. `reports.my_data` gathers
them into one answer; the page labels every field key and every code from `nb.ts`. In `platform`
so that no module imports `reports`.

A reader takes the caller's own id from the route's principal, never an id from the request.
"""

import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

__all__ = ["CATEGORIES", "Category", "FieldKind", "OwnField", "OwnRecord", "merge", "record"]

Category = Literal[
    "account",
    "orders",
    "game",
    "explanation",
    "reflection",
    "follow_ups",
    "debrief",
    "quiz",
    "starting_task",
    "test",
    "assessment",
    "letter",
    "adjustments",
    "messages",
    "completion",
]
CATEGORIES: tuple[Category, ...] = (
    "account",
    "orders",
    "game",
    "explanation",
    "reflection",
    "follow_ups",
    "debrief",
    "quiz",
    "starting_task",
    "test",
    "assessment",
    "letter",
    "adjustments",
    "messages",
    "completion",
)
"""The «Mine data» categories in page order (EXPERIENCE.md → Mine data)."""

FieldKind = Literal["text", "number", "bool", "datetime", "date", "code"]
Value = str | int | bool | Decimal | datetime | date | None


@dataclass(frozen=True)
class OwnField:
    key: str
    kind: FieldKind
    value: str | None


@dataclass(frozen=True)
class OwnRecord:
    """One stored row of the User, as the page shows it: where it belongs (a Class session or a
    Class), when it was stored, and its fields."""

    fields: tuple[OwnField, ...]
    class_session_id: uuid.UUID | None = None
    class_id: uuid.UUID | None = None
    at: datetime | None = None
    kind: str = field(default="")
    """What the row is within its category (`role`, `answer`, …), labelled by the page."""


def _value(kind: FieldKind, value: Value) -> str | None:
    if value is None:
        return None
    if kind == "bool":
        return "true" if value else "false"
    if isinstance(value, datetime | date):
        return value.isoformat()
    return str(value)


def record(
    kind: str,
    fields: Iterable[tuple[str, FieldKind, Value]],
    *,
    class_session_id: uuid.UUID | None = None,
    class_id: uuid.UUID | None = None,
    at: datetime | None = None,
) -> OwnRecord:
    """An `OwnRecord` from `(key, kind, value)` triples; a value is kept as text."""
    return OwnRecord(
        fields=tuple(OwnField(key, k, _value(k, value)) for key, k, value in fields),
        class_session_id=class_session_id,
        class_id=class_id,
        at=at,
        kind=kind,
    )


def merge(
    *parts: Mapping[str, list[OwnRecord]],
) -> dict[str, list[OwnRecord]]:
    """The readers' answers together, by category."""
    out: dict[str, list[OwnRecord]] = {}
    for part in parts:
        for category, records in part.items():
            if category not in CATEGORIES:
                raise ValueError(f"not a «Mine data» category: {category}")
            out.setdefault(category, []).extend(records)
    return out
