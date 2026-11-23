"""The Admin exports pseudonymised data for evaluation (Story 15.4, FR-71, FR-67, FR-77, AD-12,
AD-13, AD-14, AD-15). Through the api: an agreement is recorded per Class session, the key is typed
in the run, only its fingerprint is stored, a changed key is refused, every Student is the same
`HMAC(key, user_id)` across files and runs, a Lecturer's test Game is left out, and no name,
address or key is left anywhere. The api's clock is fixed; the database clock is never compared
with it."""

import csv
import io
import json
import logging
import unicodedata
import uuid
import zipfile

import psycopg
import pytest

from app.ai import calls as ai_calls
from app.engine.settings import GameSettings
from app.modules.games import commands as games_commands
from app.modules.identity.schemas import AccountRole
from app.modules.ops import evaluation
from app.platform import retention
from tests.classes.test_classes import LECTURER, as_user, make
from tests.classes.test_invitation_counts import execute
from tests.identity.helpers import CSRF, client
from tests.identity.test_user_delete import everywhere, user_id_of
from tests.messaging.helpers import rows
from tests.sessions.test_dates import TEST
from tests.sessions.test_lock import dated
from tests.sessions.test_play import played_to, running
from tests.sessions.test_student_home import _empty, clock, klass

__all__ = ["_empty", "clock", "klass"]

ADMIN = "admin154@example.com"
KEY = "Nøkkelholder-K7q2-evaluering-2026-wXyZ-0123456789"
OTHER_KEY = "En-helt-annen-nøkkel-for-evaluering-abcdefghij"
EXPLANATION = "Jeg bestilte for mye fordi etterspørselen så ut til å stige."
AGREEMENT = {
    "agreed_by": "Prorektor for utdanning",
    "agreed_on": "2026-11-01",
    "controller": "Høgskolen, ved prorektor",
}
BASE = "/api/admin/evaluation"


@pytest.fixture
async def admin(klass) -> uuid.UUID:
    execute("DELETE FROM pseudonym_key_fingerprints")
    return await make(ADMIN, roles=(AccountRole.admin,))


async def call(method: str, path: str, who: str = ADMIN, **kwargs):
    async with client() as c:
        await as_user(c, who)
        return await c.request(method, f"{BASE}{path}", headers=CSRF, **kwargs)


async def agree(session_id: str, **changes):
    return await call(
        "PUT", f"/class-sessions/{session_id}/agreement", json={**AGREEMENT, **changes}
    )


async def export(*session_ids: str, key: str = KEY, who: str = ADMIN):
    return await call(
        "POST", "/exports", who, json={"class_session_ids": list(session_ids), "key": key}
    )


def files(response) -> dict[str, list[dict[str, str]]]:
    """Each CSV of the ZIP as rows by column, and the manifest under its own name."""
    found: dict = {}
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        for name in archive.namelist():
            text = archive.read(name).decode()
            found[name] = (
                json.loads(text)
                if name.endswith(".json")
                else list(csv.DictReader(io.StringIO(text)))
            )
    return found


def runs() -> list[tuple]:
    return rows(
        "SELECT actor_user_id, change FROM audit_events "
        "WHERE action = 'evaluation_export.run' ORDER BY occurred_at, id"
    )


def plant_explanation(user_id: uuid.UUID, session_id: str, game_id: str) -> None:
    execute(
        "INSERT INTO debrief_explanations (user_id, class_session_id, game_id, text, length, "
        "saved_at) VALUES (%s, %s, %s, %s, %s, now())",
        user_id,
        session_id,
        game_id,
        EXPLANATION,
        len(EXPLANATION),
    )


def plant_starting_task(user_id: uuid.UUID, session_id: str) -> None:
    execute(
        "INSERT INTO starting_task_answers (id, user_id, class_session_id, content_version, "
        "item_id, answer, correct, answered_at) VALUES (%s, %s, %s, 1, 'q1', 12, true, now())",
        uuid.uuid7(),
        user_id,
        session_id,
    )


