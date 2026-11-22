"""A Class session's selection of the question set: «Spørsmål og vekter» (Story 11.1, FR-52,
FR-53, FR-18, AD-4, AD-12, AD-23).

The question set is an immutable versioned record in `content` (kind `question_set`). A Class
session keeps one selection row (`test_selections`): the version it was saved on, the items taken
out, each Core item's weight and the Adapted total weight. The selection in force (`effective`)
is that row when it was saved on the latest version, and the latest version's defaults otherwise
(no row, or a row on an older version: `outdated`). The block shows exactly what the Start-date
lock pins: `question_set_pin`, registered with `sessions`, stores the selection in force under
`SessionRuntime.pins["question_set"]`; from then on the block reads the pin. In production the
lock is refused while that version is a `draft` (issue #16): `sessions.PinRefused`
(`question_set_draft`).

A save («Lagre vekter») is for the Class's owners (`question_set.change`) before the Start-date
lock point (`sessions.lock_for_question_set`, 409 `session_locked`), in one transaction holding
the Class session's row lock; the weights of the items left in plus the Adapted total must be
100 (`WeightsNot100`, 422 `weights_not_100`). It is recorded in the audit log and emits
`session:<id>`. `copy_selection`, registered with `sessions`, copies the selection into a Class
session made from this one (FR-66).

`sessions` never imports this module: it registers itself there, and `ops.sweep` and the app
import it so every lock has the pin."""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.content import service as content
from app.modules.content.schemas import QuestionSet
from app.modules.sessions import service as sessions
from app.modules.tests.models import test_selections
from app.modules.tests.schemas import AdaptedOut, QuestionItemOut, QuestionSetIn, QuestionSetOut
from app.platform import audit, authz, events
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker

__all__ = [
    "PIN",
    "SELECTION_CHANGED",
    "Selection",
    "UnknownItems",
    "WeightsNot100",
    "copy_selection",
    "effective",
    "pinned_selection",
    "question_set_pin",
    "read_block",
    "save",
]

log = structlog.get_logger(__name__)

PIN = content.Kind.QUESTION_SET.value
"""The pin of the question set selection in `SessionRuntime.pins`."""

SELECTION_CHANGED = "question_set.selection_changed"
"""The audit action of a saved selection (Story 11.1)."""

DRAFT_REFUSED = "question_set_draft"
"""The code of a lock refused in production on a draft question set (issue #16)."""


class WeightsNot100(Exception):
    """The weights of the items left in plus the Adapted total are not 100 (422
    `weights_not_100`)."""

    def __init__(self, total: int) -> None:
        super().__init__(total)
        self.total = total


class UnknownItems(Exception):
    """The save names an item the version does not have, leaves a Core item without a weight, or
    takes every Core item out (422 `validation_error`); `fields` says which."""

    def __init__(self, fields: dict[str, str]) -> None:
        super().__init__(fields)
        self.fields = fields


@dataclass(frozen=True)
class Selection:
    """A selection of one question set version: the items taken out, every Core item's weight
    and the Adapted total weight."""

    version: int
    excluded: frozenset[str]
    weights: Mapping[str, int]
    adapted_weight: int

    def total(self) -> int:
        """The weights of the items left in plus the Adapted total."""
        kept = sum(w for item, w in self.weights.items() if item not in self.excluded)
        return kept + self.adapted_weight

    def as_json(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "excluded": sorted(self.excluded),
            "weights": dict(self.weights),
            "adapted_weight": self.adapted_weight,
        }


def _defaults(version: int, question_set: QuestionSet) -> Selection:
    return Selection(
        version=version,
        excluded=frozenset(),
        weights={item.id: item.weight for item in question_set.items},
        adapted_weight=question_set.adapted_weight,
    )


def _from_row(row: Mapping[str, Any], question_set: QuestionSet) -> Selection:
    stored = row["weights"] or {}
    return Selection(
        version=row["question_set_version"],
        excluded=frozenset(row["excluded"] or ()),
        # A stored weight for every item of its version; the default if one were ever missing.
        weights={item.id: int(stored.get(item.id, item.weight)) for item in question_set.items},
        adapted_weight=row["adapted_weight"],
    )


