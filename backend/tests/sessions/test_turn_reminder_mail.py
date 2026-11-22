"""Story 8.13 through the mail pipeline: a Student the Class game has waited for gets the
`turn_reminder` digest, gathered with the day's other notices into one mail and never sent
between 22:00 and 07:00 Europe/Oslo (FR-27, AD-9); a game that no longer waits for them is left
out (ordered, taken over, finished, paused); the mail names no Uke (FR-14, FR-72).

The reminder and Takeover times are written directly and the sweep runs on a controlled clock;
nothing is compared with the host's clock (Issue #63)."""

import re
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.modules.games import commands
from app.modules.messaging import delivery
from app.modules.ops import sweep
from app.modules.sessions import service
from app.platform.db import get_sessionmaker
from app.platform.email.render import Recipient, Section, render
from tests.conftest import TEST_DATABASE_URL
from tests.games.helpers import execute, query
from tests.games.test_set_snapshot import SETTINGS, snapshot
from tests.games.test_takeover import _user
from tests.messaging.helpers import drain, mails
from tests.sessions.test_dates import START
from tests.sessions.test_play import running
from tests.sessions.test_student_home import _empty, clock, klass

__all__ = ["_empty", "clock", "klass"]

OSLO = ZoneInfo("Europe/Oslo")
DAY = START.astimezone(OSLO).date() + timedelta(days=3)


def oslo(hour: int, minute: int = 0, days: int = 0) -> datetime:
    """The controlled clock: a day after the Class session's start, Europe/Oslo."""
    return datetime.combine(DAY + timedelta(days=days), datetime.min.time(), OSLO).replace(
        hour=hour, minute=minute
    )


def user_of(email: str) -> uuid.UUID:
    [(found,)] = query(TEST_DATABASE_URL, "SELECT id FROM users WHERE email = %s", (email,))
    return found


def due_at(game_id: str, user_id: uuid.UUID, at: datetime) -> uuid.UUID:
    """The reminder of `user_id`'s turn in the open Week due at `at`, with Takeover days later;
    returns the turn id. The turn must have its own reminder time already: the Student's wait has
    started (an Order, or a view of a Guided Week)."""
    [(turn_id, stored)] = query(
        TEST_DATABASE_URL,
        "SELECT t.id, t.reminder_due_at FROM seat_turns t "
        "JOIN seat_occupancy o ON o.seat_id = t.seat_id "
        "WHERE t.game_id = %s AND o.user_id = %s AND t.week = "
        "(SELECT max(week) FROM game_weeks WHERE game_id = %s AND NOT finished)",
        (game_id, user_id, game_id),
    )
    assert stored is not None
    execute(
        TEST_DATABASE_URL,
        "UPDATE seat_turns SET reminder_due_at = %s, takeover_due_at = %s, "
        "insert_allowed_at = %s WHERE id = %s",
        (at, at + timedelta(days=3), at + timedelta(days=3), turn_id),
    )
    return turn_id


async def sweep_at(now: datetime) -> None:
    await sweep.run(now)
    await drain(now)


def digests_to(email: str) -> list:
    return [m for m in mails() if m.to == email and m.subject == "Nytt fra ØL-spillet"]


