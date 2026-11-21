import { expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import type { PlayEnvelope } from "../src/modules/games/api";
import week11 from "../src/modules/games/fixtures/play-week-11.json";
import { loginByApi } from "./support/auth";
import { expectAccessible } from "./support/classes";
import { GAME_ID, openPlay, orderField } from "./support/play";

/** A Seat an AI player took over after the Inactivity limit (Story 8.2, FR-34, FR-36, FR-17,
 * UX-DR62, UX-DR69). Stand-in envelopes of the api's shape over the demo Student's login: the
 * Takeover itself, its timing and the stored rows are `backend/tests/games/test_takeover.py` and
 * `backend/tests/sessions/test_takeover_view.py`; here only what the Students see. */
const copy = nb.homes.student;
type Seat = PlayEnvelope["table_status"]["seats"][number];

const region = (page: Page) => page.getByRole("main").getByRole("region", { name: copy.seats });
const rows = (page: Page) => region(page).getByRole("listitem");
const announce = (page: Page) => page.locator("[data-seat-status-announce]");

/** Uke 11 with the Seats changed by `change`. */
function week11With(change: (seat: Seat) => Seat, turn: PlayEnvelope["turn"] = week11.turn) {
  return {
    ...week11,
    turn,
    table_status: {
      seats: (week11.table_status.seats as unknown as Seat[]).map(change),
    },
  };
}

/** Jonas Berg's Distributør Seat, taken over: the AI player has ordered for him. */
const jonasTakenOver = week11With((seat) =>
  seat.role === "distributor"
    ? {
        ...seat,
        holder: "ai",
        name: null,
        ordered: true,
        wait_started_at: null,
        mark: "takeover_inactivity",
        taken_over: true,
        ordering_for: "Jonas Berg",
      }
    : seat,
);

/** The demo Student's own Grossist Seat, taken over; the AI player's Order is 9. */
const ownTakenOver = week11With(
  (seat) =>
    seat.mine
      ? {
          ...seat,
          holder: "ai",
          name: null,
          ordered: true,
          wait_started_at: null,
          mark: "takeover_inactivity",
          taken_over: true,
          ordering_for: null,
        }
      : seat,
  { ...week11.turn, order: 9 },
);

/** The play screen over `envelope`, with the game read as Obligatorisk or not. */
async function openTakenOver(page: Page, envelope: object, obligatory: boolean) {
  await loginByApi(page, "student");
  const seats = (envelope as typeof week11).table_status.seats;
  await page.route(`**/api/me/games/${GAME_ID}`, (route) =>
    route.fulfill({
      json: {
        id: GAME_ID,
        number: 17,
        role: "wholesaler",
        seats,
        briefing_first: false,
        rules: {
          order_delay: 2,
          shipping_delay: 2,
          production_delay: 2,
          guided_weeks: 4,
          holding_cost: "0.50",
          backorder_cost: "1.00",
        },
        status: "running",
        week: 11,
        server_now: week11.server_now,
        obligatory,
      },
    }),
  );
  await page.route(`**/api/me/games/${GAME_ID}/play`, (route) =>
    route.fulfill({ json: envelope }).catch(() => undefined),
  );
  await page.goto(`/spill/${GAME_ID}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(nb.games.play.week(11));
}

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

for (const width of [320, 1440]) {
  test.describe(`${width} px`, () => {
    test.use({ viewport: { width, height: 800 } });

    test("the group sees «Distributør  KI-spiller  bestiller for Jonas Berg», announced politely", async ({ page }) => {
      const stub = await openPlay(page);
      await expect(rows(page)).toHaveText([
        /^Fabrikk\s*KI-spiller\s*har bestilt$/,
        /^Distributør\s*Jonas Berg\s*venter, \d+ min$/,
        /^Grossist\s*Demo Student \(deg\)\s*venter$/,
        /^Detaljist\s*KI-spiller\s*har bestilt$/,
      ]);
      // The Takeover arrives with the next read of the envelope (a `game:` event in the app).
      stub.envelope = jonasTakenOver;
      await page.evaluate(() => window.dispatchEvent(new Event("online")));
      await expect(rows(page).nth(1)).toHaveText(/^Distributør\s*KI-spiller\s*bestiller for Jonas Berg$/);
      await expect(announce(page)).toHaveText(/^Distributør: KI-spiller bestiller for Jonas Berg\. Venter på: deg\.$/);
      // The viewer's own Ordrefelt is untouched.
      await expect(orderField(page)).toBeEditable();
      if (width === 1440) await expectAccessible(page, false);
    });

    test("the Student whose Seat it was is told so, with the requirement warning, and has no Ordrefelt", async ({
      page,
    }) => {
      await openTakenOver(page, ownTakenOver, true);
      const note = page.locator("[data-taken-over]");
      await expect(note).toContainText(copy.takeover.takenOver);
      await expect(note).toContainText(copy.takeover.requirementWarning);
      await expect(note).not.toContainText(/\d/);
      await expect(page.locator("[data-order-field]")).toHaveCount(0);
      await expect(rows(page).nth(2)).toHaveText(/^Grossist\s*KI-spiller\s*bestiller for deg$/);
      // No horizontal scroll at any width.
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      await expectAccessible(page, width === 320);
    });
  });
}

test("an Order sent as the Seat is taken over is never confirmed, even when the AI player ordered the same", async ({
  page,
}) => {
  const stub = await openPlay(page);
  // The Takeover won the lock: the api refuses the Order, and the Uke now holds the AI player's 24.
  stub.answer = async (route) => {
    stub.envelope = { ...ownTakenOver, turn: { ...ownTakenOver.turn, order: 24 } };
    await route.fulfill({ status: 409, json: { error: { code: "seat_not_yours", message: "x" } } });
  };
  await orderField(page).fill("24");
  await page.locator("[data-order-field] button.w-full").click();
  await expect(page.locator("[data-taken-over]")).toContainText(copy.takeover.takenOver);
  await expect(page.locator("[data-order-sent]")).toHaveCount(0);
  await expect(page.getByText(nb.games.play.order.sent("24"))).toHaveCount(0);
});

test("a Guided Uke of a Seat taken over is never reported as opened", async ({ page }) => {
  let views = 0;
  await page.route(`**/api/me/games/${GAME_ID}/weeks/*/view`, (route) => {
    views += 1;
    return route.fulfill({ status: 204 });
  });
  const guided = { ...ownTakenOver, turn: { guided: true, order: 9, viewed: false } };
  await openTakenOver(page, guided, false);
  await expect(page.locator("[data-taken-over]")).toBeVisible();
  // Long enough for the view's effect to have run; the stub would have counted it.
  await page.evaluate(() => new Promise((resolve) => setTimeout(resolve, 300)));
  expect(views).toBe(0);
});

test("outside an Obligatorisk Class session the warning is left out", async ({ page }) => {
  await openTakenOver(page, ownTakenOver, false);
  await expect(page.locator("[data-taken-over]")).toHaveText(copy.takeover.takenOver);
});

test("on Hjem the Student whose Seat it was reads the line instead of the Spillkort", async ({ page }) => {
  await loginByApi(page, "student");
  await page.route("**/api/me/class-sessions", async (route) => {
    const response = await route.fetch();
    const classes = await (await page.request.get("/api/classes/enrolled")).json();
    const [klass] = classes.items;
    const game = {
      id: GAME_ID,
      number: 17,
      role: "wholesaler",
      seats: ownTakenOver.table_status.seats,
      briefing_first: false,
      rules: {
        order_delay: 2,
        shipping_delay: 2,
        production_delay: 2,
        guided_weeks: 4,
        holding_cost: "0.50",
        backorder_cost: "1.00",
      },
      status: "running",
      week: 11,
      server_now: week11.server_now,
      seat_state: week11.seat_state,
      turn: ownTakenOver.turn,
      obligatory: true,
    };
    const items = [
      {
        id: "01a1f8ee-33b9-75e6-9502-79db27b37c00",
        class_id: klass.id,
        class_name: klass.name,
        number: 1,
        start_at: "2026-11-24T09:00:00Z",
        play_deadline: "2026-12-08T13:00:00Z",
        debrief_deadline: null,
        test_deadline: null,
        next_deadline: { kind: "play", at: "2026-12-08T13:00:00Z" },
        obligatory: true,
        lab_hours: [],
        seat_choice_open: false,
        drawn_seat: null,
        steps: [{ step: "class_game", state: "current" }],
        game,
      },
    ];
    await route.fulfill({ response, json: { items } });
  });
  await page.goto("/hjem");
  const main = page.getByRole("main");
  await expect(main.locator("[data-taken-over]")).toContainText(copy.takeover.takenOver);
  await expect(main.locator("[data-taken-over]")).toContainText(copy.takeover.requirementWarning);
  await expect(main.locator("[data-game-card]")).toHaveCount(0);
  // The game is not waiting for this Student: no primary button for it.
  await expect(main.locator("a.bg-ink, button.bg-ink")).toHaveCount(0);
  await expect(rows(page).nth(2)).toHaveText(/^Grossist\s*KI-spiller\s*bestiller for deg$/);
});
