"""Story 8.2 through the api: a Guided Week in which one Student never opens Week 1 is taken over
by the sweep at the absent Seat's due time and advances (FR-24, FR-36); the Students' Setestatus
on Spill and Hjem names the AI player and whom it orders for, the Student whose Seat it was is
told so, with the requirement warning in an Obligatorisk session, and the immediate Takeover
notice mail never counts Uker (FR-34, FR-17, FR-14, UX-DR62, UX-DR69)."""

import re
import uuid
from datetime import timedelta

from app.modules.messaging import delivery
from app.modules.ops import sweep
from app.modules.sessions import service
from app.platform.db import get_sessionmaker
from app.platform.email.render import Recipient, Section, render
from tests.classes.test_invitation_counts import execute
from tests.conftest import TEST_DATABASE_URL
from tests.games.helpers import query
from tests.messaging.helpers import drain, mails
from tests.sessions.test_guided_weeks import view as view_as
from tests.sessions.test_orders import code, order
from tests.sessions.test_play import play, running
from tests.sessions.test_student_home import _empty, clock, home, klass

__all__ = ["_empty", "clock", "klass"]


def due(game_id: str, role: str) -> object:
    [(at,)] = query(
        TEST_DATABASE_URL,
        "SELECT t.takeover_due_at FROM seat_turns t JOIN seats s ON s.id = t.seat_id "
        "WHERE t.game_id = %s AND t.week = 1 AND s.role = %s",
        (game_id, role),
    )
    return at


def seat(seats: list[dict], role: str) -> dict:
    return next(s for s in seats if s["role"] == role)


async def test_the_absent_seat_is_taken_over_and_every_student_sees_it(klass):
    session_id, game_id, by_role = await running(klass, students=2)
    first, absent = by_role
    execute("UPDATE class_sessions SET obligatory = true WHERE id = %s", session_id)
    name = seat((await home(by_role[first]))["game"]["seats"], absent)["name"]
    assert name
    assert (await view_as(by_role[first], game_id, 1)).status_code == 204
    at = due(game_id, absent)
    assert at is not None
    await sweep.run(at + timedelta(seconds=30))

    # The Week advanced at once: the other Student plays Week 2.
    envelope = (await play(by_role[first], game_id)).json()
    assert envelope["seat_state"]["week"] == 2
    row = seat(envelope["table_status"]["seats"], absent)
    assert (row["holder"], row["taken_over"], row["ordering_for"], row["mine"]) == (
        "ai",
        True,
        name,
        False,
    )
    assert row["mark"] == "takeover_inactivity" and row["guard_switched"] is False
    assert seat(envelope["table_status"]["seats"], first)["taken_over"] is False

    # The Student whose Seat it was still reads the game: their own row is the AI player's.
    own = (await home(by_role[absent]))["game"]
    mine = seat(own["seats"], absent)
    assert (mine["mine"], mine["taken_over"], mine["holder"]) == (True, True, "ai")
    assert own["obligatory"] is True
    assert (await home(by_role[first]))["game"]["obligatory"] is True
    # An Order the Student sends after the Takeover is not theirs to place.
    sent = await order(by_role[absent], game_id, 2, {"order": 9})
    assert code(sent) == (409, "seat_not_yours")

    # The immediate notices go out through the mail pipeline, one mail to each Student.
    await drain()
    sent_to = sorted(
        mail.to for mail in mails() if mail.subject == "KI-spiller har tatt over et sete"
    )
    assert sent_to == sorted([by_role[first], by_role[absent]])
    own_sent = next(
        mail
        for mail in mails()
        if mail.to == by_role[absent] and mail.subject == "KI-spiller har tatt over et sete"
    )
    assert "KI-spiller har bestilt for deg" in own_sent.html and "påvirke" in own_sent.html

    # One immediate notice each; the mail never holds a number of Uker.
    notices = query(
        TEST_DATABASE_URL,
        "SELECT n.user_id, n.ref FROM notices n WHERE n.kind = 'takeover_notice'",
    )
    assert len(notices) == 2
    [ref] = {ref for _, ref in notices}
    users = dict(
        query(
            TEST_DATABASE_URL,
            "SELECT email, id FROM users WHERE email = ANY(%s)",
            ([by_role[first], by_role[absent]],),
        )
    )
    async with get_sessionmaker()() as s:
        own_context = await service.takeover_mail_context(s, users[by_role[absent]], ref, at)
        other_context = await service.takeover_mail_context(s, users[by_role[first]], ref, at)
        assert (
            await service.takeover_mail_context(s, users[by_role[first]], uuid.uuid7(), at) is None
        )
    assert own_context is not None and other_context is not None
    assert (own_context["own"], own_context["obligatory"]) == (True, True)
    assert (other_context["own"], other_context["student"]) == (False, name)
    template = delivery.KINDS["takeover_notice"].template
    own_mail = render(Recipient("a@x.no", context=own_context), [Section(template)], digest=False)
    other_mail = render(
        Recipient("b@x.no", context=other_context), [Section(template)], digest=False
    )
    assert own_mail.text.startswith("ØL-spillet")
    assert "KI-spiller har bestilt for deg" in own_mail.text
    assert "obligatorisk" in own_mail.text and "påvirke" in own_mail.text
    assert f"KI-spiller bestiller nå for {name}" in other_mail.text
    assert "obligatorisk" not in other_mail.text
    for mail in (own_mail, other_mail):
        body = mail.text.split("Hei", 1)[1].split("Hilsen")[0]
        # Only the game number is a figure; never how many Uker.
        assert not re.search(r"\buke", body, re.IGNORECASE)
