"""The play screen's envelope (Story 6.6, FR-14, FR-23, AD-3): `GET /api/me/games/{id}/play`
answers the Student's own running Class game with `seat_state` (their own Seat in the open Week,
numbers only), `table_status` (people only), `server_now` and `next_change_at`. It never holds the
number of Weeks, future demand, another Seat's numbers or a reference Order; a game that is not
running answers `game_not_running`; any other game is refused alike."""

import uuid
from datetime import datetime

from app.engine.demand import series
from app.engine.settings import GameSettings
from app.modules.games import commands
from app.modules.games import service as games_service
from app.modules.ops import sweep
from tests.classes.test_classes import make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_staff import call
from tests.messaging.helpers import rows
from tests.platform.test_event_stream import append_occupant, user_id
from tests.sessions.test_dates import OUTSIDER, START
from tests.sessions.test_lock import MINUTE
from tests.sessions.test_open_games import confirmed, games_of
from tests.sessions.test_start_game import start, task_done
from tests.sessions.test_student_choice import email
from tests.sessions.test_student_home import _empty, clock, home, klass

__all__ = ["_empty", "clock", "klass"]

# Keys no part of the envelope may hold (FR-14, FR-23): the length of the game, the demand
# series and its seed, the settings, and the reference Orders stored on the turns.
FORBIDDEN = {
    "weeks",
    "demand",
    "demand_seed",
    "demand_series",
    "settings",
    "guided_weeks",
    "rule_based_reference_order",
    "near_optimal_reference_order",
    "near_optimal_algorithm_version",
    "reference_order",
}


async def play(who: str, game_id: str):
    return await call(who, "GET", f"/api/me/games/{game_id}/play")


def keys(value) -> set[str]:
    """Every key anywhere in a JSON value."""
    if isinstance(value, dict):
        return set(value) | {k for item in value.values() for k in keys(item)}
    if isinstance(value, list):
        return {k for item in value for k in keys(item)}
    return set()


async def running(klass: str, students: int = 4) -> tuple[str, str, dict[str, str]]:
    """A started Class game with `students` Students: (session id, game id, email by Role)."""
    session_id, seated = await confirmed(klass, students)
    await sweep.run(START + MINUTE)
    game_id = (await home(email(0)))["game"]["id"]
    await task_done(seated[0], session_id)
    assert (await start(email(0), game_id)).status_code == 200
    by_role = {(await home(email(i)))["game"]["role"]: email(i) for i in range(students)}
    return session_id, game_id, by_role


async def played_to(game_id: str, roles: list[str], week: int) -> None:
    """Every Student Seat orders until `week` is open: views each Guided Week (Story 6.10), then
    Orders that differ by Role and Week."""
    settings = GameSettings()  # the Classic game the Class session froze
    holders = {seat.role: seat.user_id for seat in (await games_service.get_game(game_id)).seats}
    for current in range(1, week):
        for index, role in enumerate(roles):
            if current <= settings.guided_weeks:
                # The guided Order was placed when the Week opened; the view completes it (6.10).
                await commands.view_week(game_id, role, current, actor=holders[role])
            else:
                await commands.place_order(game_id, role, current, 4 + index + current, "student")


async def test_the_envelope_is_the_own_seat_in_the_open_week_for_every_role(klass):
    _, game_id, by_role = await running(klass)
    settings = (await games_service.get_game(game_id)).settings
    demand = list(series(settings.demand, 6, settings.demand_seed))
    await played_to(game_id, list(by_role), 6)
    for role, who in by_role.items():
        response = await play(who, game_id)
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {
            "seat_state",
            "turn",
            "table_status",
            "server_now",
            "next_change_at",
        }
        assert body["turn"] == {"guided": False, "order": None, "viewed": False}
        state = body["seat_state"]
        # The Seat's own state in the open Week, exactly as the one read model builds it.
        expected = await games_service.seat_state(game_id, role)
        assert state == expected.model_dump(mode="json")
        assert (state["role"], state["week"], state["schema_version"]) == (role, 6, 4)
        assert [row["week"] for row in state["history"]] == [1, 2, 3, 4, 5]
        assert state["net_inventory"] == state["inventory"] - state["backlog"]
        for row in state["history"]:
            assert row["net_inventory"] == row["inventory"] - row["backlog"]
        # One Week at a time: an incoming order per opened Week, nothing ahead of the open one.
        assert len(state["incoming_orders"]) == 6
        assert all(slot["arrival_week"] > 6 for slot in state["supply_line_slots"])
        # No other Seat's numbers; customer demand only as the Retailer's own incoming order: past
        # the Guided Weeks every other Role's incoming orders are its downstream Seat's Orders.
        assert state["neighbour_numbers"] == []
        if role == "retailer":
            assert state["incoming_orders"] == demand
        else:
            assert state["incoming_orders"] != demand
        assert not keys(body) & FORBIDDEN
        seats = body["table_status"]["seats"]
        assert [seat["role"] for seat in seats] == [
            "factory",
            "distributor",
            "wholesaler",
            "retailer",
        ]
        assert all(
            set(seat) == {"role", "holder", "name", "mine", "ordered", "wait_started_at", "mark"}
            for seat in seats
        )
        assert [seat["role"] for seat in seats if seat["mine"]] == [role]
        assert datetime.fromisoformat(body["server_now"]).tzinfo is not None
        assert body["next_change_at"] is None


