"""Reading an uploaded Roster file in memory (Story 4.2, FR-7). Only `identity.service` calls it.

The file is never written anywhere: its bytes are read here and only the cell values leave, as
strings. `.xlsx` is read with openpyxl in read-only mode; `.csv` is decoded as UTF-8 (with or
without a byte-order mark) or Windows-1252 and split on comma, semicolon or tab, whichever the
first line uses most. The first non-empty row is a header unless one of its cells looks like an
address. Empty rows are skipped; each row keeps its number in the file. Nothing here logs.
"""

import csv
import io
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, time

from app.modules.identity.schemas import email_is_valid, normalise_email

MAX_COLUMNS = 200
"""The most columns read; cells beyond are dropped (a Canvas grade book stays well under)."""
MAX_CELL_CHARS = 1000
"""A longer cell is cut to this length; no address is anywhere near it."""
DELIMITERS = (",", ";", "\t")
EMPTY_ROWS_PER_ROW = 20
"""A sheet is read to at most this many rows per allowed data row, empty ones included."""
MAX_UNPACKED_BYTES = 200 * 1024 * 1024
"""A workbook whose parts unpack to more than this is refused before openpyxl opens it (a zip
bomb); a real export of a few thousand rows unpacks to a few megabytes."""


class RosterUnreadable(Exception):
    """The file cannot be used: not .xlsx or .csv, unparseable, empty, or over a limit. The reason
    is for tests and the code's reader, never shown or logged with the file's content."""


@dataclass(frozen=True)
class ParsedRoster:
    headers: list[str]
    """One per column; all "" when the file has no header row."""
    has_header: bool
    rows: list[tuple[int, list[str]]]
    """(row number in the file, cells) for each non-empty data row."""

    @property
    def column_count(self) -> int:
        return len(self.headers)


def looks_like_address(value: str) -> bool:
    """Whether a cell is shaped as an e-mail address (`schemas.email_is_valid`, trimmed and
    lower-cased). Story 4.3 adds the reasons for one that is not."""
    return email_is_valid(normalise_email(value))


def column_letter(index: int) -> str:
    """0 → A, 25 → Z, 26 → AA, as a spreadsheet names its columns."""
    letters = ""
    index += 1
    while index:
        index, rest = divmod(index - 1, 26)
        letters = chr(ord("A") + rest) + letters
    return letters


def parse(file_name: str, data: bytes, *, max_rows: int) -> ParsedRoster:
    """The file's header and data rows. Raises `RosterUnreadable`."""
    kind = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if not data:
        raise RosterUnreadable("empty")
    if kind == "xlsx":
        raw = _xlsx_rows(data, max_rows)
    elif kind == "csv":
        raw = _csv_rows(data, max_rows)
    else:
        raise RosterUnreadable("type")
    return _shape(raw, max_rows)


def _cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, datetime | date | time):
        value = value.isoformat()
    return str(value).strip()[:MAX_CELL_CHARS]


def _xlsx_rows(data: bytes, max_rows: int) -> list[tuple[int, list[str]]]:
    if not data.startswith(b"PK"):
        raise RosterUnreadable("not a workbook")
    from openpyxl import load_workbook  # imported here: only an upload needs it

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            unpacked = sum(info.file_size for info in archive.infolist())
    except (zipfile.BadZipFile, OSError, ValueError) as error:
        raise RosterUnreadable("unparseable workbook") from error
    if unpacked > MAX_UNPACKED_BYTES:
        raise RosterUnreadable("workbook unpacks too large")
    try:
        book = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception as error:  # openpyxl raises a range of its own on a broken file
        raise RosterUnreadable("unparseable workbook") from error
    try:
        sheet = book.worksheets[0] if book.worksheets else None
        if sheet is None:
            raise RosterUnreadable("no sheet")
        rows: list[tuple[int, list[str]]] = []
        max_scanned = (max_rows + 1) * EMPTY_ROWS_PER_ROW
        for number, values in enumerate(
            sheet.iter_rows(values_only=True, max_col=MAX_COLUMNS), start=1
        ):
            if number > max_scanned:  # a sheet that declares a huge, mostly empty range
                raise RosterUnreadable("too many rows")
            cells = [_cell(v) for v in values]
            if any(cells):
                rows.append((number, cells))
                if len(rows) > max_rows + 1:  # the header plus the limit
                    raise RosterUnreadable("too many rows")
        return rows
    except RosterUnreadable:
        raise
    except Exception as error:
        raise RosterUnreadable("unparseable workbook") from error
    finally:
        book.close()


