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


def _game_until(week: int, settings: GameSettings | None = None):
    """The fixture game's opened Weeks 1..`week` and the Order maps of Weeks 1..`week` - 1."""
    settings = settings or GameSettings()
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
    return settings, states, orders


def seat_in_week(role: str, week: int) -> SeatState:
    settings, states, orders = _game_until(week)
    return build_seat_state(settings, states, orders, role)


def wholesaler_in_week(week: int) -> SeatState:
    return seat_in_week("wholesaler", week)


@pytest.mark.parametrize("week", [1, 3, 11, 14, 30])
def test_the_stand_in_envelope_is_the_engines_week(week):
    stored = json.loads((FIXTURES / f"play-week-{week}.json").read_text(encoding="utf-8"))
    envelope = PlayOut.model_validate(stored)
    assert envelope.seat_state == wholesaler_in_week(week)
    assert stored["seat_state"] == wholesaler_in_week(week).model_dump(mode="json")
    # The own turn (Story 6.10): a Guided Week holds the fixed Order placed when it opened.
    settings = GameSettings()
    guided = week <= settings.guided_weeks
    assert stored["turn"] == {
        "guided": guided,
        "order": guided_order(settings) if guided else None,
        "viewed": False,
    }


# The Landing's Demodata Seat (Story 6.8, UX-DR70): the same Grossist in Uke 4, a Veiledet uke,
# with the fixed Order the game places there. Only `seat_state`: no names, no other Seat.
LANDING = (
    Path(__file__).resolve().parents[3]
    / "frontend"
    / "src"
    / "modules"
    / "landing"
    / "demo-seat.json"
)


def landing_demo_seat() -> dict:
    return {
        "seat_state": wholesaler_in_week(4).model_dump(mode="json"),
        "guided_order": guided_order(GameSettings()),
    }


def test_the_landing_demodata_is_the_engines_guided_week():
    # The caption says «Uke 4. Veiledet uke.»: Uke 4 must still be a Guided Week.
    assert 4 <= GameSettings().guided_weeks
    stored = json.loads(LANDING.read_text(encoding="utf-8"))
    assert stored == landing_demo_seat()
    assert SeatState.model_validate(stored["seat_state"]) == wholesaler_in_week(4)


# The Kjedebånd's scale test (Story 6.9, UX-DR15): every Uke of the fixture game for all four
# Roles, with only the `seat_state` fields the band draws. One object per line; to regenerate,
# write `chain_band_classic()` with one `json.dumps(item, ensure_ascii=False)` per line.
CHAIN_BAND = FIXTURES / "chain-band-classic.json"
LAST_WEEK = GameSettings().guided_weeks + len(ORDERS["retailer"]) + 1
BAND_FIELDS = (
    "role",
    "week",
    "incoming_order",
    "incoming_delivery",
    "shipped",
    "inventory",
    "backlog",
    "supply_line",
    "supply_line_slots",
    "overdue",
)


def chain_band_classic(settings: GameSettings | None = None) -> list[dict]:
    settings, states, orders = _game_until(LAST_WEEK, settings)
    found = []
    for role in settings.roles:
        for week in range(1, LAST_WEEK + 1):
            state = build_seat_state(settings, states[:week], orders[: week - 1], role)
            dumped = state.model_dump(mode="json")
            found.append({field: dumped[field] for field in BAND_FIELDS})
    return found


def test_the_chain_band_fixture_is_every_week_of_the_engines_game():
    stored = json.loads(CHAIN_BAND.read_text(encoding="utf-8"))
    assert stored == chain_band_classic()


# A capped Seat (Story 6.22, FR-12): the same Orders with the Grossist shipping at most 6 a Week, so
# it holds stock and backlog at once. `chain-band-capped.json` runs the band's scale test with both
# bars; `play-capped.json` is the capped Grossist's envelope in Uke `CAPPED_WEEK` for the browser.
CAPPED = GameSettings(capacity={"wholesaler": 6})
CHAIN_BAND_CAPPED = FIXTURES / "chain-band-capped.json"
PLAY_CAPPED = FIXTURES / "play-capped.json"
CAPPED_WEEK = 9


def test_the_capped_chain_band_fixture_is_every_week_of_the_engines_capped_game():
    stored = json.loads(CHAIN_BAND_CAPPED.read_text(encoding="utf-8"))
    assert stored == chain_band_classic(CAPPED)
    both = [s for s in stored if s["inventory"] > 0 and s["backlog"] > 0]
    assert {s["role"] for s in both} == {"wholesaler"} and len(both) >= 10


def test_the_capped_stand_in_envelope_is_the_engines_week():
    stored = json.loads(PLAY_CAPPED.read_text(encoding="utf-8"))
    settings, states, orders = _game_until(CAPPED_WEEK, CAPPED)
    state = build_seat_state(settings, states, orders, "wholesaler")
    assert PlayOut.model_validate(stored).seat_state == state
    assert state.inventory > 0 and state.backlog > 0


