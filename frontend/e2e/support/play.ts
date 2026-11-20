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
export const confirmedWeek11 = { ...week11, turn: { ...week11.turn, order: 24 } };

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