def pinned_selection(pins: Any) -> Selection | None:
    """The selection the lock pinned, from a snapshot's `pins`; None before the lock and for a
    Class session locked before this pin existed."""
    found = pins.get(PIN) if isinstance(pins, dict) else None
    if not isinstance(found, dict):
        return None
    return Selection(
        version=int(found["version"]),
        excluded=frozenset(found.get("excluded") or ()),
        weights={str(k): int(v) for k, v in (found.get("weights") or {}).items()},
        adapted_weight=int(found["adapted_weight"]),
    )


async def _row(s: AsyncSession, class_session_id: uuid.UUID) -> Mapping[str, Any] | None:
    result = await s.execute(
        select(test_selections).where(test_selections.c.class_session_id == class_session_id)
    )
    return result.mappings().one_or_none()


async def effective(
    s: AsyncSession, class_session_id: uuid.UUID | None
) -> tuple[Selection, QuestionSet, bool]:
    """The selection in force before the lock: (selection, its question set, outdated). The
    stored row when it was saved on the latest version; else the latest version's defaults, and
    `outdated` when a row on an older version exists."""
    latest = await content.latest_version(content.Kind.QUESTION_SET, s)
    _, question_set = await content.question_set(latest)
    row = await _row(s, class_session_id) if class_session_id is not None else None
    if row is not None and row["question_set_version"] == latest:
        return _from_row(row, question_set), question_set, False
    return _defaults(latest, question_set), question_set, row is not None


async def question_set_pin(s: AsyncSession, class_session: Mapping[str, Any]) -> dict[str, Any]:
    """The lock's pin provider (Story 11.1, AD-4, AD-23): the selection in force, under
    `SessionRuntime.pins["question_set"]`. In production a draft version refuses the lock
    (`sessions.PinRefused`, `question_set_draft`, issue #16)."""
    selection, question_set, _ = await effective(s, class_session.get("id"))
    if question_set.status == "draft" and get_settings().app_env == "production":
        raise sessions.PinRefused(DRAFT_REFUSED)
    return selection.as_json()


async def copy_selection(
    s: AsyncSession, source: Mapping[str, Any], target_id: uuid.UUID, now: datetime
) -> None:
    """`sessions.copy_from`'s copier (Story 11.1, FR-66): the source's selection, its pin when it
    is locked, else its stored row; nothing when it has neither (the copy reads the defaults).
    A copy on an older version reads as `outdated`, like any such row."""
    pins = ((source.get("snapshot") or {}).get("session_runtime") or {}).get("pins")
    selection = pinned_selection(pins)
    if selection is None:
        row = await _row(s, source["id"])
        if row is None:
            return
        selection = Selection(
            version=row["question_set_version"],
            excluded=frozenset(row["excluded"] or ()),
            weights=dict(row["weights"] or {}),
            adapted_weight=row["adapted_weight"],
        )
    await s.execute(
        insert(test_selections).values(
            class_session_id=target_id,
            question_set_version=selection.version,
            excluded=sorted(selection.excluded),
            weights=dict(selection.weights),
            adapted_weight=selection.adapted_weight,
            updated_by=None,
            updated_at=now,
        )
    )


def _out(
    selection: Selection,
    question_set: QuestionSet,
    *,
    outdated: bool,
    pinned: bool,
    open_: bool,
    can_change: bool,
) -> QuestionSetOut:
    return QuestionSetOut(
        version=selection.version,
        draft=question_set.status == "draft",
        outdated=outdated,
        pinned=pinned,
        open=open_,
        can_change=can_change,
        items=[
            QuestionItemOut(
                id=item.id,
                type=item.type,
                title=item.title,
                weight=selection.weights.get(item.id, item.weight),
                default_weight=item.weight,
                excluded=item.id in selection.excluded,
                quantity="quantity" in item.tags,
                starting_task=item.starting_task_item is not None,
            )
            for item in question_set.items
        ],
        adapted=AdaptedOut(
            weight=selection.adapted_weight,
            default_weight=question_set.adapted_weight,
            replacements=len(question_set.replacements),
        ),
        sum=selection.total(),
    )


