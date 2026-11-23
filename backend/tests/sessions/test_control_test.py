"""The Control test set up in the operator's own Institution (Story 12.7, FR-82, AD-12, AD-13,
AD-15, AD-23, AD-27): the operator mark on one Institution, Admin-område → «Kontrolltest» making a
Class and a `control_test` Class session in one transaction pinned to the Scoring guide version
and the model config under test, the Admin as the Class's owner on the ordinary Epic 4/5 routes,
and a Control test left out of every staff list and closed to everyone else. The api's clock is
fixed and moved by hand; the database clock is never read."""

import uuid
from datetime import timedelta

import psycopg
import pytest

from app.ai import budget, config, seed
from app.modules.identity.schemas import AccountRole
from app.modules.sessions import service as sessions
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_classes import LECTURER, institution, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_staff import call, put_staff
from tests.classes.test_student_registration import emitted
from tests.messaging.helpers import rows
from tests.question_set.test_question_set import in_production
from tests.sessions.test_dates import PLAN, START, TEST, iso, new_session, refusal, student_of
from tests.sessions.test_lab_hours import sweep_at
from tests.sessions.test_rerun import copy, flag

__all__ = ["clock", "emitted", "klass"]

ADMIN = "admin@x.no"
ADMIN_LECTURER = "admin-laerer@x.no"
ASSISTANT = "assistent@x.no"
STUDENT = "student@x.no"
MINUTE = timedelta(minutes=1)
TESTS = "/api/admin/control-tests"


@pytest.fixture(autouse=True)
def _empty(ai_db, games_db):
    """No model config, budget or game: each test adds what it needs."""


@pytest.fixture
async def people(klass) -> dict:
    """The ordinary Class `klass` of LECTURER with an Assistant lecturer and a Student, an Admin
    and an Admin who is also a Lecturer, two model configs (the first the active default) and
    two Institutions besides the Class's."""
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")
    await student_of(klass, STUDENT)
    await make(ADMIN, roles=(AccountRole.admin,))
    await make(ADMIN_LECTURER, roles=(AccountRole.admin, AccountRole.lecturer))
    first = await config.add(config.parse({**seed.MOCK_SPEC, "name": "mock-a"}))
    second = await config.add(config.parse({**seed.MOCK_SPEC, "name": "mock-b"}))
    for row in (first, second):
        await config.add_mock_measurement(row.id, row.spec.effort_levels[0].name)
    await config.pin(first.id)
    return {
        "class": klass,
        "configs": [str(first.id), str(second.id)],
        "operator": str(await institution("Operatøren AS")),
        "other": str(await institution("Annen høgskole")),
    }


async def mark(institution_id: str, email: str = ADMIN):
    return await call(email, "PUT", f"/api/admin/institutions/{institution_id}/operator-owned")


async def overview(email: str = ADMIN) -> dict:
    response = await call(email, "GET", TESTS)
    assert response.status_code == 200
    return response.json()


async def create(people: dict, email: str = ADMIN, **body):
    page = await overview()
    wanted = {
        "name": "Kontrolltest høst",
        "scoring_guide_id": page["scoring_guides"][0]["id"],
        "model_config_id": people["configs"][1],
        **body,
    }
    return await call(email, "POST", TESTS, json=wanted)


@pytest.fixture
async def control(people) -> dict:
    """A Control test the Admin set up in the marked operator Institution."""
    assert (await mark(people["operator"])).status_code == 200
    created = await create(people)
    assert created.status_code == 201, created.text
    return created.json()


def audits(action: str) -> list[tuple]:
    return rows(
        "SELECT actor_user_id, target_ids, change FROM audit_events WHERE action = %s", action
    )


def user_id(email: str) -> uuid.UUID:
    return rows("SELECT id FROM users WHERE email = %s", email)[0][0]


# The operator mark.


