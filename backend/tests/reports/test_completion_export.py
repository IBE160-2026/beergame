"""Story 13.14 at the api (FR-60, FR-17, FR-56, AD-12, AD-13, AD-14, AD-16, C-2): the Completion
export, `GET /api/class-sessions/{id}/completion-export?format=csv|xlsx`.

The short Class game of `test_completion_status.py`, played out after Week 2, so the shares and the
playout share are known; the file is checked against `reports.service.completion_status` and the
Studentside's record, in both formats."""

import csv
import io
import uuid
from datetime import UTC, date, datetime

from openpyxl import load_workbook

from app.analysis.completion import CompletionStatus, CompletionStep
from app.modules.identity.schemas import AccountRole
from app.modules.identity.service import Person
from app.modules.reports import completion_export, scope
from app.modules.reports import service as reports
from app.modules.sessions import service as sessions
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_staff import ASSISTANT, call, put_staff
from tests.messaging.helpers import rows
from tests.reports.test_completion_status import _played_out, every_later_step, obligatory
from tests.reports.test_corrections import correct
from tests.reports.test_student_report import files
from tests.reports.test_studentside import ADMIN, OTHER_LECTURER, record
from tests.sessions.test_dates import OUTSIDER
from tests.sessions.test_game_end import _empty, clock, klass, short_game
from tests.sessions.test_orders import code
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "files", "klass"]

HEADER = (
    "Navn",
    "E-post",
    "Klassespill",
    "Debrief",
    "Quiz",
    "Replay",
    "Individuell test",
    "Bestilte uker (%)",
    "Kravet (%)",
    "Utspilling (%)",
    "Oppfølgingsspill",
    "Rettet av faglærer",
    "Krav oppfylt",
)
STEPS = ("class_game", "debrief", "quiz_passed", "replay", "test_submitted")
NORWEGIAN = "Åse Ærlig-Øyen"
FORMULA = '=HYPERLINK("http://x.no")'
GIVEN = datetime(2026, 11, 20, 23, 30, tzinfo=UTC)  # 21.11.2026 in Oslo


def export_path(session_id: str) -> str:
    return f"/api/class-sessions/{session_id}/completion-export"


async def download(session_id: str, who: str = LECTURER, fmt: str | None = None):
    params = {} if fmt is None else {"format": fmt}
    return await call(who, "GET", export_path(session_id), params=params)


def audited() -> list[tuple]:
    return rows(
        "SELECT actor_user_id, target_ids, change FROM audit_events "
        "WHERE action = 'completion_export.downloaded' ORDER BY occurred_at, id"
    )


def name(user: uuid.UUID, value: str) -> None:
    execute("UPDATE users SET name = %s WHERE id = %s", value, user)


def oslo(at: datetime) -> str:
    return at.astimezone(sessions.OSLO).strftime("%d.%m.%Y")


async def _exported(klass, monkeypatch) -> tuple[str, list[uuid.UUID]]:
    """The played-out game, obligatory; the first Student has every later step and a corrected
    Debrief, and was given an Oppfølgingsspill; names with æøå and a formula."""
    session_id, _, seated = await _played_out(klass)
    obligatory(session_id)
    me = seated[0]
    await every_later_step(me, session_id)
    assert (await correct(LECTURER, session_id, me, "debrief", True, "Muntlig.")).is_success
    name(me, NORWEGIAN)
    name(seated[1], FORMULA)

    # An Oppfølgingsspill given to the first Student (Story 13.4's row), not yet played: the
    # export shows the date given; Completion reads no share from it.
    makeup_game = uuid.uuid7()
    execute(
        "INSERT INTO games (id, purpose, lifecycle, version, class_session_id) "
        "VALUES (%s, 'makeup', 'not_started', 1, %s)",
        makeup_game,
        session_id,
    )
    execute(
        "INSERT INTO makeup_games (id, user_id, class_session_id, game_id, given_at) "
        "VALUES (%s, %s, %s, %s, %s)",
        uuid.uuid7(),
        me,
        session_id,
        makeup_game,
        GIVEN,
    )
    return session_id, seated


