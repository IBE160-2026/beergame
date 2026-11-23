"""Score Control test answers blind (Story 12.9, FR-82, AD-12, AD-15, AD-27).

The Admin names scorers among the existing Users of one Control test (audited). After its Test
deadline a named scorer reads a neutral list of the long-answer and Adapted answers of the closed
attempts («Svar N», no name or address), opens one (question, original text, an Adapted item's
facts, the pinned Scoring guide entry and scale, no AI score) and submits a step once into
`human_scores`; only then that answer's AI step shows to them. The Admin reads (each read audited)
but scores only when named; everyone else is refused alike. Attempts, answers and AI scores are
seeded by SQL; the api's clock is fixed and moved by hand."""

import json
import uuid
from datetime import timedelta

import psycopg
import pytest

from app.modules.identity.schemas import AccountRole
from app.modules.tests.blind import _ref
from tests.assessment.test_assess import stored_facts
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_staff import call
from tests.individual_test.test_adapted import OWN, TEMPLATES, stored_set
from tests.messaging.helpers import rows
from tests.sessions.test_control_test import ADMIN, ADMIN_LECTURER, STUDENT, control, people
from tests.sessions.test_dates import at, new_session
from tests.sessions.test_test_students import enrol

__all__ = ["clock", "control", "klass", "people"]

LONG = ("langsvar-forsinkelse", "langsvar-informasjon")
DEADLINE = NOW + timedelta(days=30)
AFTER = DEADLINE + timedelta(hours=1)
SCORER = "sensor@x.no"
OTHER_SCORER = "sensor2@x.no"


@pytest.fixture(autouse=True)
def _empty(ai_db, games_db):
    """No model config, budget or game but what a test adds."""


def scorers_url(session_id: str) -> str:
    return f"/api/admin/control-tests/{session_id}/scorers"


def list_url(session_id: str) -> str:
    return f"/api/scoring/{session_id}"


def item_url(session_id: str, ref: str) -> str:
    return f"{list_url(session_id)}/answers/{ref}"


def audits(action: str) -> list[tuple]:
    return rows(
        "SELECT actor_user_id, target_ids, change FROM audit_events WHERE action = %s "
        "ORDER BY occurred_at, id",
        action,
    )


def user_id(email: str) -> uuid.UUID:
    return rows("SELECT id FROM users WHERE email = %s", email)[0][0]


def answer_id_of(ref: str) -> uuid.UUID:
    """The stored answer a scorer's `ref` names."""
    found = [a for (a,) in rows("SELECT id FROM test_answers") if _ref(a) == ref]
    assert len(found) == 1
    return found[0]


def question_set_version() -> int:
    [(version,)] = rows("SELECT max(version) FROM content_records WHERE kind = 'question_set'")
    return version


def attempt(
    session_id: str,
    student: uuid.UUID,
    answers: dict[str, str],
    *,
    fact_set_id: str | None = None,
    closed: bool = True,
) -> uuid.UUID:
    """A Test attempt of the Control test with the two long items and one Adapted item frozen and
    `answers` saved (item id → text), closed at the deadline unless `closed` is false."""
    items = [
        {"id": LONG[0], "type": "long", "weight": 10},
        {"id": LONG[1], "type": "long", "weight": 10},
        {"id": "valg-1", "type": "choice", "weight": 5},
        {
            "id": OWN,
            "type": "adapted",
            "weight": 15,
            "text": {"text": "Hvorfor bestilte du mye i Uke 6?", "ai_generated": False},
            "fact_set_id": fact_set_id,
            "template_version": TEMPLATES,
            "fact_ids": [],
        },
    ]
    attempt_id = uuid.uuid7()
    execute(
        "INSERT INTO test_attempts (id, user_id, class_session_id, question_set_version, "
        "selection, items, statement_accepted_at, effective_deadline, status, submitted_at, "
        "closed_at) VALUES (%s, %s, %s, %s, '{}'::jsonb, %s::jsonb, %s, %s, %s, %s, %s)",
        attempt_id,
        student,
        session_id,
        question_set_version(),
        json.dumps(items),
        NOW,
        DEADLINE,
        "auto_submitted" if closed else "open",
        DEADLINE if closed else None,
        DEADLINE if closed else None,
    )
    for item_id, text in answers.items():
        execute(
            "INSERT INTO test_answers (id, attempt_id, item_id, value, revision, saved_at) "
            "VALUES (%s, %s, %s, %s::jsonb, 1, %s)",
            uuid.uuid7(),
            attempt_id,
            item_id,
            json.dumps(text),
            NOW,
        )
    return attempt_id


