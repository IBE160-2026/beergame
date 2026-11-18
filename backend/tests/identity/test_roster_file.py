"""Reading a Roster file in memory (Story 4.2, FR-7): no database, no files on disk."""

import io
import zipfile
from datetime import date, datetime

import pytest
from openpyxl import Workbook

from app.modules.identity import roster_file as r


def xlsx(*lines: list[object]) -> bytes:
    book = Workbook()
    for line in lines:
        book.active.append(line)
    out = io.BytesIO()
    book.save(out)
    return out.getvalue()


def test_column_letters_follow_the_spreadsheet():
    assert [r.column_letter(i) for i in (0, 1, 25, 26, 27, 51, 52, 701, 702)] == [
        "A", "B", "Z", "AA", "AB", "AZ", "BA", "ZZ", "AAA"
    ]  # fmt: skip


def test_xlsx_cells_read_as_written():
    parsed = r.parse(
        "a.xlsx",
        xlsx(
            ["Navn", "Nr", "Dato", "E-post", None],
            ["Sara", 240117.0, date(2026, 1, 2), " sara@stud.example.no ", None],
            [None, None, None, None, None],
            ["Ida", 3.5, datetime(2026, 1, 2, 3, 4), "ida@stud.example.no", True],
        ),
        max_rows=10,
    )
    assert parsed.headers == ["Navn", "Nr", "Dato", "E-post", ""]
    assert parsed.rows == [
        (2, ["Sara", "240117", "2026-01-02T00:00:00", "sara@stud.example.no"]),
        (4, ["Ida", "3.5", "2026-01-02T03:04:00", "ida@stud.example.no", "TRUE"]),
    ]


@pytest.mark.parametrize(
    ("first_line", "delimiter"),
    [
        ("Navn,E-post", ","),
        ("Navn;E-post", ";"),
        ("Navn\tE-post", "\t"),
        ('"Lund, Sara";E-post', ";"),
        ("Navn", ","),
    ],
)
def test_the_delimiter_is_the_one_the_first_line_uses_most(first_line, delimiter):
    assert r._delimiter(first_line) == delimiter


def test_utf8_with_and_without_a_byte_order_mark_and_windows_1252():
    text = "Navn;E-post\nÆrlig Øyen;ae@x.no\n"
    for data in (text.encode("utf-8"), b"\xef\xbb\xbf" + text.encode(), text.encode("cp1252")):
        parsed = r.parse("a.csv", data, max_rows=10)
        assert parsed.headers == ["Navn", "E-post"]
        assert parsed.rows == [(2, ["Ærlig Øyen", "ae@x.no"])]


def test_a_first_row_with_an_address_is_data():
    parsed = r.parse("a.csv", b"Sara,sara@x.no,\nIda,ida@x.no,ekstra\n", max_rows=10)
    assert parsed.has_header is False
    assert parsed.headers == ["", "", ""]
    assert [n for n, _ in parsed.rows] == [1, 2]


def test_suggestion_takes_the_largest_share_and_the_leftmost_on_a_tie():
    assert r.suggested_column([0, 3, 3, 1]) == 1
    assert r.suggested_column([0, 0]) is None
    assert r.suggested_column([]) is None
    assert r.address_counts([["a@x.no", "b"], ["c", "d@x.no", "e@x.no"]], 2) == [1, 1]


def test_long_cells_are_cut_and_wide_rows_stop_at_the_column_cap():
    wide = ",".join(["x"] * (r.MAX_COLUMNS + 5))
    long = "y" * (r.MAX_CELL_CHARS + 10)
    parsed = r.parse("a.csv", f"{wide}\n{long},a@x.no\n".encode(), max_rows=10)
    assert parsed.column_count == r.MAX_COLUMNS
    assert len(parsed.rows[0][1][0]) == r.MAX_CELL_CHARS


def test_a_workbook_that_unpacks_too_large_is_refused_before_it_is_opened(monkeypatch):
    monkeypatch.setattr(r, "MAX_UNPACKED_BYTES", 1000)
    with pytest.raises(r.RosterUnreadable):
        r.parse("a.xlsx", xlsx(["E-post"], ["a@x.no"]), max_rows=10)


def test_a_zip_that_is_no_workbook_is_unreadable():
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr("hei.txt", "hei")
    with pytest.raises(r.RosterUnreadable):
        r.parse("a.xlsx", out.getvalue(), max_rows=10)


def test_a_byte_order_mark_before_bytes_that_are_not_utf8_is_unreadable():
    with pytest.raises(r.RosterUnreadable):
        r.parse("a.csv", b"\xef\xbb\xbfNavn\n\xff\xfe\n", max_rows=10)


def test_a_record_with_a_quoted_line_break_keeps_its_first_line_number():
    data = b'Navn,E-post\n"Sara\nLund",sara@x.no\nIda,ida@x.no\n'
    assert [n for n, _ in r.parse("a.csv", data, max_rows=10).rows] == [2, 4]


def test_a_vertical_tab_in_the_header_does_not_hide_the_delimiter():
    parsed = r.parse("a.csv", b"Navn\x0bfull;E-post\nSara;sara@x.no\n", max_rows=10)
    assert parsed.headers == ["Navn\x0bfull", "E-post"]


def test_a_sheet_with_a_far_away_row_stops_at_the_scan_limit():
    book = Workbook()
    book.active["A1"] = "E-post"
    book.active["A2"] = "a@x.no"
    book.active["A5000"] = "b@x.no"
    out = io.BytesIO()
    book.save(out)
    with pytest.raises(r.RosterUnreadable):
        r.parse("a.xlsx", out.getvalue(), max_rows=10)
