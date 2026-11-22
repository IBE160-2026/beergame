import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { formatNumber } from "../src/lib/number-format";
import type { GameResult } from "../src/modules/games/api";
import result from "../src/modules/games/fixtures/result-classic.json";
import week11 from "../src/modules/games/fixtures/play-week-11.json";
import { loginByApi } from "./support/auth";
import { expectAccessible, expectReflow, lecturerPage, test } from "./support/classes";
import { liveClassGame } from "./support/live-game";

/** The Replay's end and the real Replay on the stack (Story 10.5, FR-34, FR-48, FR-50, NFR-6,
 * UX-DR5, UX-DR64). «Replay er ferdig» with the Student's own Totalkostnad and the one primary
 * «Gå til gjennomgangen», never the Class game's «Gå til Debrief»; Hjem's finished Replay is read
 * again by a Lenke. These two use stand-ins with the api's shapes; that the last Order finishes the
 * Replay, records the step and opens the next one is `backend/tests/replay/test_finish.py`. The last
 * test runs on the stack, with no stand-in: a fresh Class game, the Student's steps up to the passed
 * Debrief quiz through the local dev route, a real Replay started, whose play screen draws the
 * projection while the Class game's does not; its Class's Lecturer reaches it on Spillinnsikt. */
const GAME_ID = "01a1f8ee-34f2-70af-8800-f79281ed7a66";
const SESSION = "01a1f8ee-33b9-75e6-9502-79db27b37c0e";
const CSRF = { "X-Requested-With": "olspillet" };
const copy = nb.games.play;
const classic = result as GameResult;
const AI_SEATS = week11.table_status.seats.map((seat) => (seat.mine ? seat : { ...seat, holder: "ai", name: null }));

const VIEWPORTS = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
];

async function openFinished(page: Page) {
  await loginByApi(page, "student");
  await page.route(`**/api/me/games/${GAME_ID}`, (route) =>
    route.fulfill({
      json: {
        id: GAME_ID,
        number: null,
        replay: true,
        test_game: false,
        class_session_id: SESSION,
        role: "wholesaler",
        seats: AI_SEATS,
        briefing_first: false,
        rules: { order_delay: 2, shipping_delay: 2, production_delay: 2, guided_weeks: 0, holding_cost: "0.50", backorder_cost: "1.00" },
        status: "finished",
        week: null,
        server_now: "2026-11-22T10:00:00Z",
        seat_state: null,
        turn: null,
        debrief: null,
      },
    }),
  );
  await page.route(`**/api/me/games/${GAME_ID}/result`, (route) => route.fulfill({ json: classic }));
  await page.goto(`/spill/${GAME_ID}`);
}

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

for (const vp of VIEWPORTS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("«Replay er ferdig»: own Totalkostnad, one primary «Gå til gjennomgangen», no Debrief; axe passes", async ({ page }) => {
      await openFinished(page);
      const main = page.getByRole("main");
      await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.replayEnd.title);
      await expect(page.getByText(copy.roleReplay("Grossist"), { exact: true })).toBeVisible();
      const own = classic.roles.find((row) => row.role === "wholesaler")!;
      // The shared formatter's total, «553,50 kr», with the space before «kr» the hero keeps.
      const total = formatNumber(own.total_cost, { kroner: true }).replace(/\s(kr)$/, " $1");
      await expect(main.locator("[data-replay-total]")).toHaveText(total);
      await expect(main.getByText(copy.replayEnd.totalLabel, { exact: true })).toBeVisible();
      const walkthrough = main.getByRole("link", { name: copy.replayEnd.toWalkthrough });
      await expect(walkthrough).toHaveAttribute("href", `/spill/${GAME_ID}/gjennomgang`);
      await expect(main.locator("a.bg-ink, button.bg-ink")).toHaveCount(1);
      await expect(walkthrough).toHaveClass(/\bbg-ink\b/);
      await expect(main.getByText(copy.end.toDebrief)).toHaveCount(0);
      await expect(main.getByText(copy.end.why)).toHaveCount(0);
      await expect(main.getByText(copy.end.title)).toHaveCount(0);
      await expectAccessible(page, vp.phone);
      await expectReflow(page, vp.phone);
    });
  });
}