def ai_scores(session_id: str, attempt_id: uuid.UUID, student: uuid.UUID, scores: dict) -> None:
    """The AI's stored steps of the attempt (a ready assessment)."""
    assessment_id = uuid.uuid7()
    execute(
        "INSERT INTO ai_assessments (id, attempt_id, class_session_id, user_id, status, runs, "
        "question_set_version, created_at, updated_at) VALUES (%s, %s, %s, %s, 'ready', 1, %s, "
        "%s, %s)",
        assessment_id,
        attempt_id,
        session_id,
        student,
        question_set_version(),
        AFTER,
        AFTER,
    )
    for item_id, step in scores.items():
        execute(
            "INSERT INTO ai_item_scores (assessment_id, item_id, score, source, llm_call_id, "
            "question_set_version, created_at, feedback) VALUES (%s, %s, %s, 'ai', %s, %s, %s, "
            "%s::jsonb)",
            assessment_id,
            item_id,
            step,
            uuid.uuid7(),
            question_set_version(),
            AFTER,
            json.dumps({"text": "KI-tilbakemelding", "ai_generated": True, "parts": []}),
        )


@pytest.fixture
async def scored(control, monkeypatch) -> dict:
    """The Control test with its Test deadline set, two consenting test students with closed
    attempts (one long answer left blank by the second) and the AI's steps, a third test student
    whose attempt is still open, and a named scorer."""
    session_id, class_id = control["id"], control["class_id"]
    execute("UPDATE class_sessions SET test_deadline = %s WHERE id = %s", DEADLINE, session_id)
    facts = stored_set(range(1, 13), uuid.uuid7())
    stored_facts(monkeypatch, {"own": facts})
    first = await enrol(class_id, "ts1@x.no", "given")
    second = await enrol(class_id, "ts2@x.no", "given")
    third = await enrol(class_id, "ts3@x.no", "given")
    a1 = attempt(
        session_id,
        first,
        {
            LONG[0]: "Forsinkelsen gjør at ordrene svinger.",
            LONG[1]: "Ingen deler info.",
            OWN: "Jeg så lageret.",
        },
        fact_set_id=facts.id,
    )
    a2 = attempt(
        session_id,
        second,
        {LONG[0]: "Kjeden svinger.", LONG[1]: "   ", OWN: "Etterslep."},
        fact_set_id=facts.id,
    )
    attempt(session_id, third, {LONG[0]: "Ikke levert ennå."}, closed=False)
    ai_scores(session_id, a1, first, {LONG[0]: 3, LONG[1]: 1, OWN: 2})
    ai_scores(session_id, a2, second, {LONG[0]: 2, LONG[1]: 0, OWN: 4})
    await make(SCORER, roles=())
    await make(OTHER_SCORER, roles=(AccountRole.lecturer,))
    named = await call(ADMIN, "POST", scorers_url(session_id), json={"email": SCORER})
    assert named.status_code == 200, named.text
    return {"session": session_id, "students": [first, second, third], "facts": facts}


async def entries(session_id: str, who: str = SCORER) -> list[dict]:
    response = await call(who, "GET", list_url(session_id))
    assert response.status_code == 200, response.text
    return response.json()["entries"]


# Naming scorers.