async def read_block(
    user: authz.Principal, class_session_id: uuid.UUID, now: datetime
) -> QuestionSetOut | None:
    """The «Spørsmål og vekter» block for the Class's staff (`class_sessions.read`): the pinned
    selection once locked, the selection in force before. None for every other caller."""
    found = await sessions.question_set_session(user, class_session_id)
    if found is None:
        return None
    open_ = not sessions.is_locked(found.row, now=now)
    pinned = pinned_selection(found.pins)
    if pinned is not None:
        question_set: QuestionSet = await content.get(content.Kind.QUESTION_SET, pinned.version)
        selection, outdated = pinned, False
    else:
        async with get_sessionmaker()() as s:
            selection, question_set, outdated = await effective(s, class_session_id)
    return _out(
        selection,
        question_set,
        outdated=outdated,
        pinned=pinned is not None,
        open_=open_,
        can_change=found.can_change,
    )


def _judge(wanted: QuestionSetIn, version: int, question_set: QuestionSet) -> Selection:
    ids = [item.id for item in question_set.items]
    fields: dict[str, str] = {}
    if set(wanted.weights) - set(ids) or set(ids) - set(wanted.weights):
        fields["weights"] = "items"
    if set(wanted.excluded) - set(ids):
        fields["excluded"] = "unknown_item"
    elif set(ids) <= set(wanted.excluded):
        fields["excluded"] = "all"
    if fields:
        raise UnknownItems(fields)
    selection = Selection(
        version=version,
        excluded=frozenset(wanted.excluded),
        weights={item: wanted.weights[item] for item in ids},
        adapted_weight=wanted.adapted_weight,
    )
    if selection.total() != 100:
        raise WeightsNot100(selection.total())
    return selection


async def save(
    user: authz.Principal, class_session_id: uuid.UUID, wanted: QuestionSetIn, now: datetime
) -> QuestionSetOut | None:
    """«Lagre vekter» (Story 11.1, FR-52, AD-15): store the selection on the latest version, in
    one transaction holding the Class session's row lock, with one audit row and `session:<id>`.
    None (403) for anyone but an owner of the Class. Raises
    `sessions.SessionLocked` past the Start-date lock point, `classes.ClassArchived`,
    `UnknownItems` and `WeightsNot100`; nothing is stored then."""
    found = await sessions.question_set_session(user, class_session_id)
    if found is None or not found.may_change:
        return None
    async with get_sessionmaker().begin() as s:
        try:
            await sessions.lock_for_question_set(s, class_session_id, now=now)
        except LookupError:  # gone since it was read: as for one never there
            return None
        version = await content.latest_version(content.Kind.QUESTION_SET, s)
        _, question_set = await content.question_set(version)
        selection = _judge(wanted, version, question_set)
        values = {
            "question_set_version": selection.version,
            "excluded": sorted(selection.excluded),
            "weights": dict(selection.weights),
            "adapted_weight": selection.adapted_weight,
            "updated_by": user.id,
            "updated_at": now,
        }
        await s.execute(
            insert(test_selections)
            .values(class_session_id=class_session_id, **values)
            .on_conflict_do_update(index_elements=["class_session_id"], set_=values)
        )
        await audit.record(
            s,
            user.id,
            SELECTION_CHANGED,
            {"class_session_id": class_session_id},
            selection.as_json(),
            now,
        )
        await events.emit(s, "session", str(class_session_id))
    log.info(
        "question_set_selection_saved",
        class_session_id=str(class_session_id),
        version=selection.version,
        excluded=len(selection.excluded),
    )
    return await read_block(user, class_session_id, now)


# Every lock from now on pins the selection in force (AD-23), and «Lag kopi» copies it (FR-66).
sessions.register_pin_provider(PIN, question_set_pin)
sessions.register_copier(copy_selection)
