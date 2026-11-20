import type { SeatState } from "@/modules/games/api";

import demo from "./demo-seat.json";

/**
 * The Seat the Landing shows (Stories 3.13 and 6.8, UX-DR70): one Seat, the Grossist, in Uke 4,
 * the last Veiledet uke, where every Order is fixed at 4. It is Demodata: the engine's own state
 * for a Classic game with the guided Orders, not a played game, and the figure labels it
 * «Demodata». `backend/tests/games/test_play_fixture.py` holds `demo-seat.json` to the engine;
 * it carries only the Seat's own `seat_state` and the guided Order, never a name or another Seat.
 *
 * Content rules (EXPERIENCE.md → Landing, Hidden information): one Seat only, no played Week
 * beyond nå (right of nå only the known arrivals, never past nå + 4), and an Ordre inn that never
 * rises. `demo-seat.test.ts` holds the fixture to them.
 */
export const DEMO_SEAT: SeatState = demo.seat_state as SeatState;

/** The Order a Veiledet uke places by itself, written in Din ordre at nå. */
export const DEMO_GUIDED_ORDER: number = demo.guided_order;
