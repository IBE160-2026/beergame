"""Uploading or pasting a Roster for a Class, choosing its e-mail column and seeing its invalid
rows through the api (Stories 4.2 and 4.3, FR-7, AD-12, AD-14). The Canvas-shaped fixtures are
synthetic, with invented names and addresses, and are shared with Playwright
(`frontend/e2e/fixtures/roster`). The api's clock is fixed; the database clock is never read."""

import asyncio
import io
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import quote

import pytest
import structlog.testing
from openpyxl import Workbook

from app.modules.identity.schemas import AccountRole
from app.platform import auth
from app.platform.config import get_settings
from tests.classes.test_classes import LECTURER, OTHER, as_user, institution, make
from tests.identity.helpers import CSRF, client
from tests.messaging.helpers import rows

FIXTURES = Path(__file__).resolve().parents[3] / "frontend" / "e2e" / "fixtures" / "roster"
NOW = datetime(2026, 11, 19, 9, 0, tzinfo=UTC)


@pytest.fixture
def clock(monkeypatch):
    monkeypatch.setattr(auth, "utcnow", lambda: NOW)


@pytest.fixture
async def klass(identity_db, clock) -> str:
    await make(LECTURER)
    await make(OTHER)
    place = await institution()
    async with client() as c:
        await as_user(c)
        created = await c.post(
            "/api/classes",
            json={"name": "class-of-1994", "institution_id": str(place)},
            headers=CSRF,
        )
    assert created.status_code == 201
    return created.json()["id"]


@pytest.fixture
def settings_env(monkeypatch):
    """Set environment variables for the settings, read again for this test only."""

    def set_env(**values: str) -> None:
        for name, value in values.items():
            monkeypatch.setenv(name, value)
        get_settings.cache_clear()

    yield set_env
    monkeypatch.undo()
    get_settings.cache_clear()


def path(class_id: str, rest: str = "") -> str:
    return f"/api/classes/{class_id}/roster-upload{rest}"


async def upload(c, class_id: str, name: str, data: bytes):
    return await c.post(
        path(class_id),
        content=data,
        headers={**CSRF, "Content-Type": "application/octet-stream", "X-File-Name": quote(name)},
    )


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def staged() -> list[tuple]:
    return rows("SELECT file_name, row_count, chosen_column FROM roster_uploads")


def staged_rows() -> int:
    return rows("SELECT count(*) FROM roster_upload_rows")[0][0]


def xlsx(*lines: list[object]) -> bytes:
    book = Workbook()
    for line in lines:
        book.active.append(line)
    out = io.BytesIO()
    book.save(out)
    return out.getvalue()


def addresses(n: int) -> bytes:
    return ("E-post\n" + "".join(f"s{i}@stud.example.no\n" for i in range(n))).encode()


async def test_a_canvas_people_export_is_read_without_editing(klass):
    async with client() as c:
        await as_user(c)
        response = await upload(
            c, klass, "ibe160-canvas-eksport.xlsx", fixture("canvas-people.xlsx")
        )
    assert response.status_code == 201
    body = response.json()
    assert body["file_name"] == "ibe160-canvas-eksport.xlsx"
    assert body["row_count"] == 12 and body["has_header"] is True
    assert [(col["letter"], col["header"]) for col in body["columns"]] == [
        ("A", "Name"),
        ("B", "Login ID"),
        ("C", "SIS User ID"),
        ("D", "E-post"),
        ("E", "Section"),
    ]
    assert (body["suggested_column"], body["suggested_count"]) == (3, 12)
    assert (body["chosen_column"], body["chosen_count"]) == (3, 12)
    assert [row["row_number"] for row in body["preview"]] == [2, 3, 4, 5, 6]
    assert body["preview"][0]["cells"][3] == "sara.lund@stud.example.no"
    assert body["preview"][0]["cells"][2] == "240117"  # a number reads as written
    assert staged() == [("ibe160-canvas-eksport.xlsx", 12, 3)]
    assert staged_rows() == 12


