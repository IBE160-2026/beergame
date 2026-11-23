"""Story 13.13 at the api and in the job (FR-59, NFR-7, AD-9, AD-12, AD-13, AD-14, AD-18, C-2): the
staff of the Class download all Student reports of a Class session as one ZIP.

`POST /api/class-sessions/{id}/reports/zip` records a `report_zips` row and defers
`reports.build_zip` on `reports-bulk`; the job builds one report per Student through the one
assembler, snapshot and converter (here a fake that reads the snapshot through the api, as the
print route does, and returns a "PDF" holding what it read, so the ZIP can be opened and read), and
stores the ZIP in the storage mock. `GET …/zip/file` answers a signed URL."""

import io
import json
import time
import uuid
import zipfile
from datetime import date
from urllib.parse import parse_qs, urlsplit

import pytest
from structlog.testing import capture_logs

from app.modules.identity.schemas import AccountRole
from app.modules.messaging import delivery
from app.modules.reports import bundle, render, report_data, scope, snapshot
from app.modules.sessions import service as sessions
from app.platform import jobs
from app.platform.config import get_settings
from app.platform.email.render import Recipient, Section
from app.platform.email.render import render as render_mail
from app.platform.events.registry import COMMAND_TOPICS
from tests.assessment.test_letter import (
    TIGHT,
    _empty,
    assessed,
    clock,
    emitted,
    klass,
    locked,
    save,
)
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_staff import ASSISTANT, call, put_staff
from tests.debrief.test_explanation import user_id
from tests.identity.helpers import client
from tests.messaging.helpers import rows
from tests.reports.test_student_report import code, files
from tests.reports.test_studentside import ADMIN, OTHER_LECTURER
from tests.sessions.test_dates import new_session
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "emitted", "files", "klass"]


def zip_path(session_id: str) -> str:
    return f"/api/class-sessions/{session_id}/reports/zip"


async def state(session_id: str, who: str = LECTURER):
    return await call(who, "GET", zip_path(session_id))


async def press(session_id: str, who: str = LECTURER, **kw):
    return await call(who, "POST", zip_path(session_id), **kw)


async def file(session_id: str, who: str = LECTURER):
    return await call(who, "GET", zip_path(session_id) + "/file")


def zips(session_id: str) -> list[tuple]:
    return rows(
        "SELECT status, failure, object_path, students, requested_by FROM report_zips "
        "WHERE class_session_id = %s ORDER BY requested_at, id",
        session_id,
    )


def queued() -> int:
    return rows("SELECT count(*) FROM procrastinate_jobs WHERE queue_name = 'reports-bulk'")[0][0]


def snapshots() -> int:
    return rows("SELECT count(*) FROM report_snapshots")[0][0]


def audits(action: str) -> list[tuple]:
    return rows(
        "SELECT actor_user_id, target_ids FROM audit_events WHERE action = %s "
        "ORDER BY occurred_at, id",
        action,
    )


def notices_of(who: uuid.UUID) -> list[tuple]:
    return rows(
        "SELECT kind, dedupe_key, ref FROM notices WHERE user_id = %s AND kind = %s",
        who,
        "reports_zip_ready",
    )


async def run_bulk() -> float:
    started = time.monotonic()
    await jobs.run_until_idle([jobs.MAIL, jobs.REPORTS_BULK])
    return time.monotonic() - started


async def opened(response) -> zipfile.ZipFile:
    """The ZIP behind a 303 to the storage mock's signed URL."""
    assert response.status_code == 303, response.text
    async with client() as c:
        got = await c.get(response.headers["location"])
    assert got.status_code == 200 and got.headers["content-type"] == "application/zip"
    return zipfile.ZipFile(io.BytesIO(got.content))


