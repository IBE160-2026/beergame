"""«Pseudonymisert eksport»: the Admin exports the Decision log and Students' answers with stable
pseudonyms for evaluation (Story 15.4, FR-71, FR-67, FR-77, AD-12, AD-13, AD-14, AD-15).

- An Institution agreement is recorded per Class session (`record_agreement`, audited). Without
  one `platform/authz.can(admin, "export_pseudonymised", resource)` refuses that Class session,
  and nothing about its Students is read.
- The key holder, someone other than the founder, types the pseudonym key in the run form. It
  lives in this request's memory only: never in the database, a job, a log line, an environment
  variable, an error body or the audit. The first export stores its fingerprint; a later key with
  another fingerprint is refused (`KeyChanged`). `replace_key` stores a new fingerprint, audited.
- A Student is `HMAC-SHA256(key, str(user_id))` in hex in every file, so the same Student has the
  same pseudonym across files and across runs with the same key. An erased User (Story 15.2) has
  an empty pseudonym, so no export links their anonymous rows.
- Rows are read through `reports.scope` (AD-13). The files are the `SECTIONS` below plus the call
  metadata of the Decision log and a manifest, written into a ZIP whose bytes are handed out as
  they are produced, inside the request, never as a job.
- Every run and every refusal writes one audit row `evaluation_export.run`; the export list reads
  those rows.

**The seam for later epics.** A module that stores more Student data the evaluation needs
(as Epic 11's Individual test answers, `test_answers.csv`) adds a reader to its `service.py` with
the signature of `Reader` and appends a `Section` to `SECTIONS`. A reader returns column names
and rows, and puts the User id of a Student in a column named in `Section.student_columns`; this
module replaces it.
AI assessments and Indicative letters are never a section (FR-71).
"""

import csv
import hashlib
import hmac
import io
import json
import uuid
import zipfile
from collections.abc import Awaitable, Callable, Collection, Iterable, Iterator
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import calls as ai_calls
from app.modules.debrief import service as debrief
from app.modules.games import service as games
from app.modules.identity import service as identity
from app.modules.ops.models import evaluation_agreements, pseudonym_key_fingerprints
from app.modules.ops.retention import OSLO, deletion_date
from app.modules.ops.schemas import (
    AgreementIn,
    EvaluationAgreementOut,
    EvaluationSessionListOut,
    EvaluationSessionOut,
    ExportListOut,
    ExportOut,
    ExportSessionOut,
    KeyStateOut,
)
from app.modules.reports import scope
from app.modules.sessions import service as sessions
from app.modules.tests import service as tests
from app.platform import audit, authz
from app.platform.db import get_sessionmaker

EXPORT_ACTION = "evaluation_export.run"
AGREEMENT_ACTION = "evaluation_agreement.recorded"
KEY_ACTION = "pseudonym_key.replaced"
EXPORTED = "exported"
NO_AGREEMENT = "no_agreement"
KEY_CHANGED = "pseudonym_key_changed"
FAILED = "failed"
EXPORT_LIST_MAX = 100

FINGERPRINT_MESSAGE = b"olspillet:pseudonym-key-fingerprint:v1"
"""What the key's fingerprint is the HMAC of: no User id looks like it, so the fingerprint is
never a pseudonym."""
_KEY_ROW = 1


Reader = Callable[[AsyncSession, Collection[uuid.UUID], Any, Any], Awaitable[Any]]
"""`(session, class_session_ids, reporting games, reporting seat holders)` → `(columns, rows)`."""


@dataclass(frozen=True)
class Section:
    file: str
    read: Reader
    student_columns: tuple[str, ...] = ("student",)


SECTIONS: list[Section] = [
    Section("decision_log.csv", games.export_decision_log),
    Section("starting_task.csv", tests.export_starting_task),
    Section("explanations.csv", debrief.export_explanations),
    Section("test_answers.csv", tests.export_test_answers),
]
"""The files of the export, in order (FR-71): Epic 11's Individual test answers last. Epic 12's AI
assessments and Indicative letters are never a section (FR-71, Story 15.4)."""
CALLS_FILE = "llm_calls.csv"
MANIFEST_FILE = "manifest.json"