LONG_ANSWER = "=Ordrene svinger fordi hvert ledd ser bare sine egne bestillinger."
ITEMS = [
    {"id": "valg-1", "type": "choice", "weight": 10},
    {"id": "tabell-1", "type": "table", "weight": 20},
    {"id": "langsvar-1", "type": "long", "weight": 30},
]


def plant_test_answers(user_id: uuid.UUID, session_id: str) -> None:
    """A handed-in Individual test attempt with a choice, a table and a long answer."""
    attempt = uuid.uuid7()
    execute(
        "INSERT INTO test_attempts (id, user_id, class_session_id, question_set_version, "
        "selection, items, statement_accepted_at, status, submitted_at) VALUES (%s, %s, %s, 2, "
        "'{}', %s, now(), 'submitted', now())",
        attempt,
        user_id,
        session_id,
        json.dumps(ITEMS),
    )
    for item_id, value, score in (
        ("valg-1", "b", {"points": 1}),
        ("tabell-1", [3, None, 5], {"points": 2}),
        ("langsvar-1", LONG_ANSWER, None),
    ):
        execute(
            "INSERT INTO test_answers (id, attempt_id, item_id, value, revision, saved_at, score, "
            "scored_version) VALUES (%s, %s, %s, %s, 1, now(), %s, %s)",
            uuid.uuid7(),
            attempt,
            item_id,
            json.dumps(value),
            None if score is None else json.dumps(score),
            None if score is None else 2,
        )