async def test_the_admin_marks_one_institution_and_the_mark_moves(people):
    first = await mark(people["operator"])
    assert first.status_code == 200 and first.json()["operator_owned"] is True
    # Marking the marked one again writes nothing.
    assert (await mark(people["operator"])).status_code == 200
    moved = await mark(people["other"])
    assert moved.json()["operator_owned"] is True
    marked = rows("SELECT id FROM institutions WHERE operator_owned")
    assert [str(i) for (i,) in marked] == [people["other"]]
    [first_row, second_row] = sorted(
        audits("institution.operator_marked"), key=lambda r: r[2]["previous_institution_id"] or ""
    )
    assert first_row[0] == user_id(ADMIN)
    assert first_row[1] == {"institution_id": people["operator"]}
    assert first_row[2] == {"previous_institution_id": None}
    assert second_row[2] == {"previous_institution_id": people["operator"]}
    listed = (await call(ADMIN, "GET", "/api/admin/institutions")).json()["items"]
    assert {i["id"]: i["operator_owned"] for i in listed}[people["other"]] is True
    page = await overview()
    assert page["operator_institution"] == {"id": people["other"], "name": "Annen høgskole"}


async def test_only_the_admin_marks_and_an_unknown_institution_is_not_found(people):
    assert (await mark(people["operator"], LECTURER)).status_code == 403
    assert refusal(await mark(str(uuid.uuid4())))[:2] == (404, "not_found")
    # The database keeps one mark at most.
    execute("UPDATE institutions SET operator_owned = true WHERE id = %s", people["operator"])
    with pytest.raises(psycopg.errors.UniqueViolation):
        execute("UPDATE institutions SET operator_owned = true WHERE id = %s", people["other"])


# Setting up a Control test.


async def test_with_no_operator_institution_the_setup_is_refused(people):
    page = await overview()
    assert page["operator_institution"] is None and page["items"] == []
    refused = await create(people)
    assert (refused.status_code, refused.json()["error"]["code"]) == (
        409,
        "operator_institution_missing",
    )
    assert rows("SELECT count(*) FROM class_sessions WHERE kind = 'control_test'") == [(0,)]


async def test_a_bad_setup_names_every_refused_field_and_stores_nothing(people):
    assert (await mark(people["operator"])).status_code == 200
    refused = await create(
        people, name="  ", scoring_guide_id=str(uuid.uuid4()), model_config_id=str(uuid.uuid4())
    )
    assert refusal(refused) == (
        422,
        "invalid_request",
        {"name": "name_empty", "scoring_guide_id": "unknown", "model_config_id": "unknown"},
    )
    missing = await call(ADMIN, "POST", TESTS, json={"name": "X"})
    assert refusal(missing)[2] == {"scoring_guide_id": "missing", "model_config_id": "missing"}
    assert rows("SELECT count(*) FROM classes WHERE name = 'X'") == [(0,)]


async def test_only_the_admin_sets_up_or_lists_control_tests(people):
    assert (await mark(people["operator"])).status_code == 200
    for email in (LECTURER, ASSISTANT, STUDENT):
        assert (await call(email, "GET", TESTS)).status_code == 403
        assert (await create(people, email=email)).status_code == 403


