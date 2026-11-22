"""Spillinnsikt's read (Story 7.7, FR-62, FR-34, FR-5, AD-1, AD-3, AD-12, AD-15, NFR-7):
`GET /api/games/{id}/insight` answers the Class's staff with one Class game week by week — per
Role and opened Week the stored incoming order and delivery, inventory, backlog, the Order from the
Decision log, that Week's cost, who held the Seat and its marks — with the Seats, their link slots,
the customer demand series and the number of Weeks; anyone else gets the same 403.

One short Class game (`short_game`, 6 Weeks, two Students and two Rule-based players) per test."""

import uuid
from datetime import datetime
from decimal import Decimal

from app.engine import GameSettings
from app.modules.games import commands
from app.modules.games import service as games_service
from app.modules.identity.schemas import AccountRole
from tests.classes.test_classes import LECTURER, OTHER, make
from tests.classes.test_staff import ASSISTANT, call, put_staff
from tests.conftest import TEST_DATABASE_URL
from tests.games.helpers import tamper
from tests.messaging.helpers import rows
from tests.sessions.test_game_end import _empty, clock, emitted, klass, play_weeks, short_game
from tests.sessions.test_open_games import confirmed
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "emitted", "klass"]

ADMIN = "admin-only@x.no"
CHAIN = ["retailer", "wholesaler", "distributor", "factory"]


async def insight(who: str, game_id: str, **kw):
    return await call(who, "GET", f"/api/games/{game_id}/insight", **kw)


def stored(game_id: str) -> dict[tuple[int, str], tuple[int, int, int, int, Decimal]]:
    """Per (Week, Role) the stored incoming order and delivery, inventory, backlog and cost."""
    found = rows(
        "SELECT w.week, s->>'role', (s->>'incoming_order')::int, (s->>'incoming_delivery')::int, "
        "(s->>'inventory')::int, (s->>'backlog')::int, (s->>'cost')::numeric "
        "FROM game_weeks w, jsonb_array_elements(w.state->'seats') s "
        "WHERE w.game_id = %s AND NOT w.finished",
        game_id,
    )
    return {(week, role): tuple(values) for week, role, *values in found}


def orders(game_id: str) -> dict[tuple[int, str], int]:
    found = rows(
        'SELECT w.week, s.role, w."order" FROM seat_weeks w JOIN seats s ON s.id = w.seat_id '
        "WHERE w.game_id = %s",
        game_id,
    )
    return {(week, role): order for week, role, order in found}


def clock_of(game_id: str) -> dict[tuple[int, str], tuple]:
    """Per (Week, Role) the turn's stored opened_at, ordered_at and viewed_at (Story 8.1)."""
    found = rows(
        "SELECT t.week, s.role, t.opened_at, t.ordered_at, t.viewed_at FROM seat_turns t "
        "JOIN seats s ON s.id = t.seat_id WHERE t.game_id = %s",
        game_id,
    )
    return {(week, role): tuple(values) for week, role, *values in found}


def at(value: str | None) -> datetime | None:
    return None if value is None else datetime.fromisoformat(value)


def holders(game_id: str) -> dict[str, tuple[str, str | None]]:
    """Each Role's current occupant kind and Student name (from `users`)."""
    found = rows(
        "SELECT s.role, o.occupant_kind, u.name FROM seats s "
        "JOIN LATERAL (SELECT * FROM seat_occupancy WHERE seat_id = s.id "
        "ORDER BY id DESC LIMIT 1) o ON true LEFT JOIN users u ON u.id = o.user_id "
        "WHERE s.game_id = %s",
        game_id,
    )
    return {role: (kind, name) for role, kind, name in found}


