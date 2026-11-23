"""Compare human and AI scores and mark the Scoring guide as checked (Story 12.10, FR-81, FR-82,
AD-1, AD-12, AD-27).

The Admin reads a Control test's results: each listed answer's human and AI steps side by side
and the measures from `analysis.agreement`, preliminary while scores are missing. The last score
that completes the Control test marks its pinned Scoring guide version checked for its pinned
model config, in the same transaction; `content.is_checked` answers it from then on. The setup is
Story 12.9's (`scored`): attempts, answers and AI steps seeded by SQL, the api's clock moved by
hand."""

import asyncio
import uuid
from datetime import timedelta

import pytest

from app.modules.assessment import service as assessment
from app.modules.content import service as content
from app.platform.db import get_sessionmaker
from tests.assessment.test_human_scores import (
    ADMIN,
    AFTER,
    DEADLINE,
    LONG,
    OTHER_SCORER,
    SCORER,
    STUDENT,
    ai_scores,
    answer_id_of,
    attempt,
    audits,
    entries,
    item_url,
    scored,
    scorers_url,
    user_id,
)
from tests.classes.test_classes import LECTURER
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import clock, klass
from tests.classes.test_staff import call
from tests.messaging.helpers import rows
from tests.sessions.test_control_test import ADMIN_LECTURER, control, create, people
from tests.sessions.test_dates import at, new_session
from tests.sessions.test_test_students import enrol

__all__ = ["clock", "control", "klass", "people", "scored"]


@pytest.fixture(autouse=True)
def _empty(ai_db, games_db):
    """No model config, budget, game or Scoring guide check but what a test adds; the checks go
    afterwards too, so no other test's content cleanup meets one."""
    execute("DELETE FROM scoring_guide_checks")
    yield
    execute("DELETE FROM scoring_guide_checks")


def results_url(session_id: str) -> str:
    return f"/api/admin/control-tests/{session_id}/results"


async def results(session_id: str, who: str = ADMIN) -> dict:
    response = await call(who, "GET", results_url(session_id))
    assert response.status_code == 200, response.text
    return response.json()


def ai_step_of(ref: str) -> int:
    """The AI's stored step of the answer a scorer's `ref` names."""
    [(step,)] = rows(
        "SELECT s.score FROM test_answers a JOIN ai_assessments x ON x.attempt_id = a.attempt_id "
        "JOIN ai_item_scores s ON s.assessment_id = x.id AND s.item_id = a.item_id "
        "WHERE a.id = %s",
        answer_id_of(ref),
    )
    return step


def pinned(session_id: str) -> tuple[uuid.UUID, uuid.UUID]:
    """The Control test's pinned Scoring guide version and model config."""
    [(guide_id,)] = rows(
        "SELECT scoring_guide_id FROM test_scoring_guides WHERE class_session_id = %s", session_id
    )
    [(config_id,)] = rows("SELECT model_config_id FROM class_sessions WHERE id = %s", session_id)
    return guide_id, config_id


def close_open_attempts(session_id: str) -> None:
    execute(
        "UPDATE test_attempts SET status = 'auto_submitted', submitted_at = %s, closed_at = %s "
        "WHERE class_session_id = %s AND closed_at IS NULL",
        DEADLINE,
        DEADLINE,
        session_id,
    )


async def score(session_id: str, who: str, ref: str, step: int) -> None:
    response = await call(who, "POST", item_url(session_id, ref), json={"score": step})
    assert response.status_code == 201, response.text