async def test_a_lecturer_downloads_the_csv_and_it_agrees_with_the_completion_status(
    klass, monkeypatch, files
):
    session_id, seated = await _exported(klass, monkeypatch)
    me, other = seated
    got = await download(session_id)
    assert got.status_code == 200, got.text
    assert got.headers["content-type"] == "text/csv; charset=utf-8"
    assert got.headers["cache-control"] == "no-store"
    assert got.headers["content-disposition"] == (
        'attachment; filename="fullforingsliste-klasseokt-1.csv"'
    )
    raw = got.content
    assert raw.startswith("﻿".encode()) and b"\r\n" in raw
    lines = list(csv.reader(io.StringIO(raw.decode("utf-8-sig")), delimiter=";"))
    assert tuple(lines[0]) == HEADER
    # Norwegian order: the formula-like name («=») before «Åse».
    body = lines[1:]
    assert [row[0] for row in body] == [f"'{FORMULA}", NORWEGIAN]
    rows_by = {me: body[1], other: body[0]}

    sid = uuid.UUID(session_id)
    for student, row in rows_by.items():
        status = await reports.completion_status(student, sid)
        assert status is not None
        [(address,)] = rows("SELECT email FROM users WHERE id = %s", student)
        assert row[1] == address
        for column, step in zip(row[2:7], STEPS, strict=True):
            found = status.step(step)
            assert column == (oslo(found.recorded_at) if found.done else "ikke gjort")
        assert row[7:10] == [
            str(status.ordered_share),
            str(status.required_share),
            str(status.playout_share),
        ]
        assert row[12] == ("Ja" if status.requirement_met else "Nei")
        # The Studentside says the same per step.
        record_steps = (await record(LECTURER, session_id, student)).json()["completion"]["steps"]
        assert [step["done"] for step in record_steps] == [
            column != "ikke gjort" for column in row[2:7]
        ]
    # Week 2 ordered of the 5 after the Guided Week, Weeks 3 to 6 played out.
    assert rows_by[me][7:10] == ["20", "80", "80"]
    assert rows_by[me][3] != "ikke gjort"  # the corrected Debrief counts
    assert (rows_by[me][10], rows_by[me][11]) == ("21.11.2026", "Ja")
    assert (rows_by[other][10], rows_by[other][11]) == ("", "Nei")
    assert rows_by[other][3] == "ikke gjort"

    # Streamed, never stored: nothing in the bucket; one audit row, no name in it.
    assert not [path for path in files.rglob("*") if path.is_file()]
    [(actor, target, change)] = audited()
    [(lecturer,)] = rows("SELECT id FROM users WHERE email = %s", LECTURER)
    assert (actor, target, change) == (
        lecturer,
        {"class_session_id": session_id},
        {"format": "csv", "students": 2},
    )


async def test_the_excel_file_holds_dates_numbers_and_text_as_such(klass, monkeypatch):
    session_id, seated = await _exported(klass, monkeypatch)
    got = await download(session_id, fmt="xlsx")
    assert got.status_code == 200, got.text
    assert got.headers["content-type"] == completion_export.XLSX_TYPE
    assert 'filename="fullforingsliste-klasseokt-1.xlsx"' in got.headers["content-disposition"]
    sheet = load_workbook(io.BytesIO(got.content)).active
    assert sheet.title == "Fullføring"
    cells = list(sheet.iter_rows())
    assert tuple(cell.value for cell in cells[0]) == HEADER
    formula_row, own = cells[1], cells[2]
    # A name that looks like a formula is a text cell, never a formula.
    assert (formula_row[0].value, formula_row[0].data_type) == (FORMULA, "s")
    assert own[0].value == NORWEGIAN
    status = await reports.completion_status(seated[0], uuid.UUID(session_id))
    replay = status.step("replay").recorded_at.astimezone(sessions.OSLO).date()
    assert own[5].value.date() == replay and own[5].number_format == "dd.mm.yyyy"
    assert (own[7].value, own[7].data_type) == (20, "n")
    assert (own[10].value.date(), own[11].value, own[12].value) == (date(2026, 11, 21), "Ja", "Nei")
    assert [row[2] for row in audited()] == [{"format": "xlsx", "students": 2}]


async def test_a_session_that_is_not_obligatory_and_one_without_students(klass, monkeypatch):
    session_id, _, _ = await short_game(klass)
    obligatory(session_id, False)
    body = list(
        csv.reader(io.StringIO((await download(session_id)).text.lstrip("﻿")), delimiter=";")
    )
    assert len(body) == 3 and {row[12] for row in body[1:]} == {"Ikke obligatorisk"}

    async def everyone(session, ids):
        return set(ids)

    monkeypatch.setattr(scope, "_test_students", [everyone])
    only = (await download(session_id)).content.decode("utf-8-sig").splitlines()
    assert only == [";".join(HEADER)]