@pytest.mark.long
async def test_an_agreed_export_gives_each_student_one_pseudonym_and_no_name(
    klass, admin, caplog, capsys
):
    caplog.set_level(logging.DEBUG)
    session_id, game_id, by_role = await running(klass, students=2)
    await played_to(game_id, list(by_role), 3)
    (gone_role, gone_address), (stay_role, stay_address) = sorted(by_role.items())
    await games_commands.takeover(
        game_id, gone_role, actor="staff", actor_user_id=user_id_of(LECTURER)
    )
    await games_commands.view_week(game_id, stay_role, 3, actor=user_id_of(stay_address))
    ids = {address: user_id_of(address) for address in by_role.values()}
    for user_id in ids.values():
        plant_explanation(user_id, session_id, game_id)
        plant_starting_task(user_id, session_id)
        plant_test_answers(user_id, session_id)
    # A Lecturer's test Game in the same Class session, played to its end by AI players, and an
    # Explanation of the Lecturer in it: neither is a reporting Game (AD-13).
    lecturer = user_id_of(LECTURER)
    test_game = await games_commands.create(
        "lecturer_test",
        GameSettings(weeks=6, guided_weeks=1),
        class_session_id=uuid.UUID(session_id),
    )
    await games_commands.start(test_game)
    plant_explanation(lecturer, session_id, test_game)
    plant_starting_task(lecturer, session_id)
    plant_test_answers(lecturer, session_id)

    recorded = await agree(session_id)
    assert recorded.status_code == 200, recorded.text
    body = recorded.json()
    assert body["agreement"]["agreed_by"] == AGREEMENT["agreed_by"]
    assert body["deletion_date"] == retention.deletion_date(TEST, 6).isoformat()
    [(targets, change)] = rows(
        "SELECT target_ids, change FROM audit_events WHERE action = 'evaluation_agreement.recorded'"
    )
    assert (targets, change) == ({"class_session_id": session_id}, {"agreed_on": "2026-11-01"})
    async with client() as c:
        await as_user(c, ADMIN)
        logged = (await c.get("/api/admin/audit?action=evaluation_agreement.recorded")).json()
    [target] = logged["items"][0]["targets"]
    assert target["key"] == "class_session_id"
    assert target["label"].endswith("· Klasseøkt 1")

    response = await export(session_id)
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["cache-control"] == "no-store"
    found = files(response)
    assert set(found) == {
        "decision_log.csv",
        "llm_calls.csv",
        "starting_task.csv",
        "explanations.csv",
        "test_answers.csv",
        "manifest.json",
    }
    named = {evaluation.pseudonym(KEY, user_id): user_id for user_id in ids.values()}
    log = found["decision_log.csv"]
    assert {row["game_id"] for row in log} == {game_id}  # not the test Game
    assert {row["student"] for row in log} - {""} == set(named)  # AI Seats have no Student
    assert "guided" in {row["decided_by"] for row in log}
    by_week = {(row["role"], int(row["week"])): row["student"] for row in log}
    gone_name = evaluation.pseudonym(KEY, user_id_of(gone_address))
    stay_name = evaluation.pseudonym(KEY, user_id_of(stay_address))
    assert [by_week[(gone_role, week)] for week in (1, 2, 3)] == [gone_name, gone_name, ""]
    assert [by_week[(stay_role, week)] for week in (1, 2, 3)] == [stay_name] * 3
    assert json.loads(log[0]["state_seen"])  # the state the Seat saw, as JSON
    # The Students' answers; not the Lecturer's, who holds no Seat in a reporting Game.
    assert {
        (r["student"], r["item_id"], r["answer"], r["correct"]) for r in found["starting_task.csv"]
    } == {(pseudonym, "q1", "12", "true") for pseudonym in named}
    explanations = found["explanations.csv"]
    assert {(row["student"], row["text"]) for row in explanations} == {
        (pseudonym, EXPLANATION) for pseudonym in named
    }
    # The Individual test answers (Epic 11): a long answer as written, guarded against a formula,
    # any other as JSON; the computed score, never an AI assessment (FR-71).
    answers = found["test_answers.csv"]
    assert {row["student"] for row in answers} == set(named)
    by_item = {row["item_id"]: row for row in answers if row["student"] == stay_name}
    assert (by_item["langsvar-1"]["item_type"], by_item["langsvar-1"]["answer"]) == (
        "long",
        f"'{LONG_ANSWER}",
    )
    assert by_item["tabell-1"]["answer"] == "[3,null,5]" and by_item["tabell-1"]["weight"] == "20"
    assert by_item["valg-1"]["answer"] == '"b"'
    assert json.loads(by_item["valg-1"]["score"]) == {"points": 1}
    assert not {"letter", "ai_score", "feedback"} & set(answers[0])
    assert "key_fingerprint" not in found["manifest.json"]  # no help to guess the key offline
    assert found["manifest.json"]["class_sessions"] == [
        {"id": session_id, "deletion_date": retention.deletion_date(TEST, 6).isoformat()}
    ]

    # No name, address or user id of a Student in the ZIP; only the fingerprint is stored.
    raw = b"".join(
        zipfile.ZipFile(io.BytesIO(response.content)).read(n)
        for n in zipfile.ZipFile(io.BytesIO(response.content)).namelist()
    ).decode()
    names = [
        name for (name,) in rows("SELECT name FROM users WHERE id = ANY(%s)", list(ids.values()))
    ]
    for term in [*ids, *names, *(str(user_id) for user_id in ids.values())]:
        assert term not in raw, term
    assert rows("SELECT fingerprint FROM pseudonym_key_fingerprints") == [
        (evaluation.fingerprint(KEY),)
    ]
    [(actor, change)] = runs()
    assert (actor, change) == (
        admin,
        {
            "outcome": "exported",
            "class_session_ids": [session_id],
            "key_fingerprint": evaluation.fingerprint(KEY),
        },
    )

    # The same key again: the same pseudonyms in every file.
    again = files(await export(session_id))
    for name in ("decision_log.csv", "starting_task.csv", "explanations.csv", "test_answers.csv"):
        assert again[name] == found[name], name

    # The key is nowhere: not in any table (the job tables included) and not in any log line.
    assert everywhere(KEY) == {KEY: []}
    assert KEY not in caplog.text
    captured = capsys.readouterr()
    assert KEY not in captured.out and KEY not in captured.err

    # An erased User has no pseudonym: their rows stay anonymous.
    gone = next(iter(ids.values()))
    execute("UPDATE users SET deleted_at = now() WHERE id = %s", gone)
    after = files(await export(session_id))
    assert evaluation.pseudonym(KEY, gone) not in {r["student"] for r in after["decision_log.csv"]}
    assert "" in {r["student"] for r in after["explanations.csv"]}

    # The export list: each run, newest first, with the Class session's deletion date.
    listed = (await call("GET", "/exports")).json()["items"]
    assert len(listed) == 3
    assert listed[0]["outcome"] == "exported"
    assert listed[0]["key_fingerprint"] == evaluation.fingerprint(KEY)
    assert listed[0]["actor_id"] == str(admin)
    [listed_session] = listed[0]["class_sessions"]
    assert listed_session["id"] == session_id
    assert listed_session["deletion_date"] == retention.deletion_date(TEST, 6).isoformat()


