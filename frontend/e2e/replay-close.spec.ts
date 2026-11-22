import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import week11 from "../src/modules/games/fixtures/play-week-11.json";
import { loginByApi } from "./support/auth";
import { expectAccessible, expectReflow, test } from "./support/classes";

/** A Replay closed at the Testfrist (Story 10.6, FR-18, FR-48, NFR-6, UX-DR64): its play screen says
 * it was closed there and is not finished, with no Totalkostnad, no walkthrough and no button
 * forward; Hjem and Stegene say the same; an Order the api refuses with `409 test_deadline_passed`
 * says why. Stand-ins with the api's shapes; that the sweep closes it, never plays it out, records
 * no step and keeps the Orders is `backend/tests/replay/test_close.py`. */
const GAME_ID = "01a1f8ee-34f2-70af-8800-f79281ed7a66";
const SESSION = "01a1f8ee-33b9-75e6-9502-79db27b37c0e";
const copy = nb.games.play;
const AI_SEATS = week11.table_status.seats.map((seat) => (seat.mine ? seat : { ...seat, holder: "ai", name: null }));
const RULES = { order_delay: 2, shipping_delay: 2, production_delay: 2, guided_weeks: 0, holding_cost: "0.50", backorder_cost: "1.00" };

const VIEWPORTS = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
];

const card = (status: "running" | "finished", endReason: "test_deadline" | null) => ({
  id: GAME_ID,
  number: null,
  replay: true,
  test_game: false,
  class_session_id: SESSION,
  role: "wholesaler",
  seats: AI_SEATS,
  briefing_first: false,
  rules: RULES,
  status,
  end_reason: endReason,
  week: status === "running" ? 11 : null,
  server_now: "2026-12-08T13:01:00Z",
  seat_state: null,
  turn: null,
  debrief: null,
});

async function openClosed(page: Page) {
  await loginByApi(page, "student");
  let results = 0;
  await page.route(`**/api/me/games/${GAME_ID}`, (route) => route.fulfill({ json: card("finished", "test_deadline") }));
  await page.route(`**/api/me/games/${GAME_ID}/result`, (route) => {
    results += 1;
    return route.fulfill({ status: 409, json: { error: { code: "game_not_finished", message: "x" } } });
  });
  await page.goto(`/spill/${GAME_ID}`);
  return () => results;
}

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

for (const vp of VIEWPORTS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("a closed Replay says it was closed at the Testfrist and is not finished; axe passes", async ({ page }) => {
      const results = await openClosed(page);
      const main = page.getByRole("main");
      await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.replayClosed.title);
      await expect(page.getByText(copy.roleReplay("Grossist"), { exact: true })).toBeVisible();
      await expect(main.locator("[data-replay-closed]")).toContainText(copy.replayClosed.lead);
      await expect(main.locator("[data-replay-closed]")).toContainText(copy.replayClosed.kept);
      await expect(main.getByRole("link", { name: nb.navigation.toHome })).toBeVisible();
      // Not finished: no Totalkostnad, no walkthrough, no «Replay er ferdig», no button forward.
      await expect(main.getByText(copy.replayEnd.title)).toHaveCount(0);
      await expect(main.getByText(copy.replayEnd.toWalkthrough)).toHaveCount(0);
      await expect(main.locator("[data-replay-total]")).toHaveCount(0);
      await expect(main.locator("a.bg-ink, button.bg-ink")).toHaveCount(0);
      expect(results()).toBe(0); // a closed Replay has no result to ask for
      await expectAccessible(page, vp.phone);
      await expectReflow(page, vp.phone);
    });
  });
}

test("an Order after the Testfrist is refused in words, and the closed Replay shows on the next read", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  await loginByApi(page, "student");
  let closed = false;
  await page.route(`**/api/me/games/${GAME_ID}`, (route) =>
    route.fulfill({ json: closed ? card("finished", "test_deadline") : card("running", null) }),
  );
  await page.route(`**/api/me/games/${GAME_ID}/play`, (route) =>
    route.fulfill({ json: { ...week11, projection: true, table_status: { seats: AI_SEATS } } }),
  );
  await page.route(`**/api/me/games/${GAME_ID}/weeks/11/order`, (route) => {
    closed = true; // the sweep has closed it by now; the refusal reads the game again
    return route.fulfill({ status: 409, json: { error: { code: "test_deadline_passed", message: "x" } } });
  });
  await page.goto(`/spill/${GAME_ID}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.week(11));
  await page.getByRole("textbox", { name: copy.order.label(11) }).fill("24");
  await page.getByRole("button", { name: copy.order.confirmOn("24") }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.replayClosed.title);
  await expect(page.getByRole("main").locator("[data-replay-closed]")).toBeVisible();
});

test("Hjem says the Replay was closed at the Testfrist, and Stegene keeps the step not done", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  await loginByApi(page, "student");
  await page.route("**/api/me/class-sessions", async (route) => {
    const response = await route.fetch();
    const classes = await (await page.request.get("/api/classes/enrolled")).json();
    const [klass] = classes.items;
    const item = {
      id: SESSION,
      class_id: klass.id,
      class_name: klass.name,
      number: 1,
      start_at: "2026-11-01T09:00:00Z",
      play_deadline: "2026-11-15T13:00:00Z",
      debrief_deadline: "2026-11-20T13:00:00Z",
      test_deadline: "2026-12-08T13:00:00Z",
      next_deadline: null,
      obligatory: false,
      lab_hours: [],
      seat_choice_open: false,
      drawn_seat: null,
      game: {
        id: "01a1f8ee-34f2-70af-8800-f79281ed777e",
        number: 17,
        role: "wholesaler",
        replay: false,
        test_game: false,
        class_session_id: SESSION,
        seats: week11.table_status.seats,
        briefing_first: false,
        status: "finished",
        week: null,
        server_now: "2026-12-08T13:01:00Z",
        seat_state: null,
        turn: null,
        debrief: "open",
        rules: { ...RULES, guided_weeks: 4 },
      },
      steps: ["class_game", "debrief", "quiz", "replay", "test", "report"].map((step, i) => ({
        step,
        state: i < 3 ? "done" : i === 3 ? "current" : "locked",
        held: false,
        quiz_changed: false,
        group_open: false,
        closed: i === 3,
      })),
      replay: {
        can_start: false,
        game: {
          id: GAME_ID,
          role: "wholesaler",
          status: "finished",
          end_reason: "test_deadline",
          week: null,
          server_now: "2026-12-08T13:01:00Z",
          seats: AI_SEATS,
        },
      },
    };
    await route.fulfill({ response, json: { items: [item] } });
  });
  await page.goto("/hjem");
  const main = page.getByRole("main");
  const block = main.getByRole("region", { name: "Replay · Du er Grossist" });
  await expect(block.locator("[data-replay-closed]")).toHaveText(nb.homes.student.replay.closed);
  await expect(block.getByRole("link", { name: nb.homes.student.replay.view })).toHaveCount(0);
  await expect(block.getByText(/Fortsett Replay/)).toHaveCount(0);
  const step = main.getByRole("region", { name: nb.homes.student.steps }).getByRole("listitem").nth(3);
  await expect(step).toContainText(nb.homes.student.replayClosedUnfinished);
  await expectAccessible(page, true);
});
