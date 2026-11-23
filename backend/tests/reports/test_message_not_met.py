"""Story 13.6 at the api (FR-17, FR-40, AD-9, AD-12): a Message to the Students who have not met
the requirement, `recipient=requirement_not_met` on the Meldingsskjema's form and send.

The list is judged by `reports.service.completion_status` when the form is read and again when the
Message is sent. Corrections (Story 13.3) of all five steps make a Student meet the requirement
without a game; the shares come from a short game played out at the Play deadline."""

import uuid

from app.modules.identity.schemas import AccountRole
from app.modules.progress.models import CORRECTABLE_STEPS
from app.platform.collation import nb_sort_key
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_staff import ASSISTANT, call, put_staff
from tests.messaging.helpers import rows
from tests.messaging.test_messages import form, message_notices, send, stored
from tests.reports.test_completion_status import _played_out, obligatory
from tests.reports.test_corrections import correct
from tests.reports.test_studentside import ADMIN, OTHER_LECTURER
from tests.sessions.test_allocation import students
from tests.sessions.test_dates import OUTSIDER
from tests.sessions.test_game_end import _empty, clock, emitted, klass
from tests.sessions.test_lock import dated
from tests.sessions.test_orders import code

__all__ = ["_empty", "clock", "emitted", "klass"]

NOT_MET = {"recipient": "requirement_not_met"}


async def met(session_id: str, student: uuid.UUID) -> None:
    """Corrections of all five steps (Story 13.3), stored as «Lagre retting» stores them; one
    through the api, the rest directly, so the test stays fast."""
    first, *rest = CORRECTABLE_STEPS
    saved = await correct(LECTURER, session_id, student, first, True, "Gjort i timen.")
    assert saved.status_code == 200
    for step in rest:
        execute(
            "INSERT INTO completion_corrections (id, user_id, class_session_id, step, done, "
            "reason, at) VALUES (%s, %s, %s, %s, true, 'Gjort i timen.', now())",
            uuid.uuid7(),
            student,
            session_id,
            step,
        )


def names(body: dict) -> list[str]:
    return [row["name"] for row in body["not_met"]]


async def test_the_message_goes_to_those_who_have_not_met_the_requirement_when_it_is_sent(
    klass, emitted
):
    session_id = await dated(klass)
    a, b, c = await students(klass, 3)

    # Not obligatory: no requirement, nobody to write to.
    shown = (await form(LECTURER, session_id, **NOT_MET)).json()
    assert (shown["kind"], shown["students"], shown["not_met"]) == ("requirement_not_met", 0, [])
    assert code(await send(LECTURER, session_id, **NOT_MET)) == (422, "no_recipients")

    obligatory(session_id)
    await met(session_id, a)
    shown = (await form(LECTURER, session_id, **NOT_MET)).json()
    assert (shown["students"], shown["sent_before"]) == (2, 0)
    assert {row["user_id"] for row in shown["not_met"]} == {str(b), str(c)}
    assert names(shown) == sorted(names(shown), key=nb_sort_key)
    assert all(row["name"] for row in shown["not_met"])
    # No game yet: no share; the share required is the Class session's.
    assert {
        (r["ordered_share"], r["required_share"], r["playout_share"], r["share_game"])
        for r in shown["not_met"]
    } == {(None, 80, None, None)}
    # Every other recipient's form has no table.
    assert (await form(LECTURER, session_id)).json()["not_met"] == []

    # B meets it between the form and the send: the Message goes to C only.
    await met(session_id, b)
    key = uuid.uuid4()
    emitted.clear()
    sent = await send(LECTURER, session_id, "Husk testen!", key=key, **NOT_MET)
    assert sent.status_code == 201
    assert (sent.json()["students"], sent.json()["sent_before"]) == (1, 1)
    [(kind, game, user, text, recipients)] = stored(session_id)
    assert (kind, game, user, text, recipients) == (
        "requirement_not_met",
        None,
        None,
        "Husk testen!",
        [str(c)],
    )
    assert [user for user, _ in message_notices()] == [str(c)]
    assert ("session", session_id) in emitted
    # A repeat with the same key sends nothing new.
    again = await send(LECTURER, session_id, "Husk testen!", key=key, **NOT_MET)
    assert (again.status_code, again.json()["students"]) == (201, 1)
    assert len(stored(session_id)) == 1 and len(message_notices()) == 1

    # «Meldinger» lists it by its kind; the form counts it as sent before.
    listed = (await call(LECTURER, "GET", f"/api/class-sessions/{session_id}/messages")).json()
    assert [(m["kind"], m["students"]) for m in listed["items"]] == [("requirement_not_met", 1)]
    assert (await form(LECTURER, session_id, **NOT_MET)).json()["sent_before"] == 1

    # Everyone has met it: nobody left, and the send stores nothing.
    await met(session_id, c)
    shown = (await form(LECTURER, session_id, **NOT_MET)).json()
    assert (shown["students"], shown["not_met"]) == (0, [])
    assert code(await send(LECTURER, session_id, "Igjen", **NOT_MET)) == (422, "no_recipients")
    assert rows("SELECT count(*) FROM messages")[0][0] == 1


async def test_the_form_and_send_follow_the_policy_of_a_message_to_the_class_session(klass):
    session_id = await dated(klass)
    a, _ = await students(klass, 2)
    obligatory(session_id)
    await make(OTHER_LECTURER)
    await make(ADMIN, roles=(AccountRole.admin,))
    await make(OUTSIDER, roles=())
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")

    # An Assistant lecturer may, as with any Message to the Class session (Story 7.9).
    assert (await form(ASSISTANT, session_id, **NOT_MET)).json()["students"] == 2
    assert (await send(ASSISTANT, session_id, **NOT_MET)).status_code == 201

    # Anyone else, and this recipient with a game or a Student named too: one answer.
    for who in (OTHER_LECTURER, ADMIN, OUTSIDER, "s1@x.no"):
        assert code(await form(who, session_id, **NOT_MET)) == (403, "forbidden")
        assert code(await send(who, session_id, **NOT_MET)) == (403, "forbidden")
    named = {**NOT_MET, "student_id": str(a)}
    assert code(await form(LECTURER, session_id, **named)) == (403, "forbidden")
    assert code(await send(LECTURER, session_id, **named)) == (403, "forbidden")
    assert (await form(LECTURER, session_id, recipient="someone")).status_code == 422
    assert len(stored(session_id)) == 1


async def test_the_table_shows_the_share_ordered_and_the_share_the_playout_played(klass):
    session_id, _, (adjusted, other) = await _played_out(klass)
    # A Tilrettelegging share (Story 8.9) is the Student's own requirement, in the table too.
    execute(
        "INSERT INTO student_adjustments (class_session_id, user_id, time_factor, share_percent, "
        "updated_at) VALUES (%s, %s, 1.0, 50, now())",
        session_id,
        adjusted,
    )
    shown = (await form(LECTURER, session_id, **NOT_MET)).json()
    assert shown["students"] == 2
    assert {
        r["user_id"]: (r["ordered_share"], r["required_share"], r["playout_share"], r["share_game"])
        for r in shown["not_met"]
    } == {str(adjusted): (20, 50, 80, None), str(other): (20, 80, 80, None)}


def test_the_table_is_in_norwegian_alphabetical_order():
    names = ["Åse", "ørjan", "Zara", "Ærlig", "anna"]
    ordered = sorted(names, key=nb_sort_key)
    assert ordered == ["anna", "Zara", "Ærlig", "ørjan", "Åse"]