@pytest.fixture
def embedding(monkeypatch):
    """A fake converter that reads the snapshot through the api with the token, as the print route
    does, and returns a "PDF" that holds what it read."""
    seen: dict = {"data": []}

    async def to_pdf(url: str) -> bytes:
        parts = urlsplit(url)
        snapshot_id = parts.path.rsplit("/", 1)[1]
        token = parse_qs(parts.query)["token"][0]
        async with client() as c:
            got = await c.get(
                f"/api/internal/report-snapshots/{snapshot_id}", headers={"X-Render-Token": token}
            )
        assert got.status_code == 200
        seen["data"].append(got.json())
        return b"%PDF-1.7\n" + json.dumps(got.json(), ensure_ascii=False).encode()

    monkeypatch.setattr(render, "to_pdf", to_pdf)
    return seen


def contents(archive: zipfile.ZipFile) -> dict[str, dict]:
    return {
        name: json.loads(archive.read(name).removeprefix(b"%PDF-1.7\n"))
        for name in archive.namelist()
    }


async def test_staff_make_one_zip_of_every_students_report_and_it_never_holds_ai_data(
    klass, monkeypatch, emitted, files, embedding
):
    session_id = await locked(klass, monkeypatch, n=2)
    # The Lecturer shows the Indicative letter to everyone, and the first Student's AI assessment
    # is ready: the ZIP still holds neither (C-2).
    assert (
        await save(session_id, letter_setting="all", letter_thresholds=TIGHT)
    ).status_code == 200
    await assessed(session_id, monkeypatch)
    lecturer = user_id(LECTURER)
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")

    before = await state(session_id)
    assert before.status_code == 200 and before.headers["cache-control"] == "no-store"
    assert before.json() == {
        "status": "none",
        "generated_at": None,
        "students": None,
        "deleted": False,
        "completion_export": True,
        "game_data_export": True,  # Story 14.8, its flag on
    }
    assert code(await file(session_id)) == (409, "zip_not_ready")

    emitted.clear()
    # Whatever the caller sends, the ZIP is built without the AI section.
    pressed = await press(session_id, json={"ai": True})
    assert pressed.status_code == 202 and pressed.json()["status"] == "pending"
    # Story 13.14: the press answers the block's state with the Completion export flag too.
    assert pressed.json()["completion_export"] is True
    assert pressed.json()["game_data_export"] is True
    assert set(emitted) == {("user", str(lecturer))}
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["reports.request_zip"]
    # A second press, by anyone of the staff, answers the pending one.
    assisted = (await press(session_id, ASSISTANT)).json()
    assert (assisted["status"], assisted["completion_export"]) == ("pending", False)
    assert assisted["game_data_export"] is False
    assert queued() == 1
    [(actor, target)] = audits("report_zip.requested")
    [(_, _, _, _, by)] = zips(session_id)
    assert (actor, target["class_session_id"], by) == (lecturer, session_id, lecturer)

    emitted.clear()
    assert await run_bulk() < 600  # the 10-minute placeholder target
    assert ("user", str(lecturer)) in emitted
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["reports.build_zip"]
    [(status, failure, path, students, _)] = zips(session_id)
    assert (status, failure, students) == ("ready", None, 2)
    assert path.startswith(f"class-sessions/{session_id}/bundles/") and path.endswith(".zip")
    assert snapshots() == 0
    # The requester is told, once.
    [(kind, key, ref)] = notices_of(lecturer)
    assert (kind, str(ref)) == ("reports_zip_ready", session_id) and key.endswith(
        str(target["zip_id"])
    )

    # Shared by the staff: the Assistant lecturer downloads it.
    shared = (await state(session_id, ASSISTANT)).json()
    assert (shared["status"], shared["students"]) == ("ready", 2)
    got = await file(session_id, ASSISTANT)
    assert "studentrapporter-klasseokt-1.zip" in got.headers["location"]
    archive = await opened(got)
    [(downloader, gave)] = audits("report_zip.downloaded")
    assert (downloader, gave["zip_id"]) == (user_id(ASSISTANT), target["zip_id"])

    # One file per Student, named so a Lecturer finds them.
    names = {
        row[0]
        for row in rows(
            "SELECT name FROM users WHERE id IN (%s, %s)", user_id(email(0)), user_id(email(1))
        )
    }
    assert sorted(archive.namelist()) == sorted(f"{name}.pdf" for name in names)
    read = contents(archive)
    for name, data in read.items():
        assert data["student_name"] == name.removesuffix(".pdf")
        assert all(section["kind"] != "assessment" for section in data["sections"])
    raw = b"".join(archive.read(name) for name in archive.namelist()).decode()
    assert '"letter"' not in raw and '"total_max"' not in raw and "assessment" not in raw


