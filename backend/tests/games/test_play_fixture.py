"""The play screen's browser and unit tests stand in a Classic game's Grossist for the api (Story
6.6): `play-week-1.json` and `play-week-11.json` in `frontend/src/modules/games/fixtures/`. Their
`seat_state` must be exactly what the engine and `SeatState` give for these Orders, so the
stand-ins never drift from the real envelope."""

import json
from pathlib import Path

import pytest

from app.engine import GameSettings, advance, guided_order, initial_state
from app.modules.games.schemas import SeatState
from app.modules.games.views import build_seat_state
from app.modules.sessions.schemas import PlayOut

FIXTURES = (
    Path(__file__).resolve().parents[3] / "frontend" / "src" / "modules" / "games" / "fixtures"
)

# The Orders of Weeks 5..10 per Role after the four Guided Weeks: the Retailer chases the step in
# demand, the Grossist holds on and then orders more, as the spine's Uke 11 (EXPERIENCE.md). Weeks
# 11..29 (for the late Uke 30) follow: the Retailer keeps ordering hard, the Grossist orders too
# little and then far too much, so backlog builds, a Uke costs more than 40 kr and stock follows.
ORDERS = {
    "retailer": [8, 12, 12, 10, 10, 8]
    + [16, 16, 14, 12, 10, 10, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8],
    "wholesaler": [4, 4, 4, 4, 4, 8]
    + [8, 8, 8, 30, 30, 30, 20, 10, 4, 4, 4, 4, 4, 4, 8, 8, 8, 8, 8],
    "distributor": [4, 4, 6, 8, 10, 10]
    + [12, 14, 16, 20, 24, 24, 20, 16, 12, 10, 8, 8, 8, 8, 8, 8, 8, 8, 8],
    "factory": [4, 4, 4, 6, 8, 10]
    + [12, 14, 16, 20, 24, 24, 20, 16, 12, 10, 8, 8, 8, 8, 8, 8, 8, 8, 8],
}


def wholesaler_in_week(week: int) -> SeatState:
    settings = GameSettings()
    states = [initial_state(settings)]
    orders: list[dict[str, int]] = []
    for placed_in in range(1, week):
        if placed_in <= settings.guided_weeks:
            placed = {role: guided_order(settings) for role in settings.roles}
        else:
            after = placed_in - settings.guided_weeks - 1
            placed = {role: ORDERS[role][after] for role in settings.roles}
        orders.append(placed)
        states.append(advance(settings, states[-1], placed))
    return build_seat_state(settings, states, orders, "wholesaler")


@pytest.mark.parametrize("week", [1, 3, 11, 14, 30])
def test_the_stand_in_envelope_is_the_engines_week(week):
    stored = json.loads((FIXTURES / f"play-week-{week}.json").read_text(encoding="utf-8"))
    envelope = PlayOut.model_validate(stored)
    assert envelope.seat_state == wholesaler_in_week(week)
    assert stored["seat_state"] == wholesaler_in_week(week).model_dump(mode="json")
