import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { loginByApi } from "./support/auth";
import { expectAccessible, expectReflow, test } from "./support/classes";

/** The Replay-gjennomgang (Story 10.7, FR-50, FR-44, FR-34, NFR-6, UX-DR64): the Student's
 * Totalkostnad, the Replay and the Class game on one Uke axis with «Vis som tabell», «Ikke like for
 * like.» with its reasons, the line (AI text marked) and the moments; «Gjennomgangen lages.» in a
 * Skjelett of the chart while the line is worded, then the walkthrough after the api's wait; a
 * Class game played mostly by AI players set aside in words; a closed Replay keeps Story 10.6's
 * message. Stand-ins with the api's shapes; that every number is the two Games' stored rows, the
 * job, the record and who may read it is `backend/tests/replay/test_walkthrough.py`. */
const GAME_ID = "01a1f8ee-34f2-70af-8800-f79281ed7b07";
const copy = nb.replay.walkthrough;

const VIEWPORTS = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
];

/** A run of `weeks` Uker: Netto lager swinging below zero, the running cost growing. */
function run(weeks: number, shift: number) {
  let total = 0;
  const rows = Array.from({ length: weeks }, (_, i) => {
    const net = Math.round(12 * Math.cos((i + shift) / 4)) - (i > weeks / 2 ? 6 : 0);
    total += net < 0 ? -net : net / 2;
    return { week: i + 1, net_inventory: net, order: 4 + ((i * 3) % 9), total_cost: total.toFixed(2) };
  });
  return { weeks: rows, total_cost: total.toFixed(2) };
}

const MOMENTS = [
  {
    id: "moment:wholesaler:9",
    week: 9,
    order: 20,
    heading: "Uke 9: du bestilte 20 da 16 allerede var på vei.",
    reckoning: "Posisjon 0 − 13 + 16 = 3. Med 20 ble den 23.",
    later: "De neste fire ukene, Uke 10 til Uke 13, kostet setet ditt 54,00 kr.",
    patterns: ["Stor ordre mens mye allerede er på vei: du bestilte mer enn ordren inn mens mye var på vei.", "Det du bestiller, kommer først etter noen uker."],
  },
  {
    id: "moment:wholesaler:21",
    week: 21,
    order: 2,
    heading: "Uke 21: du bestilte 2 da 30 allerede var på vei.",
    reckoning: "Posisjon 14 − 0 + 30 = 44. Med 2 ble den 46.",
    later: "De neste fire ukene, Uke 22 til Uke 25, kostet setet ditt 88,00 kr.",
    patterns: ["Ordren var 6 under ordren inn, som var 8."],
  },
];

const LINE = "I Uke 9 bestilte du 20 da ordren inn var 8, og i Uke 21 bestilte du 2 da ordren inn var 8.";

function ready(ai: boolean, mostlyAi = false) {
  return {
    game_id: GAME_ID,
    role: "wholesaler",
    state: "ready",
    retry_after_seconds: null,
    replay: run(32, 0),
    class_game: mostlyAi ? null : { ...run(36, 3), game_number: 17 },
    mostly_ai: mostlyAi,
    moments: mostlyAi ? [...MOMENTS, { ...MOMENTS[0]!, id: "moment:wholesaler:27", week: 27 }] : MOMENTS,
    narration: ai
      ? { text: LINE, ai_generated: true, llm_call_id: "01a1f8ee-0000-7000-8000-000000000107" }
      : { text: LINE, ai_generated: false, llm_call_id: null },
  };
}

const PENDING = { game_id: GAME_ID, role: "wholesaler", state: "pending", retry_after_seconds: 1, replay: null, class_game: null, mostly_ai: false, moments: [], narration: null };

async function open(page: Page, answers: object[], status = 200) {
  await loginByApi(page, "student");
  // Story 10.8: the two optional questions, as a finished Replay asks them; answers are stored.
  let rating: number | null = null;
  let round: boolean | null = null;
  await page.route(`**/api/me/games/${GAME_ID}/believability`, (route) => {
    if (route.request().method() === "POST") {
      rating = (route.request().postDataJSON() as { rating: number }).rating;
      return route.fulfill({ status: 201, json: { offered: true, rating } });
    }
    return route.fulfill({ json: { offered: true, rating } });
  });
  await page.route(`**/api/me/games/${GAME_ID}/another-round`, (route) => {
    if (route.request().method() === "POST") {
      round = (route.request().postDataJSON() as { answer: boolean }).answer;
      return route.fulfill({ status: 201, json: { answer: round } });
    }
    return route.fulfill({ json: { answer: round } });
  });
  let calls = 0;
  await page.route(`**/api/me/games/${GAME_ID}/walkthrough`, (route) => {
    const json = answers[Math.min(calls, answers.length - 1)]!;
    calls += 1;
    return route.fulfill({ status, json });
  });
  await page.goto(`/spill/${GAME_ID}/gjennomgang`);
  return () => calls;
}

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

