"""The Klasserapport's learning part (Story 14.2, FR-64, FR-55, FR-56, FR-61, FR-63, FR-5, AD-1,
AD-10, AD-12, AD-13): `GET /api/class-sessions/{id}/class-report/learning` answers the Class's
owners with the Starting task beside the matching test items, results per question and the AI
assessment totals with the Core-only subscore, over the reporting Students; everyone else gets one
403. The Students' Starting task answers, attempts, saved answers and assessments are written
straight to the tables (the stories that write them have their own tests), so the tests stay
fast."""

import json
import uuid
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import event

from app.analysis.total import core_total_score, total_score
from app.modules.content import service as content
from app.modules.identity.schemas import AccountRole
from app.modules.reports import class_report_learning
from app.platform.db import get_engine
from tests.classes.test_classes import LECTURER, OTHER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_staff import ASSISTANT, call, put_staff
from tests.debrief.test_explanation import user_id
from tests.sessions.test_dates import TEST, at
from tests.sessions.test_game_end import _empty, clock, emitted, klass
from tests.sessions.test_open_games import confirmed
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "emitted", "klass"]

ADMIN = "admin-learning@x.no"
SENDE, RESTORDRE = "startoppgave-sende", "startoppgave-restordre"
CHOICE, LONG = "flervalg-forklaring", "langsvar-forsinkelse"
OWN, REPLAY = "tilpasset-eget-spill", "tilpasset-replay"
TO_SHIP, BACKLOG = "to-ship", "backlog"
"""The Starting task items the test items `SENDE` and `RESTORDRE` name."""


async def learning(who: str, session_id: str):
    return await call(who, "GET", f"/api/class-sessions/{session_id}/class-report/learning")


async def question_set():
    version, found = await content.question_set(None)
    return version, found


async def frozen(adapted: bool = True) -> tuple[int, list[dict]]:
    """The default selection's frozen items: every Core item, then the two Adapted items (15 and
    15) or the replacement items with `replaces`."""
    version, found = await question_set()
    items = [{"id": i.id, "type": i.type, "weight": i.weight} for i in found.items]
    if adapted:
        items += [
            {"id": OWN, "type": "adapted", "weight": 15},
            {"id": REPLAY, "type": "adapted", "weight": 15},
        ]
    else:
        items += [
            {"id": i.id, "type": i.type, "weight": i.weight, "replaces": "few_orders"}
            for i in found.replacements
        ]
    return version, items


def starting(session_id: str, who: int, answers: dict[str, bool], done: bool = True) -> None:
    for item_id, correct in answers.items():
        execute(
            "INSERT INTO starting_task_answers (id, user_id, class_session_id, content_version, "
            "item_id, answer, correct, answered_at) VALUES (%s, %s, %s, 1, %s, 1, %s, now())",
            uuid.uuid7(),
            user_id(email(who)),
            session_id,
            item_id,
            correct,
        )
    if done:
        execute(
            "INSERT INTO starting_task_answers (id, user_id, class_session_id, content_version, "
            "item_id, choice, answered_at) VALUES (%s, %s, %s, 1, 'played_before', 'no', now())",
            uuid.uuid7(),
            user_id(email(who)),
            session_id,
        )


async def attempt(
    session_id: str,
    who: int,
    credits: dict[str, float | None],
    *,
    status: str = "submitted",
    closed: bool = True,
    adapted: bool = True,
    texts: dict[str, str] | None = None,
) -> uuid.UUID:
    """A Student's attempt with saved answers: each computed item of `credits` scored with that
    credit (None: saved but scored as not answered), each item of `texts` a saved text."""
    version, items = await frozen(adapted)
    attempt_id = uuid.uuid7()
    execute(
        "INSERT INTO test_attempts (id, user_id, class_session_id, question_set_version, "
        "selection, items, statement_accepted_at, effective_deadline, status, submitted_at, "
        "closed_at) VALUES (%s, %s, %s, %s, '{}', %s, now(), %s, %s, %s, %s)",
        attempt_id,
        user_id(email(who)),
        session_id,
        version,
        json.dumps(items),
        TEST,
        status,
        None if status == "open" else TEST,
        TEST if closed and status != "open" else None,
    )
    for item_id, credit in credits.items():
        score = {"answered": credit is not None, "credit": credit or 0.0, "criteria": []}
        execute(
            "INSERT INTO test_answers (id, attempt_id, item_id, value, revision, saved_at, score, "
            "scored_version) VALUES (%s, %s, %s, %s, 1, now(), %s, %s)",
            uuid.uuid7(),
            attempt_id,
            item_id,
            json.dumps(16 if credit is not None else None),
            json.dumps(score),
            version,
        )
    for item_id, text in (texts or {}).items():
        execute(
            "INSERT INTO test_answers (id, attempt_id, item_id, value, revision, saved_at) "
            "VALUES (%s, %s, %s, %s, 1, now())",
            uuid.uuid7(),
            attempt_id,
            item_id,
            json.dumps(text),
        )
    return attempt_id


