"""«Mine data» at the api (Story 15.1, FR-75, FR-5, AD-12, AD-14): `GET /api/me/data` answers every
category in page order, the caller's own rows only, each with its Class and Klasseøkt; another
Student's text, Seat or id never; `adjustments` only when there is a Tilrettelegging; 401 without
a session. One Class game played 14 Uker by one Student serves the main test."""

import uuid
from datetime import UTC, datetime

import pytest

from app.platform.own_data import CATEGORIES
from tests.classes.test_classes import LECTURER
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import clock, klass
from tests.classes.test_staff import call
from tests.classes.test_student_registration import emitted
from tests.debrief.test_explanation import OWN_ORDERS, played, user_id
from tests.identity.helpers import client
from tests.messaging.helpers import rows
from tests.sessions.test_allocation import students
from tests.sessions.test_dates import new_session
from tests.sessions.test_lock import _empty

__all__ = ["_empty", "clock", "emitted", "klass"]

AT = datetime(2026, 11, 20, 12, tzinfo=UTC)
MINE = "Restordren vokste, så jeg bestilte mye."
THEIRS = "Den andre Studentens egen Forklaring, som aldri vises."


def explain(user: uuid.UUID, session_id: str, game_id: str, text: str) -> None:
    execute(
        "INSERT INTO debrief_explanations (user_id, class_session_id, game_id, text, length, "
        "saved_at) VALUES (%s, %s, %s, %s, %s, %s)",
        user,
        session_id,
        game_id,
        text,
        len(text),
        AT,
    )


MINE_QUESTION = "Hvorfor kom ølet så sent?"
THEIRS_QUESTION = "Den andre Studentens spørsmål."


def seed(user: uuid.UUID, session_id: str, game_id: str, question: str) -> None:
    """A reflection answer, a Completion correction, a Message and a deadline reminder."""
    execute(
        "INSERT INTO debrief_reflection_answers (user_id, class_session_id, question_id, game_id, "
        "questions_version, text, length, saved_at) VALUES (%s, %s, 'feelings', %s, 1, %s, %s, %s)",
        user,
        session_id,
        game_id,
        question,
        len(question),
        AT,
    )
    execute(
        "INSERT INTO completion_corrections (id, user_id, class_session_id, step, done, reason, "
        "at) VALUES (%s, %s, %s, 'debrief', true, 'Muntlig levert', %s)",
        uuid.uuid7(),
        user,
        session_id,
        AT,
    )
    message = uuid.uuid7()
    execute(
        "INSERT INTO messages (id, key, class_session_id, sender_id, recipient_kind, "
        "recipient_user_id, text, created_at) SELECT %s, %s, %s, id, 'student', %s, "
        "'Husk Debriefen.', %s FROM users WHERE email = %s",
        message,
        uuid.uuid7(),
        session_id,
        user,
        AT,
        LECTURER,
    )
    execute("INSERT INTO message_recipients (message_id, user_id) VALUES (%s, %s)", message, user)
    execute(
        "INSERT INTO deadline_reminders (id, class_session_id, deadline, deadline_at, created_at, "
        "user_id) VALUES (%s, %s, 'test_deadline', %s, %s, %s)",
        uuid.uuid7(),
        session_id,
        AT,
        AT,
        user,
    )


async def data(who: str) -> dict:
    answer = await call(who, "GET", "/api/me/data")
    assert answer.status_code == 200
    assert answer.headers["cache-control"] == "no-store"
    return {c["key"]: c["items"] for c in answer.json()["categories"]}


def fields(item: dict) -> dict:
    return {f["key"]: f["value"] for f in item["fields"]}


