"""The Completion export of a Class session, CSV or Excel (Story 13.14, FR-60, FR-17, FR-56, AD-12,
AD-13, AD-14, AD-16, C-2).

«Last ned fullføringsliste (CSV eller Excel)» in the Klasseøkt's «Eksport» block downloads one row
per Student in `scope.reporting_students`, built at request time and sent to the Lecturer,
never stored (AD-14). Every status value comes from the one assembler
(`service.completion_statuses`, which is `completion_status` per Student), so the file agrees
with the Studentside, Hjem and the funnel (AD-16). Names and addresses are read through
`identity.service.student_contacts` at the time of the download.

The columns are the fixed allow-list `COLUMNS`: no AI score, AI feedback or Indicative letter can
reach the file (FR-60, C-2). Only the Lecturers of the Class (`completion.export`); an Assistant
lecturer downloads the reports only.

Norwegian Excel: the CSV is UTF-8 with a byte order mark, `;` between fields, dates `dd.mm.yyyy`
and the decimal comma; the .xlsx holds real date and number cells. A text that a spreadsheet would
read as a formula is written as text in both."""

from __future__ import annotations

import csv
import io
import uuid
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

from app.analysis.completion import COMPLETION_STEPS, CompletionStatus
from app.modules.identity import service as identity
from app.modules.identity.service import Person
from app.modules.reports import repo, service
from app.modules.reports.report import ReportRefused
from app.modules.sessions import service as sessions
from app.platform import audit, auth, authz
from app.platform.collation import nb_sort_key
from app.platform.db import get_sessionmaker

__all__ = [
    "COLUMNS",
    "CSV_TYPE",
    "DOWNLOADED_AUDIT",
    "EXPORT",
    "XLSX_TYPE",
    "Export",
    "export",
    "file_name",
    "row_values",
    "to_csv",
    "to_xlsx",
]

EXPORT = "completion.export"
"""The Class action of the Completion export: the Class's owners only."""

DOWNLOADED_AUDIT = "completion_export.downloaded"

Format = Literal["csv", "xlsx"]

CSV_TYPE = "text/csv; charset=utf-8"
XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

STEP_COLUMNS: dict[str, str] = {
    "class_game": "Klassespill",
    "debrief": "Debrief",
    "quiz_passed": "Quiz",
    "replay": "Replay",
    "test_submitted": "Individuell test",
}
"""The header of each step's date column, in the order of the requirement."""

COLUMNS: tuple[str, ...] = (
    "Navn",
    "E-post",
    *(STEP_COLUMNS[step] for step in COMPLETION_STEPS),
    "Bestilte uker (%)",
    "Kravet (%)",
    "Utspilling (%)",
    "Oppfølgingsspill",
    "Rettet av faglærer",
    "Krav oppfylt",
)
"""The allow-list of the file's columns, in order (FR-60). Nothing else is written: no AI score,
AI feedback or Indicative letter (C-2). A test holds it to a literal."""

NOT_DONE = "ikke gjort"
DONE_UNDATED = "gjort"
"""A step done by a Lecturer's correction alone has no recorded date."""
YES, NO = "Ja", "Nei"
NOT_OBLIGATORY = "Ikke obligatorisk"

Value = str | int | float | date | None


@dataclass(frozen=True)
class Export:
    """What the download sends: the rows in `COLUMNS` order and the Class session's number."""

    rows: list[tuple[Value, ...]]
    number: int | None


def _oslo_date(at: datetime) -> date:
    return at.astimezone(sessions.OSLO).date()


def row_values(
    status: CompletionStatus, contact: Person | None, makeup_given_at: datetime | None
) -> tuple[Value, ...]:
    """One Student's row in `COLUMNS` order, from their Completion status alone (pure): the date
    each step was done, «ikke gjort» for a step not done, the shares as whole percents as the
    Studentside shows them, the date an Oppfølgingsspill was given, whether a Lecturer corrected
    any step, and whether the requirement is met."""
    steps: list[Value] = []
    for name in COMPLETION_STEPS:
        step = status.step(name)
        if not step.done:
            steps.append(NOT_DONE)
        elif step.recorded_at is None:
            steps.append(DONE_UNDATED)
        else:
            steps.append(_oslo_date(step.recorded_at))
    if not status.obligatory or status.requirement_met is None:
        met = NOT_OBLIGATORY
    else:
        met = YES if status.requirement_met else NO
    return (
        "" if contact is None else contact.name,
        "" if contact is None else contact.email,
        *steps,
        status.ordered_share,
        status.required_share,
        status.playout_share,
        None if makeup_given_at is None else _oslo_date(makeup_given_at),
        YES if any(step.corrected for step in status.steps) else NO,
        met,
    )