async def assessed(
    session_id: str, who: int, attempt_id: uuid.UUID, steps: dict[str, int], status: str = "ready"
) -> None:
    version, _ = await question_set()
    assessment_id = uuid.uuid7()
    execute(
        "INSERT INTO ai_assessments (id, attempt_id, class_session_id, user_id, status, runs, "
        "question_set_version, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, 1, %s, now(), "
        "now())",
        assessment_id,
        attempt_id,
        session_id,
        user_id(email(who)),
        status,
        version,
    )
    for item_id, step in steps.items():
        execute(
            "INSERT INTO ai_item_scores (assessment_id, item_id, score, source, "
            "question_set_version, created_at) VALUES (%s, %s, %s, 'blank', %s, now())",
            assessment_id,
            item_id,
            step,
            version,
        )


def all_steps(step: int, adapted: bool = True) -> dict[str, int]:
    found = {LONG: step, "langsvar-informasjon": step}
    return found | ({OWN: step, REPLAY: step} if adapted else {})


async def full_credits(credit: float) -> dict[str, float | None]:
    _, found = await question_set()
    return {i.id: credit for i in found.items if i.type != "long"}


def question(body: dict, item_id: str) -> dict:
    return next(row for row in body["questions"] if row["id"] == item_id)


async def test_nobody_handed_in_reads_counts_questions_and_not_ready(klass):
    session_id, _ = await confirmed(klass, 2)
    await attempt(session_id, 0, {}, status="open")
    response = await learning(LECTURER, session_id)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert (body["students"], body["submitted"], body["still_to_submit"]) == (2, 0, 2)
    assert body["starting_task"]["students"] == 0
    assert [row["students"] for row in body["starting_task"]["items"]] == [0, 0, 0]
    _, found = await question_set()
    assert [row["id"] for row in body["questions"]] == [i.id for i in found.items]
    assert [row["number"] for row in body["questions"]] == list(range(1, len(found.items) + 1))
    assert {row["students"] for row in body["questions"]} == {0}
    assert body["ai"] == {
        "state": "not_ready",
        "ready": 0,
        "submitted": 0,
        "total": None,
        "core": None,
        "bands": [],
    }


async def test_handed_in_tests_fill_every_figure_with_no_identifier(klass):
    session_id, _ = await confirmed(klass, 3)
    # Student 0 did both, every computed item right except the Starting-task item `restordre`.
    starting(session_id, 0, {TO_SHIP: True, BACKLOG: False})
    credits = await full_credits(1.0) | {RESTORDRE: 0.0, "tabell-nytt-monster": 0.5}
    first = await attempt(session_id, 0, credits, texts={LONG: "Fordi forsinkelsen.", OWN: " "})
    await assessed(session_id, 0, first, all_steps(2))
    # Student 1 did only the Starting task; Student 2 handed in with replacement items, no
    # Starting task, and their assessment is not ready.
    starting(session_id, 1, {TO_SHIP: False, BACKLOG: True})
    second = await attempt(session_id, 2, {CHOICE: 0.0}, adapted=False)
    await assessed(session_id, 2, second, {LONG: 1}, status="incomplete")
    response = await learning(LECTURER, session_id)
    assert response.status_code == 200
    body = response.json()
    assert (body["students"], body["submitted"], body["still_to_submit"]) == (3, 2, 1)

    assert body["starting_task"]["students"] == 1
    sende, restordre = body["starting_task"]["items"][:2]
    assert (sende["number"], sende["students"], sende["start_correct"]) == (1, 1, 1)
    assert (sende["start_percent"], sende["test_right"], sende["test_percent"]) == (
        "100.0",
        1,
        "100.0",
    )
    assert (restordre["start_correct"], restordre["start_percent"]) == (0, "0.0")
    assert (restordre["test_right"], restordre["test_percent"]) == (0, "0.0")

    choice = question(body, CHOICE)
    assert (choice["students"], choice["answered"], choice["right"], choice["wrong"]) == (
        2,
        2,
        1,
        1,
    )
    assert (choice["scoring"], choice["percent"]) == ("computed", "50.0")
    table = question(body, "tabell-nytt-monster")
    assert (table["answered"], table["partly"], table["not_answered"]) == (1, 1, 1)
    assert table["percent"] == "25.0"
    long = question(body, LONG)
    assert (long["scoring"], long["answered"], long["percent"], long["right"]) == ("ai", 1, None, 0)
    assert body["adapted"] == {"weight": 30, "adapted": 1, "replaced": 1}

    _, items = await frozen()
    weights = {item["id"]: item["weight"] for item in items}
    computed = {i: credits.get(i, 0.0) for i in weights if i not in all_steps(2)}
    total = total_score(computed, all_steps(2), weights)
    core = core_total_score(
        computed, all_steps(2), weights, [i for i in weights if i not in (OWN, REPLAY)]
    )
    assert total is not None and core is not None
    ai = body["ai"]
    assert (ai["state"], ai["ready"], ai["submitted"]) == ("ready", 1, 2)
    assert ai["total"]["values"] == [str(Decimal(str(total)).quantize(Decimal("0.1")))]
    assert ai["core"]["median"] == str(Decimal(str(core)).quantize(Decimal("0.1")))
    assert sum(band["total"] for band in ai["bands"]) == 1
    assert sum(band["core"] for band in ai["bands"]) == 1
    # A group of one is shown with its count (FR-63), and nothing in the answer names anyone.
    text = response.text
    for who in range(3):
        assert str(user_id(email(who))) not in text
    for attempt_id in (first, second):
        assert str(attempt_id) not in text
    assert "Fordi" not in text and "letter" not in text