@pytest.mark.long
async def test_a_student_sees_their_own_rows_in_every_category_and_no_one_elses(klass, emitted):
    session_id, game_id, _, game_of, me = await played(klass)
    mate = next(who for who, game in game_of.items() if game == game_id and who != me)
    explain(user_id(me), session_id, game_id, MINE)
    explain(user_id(mate), session_id, game_id, THEIRS)
    seed(user_id(me), session_id, game_id, MINE_QUESTION)
    seed(user_id(mate), session_id, game_id, THEIRS_QUESTION)

    answer = await call(me, "GET", "/api/me/data")
    body = answer.text
    found = await data(me)
    # Every category but the Tilrettelegging, which the Student does not have, in page order.
    assert list(found) == [key for key in CATEGORIES if key != "adjustments"]
    [profile] = [item for item in found["account"] if item["kind"] == "profile"]
    assert fields(profile)["email"] == me
    # The Explanation: the Student's own, named by Class and Klasseøkt.
    [explanation] = found["explanation"]
    assert fields(explanation)["text"] == MINE
    assert (explanation["class_name"], explanation["session_number"]) == ("class-of-1994", 1)
    # The Orders: the Student's own Seat weeks only, their own Orders among them.
    orders = found["orders"]
    assert len({fields(o)["role"] for o in orders}) == 1
    stored = rows(
        'SELECT w.week, w."order", w.decided_by FROM seat_weeks w JOIN seats s ON s.id = w.seat_id '
        "JOIN seat_occupancy o ON o.seat_id = s.id WHERE s.game_id = %s AND o.user_id = %s "
        "ORDER BY w.week",
        game_id,
        user_id(me),
    )
    shown = [(int(fields(o)["week"]), fields(o)["order"], fields(o)["decided_by"]) for o in orders]
    assert shown == [(w, None if o is None else str(o), d) for w, o, d in stored]
    assert sum(1 for _, _, d in stored if d == "student") >= len(OWN_ORDERS) - 2
    # The other Student never appears: not their text, not their id, not their address.
    assert THEIRS not in body
    assert str(user_id(mate)) not in body and mate not in body
    assert found["explanation"] and not found["quiz"]  # nothing stored: an empty list
    # One stored row in more categories, each read back with its own fields.
    [answer] = found["reflection"]
    assert fields(answer) == {"question_id": "feelings", "text": MINE_QUESTION}
    [correction] = [i for i in found["completion"] if i["kind"] == "correction"]
    assert fields(correction) == {"step": "debrief", "done": "true", "reason": "Muntlig levert"}
    [message] = [i for i in found["messages"] if i["kind"] == "message"]
    assert fields(message)["text"] == "Husk Debriefen."
    [reminder] = [i for i in found["messages"] if i["kind"] == "reminder"]
    assert fields(reminder)["deadline"] == "test_deadline"
    assert THEIRS_QUESTION not in body


async def test_a_new_student_sees_empty_categories_and_a_tilrettelegging_once_given(klass):
    [student] = await students(klass, 1)
    session_id = await new_session(klass)
    me = "s0@x.no"
    found = await data(me)
    assert "adjustments" not in found and found["explanation"] == [] and found["orders"] == []
    execute(
        "INSERT INTO student_adjustments (class_session_id, user_id, time_factor, share_percent, "
        "updated_at) VALUES (%s, %s, 2.0, 60, %s)",
        session_id,
        student,
        AT,
    )
    [adjustment] = (await data(me))["adjustments"]
    assert (fields(adjustment)["time_factor"], fields(adjustment)["share_percent"]) == ("2.0", "60")


async def test_without_a_session_it_is_401(klass):
    async with client() as c:
        assert (await c.get("/api/me/data")).status_code == 401


def test_the_orders_are_only_the_weeks_the_student_held_the_seat():
    """`games.own_data._spans` (FR-5): a Seat taken over in Uke 6 and given back in Uke 9 keeps the
    Student's weeks 1-5 and 9 on; a row replaced within its week spans nothing."""
    from app.modules.games.own_data import _held, _spans

    seat, me, other = uuid.uuid7(), uuid.uuid7(), uuid.uuid7()
    rows = [
        {"id": uuid.uuid7(), "seat_id": seat, "from_week": 1, "user_id": me},
        {"id": uuid.uuid7(), "seat_id": seat, "from_week": 6, "user_id": None},
        {"id": uuid.uuid7(), "seat_id": seat, "from_week": 9, "user_id": other},
        {"id": uuid.uuid7(), "seat_id": seat, "from_week": 9, "user_id": me},
    ]
    mine = _spans(rows, me)[seat]
    assert [w for w in range(1, 15) if _held(mine, w)] == [1, 2, 3, 4, 5, *range(9, 15)]
    theirs = _spans(rows, other)
    assert seat not in theirs  # replaced within Uke 9: never held a decision


def test_the_category_lists_agree():
    """The api's category Literal is the readers' list (`platform.own_data.CATEGORIES`)."""
    from typing import get_args

    from app.modules.reports.schemas import MyDataCategory

    assert get_args(MyDataCategory) == CATEGORIES