async def test_a_failed_job_says_so_leaves_nothing_behind_and_a_new_press_tries_again(
    klass, monkeypatch, files, embedding
):
    session_id = await locked(klass, monkeypatch, n=2)
    good = render.to_pdf

    async def broken(url: str) -> bytes:
        raise RuntimeError(f"failed at {url}")  # a message with the token: never logged

    monkeypatch.setattr(render, "to_pdf", broken)
    assert (await press(session_id)).status_code == 202
    with capture_logs() as logs:
        await run_bulk()
    [(status, failure, path, students, _)] = zips(session_id)
    assert (status, failure, path, students) == ("failed", "render_failed", None, None)
    assert (await state(session_id)).json()["status"] == "failed"
    assert snapshots() == 0 and not list(files.rglob("*.zip"))
    failed = [entry for entry in logs if entry["event"] == "reports_zip_failed"]
    assert failed and "token" not in json.dumps(failed, default=str)

    # «Prøv igjen»: a new press builds it.
    monkeypatch.setattr(render, "to_pdf", good)
    assert (await press(session_id)).status_code == 202
    await run_bulk()
    assert [row[0] for row in zips(session_id)] == ["failed", "ready"]


async def test_a_job_delivered_twice_builds_once_and_one_zip_stays(
    klass, monkeypatch, files, embedding
):
    session_id = await locked(klass, monkeypatch, n=2)
    assert (await press(session_id)).status_code == 202
    [zip_id] = [row[0] for row in rows("SELECT id FROM report_zips")]
    await run_bulk()
    assert await bundle.build(zip_id) == "skipped"  # a retried delivery
    first = zips(session_id)[0][2]
    assert len(list(files.rglob("*.zip"))) == 1

    # A new ZIP replaces the earlier one: its object goes.
    assert (await press(session_id)).status_code == 202
    await run_bulk()
    [(_, _, gone, _, _), (_, _, kept, _, _)] = zips(session_id)
    assert gone is None and kept != first
    assert [p.name for p in files.rglob("*.zip")] == [kept.rsplit("/", 1)[1]]


async def test_a_zip_that_never_ended_gives_way_to_a_new_press(
    klass, monkeypatch, files, embedding
):
    session_id = await locked(klass, monkeypatch)
    assert (await press(session_id)).status_code == 202
    stale = get_settings().report_zip_stale_seconds + 1
    execute(f"UPDATE report_zips SET requested_at = requested_at - interval '{stale} seconds'")
    assert (await state(session_id)).json()["status"] == "failed"
    assert (await press(session_id)).status_code == 202
    assert [(row[0], row[1]) for row in zips(session_id)] == [
        ("failed", "stale"),
        ("pending", None),
    ]


async def test_outsiders_are_refused_alike_and_nothing_is_recorded(
    klass, monkeypatch, files, embedding
):
    session_id = await locked(klass, monkeypatch, n=2)
    await make(OTHER_LECTURER)
    await make(ADMIN, roles=(AccountRole.admin,))
    for who, where in (
        (OTHER_LECTURER, session_id),  # a Lecturer of another Class
        (ADMIN, session_id),  # an Admin without a staff role in the Class
        (email(0), session_id),  # a Student of the Class
        (LECTURER, "00000000-0000-0000-0000-000000000000"),  # no such Class session
        (LECTURER, "not-an-id"),
    ):
        for answer in (await state(where, who), await press(where, who), await file(where, who)):
            assert code(answer) == (403, "forbidden"), (who, answer.text)
    assert zips(session_id) == [] and queued() == 0 and audits("report_zip.requested") == []