async def export(user: authz.Principal, class_session_id: uuid.UUID) -> Export | None:
    """The rows of the Completion export for a Lecturer of the Class, recorded in the audit log by
    the caller once the format is known. None (403) for anyone else and a Class session that does
    not exist; raises `ReportRefused("data_deleted")` once the Student data is deleted."""
    row = await sessions.staff_session_row(user, class_session_id, EXPORT)
    if row is None:
        return None
    if sessions.data_deleted(row, auth.utcnow()):
        raise ReportRefused("data_deleted")
    async with get_sessionmaker()() as s:
        statuses = await service.completion_statuses(class_session_id, session=s)
        students = list(statuses)
        contacts = await identity.student_contacts(row["class_id"], students, session=s)
        makeups = {}
        for student in students:
            given = await repo.makeup_of(s, student, class_session_id)
            if given is not None:
                makeups[student] = given.given_at
        heading = await sessions.report_heading(s, class_session_id, user.id)
    ordered = sorted(
        students,
        key=lambda student: (
            nb_sort_key(contacts[student].name if student in contacts else ""),
            str(student),
        ),
    )
    return Export(
        rows=[
            row_values(statuses[each], contacts.get(each), makeups.get(each)) for each in ordered
        ],
        number=None if heading is None else heading.number,
    )


async def record_download(
    user: authz.Principal, class_session_id: uuid.UUID, fmt: Format, students: int
) -> None:
    """One audit row per download, once the file is built: the Class session, the format and how
    many Students it lists, never a name (AD-14)."""
    async with get_sessionmaker().begin() as s:
        await audit.record(
            s,
            user.id,
            DOWNLOADED_AUDIT,
            {"class_session_id": class_session_id},
            {"format": fmt, "students": students},
            auth.utcnow(),
        )


def file_name(number: int | None, fmt: Format) -> str:
    """The file name the browser saves: no name of a person in it."""
    stem = "fullforingsliste" if number is None else f"fullforingsliste-klasseokt-{number}"
    return f"{stem}.{fmt}"


_FORMULA_START = ("=", "+", "-", "@", "\t", "\r", "\n")


def _text(value: str) -> str:
    """A text a spreadsheet would read as a formula gets a leading apostrophe (CSV only)."""
    return "'" + value if value.startswith(_FORMULA_START) else value


def _csv_cell(value: Value) -> str:
    if value is None:
        return ""
    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")
    if isinstance(value, bool):  # never written, but never as a number either
        return YES if value else NO
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.1f}".replace(".", ",")
    return _text(value)


def to_csv(rows: Sequence[Sequence[Value]]) -> Iterator[bytes]:
    """The CSV for Norwegian Excel, one line at a time: a byte order mark, then the header and
    the rows, `;` between fields, CRLF line ends."""
    yield "﻿".encode()
    for values in (COLUMNS, *rows):
        line = io.StringIO()
        csv.writer(line, delimiter=";", lineterminator="\r\n").writerow(
            [_csv_cell(value) for value in values]
        )
        yield line.getvalue().encode()


def to_xlsx(rows: Sequence[Sequence[Value]]) -> bytes:
    """The .xlsx: one sheet «Fullføring» with the header and the rows; dates are date cells shown
    `dd.mm.yyyy`, the shares number cells, and every text a string cell, never a formula."""
    from openpyxl import Workbook  # imported here: only this download needs it
    from openpyxl.cell import WriteOnlyCell
    from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

    book = Workbook(write_only=True)
    sheet = book.create_sheet("Fullføring")

    def cell(value: Value) -> WriteOnlyCell:
        if isinstance(value, str):
            made = WriteOnlyCell(sheet, value=ILLEGAL_CHARACTERS_RE.sub("", value))
            made.data_type = "s"  # a text that begins with «=» stays text
            return made
        made = WriteOnlyCell(sheet, value=value)
        if isinstance(value, date):
            made.number_format = "dd.mm.yyyy"
        return made

    for values in (COLUMNS, *rows):
        sheet.append([cell(value) for value in values])
    out = io.BytesIO()
    book.save(out)
    return out.getvalue()