async def test_a_canvas_grade_book_export_is_read_without_editing(klass):
    async with client() as c:
        await as_user(c)
        response = await upload(c, klass, "Karakterbok.csv", fixture("canvas-gradebook.csv"))
    body = response.json()
    assert response.status_code == 201
    # The «Points Possible» row is a row of the file: it holds no address.
    assert body["row_count"] == 13
    assert body["columns"][0]["header"] == "Student"  # the byte-order mark is gone
    assert body["columns"][3] == {"index": 3, "letter": "D", "header": "SIS Login ID"}
    assert (body["suggested_column"], body["suggested_count"]) == (3, 12)
    assert body["preview"][1]["cells"][0] == "Lund, Sara"  # a quoted comma stays in its cell


async def test_a_file_with_no_email_column_is_staged_with_nothing_chosen(klass):
    async with client() as c:
        await as_user(c)
        response = await upload(c, klass, "uten-epost.csv", fixture("uten-epost.csv"))
    body = response.json()
    assert response.status_code == 201
    assert (body["suggested_column"], body["chosen_column"], body["chosen_count"]) == (
        None,
        None,
        0,
    )
    assert body["row_count"] == 12
    assert staged() == [("uten-epost.csv", 12, None)]


async def test_a_semicolon_csv_in_windows_1252_is_read(klass):
    data = "Navn;E-post\r\nØrjan Næss;orjan@stud.example.no\r\nÅse Strøm;ase@stud.example.no\r\n"
    async with client() as c:
        await as_user(c)
        response = await upload(c, klass, "liste.CSV", data.encode("cp1252"))
    body = response.json()
    assert response.status_code == 201
    assert [col["header"] for col in body["columns"]] == ["Navn", "E-post"]
    assert body["preview"][0]["cells"] == ["Ørjan Næss", "orjan@stud.example.no"]
    assert (body["suggested_column"], body["suggested_count"]) == (1, 2)


async def test_a_file_with_no_header_row_keeps_every_row(klass):
    data = (
        b"Sara Lund,sara@stud.example.no\nIda Berg,ida@stud.example.no\n\n"
        b"Thea Moe,thea@stud.example.no\n"
    )
    async with client() as c:
        await as_user(c)
        response = await upload(c, klass, "uten-overskrift.csv", data)
    body = response.json()
    assert response.status_code == 201
    assert body["has_header"] is False and body["row_count"] == 3
    assert [(col["letter"], col["header"]) for col in body["columns"]] == [("A", ""), ("B", "")]
    # The empty line is skipped, and each row keeps its number in the file.
    assert [row["row_number"] for row in body["preview"]] == [1, 2, 4]


async def test_choosing_a_column_evaluates_the_staged_rows_again(klass):
    async with client() as c:
        await as_user(c)
        await upload(c, klass, "personer.xlsx", fixture("canvas-people.xlsx"))
        chosen = await c.put(path(klass, "/column"), json={"column": 1}, headers=CSRF)
        again = await c.get(path(klass))
        back = await c.put(path(klass, "/column"), json={"column": 3}, headers=CSRF)
    assert chosen.status_code == 200
    assert (chosen.json()["chosen_column"], chosen.json()["chosen_count"]) == (1, 0)
    # The suggestion stays, so the page can still name it.
    assert chosen.json()["suggested_column"] == 3
    assert again.json()["upload"]["chosen_column"] == 1
    # The preview read back from the staged rows is the file's first rows, in order.
    for answer in (again.json()["upload"], back.json()):
        assert [row["row_number"] for row in answer["preview"]] == [2, 3, 4, 5, 6]
        assert answer["preview"][0]["cells"][3] == "sara.lund@stud.example.no"
    assert back.json()["chosen_count"] == 12
    assert staged() == [("personer.xlsx", 12, 3)]


async def test_a_column_the_file_does_not_have_is_refused(klass):
    async with client() as c:
        await as_user(c)
        await upload(c, klass, "personer.xlsx", fixture("canvas-people.xlsx"))
        response = await c.put(path(klass, "/column"), json={"column": 5}, headers=CSRF)
        negative = await c.put(path(klass, "/column"), json={"column": -1}, headers=CSRF)
    assert response.status_code == 422
    assert response.json()["error"]["fields"] == {"column": "column_unknown"}
    assert negative.status_code == 422
    assert staged() == [("personer.xlsx", 12, 3)]