for (const vp of VIEWPORTS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("pending: «Gjennomgangen lages.» in a Skjelett of the chart, no numbers; axe passes", async ({ page }) => {
      await open(page, [{ ...PENDING, retry_after_seconds: 60 }]);
      const main = page.getByRole("main");
      await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.title);
      await expect(main.getByRole("status").filter({ hasText: copy.pending })).toBeVisible();
      await expect(main.locator("[data-walkthrough-pending] [data-skeleton]")).toBeVisible();
      await expect(main.locator("[data-walkthrough-total]")).toHaveCount(0);
      await expect(main.locator("svg")).toHaveCount(0);
      await expect(main.locator("[data-replay-questions]")).toHaveCount(0);
      await expectAccessible(page, vp.phone);
      await expectReflow(page, vp.phone);
    });

    test("ready with AI text: totals, both runs on one axis, «Ikke like for like.», the marked line and two moments; axe passes", async ({ page }) => {
      await open(page, [ready(true)]);
      const main = page.getByRole("main");
      await expect(main.locator("[data-walkthrough-ready]")).toBeVisible();
      await expect(main.getByText(copy.roleReplay("Grossist"), { exact: true })).toBeVisible();
      await expect(main.locator("[data-walkthrough-total]")).toHaveText(/\d,\d\d kr$/);
      await expect(main.locator("[data-walkthrough-class-total]")).toBeVisible();
      await expect(main.getByText(copy.classTotalLabel(17))).toBeVisible();
      const chart = main.locator("[data-walkthrough-chart]");
      await expect(chart.locator('svg[aria-hidden="true"] [data-mark="net"]')).toHaveCount(1);
      await expect(chart.locator('svg [data-mark="compare"]')).toHaveCount(1);
      await expect(chart.getByText(copy.legend)).toBeVisible();
      const unlike = main.getByRole("region", { name: copy.unlike });
      await expect(unlike.getByRole("listitem")).toHaveText([copy.unlikeNeighbours, copy.unlikeDemand, copy.unlikeWeeks(32, 36)]);
      const narration = main.locator("[data-walkthrough-narration]");
      await expect(narration.locator('[data-ai-generated="true"]')).toContainText("KI-generert, kan ta feil:");
      await expect(narration).toContainText(nb.debrief.aiNote);
      await expect(main.locator("[data-walkthrough-moment]")).toHaveCount(2);
      await expect(main.getByRole("button", { name: /bedre|best/i })).toHaveCount(0);
      // Story 10.8: two optional questions follow the walkthrough.
      const questions = main.getByRole("region", { name: nb.replay.questions.title });
      await expect(questions.getByRole("group", { name: nb.believability.legend }).getByRole("radio")).toHaveCount(5);
      await expect(questions.getByRole("group", { name: nb.replay.questions.anotherRound }).getByRole("radio")).toHaveCount(2);
      await expectAccessible(page, vp.phone);
      await expectReflow(page, vp.phone);
    });

    test("code fallback: the same chart and numbers, the line without the KI prefix; axe passes", async ({ page }) => {
      await open(page, [ready(false)]);
      const main = page.getByRole("main");
      await expect(main.locator("[data-walkthrough-chart] svg [data-mark=\"compare\"]")).toHaveCount(1);
      const narration = main.locator("[data-walkthrough-narration]");
      await expect(narration).toContainText(LINE);
      await expect(narration.locator("[data-ai-generated]")).toHaveCount(0);
      await expect(narration).not.toContainText("KI-generert");
      await expectAccessible(page, vp.phone);
      await expectReflow(page, vp.phone);
    });
  });
}