async def test_only_the_lecturers_of_the_class_may_export_and_the_block_says_so(klass):
    session_id, _, seated = await short_game(klass)
    await make(OTHER_LECTURER)
    await make(ADMIN, roles=(AccountRole.admin,))
    await make(OUTSIDER, roles=())
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")
    # A Lecturer account who is an Assistant lecturer in this Class is still refused.
    assisting = "assisterende-faglaerer@x.no"
    put_staff(klass, await make(assisting), "assistant")
    refusals = [
        await download(session_id, ASSISTANT),
        await download(session_id, assisting),
        await download(session_id, OTHER_LECTURER),
        await download(session_id, ADMIN),
        await download(session_id, OUTSIDER),
        await download(session_id, email(0)),
        await download("not-an-id"),
        await download(str(uuid.uuid7())),
    ]
    assert {(r.status_code, r.text) for r in refusals} == {
        (refusals[0].status_code, refusals[0].text)
    }
    assert code(refusals[0]) == (403, "forbidden")
    assert audited() == []
    assert (await download(session_id, fmt="pdf")).status_code == 422

    zip_state = f"/api/class-sessions/{session_id}/reports/zip"
    assert (await call(LECTURER, "GET", zip_state)).json()["completion_export"] is True
    assert (await call(ASSISTANT, "GET", zip_state)).json()["completion_export"] is False
    assert (await call(assisting, "GET", zip_state)).json()["completion_export"] is False

    # Once the Student data is deleted, no file.
    execute(
        "UPDATE class_sessions SET deletion_date = %s WHERE id = %s", date(2000, 1, 1), session_id
    )
    assert code(await download(session_id)) == (409, "data_deleted")
    assert audited() == []


def _status(**changes) -> CompletionStatus:
    steps = tuple(
        CompletionStep(step=step, recorded=False, recorded_at=None, done=False) for step in STEPS
    )
    return CompletionStatus(
        **{
            "steps": steps,
            "obligatory": True,
            "requirement_met": False,
            "required_share": 80,
            **changes,
        }
    )


def test_the_columns_are_the_fixed_allow_list_with_no_ai_data():
    assert completion_export.COLUMNS == HEADER
    banned = ("ki", "ai", "poeng", "score", "vurdering", "tilbakemelding", "karakter", "letter")
    for column in HEADER:
        words = column.casefold().replace("(", " ").replace(")", " ").replace("-", " ").split()
        assert not set(words) & set(banned), column
    # A row has exactly one value per column, whatever the status holds.
    assert len(completion_export.row_values(_status(), None, None)) == len(HEADER)


def test_a_step_done_by_a_correction_alone_reads_done_and_numbers_take_a_decimal_comma():
    at = datetime(2026, 11, 23, 23, 30, tzinfo=UTC)
    steps = (
        CompletionStep("class_game", False, None, True, corrected=True),
        CompletionStep("debrief", True, at, True),
        CompletionStep("quiz_passed", True, at, False),
        CompletionStep("replay", False, None, False),
        CompletionStep("test_submitted", False, None, False),
    )
    values = completion_export.row_values(
        _status(steps=steps), Person(uuid.uuid7(), "Kari", "kari@x.no"), None
    )
    assert values[2:7] == ("gjort", date(2026, 11, 24), "ikke gjort", "ikke gjort", "ikke gjort")
    assert values[7:13] == (None, 80, None, None, "Ja", "Nei")
    *_, line = list(completion_export.to_csv([(*values[:7], 12.5, *values[8:])]))
    assert line.decode() == (
        "Kari;kari@x.no;gjort;24.11.2026;ikke gjort;ikke gjort;ikke gjort;12,5;80;;;Ja;Nei\r\n"
    )
    assert completion_export.file_name(None, "csv") == "fullforingsliste.csv"


def test_every_text_a_spreadsheet_reads_as_a_formula_is_written_as_text_in_the_csv():
    texts = ["=1+1", "+47 1", "-2+3", "@SUM(1)", "\tx", "\rx", "\nx", "Kari Nordmann"]
    *_, line = list(completion_export.to_csv([texts]))
    cells = next(csv.reader(io.StringIO(line.decode()), delimiter=";"))
    assert cells == [
        "'=1+1",
        "'+47 1",
        "'-2+3",
        "'@SUM(1)",
        "'\tx",
        "'\rx",
        "'\nx",
        "Kari Nordmann",
    ]