# The Order preview's check (Story 6.11, AD-10): `frontend/src/lib/preview.ts` is the product's only
# client arithmetic and is tested in Vitest against these engine values. For every Seat and Week of
# two golden-trace games (Classic delays and 3/3/3), the preview coefficients the play envelope
# carries, the Order the trace placed, and what the engine showed the next Week. One object per
# line; to regenerate, write `preview_golden()` with one `json.dumps(item)` per line.
GOLDEN = Path(__file__).resolve().parents[1] / "engine" / "golden"
PREVIEW_GOLDEN = FIXTURES / "preview-golden.json"
PREVIEW_TRACES = ("classic-step-pass-through.json", "delays-3-3-3-backlog.json")
NEXT_FIELDS = (
    "supply_line",
    "incoming_delivery",
    "position",
    "incoming_order",
    "supply_line_slots",
)


def preview_golden() -> list[dict]:
    found = []
    for name in PREVIEW_TRACES:
        golden = json.loads((GOLDEN / name).read_text(encoding="utf-8"))
        settings = GameSettings.model_validate(golden["settings"])
        states = [initial_state(settings)]
        for orders in golden["orders"]:
            states.append(advance(settings, states[-1], orders))
        placed = golden["orders"]
        for role in settings.roles:
            # The last Order ends the game: its next Week never opens.
            for week in range(1, len(placed)):
                now = build_seat_state(settings, states[:week], placed[: week - 1], role)
                after = build_seat_state(settings, states[: week + 1], placed[:week], role)
                dumped = after.model_dump(mode="json")
                found.append(
                    {
                        "trace": name,
                        "role": role,
                        "week": week,
                        "preview": now.preview.model_dump(mode="json"),
                        "order": placed[week - 1][role],
                        "next": {field: dumped[field] for field in NEXT_FIELDS},
                    }
                )
    return found


def test_the_preview_fixture_is_the_engines_golden_games():
    stored = json.loads(PREVIEW_GOLDEN.read_text(encoding="utf-8"))
    assert stored == preview_golden()


# The projection's check (Story 10.4, AD-10, UX-DR19): `orderProjection` in
# `frontend/src/lib/preview.ts` is tested in Vitest against these engine values. For every Seat and
# Week of three golden-trace games (Classic delays, 3/3/3 and 1/1/1, so horizons 4, 6 and 2), the
# fields the play envelope carries, the Order the trace placed, the delay horizon from the settings
# and Netto lager at nå + horizon if the incoming order holds and every Order is shipped in full:
# Netto lager now, plus every supply-line slot due by then and what upstream still owes, plus the
# Order, less the horizon's incoming orders. One object per line; to regenerate, write
# `projection_golden()` as a list with one `json.dumps(item)` per line.
PROJECTION_GOLDEN = FIXTURES / "projection-golden.json"
PROJECTION_TRACES = (
    "classic-step-pass-through.json",
    "delays-3-3-3-backlog.json",
    "delays-1-1-1-backlog.json",
)


def projection_golden() -> list[dict]:
    found = []
    for name in PROJECTION_TRACES:
        golden = json.loads((GOLDEN / name).read_text(encoding="utf-8"))
        settings = GameSettings.model_validate(golden["settings"])
        states = [initial_state(settings)]
        for orders in golden["orders"]:
            states.append(advance(settings, states[-1], orders))
        placed = golden["orders"]
        for role in settings.roles:
            goods = (
                settings.production_delay if role == settings.roles[-1] else settings.shipping_delay
            )
            horizon = settings.order_delay + goods
            for week in range(1, len(placed) + 1):
                now = build_seat_state(settings, states[:week], placed[: week - 1], role)
                order = placed[week - 1][role]
                due = [
                    slot for slot in now.supply_line_slots if slot.arrival_week <= week + horizon
                ]
                assert len(due) == len(now.supply_line_slots)  # all of it is due within the horizon
                found.append(
                    {
                        "trace": name,
                        "role": role,
                        "state": {
                            "week": now.week,
                            "incoming_order": now.incoming_order,
                            "net_inventory": now.net_inventory,
                            "position": now.position,
                            "preview": now.preview.model_dump(mode="json"),
                        },
                        "order": order,
                        "horizon": horizon,
                        "projection": now.net_inventory
                        + sum(slot.quantity for slot in due)
                        + now.overdue
                        + order
                        - horizon * now.incoming_order,
                    }
                )
    return found


def test_the_projection_fixture_is_the_engines_golden_games():
    stored = json.loads(PROJECTION_GOLDEN.read_text(encoding="utf-8"))
    assert stored == projection_golden()
    assert {item["horizon"] for item in stored} == {2, 4, 6}


# A Replay with shorter delays (Story 10.4): the same Grossist, Orders and demand on 1/1/1 delays,
# in Uke `SHORT_WEEK`, as the play envelope of a Replay (the projection on, three AI players). The
# browser test checks the dot stands at nå + 2 and the sentence says «om to uker».
SHORT = GameSettings(order_delay=1, shipping_delay=1, production_delay=1)
PLAY_REPLAY_SHORT = FIXTURES / "play-replay-short.json"
SHORT_WEEK = 9


def test_the_short_delay_replay_envelope_is_the_engines_week():
    stored = json.loads(PLAY_REPLAY_SHORT.read_text(encoding="utf-8"))
    settings, states, orders = _game_until(SHORT_WEEK, SHORT)
    state = build_seat_state(settings, states, orders, "wholesaler")
    envelope = PlayOut.model_validate(stored)
    assert envelope.seat_state == state and envelope.projection is True
    assert state.preview.order_arrival_week - state.week == 2
    assert {seat.holder for seat in envelope.table_status.seats if not seat.mine} == {"ai"}
