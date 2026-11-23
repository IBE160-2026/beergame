"""«Tverrinstitusjonell statistikk» (Story 14.7, cut list, FR-65, FR-5, AD-12, AD-14, AD-17): the
stored aggregates grouped by Institution for the Admin only, read from the aggregate tables only,
with Story 14.4's filters and difference labels; an Institution with one compared Class session
is listed only when none of its shown measures was withheld; absent while the flag is off. The api
tests store aggregate rows for fresh Class sessions, so no game is played."""

import json
import uuid
from decimal import Decimal

import pytest

from app.modules.identity.schemas import AccountRole
from app.modules.reports import aggregates, cross_institution
from app.modules.reports.cross_institution_schemas import (
    ComparedInstitutionOut,
    InstitutionMeasureOut,
    InstitutionStatisticsOut,
    InstitutionValueOut,
)
from app.platform.config import get_settings
from tests.classes.test_classes import LECTURER, institution, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_staff import call, put_staff
from tests.identity.helpers import client
from tests.messaging.helpers import rows
from tests.reports.test_cross_class_filters import keys
from tests.sessions.test_dates import new_session
from tests.sessions.test_game_end import _empty, clock, emitted, klass
from tests.sessions.test_rerun import flag

__all__ = ["_empty", "clock", "emitted", "klass"]

ADMIN = "admin-tverr@x.no"
ASSISTANT = "assistent-tverr@x.no"
URL = "/api/institution-statistics"
X, Y = uuid.UUID(int=101), uuid.UUID(int=102)
A, B, C, D = (uuid.UUID(int=n) for n in range(1, 5))


def value(measures: list[InstitutionMeasureOut], key: str, institution_id: uuid.UUID):
    measure = next(m for m in measures if m.key == key)
    return next(v for v in measure.values if v.institution_id == institution_id)


# Pure: `combine`.


def test_each_institution_is_the_median_of_its_unwithheld_sessions():
    stored = {
        (A, "chain.median"): (Decimal(1000), False),
        (B, "chain.median"): (Decimal(2000), False),
        (C, "chain.median"): (Decimal(3000), False),
        (D, "chain.median"): (None, True),
    }
    institutions, measures = cross_institution.combine(
        [(A, X), (B, X), (C, Y), (D, Y)], {}, stored, {X: "Østfold", Y: "Agder"}, None
    )
    # Norwegian order: «Agder» before «Østfold».
    assert [(i.name, i.sessions, i.withheld) for i in institutions] == [
        ("Agder", 2, False),
        ("Østfold", 2, False),
    ]
    assert (
        value(measures, "chain.median", X).value,
        value(measures, "chain.median", X).sessions,
    ) == (
        Decimal(1500),
        2,
    )
    y = value(measures, "chain.median", Y)
    assert (y.value, y.withheld, y.sessions) == (Decimal(3000), False, 1)
    # No row at all: not measured, neither a value nor withheld.
    core = value(measures, "core.median", X)
    assert (core.value, core.withheld, core.sessions) == (None, False, 0)


def test_only_withheld_rows_read_as_withheld():
    stored = {(A, "core.median"): (None, True), (B, "core.median"): (None, True)}
    _, measures = cross_institution.combine([(A, X), (B, X)], {}, stored, {X: "X"}, None)
    core = value(measures, "core.median", X)
    assert (core.value, core.withheld) == (None, True)


def test_a_single_session_with_a_withheld_shown_measure_withholds_the_institution():
    stored = {
        (A, "chain.median"): (Decimal(1954), False),
        (A, "core.median"): (None, True),
        (C, "chain.median"): (Decimal(2000), False),
    }
    differs = {A: ["ai_mode"], C: ["ai_mode"]}
    institutions, measures = cross_institution.combine(
        [(A, X), (C, Y)], differs, stored, {X: "Withheld", Y: "Shown"}, None
    )
    by_id = {i.institution_id: i for i in institutions}
    assert by_id[X].withheld and by_id[X].differs == [] and by_id[X].sessions == 1
    for measure in measures:
        cell = next(v for v in measure.values if v.institution_id == X)
        assert (cell.value, cell.withheld) == (None, True)
    # A single Class session whose shown measures all rest on 10 or more (or were not measured).
    assert not by_id[Y].withheld and by_id[Y].differs == ["ai_mode"]
    assert value(measures, "chain.median", Y).value == Decimal(2000)