async def test_the_setup_makes_the_class_and_the_pinned_control_test_session(people, emitted):
    assert (await mark(people["operator"])).status_code == 200
    emitted.clear()
    created = await create(people)
    assert created.status_code == 201, created.text
    control = created.json()
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["sessions.create_control_test"]
    assert emitted == [("user", str(user_id(ADMIN)))]
    session_id, class_id = control["id"], control["class_id"]
    admin = user_id(ADMIN)
    [(institution_id, created_by)] = rows(
        "SELECT institution_id, created_by FROM classes WHERE id = %s", class_id
    )
    assert (str(institution_id), created_by) == (people["operator"], admin)
    assert rows("SELECT user_id, role FROM class_staff WHERE class_id = %s", class_id) == [
        (admin, "owner")
    ]
    [(kind, config_id, ai_mode, level)] = rows(
        "SELECT kind, model_config_id, ai_mode, effort_level FROM class_sessions WHERE id = %s",
        session_id,
    )
    assert (kind, str(config_id)) == ("control_test", people["configs"][1])
    # LLM players at the config's first offered level, as «Lag Klasseøkt» gives a new session.
    offered = await config.offered_effort_levels(uuid.UUID(people["configs"][1]))
    assert (ai_mode, level) == ("llm", offered[0].name)
    pinned = await config.get(people["configs"][1])
    assert pinned is not None and pinned.referenced_at is not None
    assert await budget.get(budget.BudgetScope.class_session(session_id)) is not None
    page = await overview()
    guide = page["scoring_guides"][0]
    [(guide_id, base_id, pinned_at)] = rows(
        "SELECT scoring_guide_id, base_id, pinned_at FROM test_scoring_guides "
        "WHERE class_session_id = %s",
        session_id,
    )
    assert (str(guide_id), str(base_id), pinned_at) == (guide["id"], guide["id"], NOW)
    [item] = page["items"]
    assert item == control
    assert item["institution_name"] == "Operatøren AS" and item["can_open"] is True
    assert item["scoring_guide"]["version"] == guide["version"]
    assert item["ai_config"]["name"] == "mock-b" and item["ai_config"]["default"] is False
    assert [c["name"] for c in page["model_configs"]] == ["mock-a", "mock-b"]
    [(actor, targets, change)] = audits("control_test.created")
    assert actor == admin
    assert targets == {"class_session_id": session_id, "class_id": class_id}
    assert change["scoring_guide_version"] == guide["version"]
    assert change["model_config_id"] == people["configs"][1]
    # Another Admin reads the list but does not own the Class.
    other = await overview(ADMIN_LECTURER)
    assert other["items"][0]["can_open"] is False


async def test_the_database_keeps_a_control_tests_kind_and_model_config(people, control):
    with pytest.raises(psycopg.errors.RestrictViolation):
        execute(
            "UPDATE class_sessions SET model_config_id = %s WHERE id = %s",
            people["configs"][0],
            control["id"],
        )
    with pytest.raises(psycopg.errors.RestrictViolation):
        execute("UPDATE class_sessions SET kind = 'course' WHERE id = %s", control["id"])
    course = await new_session(people["class"])
    with pytest.raises(psycopg.errors.RestrictViolation):
        execute("UPDATE class_sessions SET kind = 'control_test' WHERE id = %s", course)
    assert await sessions.kind_of(uuid.UUID(course)) == "course"
    assert await sessions.kind_of(uuid.UUID(control["id"])) == "control_test"


# The Admin as the owner, on the ordinary screens.


async def test_the_admin_works_the_control_test_on_the_ordinary_routes(people, control):
    session_id, class_id = control["id"], control["class_id"]
    found = await call(ADMIN, "GET", f"/api/classes/{class_id}")
    assert found.status_code == 200
    assert (found.json()["can_manage"], found.json()["control_test"]) == (True, True)
    read = await call(ADMIN, "GET", f"/api/class-sessions/{session_id}")
    assert read.status_code == 200 and read.json()["kind"] == "control_test"
    saved = await call(
        ADMIN,
        "PUT",
        f"/api/class-sessions/{session_id}",
        json={"ai_mode": "rule_based", "dates": iso(PLAN)},
    )
    assert saved.status_code == 200, saved.text
    pasted = await call(
        ADMIN, "POST", f"/api/classes/{class_id}/roster-paste", json={"text": "t@x.no"}
    )
    assert pasted.status_code == 201, pasted.text
    sent = await call(
        ADMIN,
        "POST",
        f"/api/classes/{class_id}/invitations",
        json={"upload_id": pasted.json()["id"], "valid_days": 14},
    )
    assert sent.status_code == 201, sent.text
    allocation = await call(ADMIN, "GET", f"/api/class-sessions/{session_id}/allocation")
    assert allocation.status_code == 200, allocation.text
    # Another Admin who lectures does not own it: no change.
    other = await call(
        ADMIN_LECTURER, "PUT", f"/api/class-sessions/{session_id}", json={"ai_mode": "rule_based"}
    )
    assert other.status_code == 403
    # The model config stays the one under test whatever the save says.
    assert [
        str(c)
        for (c,) in rows("SELECT model_config_id FROM class_sessions WHERE id = %s", session_id)
    ] == [people["configs"][1]]
    # On an ordinary Class the Admin role grants nothing, and the Lærerhjem's reads are not its.
    for path in (
        f"/api/classes/{people['class']}",
        "/api/classes",
        "/api/lecturer-home/class-sessions",
        f"/api/classes/{people['class']}/class-sessions",
    ):
        assert (await call(ADMIN, "GET", path)).status_code == 403, path