@pytest.mark.parametrize(
    ("name", "data"),
    [
        ("tom.csv", b""),
        ("blank.csv", b"\r\n  \r\n,,\r\n"),
        ("bare-overskrift.csv", b"Navn,E-post\r\n"),
        ("liste.pdf", b"%PDF-1.4 sara@stud.example.no"),
        ("liste.txt", b"sara@stud.example.no"),
        ("uten-endelse", b"sara@stud.example.no"),
        ("binary.csv", b"\x00\x01\x02sara@stud.example.no"),
        ("ikke-en-liste.xlsx", b"PK\x03\x04 this is not a workbook"),
        ("forkledd.xlsx", b"Navn,E-post\nSara,sara@stud.example.no\n"),
        ("", b"E-post\nsara@stud.example.no\n"),
    ],
)
async def test_an_unreadable_file_stages_nothing_and_keeps_the_earlier_upload(klass, name, data):
    async with client() as c:
        await as_user(c)
        await upload(c, klass, "personer.xlsx", fixture("canvas-people.xlsx"))
        response = await upload(c, klass, name, data)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "roster_unreadable"
    assert staged() == [("personer.xlsx", 12, 3)]
    assert staged_rows() == 12


async def test_a_file_over_the_size_limit_is_refused(klass, settings_env):
    settings_env(ROSTER_MAX_FILE_MB="1")
    big = b"E-post\n" + b"sara@stud.example.no\n" * 60_000  # about 1.3 MB
    async with client() as c:
        await as_user(c)
        response = await upload(c, klass, "stor.csv", big)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "roster_unreadable"
    assert staged() == []


async def test_a_file_over_the_row_limit_is_refused_and_one_at_it_is_read(klass, settings_env):
    settings_env(ROSTER_MAX_ROWS="3")
    wide = xlsx(["E-post"], *[[f"s{i}@stud.example.no"] for i in range(9)])
    async with client() as c:
        await as_user(c)
        over = await upload(c, klass, "for-mange.csv", addresses(4))
        sheet = await upload(c, klass, "for-mange.xlsx", wide)
        at = await upload(c, klass, "akkurat.csv", addresses(3))
    assert over.status_code == 422 and sheet.status_code == 422
    assert at.status_code == 201 and at.json()["row_count"] == 3
    assert staged() == [("akkurat.csv", 3, 0)]


async def test_a_new_upload_replaces_the_earlier_one(klass):
    async with client() as c:
        await as_user(c)
        await upload(c, klass, "personer.xlsx", fixture("canvas-people.xlsx"))
        second = await upload(c, klass, "karakterbok.csv", fixture("canvas-gradebook.csv"))
    assert second.status_code == 201
    assert staged() == [("karakterbok.csv", 13, 3)]
    assert staged_rows() == 13


async def test_bytt_fil_deletes_the_staged_upload(klass):
    async with client() as c:
        await as_user(c)
        await upload(c, klass, "personer.xlsx", fixture("canvas-people.xlsx"))
        shown = await c.get(path(klass))
        deleted = await c.delete(path(klass), headers=CSRF)
        after = await c.get(path(klass))
        again = await c.delete(path(klass), headers=CSRF)
        column = await c.put(path(klass, "/column"), json={"column": 0}, headers=CSRF)
    assert shown.json()["upload"]["file_name"] == "personer.xlsx"
    assert deleted.status_code == 204 and again.status_code == 204
    assert after.status_code == 200 and after.json() == {"upload": None}
    assert column.status_code == 404 and column.json()["error"]["code"] == "not_found"
    assert staged() == [] and staged_rows() == 0