class NoAgreement(Exception):
    """An Admin chose a Class session with no recorded agreement (or one that does not exist)."""

    def __init__(self, class_session_ids: list[uuid.UUID]) -> None:
        super().__init__(NO_AGREEMENT)
        self.class_session_ids = class_session_ids


class KeyChanged(Exception):
    """The typed key's fingerprint is not the stored one."""

    def __init__(self) -> None:
        super().__init__(KEY_CHANGED)


@dataclass(frozen=True)
class ExportResource:
    """A Class session as `can(admin, "export_pseudonymised", …)` sees it."""

    class_session_id: uuid.UUID
    agreement_recorded: bool


def fingerprint(key: str) -> str:
    """The stored stand-in for the key: an HMAC of a fixed message under it, in hex."""
    return hmac.new(key.encode(), FINGERPRINT_MESSAGE, hashlib.sha256).hexdigest()


def pseudonym(key: str, user_id: uuid.UUID) -> str:
    """`HMAC(key, user_id)` in hex (AD-14)."""
    return hmac.new(key.encode(), str(user_id).encode(), hashlib.sha256).hexdigest()


# The Class sessions and their agreements.


def _agreement_out(row: Any) -> EvaluationAgreementOut:
    return EvaluationAgreementOut(
        agreed_by=row["agreed_by"],
        agreed_on=row["agreed_on"],
        controller=row["controller"],
        recorded_at=row["recorded_at"],
    )


async def _agreements(s: AsyncSession, ids: list[uuid.UUID] | None) -> dict[uuid.UUID, Any]:
    query = select(evaluation_agreements)
    if ids is not None:
        query = query.where(evaluation_agreements.c.class_session_id.in_(ids))
    rows = (await s.execute(query)).mappings()
    return {row["class_session_id"]: row for row in rows}


def _session_out(found: sessions.EvaluationSession, agreement: Any) -> EvaluationSessionOut:
    return EvaluationSessionOut(
        id=found.id,
        number=found.number,
        class_name=found.class_name,
        course_code=found.course_code,
        institution_name=found.institution_name,
        start_at=found.start_at,
        test_deadline=found.test_deadline,
        deletion_date=deletion_date(found.test_deadline),
        agreement=_agreement_out(agreement) if agreement is not None else None,
    )


async def list_sessions() -> EvaluationSessionListOut:
    """Every saved Class session, newest first, with its agreement and deletion date. Names and
    dates only: no Student data."""
    async with get_sessionmaker().begin() as s:
        found = await sessions.evaluation_sessions(s)
        agreements = await _agreements(s, None)
    return EvaluationSessionListOut(
        items=[_session_out(item, agreements.get(item.id)) for item in found]
    )


async def record_agreement(
    actor: authz.Principal, class_session_id: uuid.UUID, body: AgreementIn, *, now: datetime
) -> EvaluationSessionOut | None:
    """Record (or replace) the Institution agreement of a Class session, audited; None when the
    Class session does not exist."""
    async with get_sessionmaker().begin() as s:
        [found] = await sessions.evaluation_sessions(s, [class_session_id]) or [None]
        if found is None:
            return None
        values = {
            "agreed_by": body.agreed_by,
            "agreed_on": body.agreed_on,
            "controller": body.controller,
            "recorded_by": actor.id,
            "recorded_at": now,
        }
        row = (
            (
                await s.execute(
                    insert(evaluation_agreements)
                    .values(class_session_id=class_session_id, **values)
                    .on_conflict_do_update(index_elements=["class_session_id"], set_=values)
                    .returning(evaluation_agreements)
                )
            )
            .mappings()
            .one()
        )
        await audit.record(
            s,
            actor.id,
            AGREEMENT_ACTION,
            {"class_session_id": class_session_id},
            {"agreed_on": body.agreed_on.isoformat()},
            now,
        )
    return _session_out(found, row)