def _decode(data: bytes) -> str:
    if data.startswith(b"\xef\xbb\xbf"):
        try:
            text = data[3:].decode("utf-8")
        except UnicodeDecodeError as error:
            raise RosterUnreadable("encoding") from error
    else:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = data.decode("cp1252")
            except UnicodeDecodeError as error:
                raise RosterUnreadable("encoding") from error
    if "\x00" in text:
        raise RosterUnreadable("binary")
    return text


def _delimiter(first_line: str) -> str:
    counts = {d: 0 for d in DELIMITERS}
    quoted = False
    for ch in first_line:
        if ch == '"':
            quoted = not quoted
        elif not quoted and ch in counts:
            counts[ch] += 1
    best = max(DELIMITERS, key=lambda d: counts[d])  # first in DELIMITERS wins a tie
    return best


def _csv_rows(data: bytes, max_rows: int) -> list[tuple[int, list[str]]]:
    text = _decode(data)
    # Split as the csv reader does (on line ends only), not as `str.splitlines`.
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    first = next((line for line in lines if line.strip()), "")
    if not first:
        raise RosterUnreadable("empty")
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=_delimiter(first))
    rows: list[tuple[int, list[str]]] = []
    try:
        while True:
            start = reader.line_num + 1  # a quoted cell can span lines: the record's first one
            values = next(reader, None)
            if values is None:
                break
            cells = [_cell(v) for v in values[:MAX_COLUMNS]]
            if any(cells):
                rows.append((start, cells))
                if len(rows) > max_rows + 1:
                    raise RosterUnreadable("too many rows")
    except csv.Error as error:
        raise RosterUnreadable("unparseable csv") from error
    return rows


def _shape(raw: list[tuple[int, list[str]]], max_rows: int) -> ParsedRoster:
    if not raw:
        raise RosterUnreadable("empty")
    # Trailing empty cells do not make a column.
    trimmed = [(n, _trim(cells)) for n, cells in raw]
    first = trimmed[0][1]
    has_header = not any(looks_like_address(cell) for cell in first)
    data = trimmed[1:] if has_header else trimmed
    if not data:
        raise RosterUnreadable("no data rows")
    if len(data) > max_rows:
        raise RosterUnreadable("too many rows")
    width = max(len(cells) for _, cells in trimmed)
    headers = (first + [""] * width)[:width] if has_header else [""] * width
    return ParsedRoster(headers=headers, has_header=has_header, rows=data)


def _trim(cells: list[str]) -> list[str]:
    end = len(cells)
    while end and not cells[end - 1]:
        end -= 1
    return cells[:end]


def address_counts(parsed_rows: list[list[str]], column_count: int) -> list[int]:
    """For each column, how many rows hold a cell that looks like an address."""
    counts = [0] * column_count
    for cells in parsed_rows:
        for index, cell in enumerate(cells[:column_count]):
            if cell and looks_like_address(cell):
                counts[index] += 1
    return counts


def suggested_column(counts: list[int]) -> int | None:
    """The column with the most address-looking cells, leftmost on a tie; None when no cell in
    any column looks like an address."""
    best = max(range(len(counts)), key=lambda i: (counts[i], -i), default=None)
    return best if best is not None and counts[best] > 0 else None