async def test_two_waiting_games_give_one_morning_mail_without_any_week(klass):
    session_id, game_id, by_role = await running(klass, students=2)
    first, absent = by_role
    student, other = user_of(by_role[absent]), user_of(by_role[first])
    # Week 1 is a Guided Week: opening it counts as ordering (FR-24).
    await commands.view_week(game_id, first, 1, actor=other)
    # A second Class game of the session waits for the same Student (game number 9). A Student
    # holds one Seat per Class session, so this Seat is written directly.
    second = await commands.create("class", class_session_id=uuid.UUID(session_id), game_number=9)
    partner = _user()
    await commands.assign_seat(second, "retailer", "student", user_id=partner)
    execute(
        TEST_DATABASE_URL,
        "INSERT INTO seat_occupancy (id, seat_id, from_week, occupant_kind, reason, user_id) "
        "SELECT %s, id, 1, 'student', 'initial', %s FROM seats WHERE game_id = %s "
        "AND role = 'factory'",
        (uuid.uuid7(), student, second),
    )
    frozen = {
        **snapshot(),
        "settings": SETTINGS.model_copy(update={"guided_weeks": 0}).model_dump(mode="json"),
    }
    await commands.set_snapshot(second, frozen, keep_students=[partner, student])
    await commands.start(second)
    await commands.place_order(second, "retailer", 1, 4, "student", actor=partner)

    tonight = oslo(23, 10)
    first_turn = due_at(game_id, student, tonight)
    due_at(second, student, tonight)
    await drain(START + timedelta(minutes=2))  # the setup's own digests go first
    before = len(digests_to(by_role[absent]))
    await sweep_at(tonight - timedelta(minutes=1))
    [(count,)] = query(
        TEST_DATABASE_URL,
        "SELECT count(*) FROM notices WHERE kind = 'turn_reminder' AND user_id = %s",
        (student,),
    )
    assert count == 0
    # Queued at 23:10, held through the night (AD-9).
    for now in (tonight, oslo(23, 11), oslo(6, 59, days=1)):
        await sweep_at(now)
    keys = query(
        TEST_DATABASE_URL,
        "SELECT dedupe_key FROM notices WHERE kind = 'turn_reminder' AND user_id = %s",
        (student,),
    )
    assert sorted(k for (k,) in keys) == sorted(
        f"turn_reminder:{student}:{g}:1" for g in (game_id, second)
    )
    assert len(digests_to(by_role[absent])) == before
    await sweep_at(oslo(7, 0, days=1))
    [mail] = digests_to(by_role[absent])[before:]
    for number in (1, 9):
        assert f"Spill {number} i Klassen class-of-1994 venter på bestillingen din" in mail.text
    assert "/hjem" in mail.html and "/hjem" in mail.text
    body = mail.text.split("Hei", 1)[1].split("Hilsen")[0]
    assert not re.search(r"\buke", body, re.IGNORECASE)  # never how many Uker (FR-14)
    # The Student who ordered is not reminded.
    assert not query(
        TEST_DATABASE_URL,
        "SELECT 1 FROM notices WHERE kind = 'turn_reminder' AND user_id = %s",
        (other,),
    )

    # A game that no longer waits is left out of a later mail: ordered, paused, finished.
    async with get_sessionmaker()() as s:
        assert await service.turn_reminder_mail_context(s, student, first_turn, tonight) == {
            "class_name": "class-of-1994",
            "game_number": 1,
            "role": absent,
        }
        assert await service.turn_reminder_mail_context(s, other, first_turn, tonight) is None
        assert await service.turn_reminder_mail_context(s, student, uuid.uuid7(), tonight) is None
    # A Pause begun after the reminder was queued keeps it: the turn is marked already.
    await commands.pause(game_id, actor=other)
    async with get_sessionmaker()() as s:
        assert await service.turn_reminder_mail_context(s, student, first_turn, tonight) is not None
    await commands.view_week(game_id, absent, 1, actor=student)
    execute(TEST_DATABASE_URL, "UPDATE games SET lifecycle = 'finished' WHERE id = %s", (second,))
    second_turn = due_at(second, student, tonight)
    async with get_sessionmaker()() as s:
        assert await service.turn_reminder_mail_context(s, student, first_turn, tonight) is None
        assert await service.turn_reminder_mail_context(s, student, second_turn, tonight) is None


async def test_a_reminder_whose_seat_was_taken_over_gives_no_mail(klass):
    _, game_id, by_role = await running(klass, students=2)
    first, absent = by_role
    student = user_of(by_role[absent])
    await commands.view_week(game_id, first, 1, actor=user_of(by_role[first]))
    at = oslo(9, 0)
    turn_id = due_at(game_id, student, at)
    [(seat_id,)] = query(
        TEST_DATABASE_URL, "SELECT seat_id FROM seat_turns WHERE id = %s", (turn_id,)
    )
    assert await commands.queue_turn_reminder(game_id, str(seat_id), now=at)
    await commands.takeover(game_id, absent, actor="staff", actor_user_id=uuid.uuid7())
    await drain(START + timedelta(minutes=2))  # the setup's own digests go first
    before = len(digests_to(by_role[absent]))
    await sweep_at(at + timedelta(minutes=1))
    # The only notice in the digest is stale: no mail mentions the game.
    later = digests_to(by_role[absent])[before:]
    assert all("venter på bestillingen din" not in m.text for m in later)
    [(claimed,)] = query(
        TEST_DATABASE_URL,
        "SELECT claimed_at FROM notices WHERE kind = 'turn_reminder' AND user_id = %s",
        (student,),
    )
    assert claimed is not None  # built and left out, not still waiting


def test_the_reminder_renders_in_norwegian_with_a_link_to_hjem():
    template = delivery.KINDS["turn_reminder"].template
    context = {"class_name": "Logistikk", "game_number": 3, "role": "wholesaler"}
    mail = render(Recipient("a@x.no", context=context), [Section(template)], digest=False)
    assert mail.text.startswith("ØL-spillet")
    assert mail.subject == "Spillet venter på deg"
    assert "Spill 3 i Klassen Logistikk venter på bestillingen din som Grossist." in mail.text
    assert "/hjem" in mail.html and "/hjem" in mail.text
    body = mail.text.split("Hei", 1)[1].split("Hilsen")[0]
    assert not re.search(r"\buke|\d+\s*(kasser|enheter)", body, re.IGNORECASE)
    assert not re.search(r"\buke", mail.html, re.IGNORECASE)