test("the pending page reads again after the api's wait and shows the walkthrough", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  const calls = await open(page, [PENDING, ready(false)]);
  const main = page.getByRole("main");
  await expect(main.getByText(copy.pending)).toBeVisible();
  await expect(main.locator("[data-walkthrough-ready]")).toBeVisible({ timeout: 5000 });
  expect(calls()).toBeGreaterThanOrEqual(2);
});

test("both optional questions are answered, by keyboard and by pointer, each once", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  await open(page, [ready(false)]);
  const questions = page.getByRole("main").getByRole("region", { name: nb.replay.questions.title });
  // Two «Send svar», each named by its question (Story 10.8 follow-up).
  await expect(questions.getByRole("button", { name: nb.believability.sendName, exact: true })).toHaveCount(1);
  await expect(questions.getByRole("button", { name: nb.replay.questions.sendName, exact: true })).toHaveCount(1);
  const scale = questions.getByRole("group", { name: nb.believability.legend });
  await scale.getByRole("radio", { name: "5", exact: true }).focus();
  await page.keyboard.press("Space");
  await expect(scale.getByRole("radio", { name: "5", exact: true })).toHaveAccessibleDescription(nb.believability.high);
  await page.keyboard.press("Tab");
  await page.keyboard.press("Enter");
  await expect(questions.locator("[data-believability-saved]")).toHaveText(nb.believability.saved(5));
  const round = questions.getByRole("group", { name: nb.replay.questions.anotherRound });
  await round.getByRole("radio", { name: nb.replay.questions.no }).check();
  await questions.getByRole("button", { name: nb.replay.questions.sendName, exact: true }).click();
  await expect(questions.locator("[data-another-round-saved]")).toHaveText(nb.replay.questions.saved(false));
  await expect(questions.getByRole("radio")).toHaveCount(0);
  await expectAccessible(page, true);
});

test("«Vis som tabell» swaps the chart for every Uke of both runs, and back", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  await open(page, [ready(true)]);
  const chart = page.getByRole("main").locator("[data-walkthrough-chart]");
  await chart.getByRole("button", { name: copy.showTable }).click();
  const table = chart.locator("[data-walkthrough-table]");
  await expect(table).toBeVisible();
  await expect(table.locator("tbody tr")).toHaveCount(36);
  await expect(table.getByRole("columnheader", { name: copy.columnNet(copy.runClass) })).toBeVisible();
  await expect(table.getByRole("columnheader", { name: copy.columnCost(copy.runReplay) })).toBeVisible();
  await expectAccessible(page, true);
  await chart.getByRole("button", { name: copy.showChart }).click();
  await expect(chart.locator("svg")).toHaveCount(1);
});

test("a Class game played mostly by AI players is set aside in words, with three Replay moments", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  await open(page, [ready(false, true)]);
  const main = page.getByRole("main");
  await expect(main.locator("[data-walkthrough-mostly-ai]")).toHaveText(copy.mostlyAi);
  await expect(main.locator("[data-walkthrough-class-total]")).toHaveCount(0);
  await expect(main.locator('[data-walkthrough-chart] svg [data-mark="compare"]')).toHaveCount(0);
  await expect(main.getByText(copy.unlike)).toHaveCount(0);
  await expect(main.locator("[data-walkthrough-moment]")).toHaveCount(3);
  await expectAccessible(page, true);
});

test("a Replay closed at the Testfrist keeps its closed message; one not finished says so", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  await open(page, [{ error: { code: "replay_closed", message: "x" } }], 409);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(nb.games.play.replayClosed.title);
  await expect(page.getByRole("main").locator("[data-replay-closed]")).toContainText(nb.games.play.replayClosed.lead);
  await page.unrouteAll({ behavior: "ignoreErrors" });
  await open(page, [{ error: { code: "replay_not_finished", message: "x" } }], 409);
  await expect(page.getByRole("main").locator("[data-walkthrough-not-finished]")).toHaveText(copy.notFinished);
  await expect(page.getByRole("main").getByRole("link", { name: copy.toReplay })).toBeVisible();
});

test("the api refuses another Student's or an Admin's read (403)", async ({ page }) => {
  for (const role of ["student", "admin"] as const) {
    await loginByApi(page, role);
    const response = await page.request.get(`/api/me/games/${GAME_ID}/walkthrough`);
    expect(response.status()).toBe(403);
  }
  await loginByApi(page, "student");
  await page.goto(`/spill/${GAME_ID}/gjennomgang`);
  await expect(page.getByRole("heading", { level: 1 })).not.toHaveText(copy.title);
});