test("Hjem reads a finished Replay again through «Se Replay», with Stegene on the Individual test", async ({ page }) => {
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
      next_deadline: { kind: "test", at: "2026-12-08T13:00:00Z" },
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
        server_now: "2026-11-22T10:00:00Z",
        seat_state: null,
        turn: null,
        debrief: "open",
        rules: { order_delay: 2, shipping_delay: 2, production_delay: 2, guided_weeks: 4, holding_cost: "0.50", backorder_cost: "1.00" },
      },
      steps: ["class_game", "debrief", "quiz", "replay", "test", "report"].map((step, i) => ({
        step,
        state: i < 4 ? "done" : i === 4 ? "current" : "locked",
        held: false,
        quiz_changed: false,
        group_open: false,
        closed: false,
      })),
      replay: {
        can_start: false,
        game: { id: GAME_ID, role: "wholesaler", status: "finished", week: null, server_now: "2026-11-22T10:00:00Z", seats: AI_SEATS },
      },
    };
    await route.fulfill({ response, json: { items: [item] } });
  });
  await page.goto("/hjem");
  const main = page.getByRole("main");
  const block = main.getByRole("region", { name: "Replay · Du er Grossist" });
  const view = block.getByRole("link", { name: nb.homes.student.replay.view });
  await expect(view).toHaveAttribute("href", `/spill/${GAME_ID}`);
  await expect(view).not.toHaveClass(/\bbg-ink\b/);
  await expect(block.getByText(/Fortsett Replay/)).toHaveCount(0);
  const steps = main.getByRole("region", { name: nb.homes.student.steps }).getByRole("listitem");
  await expect(steps.nth(3)).toContainText(nb.homes.student.done);
  await expect(steps.nth(4)).toContainText(nb.homes.student.current);
  await expectAccessible(page, true);
});

test("live: a real Replay's play screen draws the projection, the Class game's none; staff reach it on Spillinnsikt", async ({
  browser,
  lecturerSession,
}) => {
  test.slow(); // an Invitation through the worker, a Class session, a lock, a Replay
  const game = await liveClassGame(browser, lecturerSession, 1, { aiMode: "rule_based" });
  const [student] = game.students;
  const passed = await student!.context.request.post(`/api/dev/class-sessions/${game.sessionId}/quiz-passed`, {
    headers: CSRF,
  });
  expect(passed.status()).toBe(204);
  const started = await student!.context.request.post(`/api/me/class-sessions/${game.sessionId}/replay`, { headers: CSRF });
  expect(started.status()).toBe(201);
  const replayId = (await started.json()).game_id as string;

  const page = await student!.context.newPage();
  await page.goto(`/spill/${replayId}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.week(1));
  const graph = page.locator('svg[data-chart="net"]:visible');
  await expect(graph).toHaveCount(1);
  await expect(graph.locator("[data-mark=projection]")).toHaveCount(1);
  await expect(page.locator("[data-projection-sentence]")).toHaveCount(1);

  await page.goto(`/spill/${game.gameId}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.week(1));
  await expect(page.locator('svg[data-chart="net"]:visible')).toHaveCount(1);
  await expect(page.locator("[data-mark=projection]")).toHaveCount(0);
  await expect(page.locator("[data-projection-sentence]")).toHaveCount(0);

  // The Lecturer: from the Student's Seat on the Class game's Spillinnsikt to the Replay's.
  const lecturer = await lecturerPage(browser, lecturerSession, { width: 1280, height: 800 });
  await lecturer.goto(`/klasseokter/${game.sessionId}/oversikt/spill/${game.gameId}`);
  const link = lecturer.getByRole("main").getByRole("link", { name: nb.insight.links.replay, exact: true });
  await link.click();
  await expect(lecturer).toHaveURL(new RegExp(`/oversikt/spill/${replayId}$`));
  await expect(lecturer.getByRole("heading", { level: 1 })).toHaveText(nb.insight.replayTitle);
  const seats = lecturer.locator("[data-insight-seats] > li");
  await expect(seats.filter({ hasText: nb.insight.aiPlayer })).toHaveCount(3);
  // A Replay is no Class game: no Message to it, nor to its Student from here.
  await expect(lecturer.locator("[data-message-game]")).toHaveCount(0);
  await expect(lecturer.locator("[data-message-student]")).toHaveCount(0);
});
