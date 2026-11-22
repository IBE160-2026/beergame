import { expect, type Page, type Route, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { loginByApi } from "./support/auth";
import { expectAccessible, expectReflow } from "./support/classes";

/** «Start Replay» on Hjem (Story 10.3, FR-48, FR-34, UX-DR8, UX-DR64), on the local stack as the
 * demo Student. Which state Hjem is in, and what a start makes, are the api's and are pinned by
 * `backend/tests/replay/test_start.py`; here the server's answer for the demo Student's Class is
 * laid over the real one (the demo Class is never changed), and the start's answer is stubbed. */
const copy = nb.homes.student;
const SESSION = "01a1f8ee-33b9-75e6-9502-79db27b37c0e";
const REPLAY_ID = "01a1f8ee-34f2-70af-8800-f79281ed7799";

const GAME = {
  id: "01a1f8ee-34f2-70af-8800-f79281ed777e",
  number: 17,
  role: "wholesaler",
  class_session_id: SESSION,
  seats: [
    { role: "factory", holder: "student", name: "Jonas Berg", mine: false },
    { role: "distributor", holder: "ai", name: null, mine: false },
    { role: "wholesaler", holder: "student", name: "Demo Student", mine: true },
    { role: "retailer", holder: "ai", name: null, mine: false },
  ],
  briefing_first: false,
  status: "finished",
  week: null,
  server_now: "2026-11-22T10:00:00Z",
  seat_state: null,
  turn: null,
  debrief: "open",
  rules: {
    order_delay: 2,
    shipping_delay: 2,
    production_delay: 2,
    guided_weeks: 4,
    holding_cost: "0.50",
    backorder_cost: "1.00",
  },
};

function steps(replay: { closed?: boolean } = {}) {
  return ["class_game", "debrief", "quiz", "replay", "test", "report"].map((step, i) => ({
    step,
    state: i < 3 ? "done" : i === 3 ? "current" : "locked",
    held: false,
    quiz_changed: false,
    group_open: false,
    closed: i === 3 && Boolean(replay.closed),
  }));
}

const STARTED = {
  can_start: false,
  game: {
    id: REPLAY_ID,
    role: "wholesaler",
    status: "running",
    week: 1,
    server_now: "2026-11-22T10:00:00Z",
    seats: [
      { role: "factory", holder: "ai", name: null, mine: false, ordered: true },
      { role: "distributor", holder: "ai", name: null, mine: false, ordered: true },
      { role: "wholesaler", holder: "student", name: "Demo Student", mine: true, ordered: false },
      { role: "retailer", holder: "ai", name: null, mine: false, ordered: true },
    ],
  },
};

type Replay = { can_start: boolean; game: typeof STARTED.game | null };

/** The demo Student's Class with one locked Class session whose quiz is passed; `state()` is read
 * at each request, so a test can move Hjem on after the start. */
async function withSession(page: Page, state: () => { replay: Replay; closed?: boolean }) {
  await page.route("**/api/me/class-sessions", async (route) => {
    const response = await route.fetch();
    const classes = await (await page.request.get("/api/classes/enrolled")).json();
    const [klass] = classes.items;
    const now = state();
    const item = {
      id: SESSION,
      class_id: klass.id,
      class_name: klass.name,
      number: 1,
      start_at: "2026-11-01T09:00:00Z",
      play_deadline: "2026-11-15T13:00:00Z",
      debrief_deadline: "2026-11-20T13:00:00Z",
      test_deadline: "2026-12-08T13:00:00Z",
      next_deadline: now.closed ? null : { kind: "test", at: "2026-12-08T13:00:00Z" },
      obligatory: false,
      lab_hours: [],
      seat_choice_open: false,
      drawn_seat: null,
      game: GAME,
      steps: steps({ closed: now.closed }),
      replay: now.replay,
    };
    await route.fulfill({ response, json: { items: [item] } });
  });
}

function replayAnswer(page: Page, answer: (route: Route) => Promise<void>) {
  return page.route(`**/api/me/class-sessions/${SESSION}/replay`, answer);
}

const VIEWPORTS = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
];

for (const vp of VIEWPORTS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test.beforeEach(async ({ page }) => {
      await loginByApi(page, "student");
    });

    test.afterEach(async ({ page }) => {
      await page.unrouteAll({ behavior: "ignoreErrors" });
    });

    test("«Start Replay» is the one primary; the started Replay names every AI Seat «KI-spiller»", async ({
      page,
    }) => {
      let replay: Replay = { can_start: true, game: null };
      await withSession(page, () => ({ replay }));
      let started = 0;
      await replayAnswer(page, async (route) => {
        started += 1;
        replay = STARTED;
        await route.fulfill({ status: 201, json: { game_id: REPLAY_ID } });
      });
      await page.goto("/hjem");
      const main = page.getByRole("main");
      const block = main.getByRole("region", { name: copy.replay.heading, exact: true });
      await expect(block.getByText(copy.replay.consequence)).toBeVisible();
      const start = block.getByRole("button", { name: copy.replay.start });
      await expect(start).toBeVisible();
      // Hjem's one primary button (UX-DR8, Knapper: filled `ink`): the finished game has none.
      await expect(main.locator("a.bg-ink, button.bg-ink")).toHaveCount(1);
      await expect(start).toHaveClass(/\bbg-ink\b/);
      const steps = main.getByRole("region", { name: copy.steps }).getByRole("listitem");
      await expect(steps.nth(3)).toHaveText(/^Replay\s*pågår$/);
      await expectAccessible(page, vp.phone);

      await start.click();
      const title = main.getByRole("region", { name: "Replay · Du er Grossist" });
      await expect(title).toBeVisible();
      expect(started).toBe(1);
      await expect(main.getByRole("button", { name: copy.replay.start })).toHaveCount(0);
      const seats = title.getByRole("region", { name: copy.seats }).getByRole("listitem");
      await expect(seats).toHaveCount(4);
      await expect(seats.filter({ hasText: copy.aiPlayer })).toHaveCount(3);
      await expect(seats.filter({ hasText: "Demo Student (deg)" })).toHaveCount(1);
      await expect(steps.nth(3)).toHaveText(/^Replay\s*pågår$/);
      await expectAccessible(page, vp.phone);
    });

    test("a refused start says why in words; after the Testfrist Stegene says the step is not done", async ({
      page,
    }) => {
      let closed = false;
      await withSession(page, () => ({ replay: { can_start: !closed, game: null }, closed }));
      await replayAnswer(page, (route) =>
        route.fulfill({
          status: 409,
          json: { error: { code: "test_deadline_passed", message: "Your Test deadline has passed." } },
        }),
      );
      await page.goto("/hjem");
      const main = page.getByRole("main");
      await main.getByRole("button", { name: copy.replay.start }).click();
      await expect(main.getByText(copy.replay.errors.test_deadline_passed)).toBeVisible();
      await expectReflow(page, vp.phone);

      closed = true;
      await page.reload();
      await expect(main.getByRole("button", { name: copy.replay.start })).toHaveCount(0);
      const steps = main.getByRole("region", { name: copy.steps }).getByRole("listitem");
      await expect(steps.nth(3)).toHaveText(new RegExp(`^Replay\\s*${copy.replayClosed}$`));
      await expectReflow(page, vp.phone);
    });
  });
}