async def test_the_admin_names_and_removes_scorers_each_audited(scored, monkeypatch):
    session_id = scored["session"]
    at(monkeypatch, AFTER)
    again = await call(
        ADMIN, "POST", scorers_url(session_id), json={"email": f" {SCORER.upper()} "}
    )
    assert again.status_code == 200  # named already: nothing written
    second = await call(ADMIN, "POST", scorers_url(session_id), json={"email": OTHER_SCORER})
    assert second.status_code == 200
    body = second.json()
    assert body["answers"] == 5
    assert [(s["email"], s["scored"]) for s in body["scorers"]] == [(SCORER, 0), (OTHER_SCORER, 0)]
    named = audits("control_test.scorer_named")
    assert [(a, t) for a, t, _ in named] == [
        (user_id(ADMIN), {"class_session_id": session_id, "user_id": str(user_id(SCORER))}),
        (user_id(ADMIN), {"class_session_id": session_id, "user_id": str(user_id(OTHER_SCORER))}),
    ]
    [first, *_] = await entries(session_id, OTHER_SCORER)
    posted = await call(OTHER_SCORER, "POST", item_url(session_id, first["ref"]), json={"score": 2})
    assert posted.status_code == 201
    removed = await call(ADMIN, "DELETE", f"{scorers_url(session_id)}/{user_id(OTHER_SCORER)}")
    assert removed.status_code == 200
    assert [s["email"] for s in removed.json()["scorers"]] == [SCORER]
    assert audits("control_test.scorer_removed") == [
        (
            user_id(ADMIN),
            {"class_session_id": session_id, "user_id": str(user_id(OTHER_SCORER))},
            {},
        )
    ]
    # A removed scorer reads nothing any more; the score they submitted stays.
    assert rows("SELECT scorer_id, score FROM human_scores") == [(user_id(OTHER_SCORER), 2)]
    assert (await call(OTHER_SCORER, "GET", list_url(session_id))).status_code == 403


async def test_naming_refuses_unknown_and_test_students_and_others_than_the_admin(scored):
    session_id = scored["session"]

    async def refused(email: str) -> tuple:
        response = await call(ADMIN, "POST", scorers_url(session_id), json={"email": email})
        return response.status_code, response.json()["error"]["fields"]

    assert await refused("ingen@x.no") == (422, {"email": "unknown"})
    assert await refused("ts1@x.no") == (422, {"email": "test_student"})
    execute("UPDATE users SET is_active = false WHERE email = %s", OTHER_SCORER)
    assert await refused(OTHER_SCORER) == (422, {"email": "unknown"})
    for who in (LECTURER, SCORER, STUDENT):
        response = await call(who, "POST", scorers_url(session_id), json={"email": SCORER})
        assert response.status_code == 403
        assert (await call(who, "GET", scorers_url(session_id))).status_code == 403
    missing = await call(ADMIN, "GET", scorers_url(str(uuid.uuid4())))
    assert (missing.status_code, missing.json()["error"]["code"]) == (404, "not_found")


# Reading the answers.


async def test_before_the_deadline_the_list_is_closed_and_empty(scored, monkeypatch):
    session_id = scored["session"]
    at(monkeypatch, DEADLINE - timedelta(minutes=1))
    response = await call(SCORER, "GET", list_url(session_id))
    assert response.status_code == 200
    body = response.json()
    assert (body["test"]["open"], body["entries"], body["can_score"]) == (False, [], True)
    at(monkeypatch, AFTER)
    [first, *_] = await entries(session_id)
    at(monkeypatch, DEADLINE - timedelta(minutes=1))
    early = await call(SCORER, "GET", item_url(session_id, first["ref"]))
    assert (early.status_code, early.json()["error"]["code"]) == (404, "not_found")


async def test_the_list_holds_each_answer_with_text_under_a_neutral_number(scored, monkeypatch):
    session_id = scored["session"]
    at(monkeypatch, AFTER)
    response = await call(SCORER, "GET", list_url(session_id))
    body = response.json()
    found = body["entries"]
    # Two closed attempts × (two long + one Adapted), less the blank one; the open attempt and the
    # computed item are not listed.
    assert [e["number"] for e in found] == [1, 2, 3, 4, 5]
    assert [e["type"] for e in found] == ["long", "long", "long", "adapted", "adapted"]
    assert all(e["scored"] is False for e in found)
    assert body["test"]["name"] == "Kontrolltest høst" and body["test"]["open"] is True
    text = response.text
    for student in scored["students"]:
        assert str(student) not in text
    for secret in ("ts1@x.no", "ts2@x.no", "Ts1", "Ts2"):
        assert secret not in text
    attempts = rows("SELECT id FROM test_attempts")
    assert all(str(a) not in text for (a,) in attempts)
    # Within one question the order is the opaque ref's, never the answer id's (a UUIDv7 carries
    # its time) and no answer id is served at all.
    for item_id in {e["question"] for e in found}:
        refs = [e["ref"] for e in found if e["question"] == item_id]
        assert refs == sorted(refs)
    answer_ids = [a for (a,) in rows("SELECT id FROM test_answers")]
    assert all(str(a) not in text for a in answer_ids)
    # The order is stable from read to read.
    assert [e["ref"] for e in await entries(session_id)] == [e["ref"] for e in found]
    # Scorers have their home's Lenke; other Users have no Control test listed.
    mine = (await call(SCORER, "GET", "/api/scoring")).json()["tests"]
    assert [(t["id"], t["open"]) for t in mine] == [(session_id, True)]
    assert (await call(LECTURER, "GET", "/api/scoring")).json()["tests"] == []


