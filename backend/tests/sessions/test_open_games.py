"""The Class games open on the frozen snapshot (Story 5.12, FR-7, FR-20, FR-22, FR-30, FR-34,
AD-2, AD-4, AD-5, AD-8, AD-9): after the lock every Class game gets the Class session's snapshot
and AI players in its empty Seats, with no confirmed allocation the lock allocates first, a
removed Student's Seat goes to an AI player, and an open cut short is finished by the next sweep.
The api's clock is fixed and the sweep is handed its `now`; the database clock is never read."""

import uuid

from app.modules.games import commands as games_commands
from app.modules.ops import sweep
from app.modules.sessions import service
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_student_registration import emitted
from tests.messaging.helpers import rows
from tests.sessions.test_ai_mode import two_levels
from tests.sessions.test_allocation import open_, read, students
from tests.sessions.test_allocation_confirm import confirm
from tests.sessions.test_dates import START, student_of
from tests.sessions.test_lock import MINUTE, _empty, dated, locked

__all__ = ["_empty", "clock", "emitted", "klass", "two_levels"]


def games_of(session_id: str) -> list[tuple]:
    """(id, number, lifecycle, version, settings, session_runtime) by game number."""
    return rows(
        "SELECT id::text, game_number, lifecycle, version, settings, session_runtime FROM games "
        "WHERE class_session_id = %s ORDER BY game_number",
        session_id,
    )


def holders(session_id: str) -> list[tuple]:
    """Each Seat's current occupant: (game number, Role, kind, reason, user id)."""
    return rows(
        "SELECT DISTINCT ON (s.id) g.game_number, s.role, o.occupant_kind, o.reason, "
        "o.user_id::text FROM games g JOIN seats s ON s.game_id = g.id "
        "LEFT JOIN seat_occupancy o ON o.seat_id = s.id WHERE g.class_session_id = %s "
        "ORDER BY s.id, o.id DESC",
        session_id,
    )


async def confirmed(klass: str, n: int, ai_mode: str = "rule_based") -> tuple[str, list]:
    seated = await students(klass, n)
    session_id = await dated(klass, ai_mode)
    shown = (await open_(session_id)).json()["draft"]
    assert (await confirm(session_id, shown)).status_code == 200
    return session_id, seated


async def test_every_class_game_opens_on_the_snapshot_with_ai_players(klass, emitted, monkeypatch):
    async def dummy(session, class_session):
        return {"version": 7}

    monkeypatch.setattr(service, "_pin_providers", {"dummy": dummy})
    session_id, seated = await confirmed(klass, 6)
    before = [g[3] for g in games_of(session_id)]
    emitted.clear()
    assert (await sweep.run(START + MINUTE))["sessions.lock"] == 1
    snapshot = locked(session_id)[1]
    games = games_of(session_id)
    # One version step per Game.
    assert [(g[1], g[2], g[3]) for g in games] == [
        (1, "not_started", before[0] + 1),
        (2, "not_started", before[1] + 1),
    ]
    for game in games:
        assert game[4] == snapshot["settings"] and game[5] == snapshot["session_runtime"]
        assert game[5]["pins"] == {"dummy": {"version": 7}}
    seats = holders(session_id)
    assert len(seats) == 8 and all(kind is not None for _, _, kind, _, _ in seats)
    assert sorted(user for *_, user in seats if user) == sorted(str(s) for s in seated)
    assert {(kind, reason) for _, _, kind, reason, user in seats if not user} == {
        ("rule_based", "initial")
    }
    # The staff and every seated Student hear of it; each Game announces itself.
    assert ("session", session_id) in emitted
    assert {i for t, i in emitted if t == "user"} == {str(s) for s in seated}
    assert {i for t, i in emitted if t == "game"} == {g[0] for g in games}
    # The «Fordeling» block lists the Class games as their Seats hold them, all not started.
    body = (await read(session_id)).json()
    assert body["opened"] is True and body["missing_count"] == 0
    listed = body["draft"]["games"]
    assert [(g["number"], g["lifecycle"], len(g["seats"])) for g in listed] == [
        (1, "not_started", 4),
        (2, "not_started", 4),
    ]
    named = [s for g in listed for s in g["seats"] if s["user_id"]]
    assert len(named) == 6 and all(s["name"] for s in named)
    assert [s["role"] for s in listed[0]["seats"]] == [
        "factory",
        "distributor",
        "wholesaler",
        "retailer",
    ]
    # `start` no longer answers game_not_ready, and the next sweep has nothing to do.
    assert await games_commands.start(games[0][0]) == 1
    assert (await sweep.run(START + 2 * MINUTE))["sessions.lock"] == 0


async def test_llm_players_take_the_empty_seats(klass, two_levels):
    session_id, _ = await confirmed(klass, 2, "llm")
    await sweep.run(START + MINUTE)
    kinds = sorted(kind for _, _, kind, _, _ in holders(session_id))
    assert kinds == ["llm", "llm", "student", "student"]
    assert games_of(session_id)[0][5]["model_config_id"] == str(two_levels)


