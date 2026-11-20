import { type Browser, expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import week1 from "../src/modules/games/fixtures/play-week-1.json";
import week11 from "../src/modules/games/fixtures/play-week-11.json";
import { DEMO_PASSWORD, loginByApi } from "./support/auth";
import { expectAccessible, freshClass, lecturerPage, test } from "./support/classes";

/** «Start spillet» (Story 6.5, FR-22, UX-DR62, UX-DR78), on the local stack through the proxy. The
 * start itself (`games.commands.start` through `POST /api/me/games/{id}/start`), its events to the
 * Class session and each seated Student, `game_not_ready`, `starting_task_required` and "started
 * first by another counts as done" are pinned by `backend/tests/sessions/test_start_game.py` and
 * `backend/tests/games/test_start.py`. A real locked game needs its Start date to pass and the
 * sweep, so here the game's state is a stand-in with the api's shapes (as for Stories 6.2 and 6.3)
 * and the demo Class is never changed. The live flow rides a real `user:` event on the real stream. */
const CSRF = { "X-Requested-With": "olspillet" };
const DAY = 24 * 60 * 60 * 1000;
const GAME_ID = "01a1f8ee-34f2-70af-8800-f79281ed7a65";
const SESSION_ID = "01a1f8ee-33b9-75e6-9502-79db27b37a65";
const start = nb.games.start;
const play = nb.games.play;

type Status = "not_ready" | "ready" | "running" | "finished";
type State = { status: Status; week: number | null };

function game(state: State) {
  return {
    id: GAME_ID,
    number: 17,
    role: "wholesaler",
    seats: [
      { role: "factory", holder: "ai", name: null, mine: false },
      { role: "distributor", holder: "student", name: "Jonas Berg", mine: false },
      { role: "wholesaler", holder: "student", name: "Demo Student", mine: true },
      { role: "retailer", holder: "ai", name: null, mine: false },
    ],
    briefing_first: false,
    rules: {
      order_delay: 2,
      shipping_delay: 2,
      production_delay: 2,
      guided_weeks: 4,
      holding_cost: "0.50",
      backorder_cost: "1.00",
    },
    ...state,
  };
}

/** Hjem with one locked Class session in the Student's first Class holding the game, the game
 * route, and the start: it answers the game running in Week 1 (or `refusal`), and counts presses. */
async function withGame(page: Page, state: State, refusal?: { status: number; code: string }) {
  const presses: number[] = [];
  await page.route("**/api/me/class-sessions", async (route) => {
    const response = await route.fetch();
    const classes = await (await page.request.get("/api/classes/enrolled")).json();
    const [klass] = classes.items;
    const item = {
      id: SESSION_ID,
      class_id: klass.id,
      class_name: klass.name,
      number: 1,
      start_at: "2026-11-17T09:00:00Z",
      play_deadline: "2026-12-08T13:00:00Z",
      debrief_deadline: null,
      test_deadline: null,
      next_deadline: { kind: "play", at: "2026-12-08T13:00:00Z" },
      obligatory: false,
      lab_hours: [],
      seat_choice_open: false,
      drawn_seat: null,
      game: game(state),
      steps: ["class_game", "debrief", "quiz", "replay", "test", "report"].map((step, j) => ({
        step,
        state: j === 0 ? "current" : "locked",
      })),
    };
    await route.fulfill({ response, json: { items: [item] } });
  });
  await page.route(`**/api/me/games/${GAME_ID}`, (route) => route.fulfill({ json: game(state) }));
  // The play envelope (Story 6.6) of the running game, in its open Week: Uke 1 or Uke 11.
  await page.route(`**/api/me/games/${GAME_ID}/play`, (route) =>
    route.fulfill({ json: state.week === 11 ? week11 : week1 }),
  );
  await page.route(`**/api/me/games/${GAME_ID}/start`, (route) => {
    presses.push(1);
    if (refusal) {
      return route.fulfill({ status: refusal.status, json: { error: { code: refusal.code, message: "", fields: {} } } });
    }
    Object.assign(state, { status: "running", week: 1 });
    return route.fulfill({ json: game(state) });
  });
  return presses;
}

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

const VIEWPORTS = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
];