async def test_an_expired_staging_is_never_returned_and_is_purged(klass):
    async with client() as c:
        await as_user(c)
        await upload(c, klass, "personer.xlsx", fixture("canvas-people.xlsx"))
        rows("UPDATE roster_uploads SET expires_at = '2000-01-01T00:00:00Z' RETURNING id")
        shown = await c.get(path(klass))
        column = await c.put(path(klass, "/column"), json={"column": 3}, headers=CSRF)
    assert shown.json() == {"upload": None}
    assert column.status_code == 404
    assert staged() == [] and staged_rows() == 0


async def test_an_upload_purges_the_expired_stagings_of_other_classes(klass):
    async with client() as c:
        await as_user(c)
        await upload(c, klass, "personer.xlsx", fixture("canvas-people.xlsx"))
        rows("UPDATE roster_uploads SET expires_at = '2000-01-01T00:00:00Z' RETURNING id")
        other = await c.post(
            "/api/classes",
            json={"name": "class-of-1995", "institution_id": str(await institution("NTNU"))},
            headers=CSRF,
        )
        await upload(c, other.json()["id"], "andre.csv", addresses(2))
    assert staged() == [("andre.csv", 2, 0)]


async def test_the_staging_expires_after_the_configured_hours(klass):
    async with client() as c:
        await as_user(c)
        await upload(c, klass, "personer.xlsx", fixture("canvas-people.xlsx"))
    assert rows("SELECT expires_at - created_at FROM roster_uploads") == [(timedelta(hours=24),)]


async def test_another_lecturer_an_unknown_class_and_a_non_lecturer_are_refused(klass):
    await make("admin@example.com", roles=(AccountRole.admin,))
    unknown = str(uuid.uuid4())
    people = fixture("canvas-people.xlsx")
    async with client() as c:
        await as_user(c, OTHER)
        answers = [
            await upload(c, klass, "personer.xlsx", people),
            await upload(c, unknown, "personer.xlsx", people),
            await upload(c, klass, "tom.csv", b""),
            await upload(c, klass, "", people),
            await upload(c, "ikke-en-klasse", "personer.xlsx", people),
            await c.get(path(klass)),
            await c.get(path(unknown)),
            await c.put(path(klass, "/column"), json={"column": 0}, headers=CSRF),
            await c.delete(path(klass), headers=CSRF),
        ]
    async with client() as c:
        await as_user(c, "admin@example.com")
        answers.append(await c.get(path(klass)))
        answers.append(await upload(c, klass, "personer.xlsx", people))
    assert [a.status_code for a in answers] == [403] * len(answers)
    assert {a.json()["error"]["code"] for a in answers} == {"forbidden"}
    assert staged() == []


async def test_an_upload_without_the_csrf_header_is_refused(klass):
    async with client() as c:
        await as_user(c)
        response = await c.post(
            path(klass), content=fixture("canvas-people.xlsx"), headers={"X-File-Name": "a.xlsx"}
        )
    assert response.status_code == 403
    assert staged() == []


async def test_no_file_name_cell_or_address_reaches_the_logs(klass):
    with structlog.testing.capture_logs() as logs:
        async with client() as c:
            await as_user(c)
            await upload(c, klass, "hemmelig-navn.csv", fixture("canvas-gradebook.csv"))
            await c.put(path(klass, "/column"), json={"column": 0}, headers=CSRF)
            await upload(c, klass, "hemmelig-navn.pdf", b"x")
            await c.delete(path(klass), headers=CSRF)
    text = repr(logs)
    assert "roster_upload_staged" in text
    for secret in ("hemmelig-navn", "stud.example.no", "Lund", "Points Possible"):
        assert secret not in text


async def test_a_file_name_with_a_path_keeps_only_its_own_name(klass):
    async with client() as c:
        await as_user(c)
        response = await upload(
            c, klass, "C:\\Users\\bard\\Nedlastinger\\eksport.csv", fixture("canvas-gradebook.csv")
        )
    assert response.status_code == 201
    assert response.json()["file_name"] == "eksport.csv"