async def test_test_students_and_control_tests_are_left_out(klass, admin):
    """AD-13 through `reports.scope`: a test student (Story 12.8) is in no file, and a Control
    test's Class session (Story 12.7) gives no row at all."""
    session_id, game_id, by_role = await running(klass, students=2)
    await played_to(game_id, list(by_role), 2)
    ids = [user_id_of(address) for address in by_role.values()]
    for user_id in ids:
        plant_explanation(user_id, session_id, game_id)
        plant_starting_task(user_id, session_id)
        plant_test_answers(user_id, session_id)
    tester, student = ids
    execute("UPDATE users SET is_test_student = true WHERE id = %s", tester)
    assert (await agree(session_id)).status_code == 200

    found = files(await export(session_id))
    for name in ("decision_log.csv", "starting_task.csv", "explanations.csv", "test_answers.csv"):
        assert {row["student"] for row in found[name]} - {""} == {
            evaluation.pseudonym(KEY, student)
        }, name

    # The same Class session as a Control test (its kind never changes in the app: the trigger
    # is bypassed here) holds nothing a report counts.
    from tests.conftest import TEST_DATABASE_URL, libpq_dsn

    with psycopg.connect(libpq_dsn(TEST_DATABASE_URL)) as conn:
        conn.execute("SET LOCAL session_replication_role = replica")
        conn.execute("UPDATE class_sessions SET kind = 'control_test' WHERE id = %s", (session_id,))
    found = files(await export(session_id))
    for name in ("decision_log.csv", "starting_task.csv", "explanations.csv", "test_answers.csv"):
        assert found[name] == [], name


async def test_a_changed_key_is_refused_until_the_fingerprint_is_replaced(klass, admin):
    session_id = await dated(klass)
    assert (await agree(session_id)).status_code == 200
    assert (await call("GET", "/key")).json() == {"fingerprint": None, "set_at": None}
    assert (await export(session_id)).status_code == 200  # the first export stores it
    assert (await call("GET", "/key")).json()["fingerprint"] == evaluation.fingerprint(KEY)

    refused = await export(session_id, key=OTHER_KEY)
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "pseudonym_key_changed"
    assert OTHER_KEY not in refused.text
    assert runs()[-1][1] == {
        "outcome": "pseudonym_key_changed",
        "class_session_ids": [session_id],
        "key_fingerprint": evaluation.fingerprint(OTHER_KEY),
    }

    # Replacing the fingerprint is its own audited action; then the new key exports.
    replaced = await call("POST", "/key", json={"key": f"  {OTHER_KEY} "})
    assert replaced.status_code == 200
    assert replaced.json()["fingerprint"] == evaluation.fingerprint(OTHER_KEY)
    [(change,)] = rows("SELECT change FROM audit_events WHERE action = 'pseudonym_key.replaced'")
    assert change == {
        "old_fingerprint": evaluation.fingerprint(KEY),
        "new_fingerprint": evaluation.fingerprint(OTHER_KEY),
    }
    assert (await export(session_id, key=OTHER_KEY)).status_code == 200
    assert (await export(session_id)).status_code == 409
    before = (await call("GET", "/key")).json()
    again = await call("POST", "/key", json={"key": unicodedata.normalize("NFD", OTHER_KEY)})
    assert again.json() == before
    assert rows("SELECT count(*) FROM audit_events WHERE action = 'pseudonym_key.replaced'") == [
        (1,)
    ]
    nfd = await export(session_id, key=unicodedata.normalize("NFD", OTHER_KEY))
    assert nfd.status_code == 200
    outcomes = [item["outcome"] for item in (await call("GET", "/exports")).json()["items"]]
    assert outcomes == [
        "exported",
        "pseudonym_key_changed",
        "exported",
        "pseudonym_key_changed",
        "exported",
    ]
    assert everywhere(KEY, OTHER_KEY) == {KEY: [], OTHER_KEY: []}