async def test_a_game_that_is_not_running_has_no_envelope(klass):
    session_id, seated = await confirmed(klass, 1)
    await sweep.run(START + MINUTE)
    game_id = (await home(email(0)))["game"]["id"]
    refused = await play(email(0), game_id)  # ready, not started
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "game_not_running"
    await task_done(seated[0], session_id)
    assert (await start(email(0), game_id)).status_code == 200
    assert (await play(email(0), game_id)).status_code == 200
    execute("UPDATE games SET lifecycle = 'playing_out' WHERE id = %s", game_id)
    assert (await play(email(0), game_id)).status_code == 200
    execute("UPDATE games SET lifecycle = 'finished' WHERE id = %s", game_id)
    assert (await play(email(0), game_id)).json()["error"]["code"] == "game_not_running"


async def test_any_other_game_is_refused_alike(klass):
    session_id, seated = await confirmed(klass, 5)  # two Class games
    await sweep.run(START + MINUTE)
    for user in seated:
        await task_done(user, session_id)
    games = [g[0] for g in games_of(session_id)]
    started: set[str] = set()
    for i in range(5):  # both games running, so only ownership can refuse
        game_id = (await home(email(i)))["game"]["id"]
        if game_id not in started:
            assert (await start(email(i), game_id)).status_code == 200
            started.add(game_id)
        if len(started) == len(games):
            break
    await make(OUTSIDER, roles=())
    mine = (await home(email(0)))["game"]["id"]
    other = next(g for g in games if g != mine)
    refusals = [
        await play(email(0), other),
        await play(email(0), str(uuid.uuid7())),
        await play(email(0), "not-a-uuid"),
        await play(OUTSIDER, mine),
    ]
    assert {r.status_code for r in refusals} == {403}
    assert len({r.content for r in refusals}) == 1


async def test_hjem_carries_the_envelopes_own_seat_and_turn_while_running(klass):
    """Story 6.17 (AD-3): Hjem's Spillkort reads the play envelope's `seat_state` and own turn,
    so Hjem and the play screen never disagree; before the start and once finished, neither."""
    session_id, seated = await confirmed(klass, 2)
    await sweep.run(START + MINUTE)
    ready = await home(email(0))
    assert (ready["game"]["status"], ready["game"]["seat_state"], ready["game"]["turn"]) == (
        "ready",
        None,
        None,
    )
    game_id = ready["game"]["id"]
    await task_done(seated[0], session_id)
    assert (await start(email(0), game_id)).status_code == 200
    roles = [(await home(email(i)))["game"]["role"] for i in range(2)]
    await played_to(game_id, roles, 6)
    await commands.place_order(game_id, roles[0], 6, 9, "student")
    for i, ordered in ((0, 9), (1, None)):
        game = (await home(email(i)))["game"]
        envelope = (await play(email(i), game_id)).json()
        assert game["week"] == game["seat_state"]["week"] == 6
        assert game["seat_state"] == envelope["seat_state"]
        assert (
            game["turn"] == envelope["turn"] == {"guided": False, "order": ordered, "viewed": False}
        )
        assert [s["ordered"] for s in game["seats"] if s["mine"]] == [ordered is not None]
        assert not keys([game["seat_state"], game["turn"]]) & FORBIDDEN
    execute("UPDATE games SET lifecycle = 'finished' WHERE id = %s", game_id)
    finished = (await home(email(0)))["game"]
    assert (finished["seat_state"], finished["turn"]) == (None, None)


async def test_a_seat_another_student_held_after_them_is_never_read(klass):
    """Follow-up review of Story 6.1 (FR-5): a Student who no longer holds a Seat is shown the
    one they held last, but never one another Student took after them: it shows that Student's
    play."""
    _, game_id, by_role = await running(klass, students=2)
    first, second = (user_id(who) for who in by_role.values())
    who = next(iter(by_role.values()))
    assert (await play(who, game_id)).status_code == 200
    # The Seat goes to an AI player: still the Student's game to look back on.
    append_occupant(first, "rule_based", None)
    assert (await play(who, game_id)).status_code == 200
    # Then another Student takes it: no longer readable, alike with any other game.
    [(seat,)] = rows(
        "SELECT DISTINCT ON (seat_id) seat_id FROM seat_occupancy WHERE user_id = %s "
        "ORDER BY seat_id, id DESC",
        first,
    )
    execute(
        "INSERT INTO seat_occupancy (id, seat_id, from_week, occupant_kind, reason, user_id) "
        "VALUES (%s, %s, 1, 'student', 'takeover_peer', %s)",
        uuid.uuid7(),
        seat,
        second,
    )
    for path in ("/play", ""):
        refused = await call(who, "GET", f"/api/me/games/{game_id}{path}")
        assert refused.status_code == 403