async def test_with_no_confirmed_allocation_the_lock_allocates_first(klass, emitted):
    seated = await students(klass, 5)
    session_id = await dated(klass)
    previewed = (await open_(session_id)).json()["draft"]
    emitted.clear()
    assert (await sweep.run(START + MINUTE))["sessions.lock"] == 1
    # A fresh draw replaces the preview, confirmed by nobody at the lock.
    ((draft_id, confirmed_at, confirmed_by, drawn_by),) = rows(
        "SELECT id::text, confirmed_at, confirmed_by, drawn_by FROM allocation_drafts "
        "WHERE class_session_id = %s",
        session_id,
    )
    assert draft_id != previewed["id"]
    assert (confirmed_at, confirmed_by, drawn_by) == (START + MINUTE, None, None)
    assert [g[1] for g in games_of(session_id)] == [1, 2]
    seats = holders(session_id)
    assert sorted(user for *_, user in seats if user) == sorted(str(s) for s in seated)
    assert all(kind is not None for _, _, kind, _, _ in seats)
    # Each Student gets the allocation notice of Story 5.9.
    assert rows("SELECT count(*) FROM notices WHERE kind = 'allocation_confirmed'") == [(5,)]
    assert {i for t, i in emitted if t == "user"} == {str(s) for s in seated}
    assert {t for t, _ in emitted} == COMMAND_TOPICS["sessions.lock"]
    assert (await read(session_id)).json()["opened"] is True
    # A Student who registers after the open holds no Seat, and the block says so.
    await student_of(klass, "sen@x.no")
    body = (await read(session_id)).json()
    assert (body["opened"], body["registered_count"], body["missing_count"]) == (True, 6, 1)


async def test_a_preview_of_students_who_all_left_is_cleared_at_the_lock(klass):
    await students(klass, 2)
    session_id = await dated(klass)
    assert (await open_(session_id)).json()["draft"] is not None
    execute("UPDATE roster_entries SET removed_at = %s WHERE class_id = %s", NOW, klass)
    await sweep.run(START + MINUTE)
    body = (await read(session_id)).json()
    assert (body["draft"], body["opened"], games_of(session_id)) == (None, False, [])


async def test_no_allocation_for_an_archived_class_or_without_students(klass):
    empty = await dated(klass)
    assert (await sweep.run(START + MINUTE))["sessions.lock"] == 1
    assert locked(empty)[0] is not None and games_of(empty) == []
    assert (await read(empty)).json()["opened"] is False
    await students(klass, 3)
    archived = await dated(klass)
    execute("UPDATE classes SET archived_at = %s WHERE id = %s", NOW, klass)
    assert await service.lock(uuid.UUID(archived), now=START) is True
    assert games_of(archived) == []


async def test_a_removed_students_seat_goes_to_an_ai_player(klass):
    session_id, seated = await confirmed(klass, 4)
    gone = seated[0]
    execute("UPDATE roster_entries SET removed_at = %s WHERE user_id = %s", NOW, gone)
    await sweep.run(START + MINUTE)
    history = rows(
        "SELECT o.occupant_kind, o.reason, o.user_id::text FROM seat_occupancy o "
        "JOIN seats s ON s.id = o.seat_id "
        "WHERE s.id = (SELECT seat_id FROM seat_occupancy WHERE user_id = %s) ORDER BY o.id",
        gone,
    )
    assert history == [("student", "initial", str(gone)), ("rule_based", "initial", None)]
    body = (await read(session_id)).json()
    assert body["registered_count"] == 3 and body["missing_count"] == 0
    users = {s["user_id"] for g in body["draft"]["games"] for s in g["seats"]} - {None}
    assert users == {str(s) for s in seated[1:]}


async def test_an_open_cut_short_is_finished_by_the_next_sweep(klass, monkeypatch):
    session_id, _ = await confirmed(klass, 5)
    real = games_commands.set_snapshot
    calls: list[str] = []

    async def fails_after_the_first(game_id, snapshot, *, keep_students):
        calls.append(game_id)
        if len(calls) > 1:
            raise RuntimeError("the process stopped")
        return await real(game_id, snapshot, keep_students=keep_students)

    monkeypatch.setattr(games_commands, "set_snapshot", fails_after_the_first)
    waiting = games_of(session_id)[1][3]
    # The lock stands; the Game that failed is logged and left for the next sweep.
    assert (await sweep.run(START + MINUTE))["sessions.lock"] == 1
    first, second = games_of(session_id)
    assert locked(session_id)[0] is not None
    assert first[4] is not None and (second[3], second[4]) == (waiting, None)
    # The half-open session is not shown as open.
    assert (await read(session_id)).json()["opened"] is False
    monkeypatch.setattr(games_commands, "set_snapshot", real)
    assert (await sweep.run(START + 2 * MINUTE))["sessions.lock"] == 1
    again_first, again_second = games_of(session_id)
    assert again_first == first  # untouched: same version, same snapshot
    assert again_second[4] == first[4] and again_second[3] == waiting + 1
    assert (await sweep.run(START + 3 * MINUTE))["sessions.lock"] == 0