async def test_a_question_taken_out_is_listed_as_such_and_left_out(klass):
    session_id, _ = await confirmed(klass, 1)
    version, found = await question_set()
    weights = {i.id: i.weight for i in found.items}
    weights[SENDE] += weights.pop("flervalg-arsaker")
    weights["flervalg-arsaker"] = 0
    execute(
        "INSERT INTO test_selections (class_session_id, question_set_version, excluded, weights, "
        "adapted_weight, updated_at) VALUES (%s, %s, %s, %s, 30, now())",
        session_id,
        version,
        ["flervalg-arsaker"],
        json.dumps(weights),
    )
    await attempt(session_id, 0, {CHOICE: 1.0, "flervalg-arsaker": 1.0})
    body = (await learning(LECTURER, session_id)).json()
    out = question(body, "flervalg-arsaker")
    assert out == out | {
        "excluded": True,
        "scoring": "excluded",
        "number": None,
        "weight": None,
        "students": 0,
        "answered": 0,
        "percent": None,
    }
    numbers = [row["number"] for row in body["questions"] if not row["excluded"]]
    assert numbers == list(range(1, len(found.items)))
    assert question(body, SENDE)["weight"] == weights[SENDE]


async def test_a_student_with_an_extension_is_still_to_submit_after_the_class_deadline(
    klass, monkeypatch
):
    session_id, _ = await confirmed(klass, 3)
    execute(
        "INSERT INTO student_deadline_extensions (class_session_id, user_id, test_deadline, "
        "updated_at) VALUES (%s, %s, %s, now())",
        session_id,
        user_id(email(0)),
        TEST + timedelta(days=2),
    )
    await attempt(session_id, 2, {}, status="auto_submitted")
    at(monkeypatch, TEST + timedelta(hours=1))
    body = (await learning(LECTURER, session_id)).json()
    # Student 0 has their own later deadline; Student 1's has passed; Student 2 handed in.
    assert (body["submitted"], body["still_to_submit"]) == (1, 1)


async def test_the_ai_part_says_switched_off_and_the_computed_parts_stay(klass):
    session_id, _ = await confirmed(klass, 1)
    execute(
        "INSERT INTO assessment_switches (class_session_id, enabled) VALUES (%s, false)",
        session_id,
    )
    await attempt(session_id, 0, {CHOICE: 1.0})
    body = (await learning(LECTURER, session_id)).json()
    assert (body["ai"]["state"], body["ai"]["total"], body["ai"]["bands"]) == (
        "switched_off",
        None,
        [],
    )
    assert question(body, CHOICE)["percent"] == "100.0"


async def test_an_assessment_missing_an_item_score_is_not_ready(klass):
    session_id, _ = await confirmed(klass, 2)
    first = await attempt(session_id, 0, await full_credits(1.0))
    await assessed(session_id, 0, first, {LONG: 4})  # `ready` with three AI items unscored
    second = await attempt(session_id, 1, await full_credits(0.0), closed=False)
    await assessed(session_id, 1, second, all_steps(4))  # handed in early, not closed yet
    body = (await learning(LECTURER, session_id)).json()
    assert (body["ai"]["state"], body["ai"]["ready"], body["ai"]["submitted"]) == (
        "not_ready",
        0,
        2,
    )


