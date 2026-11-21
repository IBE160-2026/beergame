import { expect, type Page, type Route } from "@playwright/test";

import { nb } from "../../src/copy/nb";
import week11 from "../../src/modules/games/fixtures/play-week-11.json";
import { loginByApi } from "./auth";

/** The play screen of Uke 11 with stand-in game and envelopes (Stories 6.12 and 6.13). As in
 * `order-field.spec.ts`, they have the api's shapes: the engine's Grossist of a Classic game in
 * Uke 11, held to the engine by `backend/tests/games/test_play_fixture.py`. The Order's POST is
 * answered here and recorded; the api side of the send is `backend/tests/sessions/test_orders.py`. */
export const GAME_ID = "01a1f8ee-34f2-70af-8800-f79281ed7a67";
export const ORDER_PATH = `/api/me/games/${GAME_ID}/weeks/11/order`;
/** Uke 11 once the Grossist's 24 is stored: its Setestatus row has ordered (Story 6.14). */
export const confirmedWeek11 = {
  ...week11,
  turn: { ...week11.turn, order: 24 },
  table_status: {
    seats: week11.table_status.seats.map((seat) => (seat.mine ? { ...seat, ordered: true } : seat)),
  },
};

/** Uke 12 after the Grossist's `ordered` in Uke 11 (Story 6.15): the Uke-overgang's numbers. The
 * engine's next Uke from Uke 11: Levering 4, Ordre inn 11, Sendt 4, Restordre 20 blir 27, Kost
 * 27,00 kr; so far Lagerkostnad 40,00 kr and Restordrekostnad 69,00 kr (Story 6.16). */
export function week12(ordered = 24) {
  const state = week11.seat_state;
  return {
    ...week11,
    seat_state: {
      ...state,
      week: 12,
      backlog: 27,
      incoming_orders: [...state.incoming_orders, 11],
      order_history: [...state.order_history, ordered],
      supply_line: 12 + ordered,
      incoming_order: 11,
      incoming_delivery: 4,
      shipped: 4,
      supply_line_slots: [
        { stage: "in_transit", quantity: 4, arrival_week: 13 },
        { stage: "in_transit", quantity: 8, arrival_week: 14 },
        { stage: "ordered", quantity: ordered, arrival_week: 15 },
      ],
      net_inventory: -27,
      position: -27 + 12 + ordered,
      cost_lines: [
        { kind: "holding", units: 0, rate: "0.50", amount: "0.00" },
        { kind: "backorder", units: 27, rate: "1.00", amount: "27.00" },
      ],
      week_cost: "27.00",
      total_cost: "109.00",
      total_holding_cost: "40.00",
      total_backorder_cost: "69.00",
      history: [
        ...state.history,
        {
          week: 11,
          incoming_order: 10,
          incoming_delivery: 4,
          shipped: 4,
          inventory: 0,
          backlog: 20,
          net_inventory: -20,
          supply_line: 16,
          position: -4,
          cost: "20.00",
          holding_cost: "0.00",
          backorder_cost: "20.00",
          total_cost: "82.00",
          total_holding_cost: "40.00",
          total_backorder_cost: "42.00",
          order: ordered,
        },
      ],
      preview: { order_arrival_week: 16, supply_line_base: 12 + ordered, position_base: -27 + 12 + ordered },
    },
    turn: { guided: false, order: null, viewed: false },
    table_status: { seats: week11.table_status.seats.map((seat) => ({ ...seat, ordered: false, wait_started_at: null })) },
  };
}

export type PlayStub = {
  /** What the next read of the play envelope gets. */
  envelope: unknown;
  /** While set, reads of the play envelope wait for it. */
  held?: Promise<void>;
  posts: unknown[];
  /** Answers the Order's POST: by default 204, and Uke 11 then holds 24. */
  answer: (route: Route) => Promise<void>;
};

export async function openPlay(page: Page, login = true): Promise<PlayStub> {
  const stub: PlayStub = {
    envelope: week11,
    posts: [],
    answer: async (route) => {
      stub.envelope = confirmedWeek11;
      await route.fulfill({ status: 204 });
    },
  };
  if (login) await loginByApi(page, "student");
  await page.route(`**/api/me/games/${GAME_ID}`, (route) =>
    route.fulfill({
      json: {
        id: GAME_ID,
        number: 17,
        role: "wholesaler",
        seats: week11.table_status.seats,
        briefing_first: false,
        rules: { order_delay: 2, shipping_delay: 2, production_delay: 2, guided_weeks: 4, holding_cost: "0.50", backorder_cost: "1.00" },
        status: "running",
        week: 11,
        server_now: week11.server_now,
      },
    }),
  );
  await page.route(`**/api/me/games/${GAME_ID}/play`, async (route) => {
    if (stub.held) await stub.held;
    await route.fulfill({ json: stub.envelope }).catch(() => undefined); // the page may have left
  });
  await page.route(`**${ORDER_PATH}`, (route) => {
    stub.posts.push(route.request().postDataJSON());
    return stub.answer(route);
  });
  await page.goto(`/spill/${GAME_ID}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(nb.games.play.week(11));
  return stub;
}

/** Holds reads of the play envelope until the returned function is called. */
export function holdPlay(stub: PlayStub): () => void {
  let release: () => void = () => undefined;
  stub.held = new Promise<void>((resolve) => (release = resolve));
  return () => {
    stub.held = undefined;
    release();
  };
}

export const orderField = (page: Page, week = 11) => page.getByRole("textbox", { name: nb.games.play.order.label(week) });
export const confirmButton = (page: Page) => page.locator("[data-order-field] button.w-full");
/** Read the play envelope again, as coming back online does (`providers.tsx`). */
export const refetchPlay = (page: Page) => page.evaluate(() => window.dispatchEvent(new Event("online")));
export const drafts = (page: Page) =>
  page.evaluate(() => Object.keys(localStorage).filter((key) => key.startsWith("olspillet:draft:")));