async def test_results_are_preliminary_while_scores_are_missing(scored, monkeypatch, people):
    """5 listed answers, 2 named scorers, an attempt still open. SCORER scores two answers: one
    as the AI did, one two steps off. Missing 2 × 5 − 2 = 8; exact 1/2, within one 1/2."""
    session_id = scored["session"]
    at(monkeypatch, AFTER)
    await call(ADMIN, "POST", scorers_url(session_id), json={"email": OTHER_SCORER})
    first, second, *_ = await entries(session_id)
    first_ai, second_ai = ai_step_of(first["ref"]), ai_step_of(second["ref"])
    off = second_ai - 2 if second_ai >= 2 else second_ai + 2
    await score(session_id, SCORER, first["ref"], first_ai)
    await score(session_id, SCORER, second["ref"], off)
    found = await results(session_id)
    assert found["test"]["open"] is True
    assert found["scoring_guide"] == {"version": 1, "edited": False}
    assert found["ai_config"]["name"] == "mock-b"
    assert len(found["scorers"]) == 2
    assert [row["number"] for row in found["rows"]] == [1, 2, 3, 4, 5]
    assert found["rows"][0]["human"] == [first_ai, None]
    assert found["rows"][1]["human"] == [off, None]
    assert found["rows"][2]["human"] == [None, None]
    assert found["rows"][0]["ai"] == first_ai and found["rows"][0]["words"] > 0
    assert (found["missing"], found["ai_missing"], found["open_attempts"]) == (8, 0, 1)
    assert (found["complete"], found["checked"], found["withheld"]) == (False, False, False)
    measures = found["measures"]
    assert (measures["pairs"], measures["exact"], measures["within_one"]) == (2, 0.5, 0.5)
    assert measures["offset"] == (0 + second_ai - off) / 2
    assert [band["band"] for band in measures["by_length"]] == ["short", "medium", "long"]
    assert measures["by_length"][0]["pairs"] == 2  # every seeded answer is under 50 words
    # Each read is audited with ids only; nothing is checked.
    read = audits("control_test.results_read")
    assert [(a, t) for a, t, _ in read] == [(user_id(ADMIN), {"class_session_id": session_id})]
    assert rows("SELECT count(*) FROM scoring_guide_checks") == [(0,)]
    guide_id, config_id = pinned(session_id)
    assert await content.is_checked(guide_id, config_id) is False


async def test_a_removed_scorers_kept_scores_are_left_out_of_the_measures(scored, monkeypatch):
    session_id = scored["session"]
    at(monkeypatch, AFTER)
    await call(ADMIN, "POST", scorers_url(session_id), json={"email": OTHER_SCORER})
    [first, *_] = await entries(session_id)
    await score(session_id, OTHER_SCORER, first["ref"], 0)
    assert (await results(session_id))["measures"]["pairs"] == 1
    await call(ADMIN, "DELETE", f"{scorers_url(session_id)}/{user_id(OTHER_SCORER)}")
    found = await results(session_id)
    assert found["measures"]["pairs"] == 0 and found["measures"]["exact"] is None
    assert [row["human"] for row in found["rows"]][0] == [None]