async def test_only_its_scorers_and_the_admin_read_a_control_tests_answers(scored, monkeypatch):
    session_id = scored["session"]
    at(monkeypatch, AFTER)
    [first, *_] = await entries(session_id)
    await make("assistent2@x.no", roles=())
    for who in (LECTURER, STUDENT, OTHER_SCORER, "ts1@x.no", "assistent2@x.no"):
        assert (await call(who, "GET", list_url(session_id))).status_code == 403, who
        item = await call(who, "GET", item_url(session_id, first["ref"]))
        assert item.status_code == 403, who
        posted = await call(who, "POST", item_url(session_id, first["ref"]), json={"score": 2})
        assert posted.status_code == 403, who
    # No such Control test, or an ordinary Class session, reads the same as a refusal.
    assert (await call(SCORER, "GET", list_url(str(uuid.uuid4())))).status_code == 403
    assert (await call(SCORER, "GET", list_url("nope"))).status_code == 403
    assert (await call(ADMIN, "GET", list_url(str(uuid.uuid4())))).status_code == 403
    assert rows("SELECT count(*) FROM human_scores") == [(0,)]


async def test_an_item_shows_the_answer_and_the_guide_and_no_ai_score(scored, monkeypatch):
    session_id = scored["session"]
    at(monkeypatch, AFTER)
    listed = await entries(session_id)
    long_one = next(e for e in listed if e["type"] == "long")
    response = await call(SCORER, "GET", item_url(session_id, long_one["ref"]))
    assert response.status_code == 200, response.text
    item = response.json()
    assert item["number"] == long_one["number"] and item["question"] == long_one["question"]
    assert item["answer"].strip() and item["facts"] == []
    assert item["guide_title"] and item["criteria"] and all(c["code"] for c in item["criteria"])
    assert [s["step"] for s in item["scale"]] == [0, 1, 2, 3, 4]
    assert all(s["label"] for s in item["scale"])
    assert (item["ai"], item["own_score"], item["can_score"]) == (None, None, True)
    assert "KI-tilbakemelding" not in response.text
    for each in (*scored["students"], *(a for (a,) in rows("SELECT id FROM test_attempts"))):
        assert str(each) not in response.text
    assert "ts1@x.no" not in response.text and "ts2@x.no" not in response.text
    assert all(str(a) not in response.text for (a,) in rows("SELECT id FROM test_answers"))
    adapted = next(e for e in listed if e["type"] == "adapted")
    shown = (await call(SCORER, "GET", item_url(session_id, adapted["ref"]))).json()
    assert shown["question"] == "Hvorfor bestilte du mye i Uke 6?"
    assert shown["facts"] and all(f["name"] and f["value"] for f in shown["facts"])
    assert shown["guide_title"]
    assert (await call(SCORER, "GET", item_url(session_id, str(uuid.uuid4())))).status_code == 404


async def test_a_submitted_score_shows_the_ai_step_for_that_item_only(scored, monkeypatch):
    session_id = scored["session"]
    at(monkeypatch, AFTER)
    first, second, *_ = await entries(session_id)
    submitted = await call(SCORER, "POST", item_url(session_id, first["ref"]), json={"score": 3})
    assert submitted.status_code == 201, submitted.text
    body = submitted.json()
    assert body["own_score"]["score"] == 3
    assert body["ai"] is not None and body["ai"]["step"] in range(5) and body["ai"]["label"]
    assert "KI-tilbakemelding" not in submitted.text
    assert rows("SELECT answer_id, scorer_id, score, submitted_at FROM human_scores") == [
        (answer_id_of(first["ref"]), user_id(SCORER), 3, AFTER)
    ]
    # Read again: the scored item shows the AI step, the other still does not.
    again = (await call(SCORER, "GET", item_url(session_id, first["ref"]))).json()
    assert again["ai"] == body["ai"]
    other = (await call(SCORER, "GET", item_url(session_id, second["ref"]))).json()
    assert other["ai"] is None and other["own_score"] is None
    marks = [e["scored"] for e in await entries(session_id)]
    assert marks == [True, False, False, False, False]
    # Another scorer's own view stays blind on the item the first scored.
    await call(ADMIN, "POST", scorers_url(session_id), json={"email": OTHER_SCORER})
    blind = (await call(OTHER_SCORER, "GET", item_url(session_id, first["ref"]))).json()
    assert blind["ai"] is None and blind["own_score"] is None
    counts = (await call(ADMIN, "GET", scorers_url(session_id))).json()["scorers"]
    assert [(s["email"], s["scored"]) for s in counts] == [(SCORER, 1), (OTHER_SCORER, 0)]