for (const vp of VIEWPORTS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("Hjem's one primary is «Start spillet» under its consequence; it lands on Uke 1", async ({ page }) => {
      await loginByApi(page, "student");
      const presses = await withGame(page, { status: "ready", week: null });
      await page.goto("/hjem");
      const main = page.getByRole("main");
      const button = main.getByRole("button", { name: start.start });
      await expect(button).toHaveClass(/(^|\s)bg-ink(\s|$)/);
      await expect(main.getByText(start.consequence)).toBeVisible();
      // The consequence stands above the button, and no other control is primary.
      const line = await main.getByText(start.consequence).boundingBox();
      expect(line!.y).toBeLessThan((await button.boundingBox())!.y);
      await expect(main.locator(".bg-ink")).toHaveCount(1);
      await expect(main.getByRole("link", { name: nb.homes.student.rulesLink })).toBeVisible();
      await expectAccessible(page, vp.phone);

      await button.click();
      await expect(page).toHaveURL(new RegExp(`/spill/${GAME_ID}$`));
      await expect(main.getByRole("heading", { level: 1 })).toHaveText(play.week(1));
      await expect(main.getByText(play.roleGame("Grossist", 17), { exact: true })).toBeVisible();
      const seats = main.getByRole("region", { name: nb.homes.student.seats });
      await expect(seats.getByRole("listitem")).toHaveCount(4);
      await expect(seats.getByText(nb.homes.student.aiPlayer)).toHaveCount(2);
      await expect(seats.getByText(nb.homes.student.you("Demo Student"))).toBeVisible();
      await expect(main.getByRole("dialog")).toHaveCount(0);
      await expectAccessible(page, vp.phone);
      expect(presses).toHaveLength(1);
    });
  });
}

test("a game that has no snapshot yet offers no start, only the line", async ({ page }) => {
  await loginByApi(page, "student");
  const presses = await withGame(page, { status: "not_ready", week: null });
  await page.goto("/hjem");
  const main = page.getByRole("main");
  await expect(main.getByText(start.notReady)).toBeVisible();
  await expect(main.getByRole("button", { name: start.start })).toHaveCount(0);
  await expect(main.getByText(start.consequence)).toHaveCount(0);
  expect(presses).toHaveLength(0);
});

test("a refused start says why beside the button and stays on Hjem", async ({ page }) => {
  await loginByApi(page, "student");
  await withGame(page, { status: "ready", week: null }, { status: 409, code: "starting_task_required" });
  await page.goto("/hjem");
  const main = page.getByRole("main");
  await main.getByRole("button", { name: start.start }).click();
  await expect(main.getByText(start.errors.starting_task_required)).toBeVisible();
  await expect(page).toHaveURL(/\/hjem$/);
});

test("a running game's play route and Hjem lead to its open Week", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  await loginByApi(page, "student");
  await withGame(page, { status: "running", week: 11 });
  await page.goto("/hjem");
  const main = page.getByRole("main");
  const toWeek = main.getByRole("link", { name: start.toWeek(11) });
  await expect(toWeek).toHaveClass(/(^|\s)bg-ink(\s|$)/);
  await toWeek.click();
  await expect(main.getByRole("heading", { level: 1 })).toHaveText(play.week(11));
});

test("a running game this Student has not been briefed on shows «Les reglene» on the play route", async ({ page }) => {
  await loginByApi(page, "student");
  await withGame(page, { status: "running", week: 2 });
  await page.route(`**/api/me/games/${GAME_ID}`, (route) =>
    route.fulfill({ json: { ...game({ status: "running", week: 2 }), briefing_first: true } }),
  );
  await page.goto(`/spill/${GAME_ID}`);
  const main = page.getByRole("main");
  await expect(main.getByRole("link", { name: nb.homes.student.readRules })).toHaveClass(/(^|\s)bg-ink(\s|$)/);
  await expect(main.getByRole("heading", { level: 1 })).toHaveText(nb.homes.student.game(17, "Grossist"));
});