async def test_a_streamed_file_over_the_size_limit_is_refused(klass, settings_env):
    settings_env(ROSTER_MAX_FILE_MB="1")

    async def chunks():
        yield b"E-post\n"
        for _ in range(60):
            yield b"sara@stud.example.no\n" * 1000  # about 1.3 MB, with no Content-Length

    async with client() as c:
        await as_user(c)
        response = await c.post(
            path(klass),
            content=chunks(),
            headers={**CSRF, "Content-Type": "application/octet-stream", "X-File-Name": "s.csv"},
        )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "roster_unreadable"
    assert staged() == []


async def test_more_rows_than_one_insert_batch_are_all_staged_and_evaluated(klass):
    async with client() as c:
        await as_user(c)
        response = await upload(c, klass, "stor.csv", addresses(1200))
        column = await c.put(path(klass, "/column"), json={"column": 0}, headers=CSRF)
    assert response.json()["row_count"] == 1200
    assert staged_rows() == 1200
    assert column.json()["chosen_count"] == 1200


async def test_two_uploads_at_once_leave_one_staging(klass):
    async with client() as c:
        await as_user(c)
        first, second = await asyncio.gather(
            upload(c, klass, "en.csv", addresses(2)), upload(c, klass, "to.csv", addresses(3))
        )
    assert (first.status_code, second.status_code) == (201, 201)
    assert len(staged()) == 1
    assert staged_rows() == staged()[0][1]


async def test_a_long_file_name_keeps_its_type(klass):
    name = "x" * 300 + ".csv"
    async with client() as c:
        await as_user(c)
        response = await upload(c, klass, name, addresses(2))
    assert response.status_code == 201
    assert len(response.json()["file_name"]) == 255
    assert response.json()["file_name"].endswith(".csv")


# Story 4.3: invalid rows and pasted addresses (FR-7). The fixture `ugyldige-rader.csv` is shared
# with Playwright.


def paste_path(class_id: str) -> str:
    return f"/api/classes/{class_id}/roster-paste"


async def paste(c, class_id: str, text: str):
    return await c.post(paste_path(class_id), json={"text": text}, headers=CSRF)


def invalid(body: dict) -> list[tuple]:
    return [
        (row["row_number"], row["value"], row["reason"], row["first_row"])
        for row in body["invalid_rows"]
    ]


async def test_each_invalid_row_is_listed_with_its_reason_and_duplicates_name_the_first_row(klass):
    async with client() as c:
        await as_user(c)
        response = await upload(c, klass, "ugyldige.csv", fixture("ugyldige-rader.csv"))
    body = response.json()
    assert response.status_code == 201
    assert body["source"] == "file"
    assert (body["row_count"], body["chosen_column"], body["valid_count"]) == (8, 2, 3)
    assert invalid(body) == [
        (4, "emma.solberg@stud", "missing_domain", None),
        (5, "jakob.lien(at)stud.example.no", "missing_at", None),
        (6, "thea.moe@@stud.example.no", "two_at", None),
        (7, "", "empty", None),
        (9, "Sara.Lund@stud.example.no", "duplicate", 2),
    ]


async def test_choosing_another_column_evaluates_its_rows(klass):
    async with client() as c:
        await as_user(c)
        await upload(c, klass, "ugyldige.csv", fixture("ugyldige-rader.csv"))
        chosen = await c.put(path(klass, "/column"), json={"column": 0}, headers=CSRF)
        again = await c.get(path(klass))
    for body in (chosen.json(), again.json()["upload"]):
        assert body["valid_count"] == 0
        assert [r["reason"] for r in body["invalid_rows"]] == ["whitespace"] * 8


async def test_a_file_with_no_column_chosen_lists_nothing_and_has_nothing_valid(klass):
    async with client() as c:
        await as_user(c)
        response = await upload(c, klass, "uten-epost.csv", fixture("uten-epost.csv"))
    body = response.json()
    assert body["chosen_column"] is None
    assert (body["valid_count"], body["invalid_rows"]) == (0, [])