async def test_staff_read_every_week_of_every_role_as_stored(klass):
    _, game_id, _ = await short_game(klass)
    await play_weeks(game_id, 2)  # Weeks 1 and 2 have run; Week 3 is open
    response = await insight(LECTURER, game_id)
    assert response.status_code == 200
    body = response.json()
    assert (body["game_id"], body["status"], body["weeks_total"]) == (game_id, "running", 6)
    assert body["game_number"] == 1 and body["session_number"] >= 1 and body["class_name"]
    [(version,)] = rows("SELECT version FROM games WHERE id = %s", game_id)
    assert body["version"] == version
    held = holders(game_id)
    assert [seat["role"] for seat in body["seats"]] == CHAIN
    for seat in body["seats"]:
        kind, name = held[seat["role"]]
        assert seat["holder"] == ("student" if kind == "student" else "ai")
        assert seat["name"] == (name if kind == "student" else None)
        assert seat["links"] == []  # the Debrief's links come once the game has finished
    values, placed, clock = stored(game_id), orders(game_id), clock_of(game_id)
    [(guided_weeks,)] = rows(
        "SELECT (settings->>'guided_weeks')::int FROM games WHERE id = %s", game_id
    )
    assert [role["role"] for role in body["roles"]] == CHAIN
    for role in body["roles"]:
        assert [week["week"] for week in role["weeks"]] == [1, 2, 3]
        kind, name = held[role["role"]]
        for week in role["weeks"]:
            key = (week["week"], role["role"])
            incoming_order, incoming_delivery, inventory, backlog, cost = values[key]
            assert (
                week["incoming_order"],
                week["incoming_delivery"],
                week["inventory"],
                week["backlog"],
            ) == (incoming_order, incoming_delivery, inventory, backlog)
            assert isinstance(week["cost"], str) and Decimal(week["cost"]) == cost
            assert week["order"] == placed.get(key)
            assert week["holder"] == ("student" if kind == "student" else "ai")
            assert week["name"] == (name if kind == "student" else None)
            assert week["marks"] == []
            # When the Week opened and when the Seat ordered (Story 8.1, FR-35): in a Guided
            # Week a Student's Seat ordered when the Student opened the Week (FR-24).
            opened, ordered, viewed = clock[key]
            guided = week["week"] <= guided_weeks and kind == "student"
            assert at(week["opened_at"]) == opened
            assert at(week["ordered_at"]) == (viewed if guided else ordered)
        # The first stored Order of 10 or more (Story 7.8), none in the open Week.
        large = [w for w in (1, 2, 3) if (placed.get((w, role["role"])) or 0) >= 10]
        assert role["first_large_order_week"] == (large[0] if large else None)
    # The open Week's Student Seats have not ordered: no Order yet.
    assert any(r["weeks"][2]["order"] is None for r in body["roles"])
    assert body["demand"] == [{"week": w, "demand": values[(w, "retailer")][0]} for w in (1, 2, 3)]
    assert response.headers["cache-control"] == "private, no-cache"
    # An Assistant lecturer of the Class reads the same; the ETag answers 304 until a change.
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")
    assistant = await insight(ASSISTANT, game_id)
    # The same answer, but only a Lecturer may pause the game (Story 8.7, AD-12).
    assert body["can_pause"] is True
    # Story 8.9: Tilrettelegging (the names' Studentside) is for Lecturers only.
    assert body["can_adjust"] is True
    # Story 8.11: «Marker som i rommet» is for Lecturers only.
    assert body["can_mark_in_room"] is True
    assert (assistant.status_code, assistant.json()) == (
        200,
        {**body, "can_pause": False, "can_adjust": False, "can_mark_in_room": False},
    )
    etag = response.headers["etag"]
    repeat = await insight(LECTURER, game_id, headers={"If-None-Match": etag})
    assert (repeat.status_code, repeat.content) == (304, b"")
    await play_weeks(game_id, 3)
    changed = await insight(LECTURER, game_id, headers={"If-None-Match": etag})
    assert changed.status_code == 200
    assert [w["week"] for w in changed.json()["roles"][0]["weeks"]] == [1, 2, 3, 4]


async def test_in_an_open_guided_week_a_student_who_has_not_opened_it_has_not_ordered(klass):
    """Story 8.1, FR-24: the Guided Order was placed when the Week opened, but the Student's Seat
    orders when the Student opens the Week; the AI Seats ordered at the opening."""
    _, game_id, _ = await short_game(klass)
    body = (await insight(LECTURER, game_id)).json()
    held = holders(game_id)
    clock = clock_of(game_id)
    for role in body["roles"]:
        [week] = role["weeks"]
        opened, ordered, _ = clock[(1, role["role"])]
        assert at(week["opened_at"]) == opened
        student = held[role["role"]][0] == "student"
        assert at(week["ordered_at"]) == (None if student else ordered)
        assert ordered is not None  # the Order itself is placed


async def test_anyone_but_the_staff_and_any_unlisted_game_is_refused_the_same(klass):
    session_id, game_id, _ = await short_game(klass)
    await make(ADMIN, roles=(AccountRole.admin,))
    test_game = await commands.create(
        "lecturer_test", GameSettings(), class_session_id=uuid.UUID(session_id)
    )
    refused = [
        await insight(email(0), game_id),  # a Student of the Class, seated in the game
        await insight(OTHER, game_id),  # a Lecturer of another Class
        await insight(ADMIN, game_id),  # an Admin not attached to the Class
        await insight(LECTURER, str(test_game)),  # a test Game is in no staff list (AD-13)
        await insight(LECTURER, str(uuid.uuid7())),  # no such Game
        await insight(LECTURER, "not-an-id"),
    ]
    assert {r.status_code for r in refused} == {403}
    assert len({r.content for r in refused}) == 1


async def test_a_game_not_started_has_its_seats_and_no_weeks(klass):
    session_id, _ = await confirmed(klass, 2)
    [(game_id,)] = rows(
        "SELECT id FROM games WHERE class_session_id = %s ORDER BY game_number LIMIT 1",
        session_id,
    )
    body = (await insight(LECTURER, str(game_id))).json()
    assert body["status"] == "not_started"
    assert [seat["role"] for seat in body["seats"]] == CHAIN
    assert sum(seat["holder"] == "student" and seat["name"] is not None for seat in body["seats"])
    assert body["demand"] == []
    assert all(role["weeks"] == [] for role in body["roles"])


