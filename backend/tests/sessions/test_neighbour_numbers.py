"""The neighbour numbers on the play envelope (Story 6.21, FR-83, AD-3, AD-17): a Class session
whose Lecturer switched the upstream view on gives each Student exactly the inventory and backlog
of the Seat directly upstream in the open Week, and nothing else of any other Seat; with
`FEATURE_INFO_VISIBILITY` off the same Game gives none."""

from app.modules.games import service as games_service
from app.modules.ops import sweep
from app.platform.config import get_settings
from tests.sessions.test_dates import START
from tests.sessions.test_lock import MINUTE
from tests.sessions.test_open_games import confirmed
from tests.sessions.test_play import FORBIDDEN, keys, play, played_to
from tests.sessions.test_settings import save
from tests.sessions.test_start_game import start, task_done
from tests.sessions.test_student_choice import email
from tests.sessions.test_student_home import _empty, clock, home, klass

__all__ = ["_empty", "clock", "klass"]

UPSTREAM = {"retailer": "wholesaler", "wholesaler": "distributor", "distributor": "factory"}
"""The Seat each Role orders from; the Fabrikk has none."""


def flag(monkeypatch, on: bool) -> None:
    monkeypatch.setenv("FEATURE_INFO_VISIBILITY", "true" if on else "false")
    get_settings.cache_clear()


async def test_the_envelope_holds_the_upstream_neighbours_two_numbers_and_nothing_else(
    klass, monkeypatch
):
    flag(monkeypatch, True)
    session_id, seated = await confirmed(klass, 4)
    views = {"info_visibility": {"upstream": True, "downstream": False}}
    assert (await save(session_id, views)).status_code == 200
    await sweep.run(START + MINUTE)
    game_id = (await home(email(0)))["game"]["id"]
    await task_done(seated[0], session_id)
    assert (await start(email(0), game_id)).status_code == 200
    by_role = {(await home(email(i)))["game"]["role"]: email(i) for i in range(4)}
    await played_to(game_id, list(by_role), 6)
    own = {role: await games_service.seat_state(game_id, role) for role in by_role}
    for role, who in by_role.items():
        body = (await play(who, game_id)).json()
        numbers = body["seat_state"]["neighbour_numbers"]
        neighbour = UPSTREAM.get(role)
        expected = (
            []
            if neighbour is None
            else [
                {
                    "role": neighbour,
                    "week": 6,
                    "quantity": "inventory",
                    "value": own[neighbour].inventory,
                },
                {
                    "role": neighbour,
                    "week": 6,
                    "quantity": "backlog",
                    "value": own[neighbour].backlog,
                },
            ]
        )
        assert numbers == expected, role
        # Only inventory and backlog, labelled with Role and Week: never an Order, cost or Supply
        # line of the neighbour, and no reference Order anywhere.
        assert all(set(n) == {"role", "week", "quantity", "value"} for n in numbers)
        assert not keys(body) & FORBIDDEN
    # With the flag off the same Game shows no neighbour (AD-17).
    flag(monkeypatch, False)
    for who in by_role.values():
        assert (await play(who, game_id)).json()["seat_state"]["neighbour_numbers"] == []