def test_an_institutions_differences_are_its_sessions_in_key_order():
    differs = {A: ["model"], B: ["ai_mode", "item_weights"]}
    institutions, _ = cross_institution.combine([(A, X), (B, X)], differs, {}, {X: "X"}, True)
    assert institutions[0].differs == ["ai_mode", "model", "item_weights"]


def test_the_score_measure_carries_the_comparability():
    _, measures = cross_institution.combine([(A, X), (B, X)], {}, {}, {X: "X"}, False)
    assert {m.key: m.comparable for m in measures}["core.median"] is False
    assert all(m.comparable is None for m in measures if m.key != "core.median")


def test_the_response_names_no_class_lecturer_or_student():
    fields = set()
    for model in (
        InstitutionStatisticsOut,
        ComparedInstitutionOut,
        InstitutionMeasureOut,
        InstitutionValueOut,
    ):
        fields |= set(model.model_fields)
    banned = (
        "class",
        "session_id",
        "session_number",
        "lecturer",
        "student",
        "user",
        "email",
        "written",
    )
    assert not [f for f in fields if any(word in f for word in banned)]


# The api.


@pytest.fixture
async def people(klass):
    await make(ADMIN, roles=(AccountRole.admin,))
    put_staff(klass, await make(ASSISTANT), "assistant")
    return klass


def store(session_id: str, stored: dict[str, object], measures: dict[str, object]) -> None:
    execute(
        "INSERT INTO class_aggregates (class_session_id, written_at, students, game_students, "
        "games_finished, keys, institution_id) VALUES (%s, now(), 12, 12, 3, %s::jsonb, "
        "(SELECT c.institution_id FROM class_sessions s JOIN classes c ON c.id = s.class_id "
        "WHERE s.id = %s))",
        session_id,
        json.dumps(stored),
        session_id,
    )
    for measure, figure in measures.items():
        execute(
            "INSERT INTO class_aggregate_measures (class_session_id, measure, group_size, value, "
            "withheld) VALUES (%s, %s, %s, %s, %s)",
            session_id,
            measure,
            12 if figure is not None else 4,
            figure,
            figure is None,
        )


async def second_class(name: str = "NTNU") -> str:
    place = await institution(name)
    created = await call(
        LECTURER,
        "POST",
        "/api/classes",
        json={"name": "class-of-2025", "institution_id": str(place)},
    )
    assert created.status_code == 201
    return created.json()["id"]


async def test_the_admin_sees_the_institutions_and_no_class(people):
    other = await second_class()
    first, second = await new_session(people), await new_session(people)
    third, fourth = await new_session(other), await new_session(other)
    store(first, keys(), {"chain.median": 1000, "core.median": 70})
    store(second, keys(), {"chain.median": 2000, "core.median": None})
    store(third, keys(ai_mode="rule_based"), {"chain.median": 3000})
    store(fourth, keys(ai_mode="rule_based"), {"chain.median": 5000})
    response = await call(ADMIN, "GET", URL)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert [(i["name"], i["sessions"], i["withheld"]) for i in body["institutions"]] == [
        ("NTNU", 2, False),
        ("USN Bø", 2, False),
    ]
    # A tie (two llm, two rule-based): both Institutions labelled with what differs.
    assert all(i["differs"] == ["ai_mode"] for i in body["institutions"])
    chain = next(m for m in body["measures"] if m["key"] == "chain.median")
    assert [Decimal(v["value"]) for v in chain["values"]] == [Decimal(4000), Decimal(1500)]
    core = next(m for m in body["measures"] if m["key"] == "core.median")
    usn = core["values"][1]
    assert (Decimal(usn["value"]), usn["sessions"]) == (Decimal(70), 1)
    assert (body["ready"], body["compared"]) == (4, 4)
    # No Class, Class session or Lecturer named.
    text = json.dumps(body)
    for name in ("class-of-1994", "class-of-2025", first, third, "Bard"):
        assert name not in text

    # A filter leaves NTNU's rule-based sessions only; USN drops out.
    [ai] = [f for f in body["filters"] if f["dimension"] == "ai_mode"]
    rule = next(o for o in ai["options"] if o["label"] == "rule_based")
    filtered = (await call(ADMIN, "GET", f"{URL}?ai_mode={rule['value']}")).json()
    assert [i["name"] for i in filtered["institutions"]] == ["NTNU"]
    assert filtered["institutions"][0]["differs"] == []
    assert (filtered["ready"], filtered["compared"]) == (4, 2)
    assert (await call(ADMIN, "GET", f"{URL}?model={'x' * 65}")).status_code == 422