REASON_MARKS = [
    ("cost_limit", "cost_limit"),
    ("takeover_inactivity", "takeover_inactivity"),
    ("takeover_staff", "takeover_staff"),
    ("takeover_peer", "takeover_peer"),
    ("reclaim", "reclaim"),
    ("playout", "playout"),
]
FALLBACK_MARKS = [
    ("timeout", "fallback_timeout"),
    ("invalid_output", "fallback_invalid_output"),
    ("budget_exhausted", "fallback_budget_exhausted"),
    ("provider_error", "fallback_provider_error"),
]


async def test_every_reason_and_fallback_shows_its_mark_and_links_reach_student_seats(klass):
    _, game_id, _ = await short_game(klass)
    await play_weeks(game_id, 99)  # finished: six Weeks with a Decision log row per Seat
    held = holders(game_id)
    first_ai, second_ai = [role for role in CHAIN if held[role][0] != "student"]
    student = next(role for role in CHAIN if held[role][0] == "student")

    def log(role: str, week: int, **values: str | int) -> None:
        sets = ", ".join(f'"{column}" = %s' for column in values)
        tamper(
            TEST_DATABASE_URL,
            f"UPDATE seat_weeks w SET {sets} FROM seats s "
            "WHERE s.id = w.seat_id AND w.game_id = %s AND s.role = %s AND w.week = %s",
            (*values.values(), game_id, role, week),
        )

    # Fixture rows: one occupancy reason a Week on one AI Seat (each differs from the last, so
    # each Week shows its seat mark), a Play guard switch and every fallback on the other.
    for week, (reason, _) in enumerate(REASON_MARKS, start=1):
        log(first_ai, week, reason=reason)
    log(second_ai, 1, occupant_kind="rule_based", reason="guard_switch")
    for week, (fallback, _) in enumerate(FALLBACK_MARKS, start=2):
        log(second_ai, week, occupant_kind="rule_based", reason="guard_switch", fallback=fallback)

    # A Takeover appended in the last Week after the Student's Order there: that Week was still
    # played by the Student, named as such; the Seat is now held by an AI player.
    [(student_seat, student_id)] = rows(
        "SELECT s.id, o.user_id FROM seats s JOIN seat_occupancy o ON o.seat_id = s.id "
        "WHERE s.game_id = %s AND s.role = %s AND o.user_id IS NOT NULL",
        game_id,
        student,
    )
    tamper(
        TEST_DATABASE_URL,
        "INSERT INTO seat_occupancy (id, seat_id, from_week, occupant_kind, reason) "
        "VALUES (%s, %s, 6, 'rule_based', 'takeover_staff')",
        (uuid.uuid7(), student_seat),
    )
    [(student_name,)] = rows("SELECT name FROM users WHERE id = %s", student_id)
    # Ordrestolper's first large Order (Story 7.8): the first Week at 10 or more, never a smaller
    # one before it; a Role whose Orders all stay under 10 has none.
    for week, order in enumerate((4, 9, 10, 15, 3, 30), start=1):
        log(student, week, order=order)
    for week in range(1, 7):
        log(first_ai, week, order=9)

    async def provider(session, wanted):
        assert wanted == uuid.UUID(game_id)
        return [
            games_service.InsightLink(role=role, kind="explanation", href=f"/x/{role}")
            for role in CHAIN
        ]

    games_service.register_insight_links(provider)
    try:
        body = (await insight(LECTURER, game_id)).json()
    finally:
        games_service.unregister_insight_links(provider)
    assert body["status"] == "finished"
    by_role = {role["role"]: role["weeks"] for role in body["roles"]}
    assert [w["marks"] for w in by_role[first_ai]] == [[mark] for _, mark in REASON_MARKS]
    # The guard switch stands in the Week it began; each replaced Order is marked in its Week.
    assert [w["marks"] for w in by_role[second_ai]] == [
        ["guard_switch"],
        *[[mark] for _, mark in FALLBACK_MARKS],
        [],
    ]
    assert all(w["marks"] == [] for w in by_role[student])
    large = {role["role"]: role["first_large_order_week"] for role in body["roles"]}
    assert (large[student], large[first_ai]) == (3, None)
    assert [(w["holder"], w["name"]) for w in by_role[student]] == [("student", student_name)] * 6
    assert next(s for s in body["seats"] if s["role"] == student)["holder"] == "ai"
    # Links reach only the Student-held Seats (the Debrief's own are left out here).
    for seat in body["seats"]:
        expected = (
            [{"kind": "explanation", "href": f"/x/{seat['role']}"}]
            if seat["holder"] == "student"
            else []
        )
        assert [link for link in seat["links"] if link["href"].startswith("/x/")] == expected