async def test_without_students_reports_count_there_is_no_zip(klass, monkeypatch, files, embedding):
    session_id = await locked(klass, monkeypatch)

    async def everyone(session, ids):
        return set(ids)

    monkeypatch.setattr(scope, "_test_students", [everyone])
    assert code(await press(session_id)) == (409, "no_students")
    assert zips(session_id) == [] and queued() == 0


async def test_once_the_student_data_is_deleted_the_block_says_so_and_builds_nothing(
    klass, monkeypatch, files, embedding
):
    session_id = await locked(klass, monkeypatch)
    assert (await press(session_id)).status_code == 202
    await run_bulk()
    execute(
        "UPDATE class_sessions SET deletion_date = %s WHERE id = %s", date(2000, 1, 1), session_id
    )
    found = (await state(session_id)).json()
    assert (found["deleted"], found["status"], found["generated_at"]) == (True, "none", None)
    assert code(await press(session_id)) == (409, "data_deleted")
    assert code(await file(session_id)) == (409, "data_deleted")
    assert len(zips(session_id)) == 1


async def test_a_zip_whose_data_is_deleted_while_it_waits_is_never_built(
    klass, monkeypatch, files, embedding
):
    session_id = await locked(klass, monkeypatch)
    assert (await press(session_id)).status_code == 202
    execute(
        "UPDATE class_sessions SET deletion_date = %s WHERE id = %s", date(2000, 1, 1), session_id
    )
    await run_bulk()
    assert [row[:3] for row in zips(session_id)] == [("failed", "data_deleted", None)]
    assert embedding["data"] == [] and not list(files.rglob("*.zip"))


def test_file_names_find_a_student_and_never_clash():
    a, b, c, d = (uuid.UUID(int=n) for n in (1, 2, 3, 4))
    names = {a: "Kari Nordmann", b: "kari nordmann", c: "Ås/Øye: «Bø»?"}
    found = bundle.file_names(names, [a, b, c, d])
    assert found[a] == f"Kari Nordmann ({a.hex[-8:]}).pdf"
    assert found[b] == f"kari nordmann ({b.hex[-8:]}).pdf"
    assert found[c] == "Ås-Øye- «Bø».pdf"
    assert found[d] == f"Student {d.hex[-8:]}.pdf"  # no name now
    assert len(set(found.values())) == 4


@pytest.mark.slow
@pytest.mark.long
async def test_a_zip_of_250_students_is_ready_within_ten_minutes(klass, monkeypatch, files):
    """The placeholder target (FR-59), on 250 generated Students and the fast fake converter.
    About 15 s: run in CI only (`slow`), or locally with `RUN_SLOW=1`."""
    session_id = await new_session(klass)
    for n in range(250):
        student = uuid.uuid7()
        execute(
            "INSERT INTO users (id, email, name) VALUES (%s, %s, %s)",
            student,
            f"z{n}@x.no",
            f"Student Nummer {n}",
        )
        execute(
            "INSERT INTO roster_entries (id, class_id, email, user_id, registration, added_at) "
            "VALUES (gen_random_uuid(), %s, %s, %s, 'registered', now())",
            klass,
            f"z{n}@x.no",
            student,
        )

    async def fast(url: str) -> bytes:
        parts = urlsplit(url)
        read = await snapshot.read(parts.path.rsplit("/", 1)[1], parse_qs(parts.query)["token"][0])
        assert read is not None
        return b"%PDF-1.7\n"

    monkeypatch.setattr(render, "to_pdf", fast)
    assert (await press(session_id)).status_code == 202
    assert await run_bulk() < 600
    [(status, _, _, students, _)] = zips(session_id)
    assert (status, students) == ("ready", 250)
    assert len((await opened(await file(session_id))).namelist()) == 250