async def test_the_last_score_marks_the_guide_checked_for_that_config_only(
    scored, monkeypatch, people, klass
):
    """One named scorer, the open attempt closed: 6 listed answers. The fifth score leaves the
    guide unchecked, the sixth checks it for the pinned config and no other, in its transaction,
    with one audit row. A Class session pinning the same pair reads «checked»; an edit of its
    guide is a new version and unchecked."""
    session_id = scored["session"]
    close_open_attempts(session_id)
    at(monkeypatch, AFTER)
    listed = await entries(session_id)
    assert len(listed) == 6
    for entry in listed[:-1]:
        await score(session_id, SCORER, entry["ref"], 2)
    guide_id, config_id = pinned(session_id)
    assert await content.is_checked(guide_id, config_id) is False
    early = await results(session_id)
    assert (early["missing"], early["complete"], early["checked"]) == (1, False, False)
    await score(session_id, SCORER, listed[-1]["ref"], 2)
    assert rows(
        "SELECT scoring_guide_id, model_config_id, control_test_id, checked_at "
        "FROM scoring_guide_checks"
    ) == [(guide_id, config_id, uuid.UUID(session_id), AFTER)]
    assert await content.is_checked(guide_id, config_id) is True
    other_config = uuid.UUID(people["configs"][0])
    assert other_config != config_id
    assert await content.is_checked(guide_id, other_config) is False
    assert await content.is_checked(guide_id, None) is False
    checked = audits("control_test.checked")
    assert [(a, t) for a, t, _ in checked] == [(user_id(SCORER), {"class_session_id": session_id})]
    assert checked[0][2] == {
        "scoring_guide_id": str(guide_id),
        "model_config_id": str(config_id),
        "first": True,
    }
    found = await results(session_id)
    assert (found["missing"], found["open_attempts"]) == (0, 0)
    assert (found["complete"], found["checked"]) == (True, True)
    assert found["measures"]["pairs"] == 5  # the third student's answer has no AI step
    assert found["ai_missing"] == 1
    # A course Class session on the same guide version and model config: «Sensorveiledning» reads
    # checked; the Lecturer's edit makes a new version, unchecked.
    course = await new_session(klass)
    execute("UPDATE class_sessions SET model_config_id = %s WHERE id = %s", config_id, course)
    block = (await call(LECTURER, "GET", f"/api/class-sessions/{course}/scoring-guide")).json()
    assert block["version_id"] == str(guide_id) and block["checked"] is True
    first_question = block["questions"][0]["id"]
    edited = await call(
        LECTURER,
        "PUT",
        f"/api/class-sessions/{course}/scoring-guide",
        json={"guides": {first_question: "En egen tekst."}},
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["version_id"] != str(guide_id) and edited.json()["checked"] is False
    # A check is never taken back nor rewritten.
    assert rows("SELECT count(*) FROM scoring_guide_checks") == [(1,)]


async def test_two_last_scores_at_once_mark_the_guide_checked_once(scored, monkeypatch):
    """Two scorers each owe one answer; they submit at the same moment. The scorer rows are held
    by each submit in turn, so the later one sees the other's score and marks the check."""
    session_id = scored["session"]
    close_open_attempts(session_id)
    at(monkeypatch, AFTER)
    await call(ADMIN, "POST", scorers_url(session_id), json={"email": OTHER_SCORER})
    listed = await entries(session_id)
    for entry in listed[:-1]:
        await score(session_id, SCORER, entry["ref"], 1)
    for entry in listed[1:]:
        await score(session_id, OTHER_SCORER, entry["ref"], 3)
    assert rows("SELECT count(*) FROM scoring_guide_checks") == [(0,)]
    await asyncio.gather(
        score(session_id, SCORER, listed[-1]["ref"], 1),
        score(session_id, OTHER_SCORER, listed[0]["ref"], 3),
    )
    assert rows("SELECT count(*) FROM scoring_guide_checks") == [(1,)]
    assert len(audits("control_test.checked")) == 1
    assert (await results(session_id))["complete"] is True


async def test_an_open_attempt_keeps_the_control_test_unchecked(scored, monkeypatch):
    session_id = scored["session"]
    at(monkeypatch, AFTER)
    for entry in await entries(session_id):
        await score(session_id, SCORER, entry["ref"], 2)
    found = await results(session_id)
    assert (found["missing"], found["open_attempts"]) == (0, 1)
    assert (found["complete"], found["checked"]) == (False, False)
    assert rows("SELECT count(*) FROM scoring_guide_checks") == [(0,)]


async def test_an_admin_who_is_a_named_scorer_gets_no_ai_steps_before_their_own(
    scored, monkeypatch
):
    session_id = scored["session"]
    close_open_attempts(session_id)
    at(monkeypatch, AFTER)
    await call(ADMIN, "POST", scorers_url(session_id), json={"email": ADMIN})
    listed = await entries(session_id, ADMIN)
    await score(session_id, ADMIN, listed[0]["ref"], 2)
    found = await results(session_id)
    assert found["withheld"] is True and found["measures"] is None
    assert found["ai_missing"] == 0  # not even whether the AI has scored
    assert all(row["ai"] is None for row in found["rows"])
    assert found["rows"][0]["human"][1] == 2  # their own score shows; the AI's does not
    for entry in listed[1:]:
        await score(session_id, ADMIN, entry["ref"], 2)
    after = await results(session_id)
    assert after["withheld"] is False and after["measures"] is not None
    assert any(row["ai"] is not None for row in after["rows"])


async def test_before_the_deadline_there_are_no_rows(scored, monkeypatch):
    session_id = scored["session"]
    at(monkeypatch, DEADLINE - timedelta(minutes=1))
    found = await results(session_id)
    assert found["test"]["open"] is False and found["rows"] == []
    assert (found["missing"], found["complete"], found["measures"]) == (0, False, None)


async def test_only_the_admin_reads_the_results(scored, monkeypatch, klass):
    """AD-12: the results are under `control_tests.manage`; a scorer, the Lecturer and a Student
    are refused alike, and no such Control test is 404 for the Admin."""
    session_id = scored["session"]
    at(monkeypatch, AFTER)
    [first, *_] = await entries(session_id)
    await score(session_id, SCORER, first["ref"], 4)
    for who in (SCORER, LECTURER, STUDENT):
        response = await call(who, "GET", results_url(session_id))
        assert response.status_code == 403, who
        assert "human" not in response.text
    assert (await call(ADMIN_LECTURER, "GET", results_url(session_id))).status_code == 200
    for missing in (str(uuid.uuid4()), "nope"):
        response = await call(ADMIN, "GET", results_url(missing))
        assert response.status_code == 404
    # An ordinary Class session is no Control test.
    course = await new_session(klass)
    assert (await call(ADMIN, "GET", results_url(course))).status_code == 404


async def test_an_edited_guide_is_checked_by_its_own_control_test(
    scored, monkeypatch, people, klass
):
    """FR-82: a Lecturer's edited guide is checked when the Admin runs a Control test pinned to
    it; the Lecturer reads neither its answers nor its results."""
    at(monkeypatch, AFTER)
    course = await new_session(klass)
    block = (await call(LECTURER, "GET", f"/api/class-sessions/{course}/scoring-guide")).json()
    edited = await call(
        LECTURER,
        "PUT",
        f"/api/class-sessions/{course}/scoring-guide",
        json={"guides": {block["questions"][0]["id"]: "Lærerens egen tekst."}},
    )
    edited_id = edited.json()["version_id"]
    made = await create(people, name="Kontrolltest av endret", scoring_guide_id=edited_id)
    assert made.status_code == 201, made.text
    second = made.json()
    execute("UPDATE class_sessions SET test_deadline = %s WHERE id = %s", DEADLINE, second["id"])
    student = await enrol(second["class_id"], "ts9@x.no", "given")
    attempt_id = attempt(second["id"], student, {LONG[0]: "Forsinkelser gir svingninger."})
    ai_scores(second["id"], attempt_id, student, {LONG[0]: 3})
    await call(ADMIN, "POST", scorers_url(second["id"]), json={"email": SCORER})
    [only] = await entries(second["id"])
    assert (await call(LECTURER, "GET", results_url(second["id"]))).status_code == 403
    assert (await call(LECTURER, "GET", f"/api/scoring/{second['id']}")).status_code == 403
    await score(second["id"], SCORER, only["ref"], 3)
    guide_id, config_id = pinned(second["id"])
    assert str(guide_id) == edited_id
    assert await content.is_checked(guide_id, config_id) is True
    found = await results(second["id"])
    assert found["scoring_guide"]["edited"] is True and found["checked"] is True
    assert found["measures"]["exact"] == 1.0
    # The first Control test (the default guide) is still unchecked.
    default_guide, _ = pinned(scored["session"])
    assert await content.is_checked(default_guide, config_id) is False


async def test_a_second_control_test_on_a_checked_pair_keeps_the_first_check(
    scored, monkeypatch, people
):
    """The first check of a pair stays: a second Control test pinned to the same guide version and
    config completes (its last score is stored, its audit row says `first: false`) and writes no
    second row."""
    first_id = scored["session"]
    close_open_attempts(first_id)
    at(monkeypatch, AFTER)
    for entry in await entries(first_id):
        await score(first_id, SCORER, entry["ref"], 2)
    [(checked_at, control_test_id)] = rows(
        "SELECT checked_at, control_test_id FROM scoring_guide_checks"
    )
    made = await create(people, name="Kontrolltest to")
    assert made.status_code == 201, made.text
    second = made.json()
    assert pinned(second["id"]) == pinned(first_id)
    execute("UPDATE class_sessions SET test_deadline = %s WHERE id = %s", DEADLINE, second["id"])
    student = await enrol(second["class_id"], "ts8@x.no", "given")
    attempt_id = attempt(second["id"], student, {LONG[0]: "Forsinkelser gir svingninger."})
    ai_scores(second["id"], attempt_id, student, {LONG[0]: 1})
    await call(ADMIN, "POST", scorers_url(second["id"]), json={"email": SCORER})
    before = await results(second["id"])
    assert before["checked"] is True and before["complete"] is False  # the pair, not this test
    [only] = await entries(second["id"])
    await score(second["id"], SCORER, only["ref"], 1)
    assert rows("SELECT checked_at, control_test_id FROM scoring_guide_checks") == [
        (checked_at, control_test_id)
    ]
    assert [change["first"] for _, _, change in audits("control_test.checked")] == [True, False]
    assert (await results(second["id"]))["complete"] is True


async def test_removing_the_last_scorer_who_owed_scores_completes_the_control_test(
    scored, monkeypatch
):
    session_id = scored["session"]
    close_open_attempts(session_id)
    at(monkeypatch, AFTER)
    await call(ADMIN, "POST", scorers_url(session_id), json={"email": OTHER_SCORER})
    for entry in await entries(session_id):
        await score(session_id, SCORER, entry["ref"], 2)
    assert rows("SELECT count(*) FROM scoring_guide_checks") == [(0,)]
    removed = await call(ADMIN, "DELETE", f"{scorers_url(session_id)}/{user_id(OTHER_SCORER)}")
    assert removed.status_code == 200, removed.text
    guide_id, config_id = pinned(session_id)
    assert await content.is_checked(guide_id, config_id) is True
    [(actor, target, change)] = audits("control_test.checked")
    assert (actor, target) == (user_id(ADMIN), {"class_session_id": session_id})
    assert change["first"] is True
    assert (await results(session_id))["complete"] is True


async def test_a_scorer_no_longer_named_stores_nothing(scored, monkeypatch):
    """`record_human_score` refuses a scorer missing from the held scorer rows."""
    session_id = scored["session"]
    at(monkeypatch, AFTER)
    [first, *_] = await entries(session_id)
    guide_id, config_id = pinned(session_id)
    with pytest.raises(assessment.ScorerNotNamed):
        async with get_sessionmaker().begin() as s:
            await assessment.record_human_score(
                s,
                uuid.UUID(session_id),
                answer_id_of(first["ref"]),
                user_id(OTHER_SCORER),
                2,
                named={user_id(SCORER)},
                listed=[answer_id_of(first["ref"])],
                settled=True,
                scoring_guide_id=guide_id,
                model_config_id=config_id,
                now=AFTER,
            )
    assert rows("SELECT count(*) FROM human_scores") == [(0,)]


async def test_answer_length_is_counted_in_words_of_the_stored_answer(scored, monkeypatch):
    """Two stored answers made 60 and 160 words long fall in the medium and long bands."""
    session_id = scored["session"]
    at(monkeypatch, AFTER)
    first, second, *_ = await entries(session_id)
    for entry, count in ((first, 60), (second, 160)):
        execute(
            "UPDATE test_answers SET value = to_jsonb(%s::text) WHERE id = %s",
            " ".join(["ord"] * count),
            answer_id_of(entry["ref"]),
        )
        await score(session_id, SCORER, entry["ref"], ai_step_of(entry["ref"]))
    found = await results(session_id)
    by_number = {row["number"]: row["words"] for row in found["rows"]}
    assert (by_number[first["number"]], by_number[second["number"]]) == (60, 160)
    bands = {band["band"]: band for band in found["measures"]["by_length"]}
    assert (bands["short"]["pairs"], bands["medium"]["pairs"], bands["long"]["pairs"]) == (0, 1, 1)
    assert bands["medium"]["exact"] == 1.0 and bands["long"]["exact"] == 1.0