async def test_pasted_addresses_are_split_staged_as_one_column_and_evaluated(klass):
    text = (
        "a@stud.example.no, b@stud.example.no;c@stud.example.no\n"
        "Ola Nordmann <d@stud.example.no>  e@stud.example.no\r\n"
        '"Nordmann, Kari" <f@stud.example.no>\tfeil(at)stud.example.no\n'
        "A@stud.example.no"
    )
    async with client() as c:
        await as_user(c)
        response = await paste(c, klass, text)
        again = await c.get(path(klass))
    body = response.json()
    assert response.status_code == 201
    assert again.json()["upload"] == body
    assert (body["source"], body["file_name"], body["has_header"]) == ("paste", "", False)
    assert [col["letter"] for col in body["columns"]] == ["A"]
    assert (body["row_count"], body["chosen_column"], body["valid_count"]) == (8, 0, 6)
    assert [row["cells"] for row in body["preview"]] == [
        ["a@stud.example.no"],
        ["b@stud.example.no"],
        ["c@stud.example.no"],
        ["d@stud.example.no"],
        ["e@stud.example.no"],
    ]
    assert invalid(body) == [
        (7, "feil(at)stud.example.no", "missing_at", None),
        (8, "A@stud.example.no", "duplicate", 1),
    ]
    assert staged() == [("", 8, 0)]


async def test_a_paste_replaces_a_staged_file_and_an_empty_paste_stages_no_rows(klass):
    async with client() as c:
        await as_user(c)
        await upload(c, klass, "ugyldige.csv", fixture("ugyldige-rader.csv"))
        response = await paste(c, klass, " ,;\n\t ")
    body = response.json()
    assert response.status_code == 201
    assert (body["row_count"], body["valid_count"], body["invalid_rows"]) == (0, 0, [])
    assert rows("SELECT source, row_count FROM roster_uploads") == [("paste", 0)]


async def test_a_paste_over_the_limits_is_refused_and_keeps_the_staging(klass, settings_env):
    settings_env(ROSTER_MAX_ROWS="3", ROSTER_MAX_FILE_MB="1")
    async with client() as c:
        await as_user(c)
        await paste(c, klass, "a@x.no b@x.no")
        too_many = await paste(c, klass, "a@x.no b@x.no c@x.no d@x.no")
        too_big = await paste(c, klass, "æ" * (512 * 1024 + 1))  # 1 MB + 2 bytes in UTF-8
        kept = await c.get(path(klass))
        at_limit = await paste(c, klass, "a@x.no b@x.no c@x.no")
    for refused in (too_many, too_big):
        assert refused.status_code == 422
        assert refused.json()["error"]["code"] == "roster_paste_too_long"
    # The refusals staged nothing: the earlier paste is still there.
    assert kept.json()["upload"]["preview"] == [
        {"row_number": 1, "cells": ["a@x.no"]},
        {"row_number": 2, "cells": ["b@x.no"]},
    ]
    assert at_limit.status_code == 201 and at_limit.json()["row_count"] == 3


async def test_a_paste_by_another_lecturer_or_without_csrf_is_refused(klass):
    async with client() as c:
        await as_user(c, OTHER)
        other = await paste(c, klass, "a@x.no")
        unknown = await paste(c, "ikke-en-klasse", "a@x.no")
    async with client() as c:
        await as_user(c)
        no_csrf = await c.post(paste_path(klass), json={"text": "a@x.no"})
    assert [r.status_code for r in (other, unknown, no_csrf)] == [403, 403, 403]
    assert staged() == []


async def test_no_pasted_address_reaches_the_logs(klass):
    with structlog.testing.capture_logs() as logs:
        async with client() as c:
            await as_user(c)
            await paste(c, klass, "Hemmelig Navn <hemmelig@stud.example.no>")
            await c.get(path(klass))
    text = repr(logs)
    assert "roster_paste_staged" in text
    for secret in ("Hemmelig", "hemmelig", "stud.example.no"):
        assert secret not in text


async def test_a_nul_in_pasted_text_separates_and_is_never_stored(klass):
    async with client() as c:
        await as_user(c)
        response = await paste(c, klass, "a@x.no\x00b@x.no")
    assert response.status_code == 201
    assert [row["cells"] for row in response.json()["preview"]] == [["a@x.no"], ["b@x.no"]]