async def test_a_control_test_class_takes_no_other_session_or_staff(people, control, monkeypatch):
    class_id = control["class_id"]
    for response in (
        await call(ADMIN, "POST", f"/api/classes/{class_id}/class-sessions"),
        await call(
            ADMIN, "POST", f"/api/classes/{class_id}/staff/lecturers", json={"email": LECTURER}
        ),
        await call(
            ADMIN, "POST", f"/api/classes/{class_id}/staff/assistants", json={"email": "a@x.no"}
        ),
    ):
        assert refusal(response)[:2] == (409, "control_test_class")
    flag(monkeypatch, True)
    # Out of it, by its owner who also lectures an ordinary Class, and into it.
    assert (await mark(people["operator"], ADMIN_LECTURER)).status_code == 200
    mine = (await create(people, email=ADMIN_LECTURER)).json()
    own = await call(
        ADMIN_LECTURER,
        "POST",
        "/api/classes",
        json={"name": "Vanlig", "institution_id": people["other"]},
    )
    own_class = own.json()["id"]
    source = (await call(ADMIN_LECTURER, "POST", f"/api/classes/{own_class}/class-sessions")).json()
    into = await copy(mine["class_id"], source["id"], email=ADMIN_LECTURER)
    out_of = await copy(own_class, mine["id"], email=ADMIN_LECTURER)
    assert refusal(into)[:2] == refusal(out_of)[:2] == (409, "control_test_class")
    assert rows("SELECT count(*) FROM class_sessions WHERE class_id = %s", class_id) == [(1,)]
    assert rows("SELECT count(*) FROM class_staff WHERE class_id = %s", class_id) == [(1,)]


async def test_the_scoring_guide_is_read_only_and_the_test_deadline_lock_keeps_it(
    people, monkeypatch
):
    assert (await mark(people["operator"], ADMIN_LECTURER)).status_code == 200
    control = (await create(people, email=ADMIN_LECTURER)).json()
    session_id = control["id"]
    path = f"/api/class-sessions/{session_id}/scoring-guide"
    block = (await call(ADMIN_LECTURER, "GET", path)).json()
    assert (block["pinned"], block["open"]) == (True, False)
    assert block["version_id"] == control["scoring_guide"]["id"]
    question = block["questions"][0]["id"]
    refused = await call(ADMIN_LECTURER, "PUT", path, json={"guides": {question: "Ny tekst."}})
    assert refusal(refused)[:2] == (409, "scoring_guide_locked")
    before = rows("SELECT * FROM test_scoring_guides WHERE class_session_id = %s", session_id)
    assert await sessions.lock_test(uuid.UUID(session_id), now=TEST + MINUTE) is True
    after = rows("SELECT * FROM test_scoring_guides WHERE class_session_id = %s", session_id)
    assert after == before


async def test_in_production_a_draft_question_set_refuses_the_control_test_lock(
    people, control, monkeypatch
):
    session_id = control["id"]
    saved = await call(
        ADMIN,
        "PUT",
        f"/api/class-sessions/{session_id}",
        json={"ai_mode": "rule_based", "dates": iso(PLAN)},
    )
    assert saved.status_code == 200
    in_production(monkeypatch)
    await sweep_at(START + MINUTE)
    refused = "SELECT locked_at, lock_refused_reason FROM class_sessions WHERE id = %s"
    assert rows(refused, session_id) == [(None, "question_set_draft")]


# Left out of every list, closed to everyone else (AD-13).