async def class_session_labels(ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    """«class-of-1994 · Klasseøkt 2» for the audit page's `class_session_id` targets."""
    async with get_sessionmaker().begin() as s:
        found = await sessions.evaluation_sessions(s, ids)
    return {item.id: f"{item.class_name} · Klasseøkt {item.number}" for item in found}


# The key.


async def _stored_key(s: AsyncSession, *, lock: bool = False) -> Any:
    query = select(pseudonym_key_fingerprints).where(pseudonym_key_fingerprints.c.id == _KEY_ROW)
    if lock:
        query = query.with_for_update()
    return (await s.execute(query)).mappings().one_or_none()


async def key_state() -> KeyStateOut:
    async with get_sessionmaker().begin() as s:
        row = await _stored_key(s)
    if row is None:
        return KeyStateOut(fingerprint=None, set_at=None)
    return KeyStateOut(fingerprint=row["fingerprint"], set_at=row["set_at"])


async def replace_key(actor: authz.Principal, key: str, *, now: datetime) -> KeyStateOut:
    """Store the fingerprint of a new key (AD-14), audited with the old and the new fingerprint.
    The same key again changes nothing and writes no audit row."""
    new = fingerprint(key)
    async with get_sessionmaker().begin() as s:
        old = await _stored_key(s, lock=True)
        if old is not None and old["fingerprint"] == new:
            return KeyStateOut(fingerprint=new, set_at=old["set_at"])
        values = {"fingerprint": new, "set_by": actor.id, "set_at": now}
        await s.execute(
            insert(pseudonym_key_fingerprints)
            .values(id=_KEY_ROW, **values)
            .on_conflict_do_update(index_elements=["id"], set_=values)
        )
        await audit.record(
            s,
            actor.id,
            KEY_ACTION,
            {},
            {"old_fingerprint": old["fingerprint"] if old else None, "new_fingerprint": new},
            now,
        )
    return KeyStateOut(fingerprint=new, set_at=now)


async def _check_key(s: AsyncSession, actor: authz.Principal, found: str, now: datetime) -> None:
    """The first export stores the fingerprint; a later one must match it."""
    await s.execute(
        insert(pseudonym_key_fingerprints)
        .values(id=_KEY_ROW, fingerprint=found, set_by=actor.id, set_at=now)
        .on_conflict_do_nothing(index_elements=["id"])
    )
    stored = await _stored_key(s, lock=True)
    if stored is None or not hmac.compare_digest(stored["fingerprint"], found):
        raise KeyChanged


# The export.


@dataclass(frozen=True)
class ExportFile:
    name: str
    columns: tuple[str, ...]
    rows: list[tuple[Any, ...]]


@dataclass(frozen=True)
class Export:
    """What one allowed run hands out: the CSV files and the manifest."""

    files: list[ExportFile]
    manifest: dict[str, Any]
    created_at: datetime


async def _refused(
    actor: authz.Principal, ids: list[uuid.UUID], found: str, outcome: str, now: datetime
) -> None:
    async with get_sessionmaker().begin() as s:
        await audit.record(
            s,
            actor.id,
            EXPORT_ACTION,
            {},
            {"outcome": outcome, "class_session_ids": ids, "key_fingerprint": found},
            now,
        )


async def run_export(
    actor: authz.Principal, class_session_ids: list[uuid.UUID], key: str, *, now: datetime
) -> Export:
    """Gate, read and pseudonymise one export (FR-71). Raises `NoAgreement` or `KeyChanged`
    after auditing the refusal; nothing about a Student is read before both checks pass."""
    ids = list(dict.fromkeys(class_session_ids))
    found = fingerprint(key)
    try:
        async with get_sessionmaker().begin() as s:
            agreements = await _agreements(s, ids)
            refused = [
                i
                for i in ids
                if not authz.can(actor, "export_pseudonymised", ExportResource(i, i in agreements))
            ]
            if refused:
                raise NoAgreement(refused)
            await _check_key(s, actor, found, now)
            export = await _read(s, ids, key, found, now)
            await audit.record(
                s,
                actor.id,
                EXPORT_ACTION,
                {},
                {"outcome": EXPORTED, "class_session_ids": ids, "key_fingerprint": found},
                now,
            )
    except NoAgreement:
        await _refused(actor, ids, found, NO_AGREEMENT, now)
        raise
    except KeyChanged:
        await _refused(actor, ids, found, KEY_CHANGED, now)
        raise
    except Exception:
        # A run that failed while reading still leaves its trace in the export list.
        await _refused(actor, ids, found, FAILED, now)
        raise
    return export


async def _read(
    s: AsyncSession, ids: list[uuid.UUID], key: str, found: str, now: datetime
) -> Export:
    in_scope = scope.reporting_games()
    students = scope.reporting_seat_holders()
    read: list[tuple[Section, tuple[str, ...], list[tuple[Any, ...]]]] = []
    for section in SECTIONS:
        columns, rows = await section.read(s, ids, in_scope, students)
        read.append((section, tuple(columns), list(rows)))

    # The call metadata of the Decision log's Orders (FR-67).
    [(_, log_columns, log_rows)] = [r for r in read if r[0].file == "decision_log.csv"]
    at = log_columns.index("llm_call_ids")
    call_ids = list(dict.fromkeys(call for row in log_rows for call in row[at] or ()))
    call_columns, call_rows = await ai_calls.export_metadata(call_ids, s)

    # Every Student column, pseudonymised; an erased User gets none.
    users: set[uuid.UUID] = set()
    for section, columns, rows in read:
        for name in section.student_columns:
            at = columns.index(name)
            users.update(row[at] for row in rows if row[at] is not None)
    erased = await identity.erased_among(s, list(users))
    names = {user: "" if user in erased else pseudonym(key, user) for user in users}

    files = []
    for section, columns, rows in read:
        places = [columns.index(name) for name in section.student_columns]
        out = []
        for row in rows:
            values = list(row)
            for at in places:
                values[at] = names[values[at]] if values[at] is not None else None
            out.append(tuple(values))
        files.append(ExportFile(section.file, columns, out))
    files.append(ExportFile(CALLS_FILE, tuple(call_columns), list(call_rows)))

    listed = {item.id: item for item in await sessions.evaluation_sessions(s, ids)}
    manifest = {
        "export": "pseudonymised evaluation export (FR-71)",
        "created_at": now.isoformat(),
        "pseudonym": "hex HMAC-SHA256(key, user_id); empty for an erased User",
        "class_sessions": [
            {
                "id": str(i),
                "deletion_date": _iso(
                    deletion_date(listed[i].test_deadline) if i in listed else None
                ),
            }
            for i in ids
        ],
        "notice": (
            "Pseudonymiserte personopplysninger. Forklaringene står slik Studentene skrev dem og "
            "kan nevne navn. Slettes senest på slettedatoen til hver Klasseøkt, og etter "
            "Institusjonens instruks."
        ),
        "csv": "UTF-8; a text starting with = + - @ has a leading ' so no spreadsheet runs it",
        "files": {f.name: {"columns": list(f.columns), "rows": len(f.rows)} for f in files},
    }
    return Export(files=files, manifest=manifest, created_at=now)


def _iso(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


FORMULA_STARTS = ("=", "+", "-", "@", "\t", "\r")
"""What makes a spreadsheet read a cell as a formula: such a text gets a leading `'`."""


def cell(value: Any) -> str:
    """One CSV cell: text as written, times in ISO 8601, JSON for structured values, the
    ids of a list separated by spaces, nothing for a missing value. A text a spreadsheet would
    run as a formula (a Student's Explanation starting with `=`) gets a leading `'`."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, uuid.UUID | Decimal | int | float):
        return str(value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if isinstance(value, list | tuple):
        return " ".join(cell(item) for item in value)
    text = str(value)
    return f"'{text}" if text.startswith(FORMULA_STARTS) else text


def _csv_lines(columns: Iterable[str], rows: Iterable[tuple[Any, ...]]) -> Iterator[str]:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(list(columns))
    yield buffer.getvalue()
    for row in rows:
        buffer.seek(0)
        buffer.truncate()
        writer.writerow([cell(value) for value in row])
        yield buffer.getvalue()


class _Sink:
    """An unseekable stream for `zipfile`: it collects what is written until it is taken."""

    def __init__(self) -> None:
        self._parts: list[bytes] = []
        self.size = 0

    def write(self, data: bytes) -> int:
        self._parts.append(bytes(data))
        self.size += len(data)
        return len(data)

    def flush(self) -> None:
        return None

    def take(self) -> bytes:
        data = b"".join(self._parts)
        self._parts.clear()
        self.size = 0
        return data


CHUNK = 64 * 1024


def zip_stream(export: Export) -> Iterator[bytes]:
    """The ZIP of the export, handed out as it is produced: each CSV file in UTF-8, then the
    manifest."""
    sink = _Sink()
    stamp = export.created_at.astimezone(OSLO).timetuple()[:6]
    with zipfile.ZipFile(sink, "w", zipfile.ZIP_DEFLATED) as archive:
        for item in export.files:
            info = zipfile.ZipInfo(item.name, date_time=stamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            with archive.open(info, "w") as out:
                for line in _csv_lines(item.columns, item.rows):
                    out.write(line.encode())
                    if sink.size >= CHUNK:
                        yield sink.take()
            yield sink.take()
        info = zipfile.ZipInfo(MANIFEST_FILE, date_time=stamp)
        info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(info, json.dumps(export.manifest, ensure_ascii=False, indent=2))
    yield sink.take()


def file_name(export: Export) -> str:
    return f"pseudonymisert-eksport-{export.created_at.astimezone(OSLO):%Y%m%d-%H%M%S}.zip"


# The export list.


async def list_exports() -> ExportListOut:
    """The newest runs and refusals, from their audit rows, each Class session with its
    deletion date (FR-3, FR-77)."""
    async with get_sessionmaker().begin() as s:
        events = await audit.page(s, limit=EXPORT_LIST_MAX, action=EXPORT_ACTION)
        wanted: list[uuid.UUID] = []
        for event in events:
            for value in event.change.get("class_session_ids") or []:
                try:
                    wanted.append(uuid.UUID(str(value)))
                except ValueError:
                    continue
        listed = {
            item.id: item
            for item in await sessions.evaluation_sessions(s, list(dict.fromkeys(wanted)))
        }
    actors = await audit.labels(
        "user_id", [e.actor_user_id for e in events if e.actor_user_id is not None]
    )

    def session(value: Any) -> ExportSessionOut | None:
        try:
            session_id = uuid.UUID(str(value))
        except ValueError:
            return None
        item = listed.get(session_id)
        return ExportSessionOut(
            id=session_id,
            number=item.number if item else None,
            class_name=item.class_name if item else None,
            deletion_date=deletion_date(item.test_deadline) if item else None,
        )

    return ExportListOut(
        items=[
            ExportOut(
                id=event.id,
                occurred_at=event.occurred_at,
                actor_id=event.actor_user_id,
                actor_name=actors.get(event.actor_user_id) if event.actor_user_id else None,
                outcome=str(event.change.get("outcome", "")),
                key_fingerprint=event.change.get("key_fingerprint"),
                class_sessions=[
                    found
                    for value in event.change.get("class_session_ids") or []
                    if (found := session(value)) is not None
                ],
            )
            for event in events
        ]
    )