async def test_one_failed_report_fails_the_whole_zip_and_a_student_left_out_is_skipped(
    klass, monkeypatch, files, embedding
):
    """Never a partial ZIP; a Student who stops being reportable meanwhile is left out."""
    session_id = await locked(klass, monkeypatch, n=2)
    good, build_data = render.to_pdf, report_data.build_report_data
    calls = {"n": 0}

    async def second_fails(url: str) -> bytes:
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("one report failed")
        return await good(url)

    monkeypatch.setattr(render, "to_pdf", second_fails)
    assert (await press(session_id)).status_code == 202
    await run_bulk()
    assert [row[:2] for row in zips(session_id)] == [("failed", "render_failed")]
    assert snapshots() == 0 and not list(files.rglob("*.zip"))

    monkeypatch.setattr(render, "to_pdf", good)
    gone = user_id(email(1))

    async def one_left_out(s, student, *args, **kw):
        if student == gone:
            raise report_data.NotReportable
        return await build_data(s, student, *args, **kw)

    monkeypatch.setattr(bundle, "build_report_data", one_left_out)
    assert (await press(session_id)).status_code == 202
    await run_bulk()
    [_, (status, _, _, students, _)] = zips(session_id)
    assert (status, students) == ("ready", 1)
    assert len((await opened(await file(session_id))).namelist()) == 1


async def test_while_a_new_zip_is_made_or_failed_the_earlier_one_stays_downloadable(
    klass, monkeypatch, files, embedding
):
    session_id = await locked(klass, monkeypatch, n=2)
    assert (await press(session_id)).status_code == 202
    await run_bulk()
    made = (await state(session_id)).json()
    pending = (await press(session_id)).json()
    assert (pending["status"], pending["generated_at"], pending["students"]) == (
        "pending",
        made["generated_at"],
        2,
    )
    assert (await file(session_id)).status_code == 303

    async def broken(url: str) -> bytes:
        raise RuntimeError("no")

    monkeypatch.setattr(render, "to_pdf", broken)
    await run_bulk()
    failed = (await state(session_id)).json()
    assert (failed["status"], failed["generated_at"]) == ("failed", made["generated_at"])
    assert (await file(session_id)).status_code == 303


async def test_a_job_replaced_as_stale_removes_its_own_zip(klass, monkeypatch, files, embedding):
    session_id = await locked(klass, monkeypatch)
    assert (await press(session_id)).status_code == 202
    stale = get_settings().report_zip_stale_seconds + 1
    execute(f"UPDATE report_zips SET requested_at = requested_at - interval '{stale} seconds'")
    [old] = [row[0] for row in rows("SELECT id FROM report_zips")]
    assert (await press(session_id)).status_code == 202  # replaces the stale one
    # The old job still runs to its end: no longer pending, it takes its object away.
    assert await bundle.build(old) == "skipped"
    assert not list(files.rglob("*.zip"))
    await run_bulk()
    assert [row[0] for row in zips(session_id)] == ["failed", "ready"]
    assert len(list(files.rglob("*.zip"))) == 1


def test_the_ready_notice_is_an_immediate_mail_without_a_link_or_student_data():
    """Story 13.13 (AD-9): the requester waits for it, so it leaves at once."""
    kind = sessions.REPORTS_ZIP_READY_NOTICE
    assert delivery.REPORTS_ZIP_READY_KIND == kind
    assert delivery.KINDS[kind].mode == delivery.IMMEDIATE
    context = {"class_name": "Logistikk", "session_number": 2}
    mail = render_mail(
        Recipient("a@x.no", context=context), [Section(delivery.KINDS[kind].template)], digest=False
    )
    assert mail.subject == "ZIP-filen med Studentrapportene er klar"
    assert "Klasseøkt 2 i Klassen Logistikk" in mail.text and "«Eksport»" in mail.html
    assert "reports/zip" not in mail.text and "storage" not in mail.text  # no link to the file


async def test_the_mail_context_names_the_class_session(klass, monkeypatch):
    session_id = await locked(klass, monkeypatch)
    from app.platform.db import get_sessionmaker

    async with get_sessionmaker()() as s:
        found = await sessions.reports_zip_mail_context(
            s, user_id(LECTURER), uuid.UUID(session_id), None
        )
        missing = await sessions.reports_zip_mail_context(s, user_id(LECTURER), uuid.uuid7(), None)
    assert found is not None and found["session_number"] == 1 and found["class_name"]
    assert missing is None