async def test_no_lecturer_assistant_or_student_sees_or_opens_a_control_test(
    people, control, monkeypatch
):
    flag(monkeypatch, True)
    session_id, class_id = control["id"], control["class_id"]
    course = await new_session(people["class"])
    for email in (LECTURER, ASSISTANT, STUDENT, ADMIN_LECTURER):
        for path in (
            f"/api/classes/{class_id}",
            f"/api/classes/{class_id}/registrations",
            f"/api/class-sessions/{session_id}",
            f"/api/class-sessions/{session_id}/overview",
            f"/api/class-sessions/{session_id}/scoring-guide",
            f"/api/classes/{class_id}/class-sessions",
        ):
            response = await call(email, "GET", path)
            assert response.status_code in (403, 404), (email, path, response.status_code)
    lists = {
        LECTURER: [
            "/api/classes",
            "/api/lecturer-home/class-sessions",
            f"/api/classes/{people['class']}/class-sessions",
            f"/api/classes/{people['class']}/class-sessions/copy-sources",
            f"/api/class-sessions/{course}/overview",
        ],
        ASSISTANT: [
            "/api/classes",
            "/api/lecturer-home/class-sessions",
            f"/api/class-sessions/{course}/overview",
        ],
        STUDENT: ["/api/classes/enrolled", "/api/me/class-sessions"],
    }
    for email, paths in lists.items():
        for path in paths:
            response = await call(email, "GET", path)
            assert response.status_code == 200, (email, path, response.text)
            assert session_id not in response.text and class_id not in response.text, path


async def test_the_admin_who_lectures_sees_no_control_test_on_the_laererhjem(people, monkeypatch):
    assert (await mark(people["operator"], ADMIN_LECTURER)).status_code == 200
    mine = (await create(people, email=ADMIN_LECTURER)).json()
    for path in ("/api/classes", "/api/lecturer-home/class-sessions"):
        response = await call(ADMIN_LECTURER, "GET", path)
        assert response.status_code == 200
        assert mine["class_id"] not in response.text and mine["id"] not in response.text
    # It still opens for its owner, and the Lecturer role can be taken back: a Control test
    # Class is no Class the Lecturer revoke blocker counts.
    assert (
        await call(ADMIN_LECTURER, "GET", f"/api/classes/{mine['class_id']}")
    ).status_code == 200
    revoked = await call(
        ADMIN,
        "DELETE",
        f"/api/admin/users/{user_id(ADMIN_LECTURER)}/roles/lecturer",
    )
    assert revoked.status_code in (200, 204), revoked.text


async def test_a_lecturers_edited_guide_is_a_choice_and_keeps_its_default(people):
    course = await new_session(people["class"])
    path = f"/api/class-sessions/{course}/scoring-guide"
    block = (await call(LECTURER, "GET", path)).json()
    question = block["questions"][0]["id"]
    edited = await call(LECTURER, "PUT", path, json={"guides": {question: "Egen veiledning."}})
    assert edited.status_code == 200, edited.text
    edited_id = edited.json()["version_id"]
    assert (await mark(people["operator"])).status_code == 200
    page = await overview()
    assert (page["scoring_guides"][0]["id"], page["scoring_guides"][0]["edited"]) == (
        block["version_id"],
        False,
    )
    [choice] = [g for g in page["scoring_guides"] if g["id"] == edited_id]
    assert choice["edited"] is True
    created = await create(people, scoring_guide_id=edited_id)
    assert created.status_code == 201, created.text
    assert created.json()["scoring_guide"]["edited"] is True
    [(guide_id, base_id)] = rows(
        "SELECT scoring_guide_id, base_id FROM test_scoring_guides WHERE class_session_id = %s",
        created.json()["id"],
    )
    assert (str(guide_id), str(base_id)) == (edited_id, block["version_id"])
    pinned = (
        await call(ADMIN, "GET", f"/api/class-sessions/{created.json()['id']}/scoring-guide")
    ).json()
    changed = {q["id"]: q["changed"] for q in pinned["questions"]}
    assert changed[question] is True and pinned["edited"] is True