async def test_a_second_submit_is_refused_and_no_update_path_exists(scored, monkeypatch):
    session_id = scored["session"]
    at(monkeypatch, AFTER)
    [first, *_] = await entries(session_id)
    url = item_url(session_id, first["ref"])
    assert (await call(SCORER, "POST", url, json={"score": 1})).status_code == 201
    again = await call(SCORER, "POST", url, json={"score": 4})
    assert (again.status_code, again.json()["error"]["code"]) == (409, "human_score_exists")
    assert rows("SELECT score FROM human_scores") == [(1,)]
    for bad in (-1, 5):
        assert (await call(SCORER, "POST", url, json={"score": bad})).status_code == 422
    with pytest.raises(psycopg.errors.RaiseException):
        execute("UPDATE human_scores SET score = 4")
    assert rows("SELECT score FROM human_scores") == [(1,)]


async def test_the_admin_reads_each_read_audited_and_scores_only_when_named(scored, monkeypatch):
    session_id = scored["session"]
    at(monkeypatch, AFTER)
    listed = await call(ADMIN, "GET", list_url(session_id))
    assert listed.status_code == 200 and listed.json()["can_score"] is False
    [first, *_] = listed.json()["entries"]
    item = await call(ADMIN, "GET", item_url(session_id, first["ref"]))
    assert item.status_code == 200 and item.json()["ai"] is None
    assert (
        await call(ADMIN, "POST", item_url(session_id, first["ref"]), json={"score": 2})
    ).status_code == 403
    read = audits("control_test.answers_read")
    assert [(a, t) for a, t, _ in read] == [
        (user_id(ADMIN), {"class_session_id": session_id}),
        (
            user_id(ADMIN),
            {"class_session_id": session_id, "answer_id": str(answer_id_of(first["ref"]))},
        ),
    ]
    # A scorer's reads are not audited; another Admin reads too.
    await entries(session_id)
    assert len(audits("control_test.answers_read")) == 2
    assert (await call(ADMIN_LECTURER, "GET", list_url(session_id))).status_code == 200
    assert len(audits("control_test.answers_read")) == 3
    # Named, the Admin scores like any scorer.
    await call(ADMIN, "POST", scorers_url(session_id), json={"email": ADMIN})
    scored_now = await call(ADMIN, "POST", item_url(session_id, first["ref"]), json={"score": 2})
    assert scored_now.status_code == 201 and scored_now.json()["ai"] is not None
    # The answer a submit gives back is a read too.
    assert len(audits("control_test.answers_read")) == 4


async def test_an_ordinary_class_session_is_no_control_test_to_score(scored, klass, monkeypatch):
    """An ordinary Class session with a closed attempt is refused on every scoring route, also to
    the Admin: only a Class session of kind `control_test` has answers to score."""
    at(monkeypatch, AFTER)
    course = await new_session(klass)
    execute("UPDATE class_sessions SET test_deadline = %s WHERE id = %s", DEADLINE, course)
    student = await make("vanlig@x.no", roles=())
    attempt(str(course), student, {LONG[0]: "Et vanlig svar."})
    course_id = str(course)
    for who in (ADMIN, SCORER):
        assert (await call(who, "GET", list_url(course_id))).status_code == 403
    missing = await call(ADMIN, "GET", scorers_url(course_id))
    assert (missing.status_code, missing.json()["error"]["code"]) == (404, "not_found")
    named = await call(ADMIN, "POST", scorers_url(course_id), json={"email": SCORER})
    assert named.status_code == 404
    assert rows(
        "SELECT count(*) FROM control_test_scorers WHERE class_session_id = %s", course
    ) == [(0,)]