async def test_without_an_agreement_or_as_a_lecturer_nothing_is_read(klass, admin):
    agreed = await dated(klass)
    unagreed = await dated(klass)
    assert (await agree(agreed)).status_code == 200

    # The Admin, with one Class session lacking an agreement: refused and audited, no key stored.
    refused = await export(agreed, unagreed)
    assert refused.status_code == 403
    assert refused.json()["error"] == {
        "code": "no_agreement",
        "message": "A chosen Class session has no Institution agreement.",
        "fields": {"class_session_ids": [unagreed]},
    }
    assert rows("SELECT count(*) FROM pseudonym_key_fingerprints") == [(0,)]
    assert [change["outcome"] for _, change in runs()] == ["no_agreement"]
    # An unknown Class session is refused alike.
    unknown = str(uuid.uuid7())
    assert (await export(unknown)).json()["error"]["fields"] == {"class_session_ids": [unknown]}

    # A Lecturer is refused by the policy before anything; no audit row.
    lecturer = await export(agreed, who=LECTURER)
    assert lecturer.status_code == 403
    assert lecturer.json()["error"]["code"] == "forbidden"
    for path in ("/class-sessions", "/exports", "/key"):
        assert (await call("GET", path, LECTURER)).status_code == 403
    assert len(runs()) == 2

    # A short key or no Class session: the field only, never the value; nothing audited.
    short = await export(agreed, key="kort")
    assert (short.status_code, short.json()["error"]["fields"]) == (422, {"key": "too_short"})
    assert "kort" not in short.text
    assert (await export()).status_code == 422
    assert (await export(*(str(uuid.uuid7()) for _ in range(21)))).status_code == 422
    assert len(runs()) == 2

    # The agreement form: a date in the future and an unknown Class session are refused.
    future = await agree(agreed, agreed_on="2030-01-01")
    assert (future.status_code, future.json()["error"]["fields"]) == (
        422,
        {"agreed_on": "in_future"},
    )
    assert (await agree(unknown)).status_code == 404
    assert (await agree(agreed, controller="  ")).status_code == 422
    assert (await agree(agreed, controller="Ny behandlingsansvarlig")).status_code == 200
    assert rows(
        "SELECT count(*) FROM audit_events WHERE action = 'evaluation_agreement.recorded'"
    ) == [(2,)]
    listed = {item["id"]: item for item in (await call("GET", "/class-sessions")).json()["items"]}
    assert listed[agreed]["agreement"]["controller"] == "Ny behandlingsansvarlig"
    assert listed[unagreed]["agreement"] is None


async def test_the_call_metadata_reads_only_the_listed_columns(klass):
    """The `llm_calls.csv` query runs and names no body, caller reference or error text."""
    columns, found = await ai_calls.export_metadata([uuid.uuid7()])
    assert found == []
    assert not {"request", "response", "error", "caller_ref"} & set(columns)