def test_bands_hold_their_lower_bound_and_100_in_the_last():
    found = class_report_learning.bands([0.0, 9.99, 10.0, 99.9, 100.0], [55.5])
    assert [(b.low, b.total, b.core) for b in found if b.total or b.core] == [
        (0, 2, 0),
        (10, 1, 0),
        (50, 0, 1),
        (90, 2, 0),
    ]
    assert class_report_learning.mean_percent([1.0, 0.0, 0.35]) == Decimal("45.0")
    assert class_report_learning.mean_percent([]) is None


async def test_a_control_test_class_session_counts_no_student(klass, monkeypatch):
    session_id, _ = await confirmed(klass, 1)
    await attempt(session_id, 0, {CHOICE: 1.0})

    async def control_test(class_session_id, *, session=None):
        return class_report_learning.sessions.CONTROL_TEST

    monkeypatch.setattr(class_report_learning.sessions, "kind_of", control_test)
    body = (await learning(LECTURER, session_id)).json()
    assert (body["students"], body["submitted"], question(body, CHOICE)["students"]) == (0, 0, 0)


async def test_only_the_lecturers_of_the_class_read_it(klass):
    session_id, _ = await confirmed(klass, 1)
    await make(ADMIN, roles=(AccountRole.admin,))
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")
    refused = [
        await learning(ASSISTANT, session_id),
        await learning(email(0), session_id),
        await learning(OTHER, session_id),
        await learning(ADMIN, session_id),
        await learning(LECTURER, str(uuid.uuid7())),
        await learning(LECTURER, "not-an-id"),
    ]
    assert {r.status_code for r in refused} == {403}
    assert len({r.content for r in refused}) == 1
    assert (await learning(LECTURER, session_id)).status_code == 200


async def test_the_read_takes_a_fixed_number_of_queries_whatever_the_number_of_students(klass):
    session_id, _ = await confirmed(klass, 12)
    engine = get_engine().sync_engine
    statements: list[str] = []

    def record(conn, cursor, statement, *rest) -> None:
        statements.append(statement)

    for who in range(2):
        found = await attempt(session_id, who, {CHOICE: 1.0})
        await assessed(session_id, who, found, all_steps(3))
    event.listen(engine, "before_cursor_execute", record)
    try:
        statements.clear()
        few = await learning(LECTURER, session_id)
        with_few = len(statements)
        for who in range(2, 12):
            starting(session_id, who, {TO_SHIP: True})
            found = await attempt(session_id, who, {CHOICE: 0.5}, texts={LONG: "Svar"})
            await assessed(session_id, who, found, all_steps(1))
        statements.clear()
        many = await learning(LECTURER, session_id)
        with_many = len(statements)
    finally:
        event.remove(engine, "before_cursor_execute", record)
    assert (few.json()["ai"]["ready"], many.json()["ai"]["ready"]) == (2, 12)
    assert with_many == with_few


async def test_blank_long_answers_and_empty_tables_are_not_answered(klass):
    """The SQL content rule matches `service._has_content`: blank text, JSON null and an all-empty
    table hold no content."""
    session_id, _ = await confirmed(klass, 4)
    for who, text in enumerate(["   ", "\n\t", "Et svar"]):
        await attempt(session_id, who, {}, texts={LONG: text})
    await attempt(session_id, 3, {"tabell-annen-bransje": None})  # stored as JSON null
    execute("UPDATE test_answers SET value = '[null, null]' WHERE item_id = 'tabell-annen-bransje'")
    long = question((await learning(LECTURER, session_id)).json(), LONG)
    assert (long["students"], long["answered"]) == (4, 1)


async def test_a_ready_test_with_replacement_items_scores_them_in_the_total_only(klass):
    other, _ = await confirmed(klass, 1)
    credits = await full_credits(1.0)
    found = await attempt(other, 0, credits, adapted=False)
    _, version = await question_set()
    steps = {LONG: 4, "langsvar-informasjon": 4} | {
        i.id: 0 for i in version.replacements if i.type == "long"
    }
    await assessed(other, 0, found, steps)
    ai = (await learning(LECTURER, other)).json()["ai"]
    _, items = await frozen(adapted=False)
    weights = {item["id"]: item["weight"] for item in items}
    replaced = {item["id"] for item in items if item.get("replaces")}
    computed = {i: credits.get(i, 0.0) for i in weights if i not in steps}
    core = core_total_score(computed, steps, weights, [i for i in weights if i not in replaced])
    total = core_total_score(computed, steps, weights, weights)
    assert core is not None and total is not None and core != total
    assert ai["core"]["values"] == [str(Decimal(str(core)).quantize(Decimal("0.1")))]
    assert ai["total"]["values"] == [str(Decimal(str(total)).quantize(Decimal("0.1")))]