async def test_a_filter_that_leaves_one_small_session_withholds_its_institution(people):
    first, second = await new_session(people), await new_session(people)
    store(first, keys(), {"chain.median": 1000, "core.median": None})
    store(second, keys(effort_level="high"), {"chain.median": 2000, "core.median": 70})
    body = (await call(ADMIN, "GET", URL)).json()
    [usn] = body["institutions"]
    assert (usn["sessions"], usn["withheld"]) == (2, False)
    [effort] = [f for f in body["filters"] if f["dimension"] == "effort_level"]
    low = next(o for o in effort["options"] if o["label"] == "low")
    filtered = (await call(ADMIN, "GET", f"{URL}?effort_level={low['value']}")).json()
    [usn] = filtered["institutions"]
    assert (usn["sessions"], usn["withheld"], usn["differs"]) == (1, True, [])
    for measure in filtered["measures"]:
        assert measure["values"] == [
            {
                "institution_id": usn["institution_id"],
                "value": None,
                "withheld": True,
                "sessions": 0,
            }
        ]
    # The other single session rests on 10 or more everywhere: listed.
    high = next(o for o in effort["options"] if o["value"] != low["value"])
    shown = (await call(ADMIN, "GET", f"{URL}?effort_level={high['value']}")).json()
    assert shown["institutions"][0]["withheld"] is False
    chain = next(m for m in shown["measures"] if m["key"] == "chain.median")
    assert Decimal(chain["values"][0]["value"]) == Decimal(2000)


async def test_no_aggregate_lists_nothing(people):
    await new_session(people)
    body = (await call(ADMIN, "GET", URL)).json()
    assert body == {"institutions": [], "measures": [], "filters": [], "ready": 0, "compared": 0}


async def test_only_the_admin_may_read_it(people):
    async with client() as c:
        assert (await c.get(URL)).status_code == 401
    assert (await call(LECTURER, "GET", URL)).status_code == 403
    assert (await call(ASSISTANT, "GET", URL)).json()["error"]["code"] == "forbidden"
    await make("student-tverr@x.no", roles=())
    assert (await call("student-tverr@x.no", "GET", URL)).status_code == 403
    me = (await call(ADMIN, "GET", "/api/auth/me")).json()["user"]
    assert me["cross_institution_stats"] is True
    lecturer = (await call(LECTURER, "GET", "/api/auth/me")).json()["user"]
    assert lecturer["cross_institution_stats"] is False


@pytest.fixture
def flag_off(monkeypatch):
    """`FEATURE_CROSS_INSTITUTION_STATS` off for one test; the cached settings are read again
    after, whatever the test's outcome."""
    flag(monkeypatch, False, "FEATURE_CROSS_INSTITUTION_STATS")
    yield
    monkeypatch.undo()
    get_settings.cache_clear()


async def test_with_the_flag_off_the_view_does_not_exist(people, flag_off):
    session_id = await new_session(people)
    store(session_id, keys(), {"chain.median": 1000})
    for who in (ADMIN, LECTURER):
        response = await call(who, "GET", URL)
        assert (response.status_code, response.json()) == (404, {"detail": "Not Found"})
    assert (await call(ADMIN, "GET", "/api/auth/me")).json()["user"][
        "cross_institution_stats"
    ] is False
    # Tverrklasse-statistikk works unchanged.
    own = (await call(LECTURER, "GET", "/api/class-statistics")).json()
    assert [s["class_session_id"] for s in own["sessions"]] == [session_id]


async def test_the_writer_stores_the_institution(people):
    session_id = await new_session(people)
    assert await aggregates.write_aggregate(uuid.UUID(session_id))
    [(stored,)] = rows(
        "SELECT institution_id FROM class_aggregates WHERE class_session_id = %s", session_id
    )
    [(expected,)] = rows("SELECT institution_id FROM classes WHERE id = %s", people)
    assert stored == expected


async def test_the_answer_reads_only_the_stored_rows(people):
    """The Class renamed after the aggregate was
    written: the answer is the same, as it reads the aggregate tables only (AD-14)."""
    first, second = await new_session(people), await new_session(people)
    store(first, keys(), {"chain.median": 1000})
    store(second, keys(), {"chain.median": 3000})
    before = (await call(ADMIN, "GET", URL)).json()
    execute("UPDATE classes SET name = 'renamed' WHERE id = %s", people)
    after = (await call(ADMIN, "GET", URL)).json()
    assert after == before
    chain = next(m for m in after["measures"] if m["key"] == "chain.median")
    assert Decimal(chain["values"][0]["value"]) == Decimal(2000)