test("another Student's game shows the permission-denied page", async ({ page }) => {
  await loginByApi(page, "student");
  await page.goto(`/spill/${GAME_ID}`); // the real api: no game of the demo Student
  await expect(page.getByText(nb.access.denied)).toBeVisible();
});

async function studentPage(browser: Browser, email: string): Promise<Page> {
  const context = await browser.newContext({
    baseURL: test.info().project.use.baseURL,
    viewport: { width: 360, height: 740 },
  });
  const login = await context.request.post("/api/auth/login", { data: { email, password: DEMO_PASSWORD }, headers: CSRF });
  expect(login.status()).toBe(200);
  return context.newPage();
}

async function saveDates(lecturer: Page, sessionId: string, days: number[]) {
  const [start_at, play_deadline, debrief_deadline, test_deadline] = days.map((d) =>
    new Date(Date.now() + d * DAY).toISOString(),
  );
  const session = await (await lecturer.request.get(`/api/class-sessions/${sessionId}`)).json();
  const saved = await lecturer.request.put(`/api/class-sessions/${sessionId}`, {
    data: { ai_mode: session.ai_mode, dates: { start_at, play_deadline, debrief_deadline, test_deadline } },
    headers: CSRF,
  });
  expect(saved.status()).toBe(200);
}

test("when one Student starts the game, the other's open Hjem shows «Gå til Uke 1» within 2 s, focus kept", async ({
  page,
  browser,
  lecturerSession,
}) => {
  // The other Student (demo `student7@`) is registered on a fresh Class with a dated Class session,
  // so a real `user:` event reaches their stream; they are taken off its Roster again.
  const lecturer = await lecturerPage(browser, lecturerSession, { width: 1280, height: 800 });
  const klass = await freshClass(lecturer);
  const registered = await lecturer.request.post(`/api/classes/${klass.id}/roster/manual`, {
    data: { email: "student7@example.com", name: "Demo Student 7" },
    headers: CSRF,
  });
  expect(registered.status()).toBe(201);
  const entry = (await registered.json()).id as string;
  let other: Page | undefined;
  try {
    const created = await lecturer.request.post(`/api/classes/${klass.id}/class-sessions`, { headers: CSRF });
    expect(created.status()).toBe(201);
    const sessionId = (await created.json()).id as string;
    await saveDates(lecturer, sessionId, [5, 30, 33, 40]);

    // Both Students see the same game, ready to start.
    const state: State = { status: "ready", week: null };
    await loginByApi(page, "student");
    await withGame(page, state);
    other = await studentPage(browser, "student7@example.com");
    await withGame(other, state);
    await other.goto("/hjem");
    const theirs = other.getByRole("main");
    await expect(theirs.getByRole("button", { name: start.start })).toBeVisible();
    await expect(other.locator("html")).toHaveAttribute("data-live", "live", { timeout: 10_000 });
    const logout = other.getByRole("button", { name: nb.auth.session.logout });
    await logout.focus();

    await page.goto("/hjem");
    await page.getByRole("main").getByRole("button", { name: start.start }).click();
    await expect(page).toHaveURL(new RegExp(`/spill/${GAME_ID}$`));
    // The start's `user:` event to each seated Student (pinned by the api tests); here the real
    // stream carries a real `user:` event for the other Student.
    await saveDates(lecturer, sessionId, [5, 31, 34, 41]);
    await expect(theirs.getByRole("link", { name: start.toWeek(1) })).toBeVisible({ timeout: 2_000 });
    await expect(theirs.getByRole("button", { name: start.start })).toHaveCount(0);
    await expect(logout).toBeFocused();
  } finally {
    await other?.context().close();
    const removed = await lecturer.request.delete(`/api/classes/${klass.id}/roster/entries/${entry}`, { headers: CSRF });
    expect(removed.status()).toBe(204);
    await lecturer.context().close();
  }
});
