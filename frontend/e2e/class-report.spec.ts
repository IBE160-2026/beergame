import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { GROUP } from "../src/lib/number-format";
import { loginByApi } from "./support/auth";
import { expectAccessible, expectReflow, lecturerPage, test, VIEWPORTS } from "./support/classes";
import { liveClassGame } from "./support/live-game";

/** The Klasserapport (Story 14.1, FR-64, FR-68, FR-70, FR-79, FR-5, NFR-6, UX-DR55, UX-DR73) on
 * the local stack: a real Class game played out turns an open report live from «Ingen spill er
 * ferdige ennå.» to its figures, and the job stores its analysis; a report of 60 games (the api's
 * shape, `backend/tests/reports/test_class_report.py`) at 320 px, 1280 px with 200 % text and
 * 1440 px, every chart with «Vis som tabell»; anyone but the Class's Lecturers is refused. */
const copy = nb.classReport;
const CSRF = { "X-Requested-With": "olspillet" };
const SESSION = "01a1f8ee-34f2-70af-8800-f79281ed7a00";
const ROLES = ["retailer", "wholesaler", "distributor", "factory"] as const;

const spread = (median: number, low: number, high: number, values: number[]) => ({
  values: values.map((v) => v.toFixed(2)),
  median: median.toFixed(2),
  lower_quartile: low.toFixed(2),
  upper_quartile: high.toFixed(2),
});

/** 60 Class games, 41 finished, 38 with their analysis: the spine's own example (FR-64). */
function richReport() {
  const costs = Array.from({ length: 41 }, (_, i) => 1200 + ((i * 97) % 1800));
  return {
    class_session_id: SESSION,
    class_id: "01a1f8ee-34f2-70af-8800-f79281ed7a01",
    class_name: "class-of-2026",
    session_number: 2,
    games: 60,
    finished: 41,
    facts_games: 38,
    funnel: [
      { stage: "registered", count: 60 },
      { stage: "class_game", count: 41 },
      { stage: "debrief", count: 30 },
      { stage: "quiz_passed", count: 22 },
      { stage: "replay", count: 12 },
      { stage: "test_submitted", count: 4 },
      { stage: "assessment_ready", count: 0 },
    ],
    cost: {
      chain: spread(1954, 1500, 2600, costs),
      holding_cost: "949.40",
      backorder_cost: "1063.10",
      roles: ROLES.map((role, i) => ({
        role,
        distribution: spread(300 + i * 150, 220 + i * 120, 420 + i * 190, costs.map((c) => (c / 4) * (0.6 + i * 0.3))),
        holding_cost: (150 + i * 60).toFixed(2),
        backorder_cost: (140 + i * 90).toFixed(2),
        total_cost: (290 + i * 150).toFixed(2),
      })),
      games: costs.map((c, i) => ({ number: i + 1, chain_cost: c.toFixed(2) })),
    },
    amplification: ROLES.map((role, i) => ({
      role,
      games: 38,
      distribution: spread(1.2 + i * 1.6, 1 + i * 1.2, 1.6 + i * 2, Array.from({ length: 38 }, (_, g) => 0.9 + i * 1.5 + (g % 7) * 0.3)),
    })),
    patterns: [
      { pattern: "large-order-full-supply-line", name: "Stor ordre mens mye allerede er på vei", occurrences: 212, games: 33 },
      { pattern: "surge-after-shortage", name: "Ordre langt over innkommende ordre etter mangel", occurrences: 174, games: 29 },
      { pattern: "low-after-overshoot", name: "Svært lave ordre etter en overreaksjon", occurrences: 61, games: 17 },
    ],
    ai: {
      seats: 164,
      ai_seats: 14,
      whole_game: 9,
      ai_percent: "8.5",
      games: costs.map((_, i) => ({
        number: i + 1,
        ordered: 140,
        llm: i % 5 === 0 ? 35 : 0,
        llm_percent: i % 5 === 0 ? "25.0" : "0.0",
        fallback: i % 9 === 0 ? 1 : 0,
      })),
      switches: [
        { number: 4, role: "wholesaler", week: 12, mark: "guard_switch" },
        { number: 17, role: "factory", week: 20, mark: "cost_limit" },
      ],
      llm_seats: 9,
      guard_switched: 1,
      guard_percent: "11.1",
    },
    ratings: [
      { ai_mode: "llm", count: 23, median: "4", values: [1, 2, 3, 4, 5].map((r) => ({ rating: r, count: [1, 2, 5, 10, 5][r - 1] })) },
      { ai_mode: "rule_based", count: 8, median: "3.5", values: [1, 2, 3, 4, 5].map((r) => ({ rating: r, count: [0, 1, 3, 3, 1][r - 1] })) },
    ],
  };
}

async function stubbed(page: Page, body: unknown, status = 200) {
  await page.route(`**/api/class-sessions/${SESSION}/class-report`, (route) =>
    route.fulfill(status === 200 ? { json: body } : { status, json: body }).catch(() => undefined),
  );
}

const section = (page: Page, name: string) => page.locator(`[data-report-section=${name}]`);

test("live: the report turns from no finished game to its figures as the game is played out", async ({
  browser,
  lecturerSession,
}) => {
  test.slow(); // an Invitation through the worker, a Class session, a lock and the facts job
  const game = await liveClassGame(browser, lecturerSession, 2, {
    aiMode: "rule_based",
    gameSettings: { weeks: 3, demand: { kind: "step", start: 4, new_level: 8, change_week: 2 } },
  });
  const lecturer = await lecturerPage(browser, lecturerSession, { width: 1440, height: 900 });
  try {
    // From the Oversikt's header, for a Lecturer of the Class.
    await lecturer.goto(`/klasseokter/${game.sessionId}/oversikt`);
    await lecturer.getByRole("link", { name: copy.link, exact: true }).click();
    await expect(lecturer.getByRole("heading", { level: 1 })).toHaveText(copy.title);
    await expect(lecturer.locator("[data-report-status]")).toHaveText(copy.none);
    await expect(section(lecturer, "funnel")).toBeVisible();
    await expect(section(lecturer, "chain")).toHaveCount(0);
    await expect(lecturer.locator("html")).toHaveAttribute("data-live", "live", { timeout: 10_000 });

    const played = await game.students[0]!.context.request.post(`/api/dev/games/${game.gameId}/playout`, { headers: CSRF });
    expect(played.status()).toBe(200);
    // `session:<id>` refetches the open report: the game is in, and its analysis follows from the
    // `llm-batch` job of `worker-batch`.
    await expect(lecturer.locator("[data-report-status]")).toHaveText(copy.all(1), { timeout: 20_000 });
    await expect(section(lecturer, "chain").locator("[data-chain-summary]")).toHaveText(/^Median \d/);
    await expect(section(lecturer, "amplification").locator("[data-covered]")).toHaveCount(0, { timeout: 30_000 });
    await expect(section(lecturer, "ai").locator("[data-ai-seats]")).toHaveText(/av 4 seter/);
    await expect(lecturer.locator("[data-report-table=llm] tbody tr")).toHaveText([/^Spill 1/]);
    await expectAccessible(lecturer, false);
  } finally {
    await lecturer.context().close();
    for (const student of game.students) await student.context.close();
  }
});

for (const viewport of VIEWPORTS) {
  test(`a report of 60 games at ${viewport.name}: every chart, its table, and no page scroll`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    if (viewport.text200) {
      await page.addInitScript(() => {
        document.addEventListener("DOMContentLoaded", () => {
          const style = document.createElement("style");
          style.textContent = "html { font-size: 200% !important; }";
          document.head.appendChild(style);
        });
      });
    }
    await loginByApi(page, "lecturer");
    await stubbed(page, richReport());
    await page.goto(`/klasseokter/${SESSION}/klasserapport`);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.title);
    await expect(page.locator("[data-report-status]")).toHaveText(copy.partial(41, 60));
    await expect(section(page, "chain").locator("[data-chain-summary]")).toHaveText(
      `Median 1${GROUP}954. Midterste halvdel 1${GROUP}500–2${GROUP}600.`,
    );
    await expect(section(page, "chain").locator("[data-chain-split]")).toHaveText(
      `Snitt per spill: lager 949 kr, restordre 1${GROUP}063 kr.`,
    );
    // Role lists: Fabrikk at the top; per-Role tables: Detaljist to Fabrikk (UX-DR73).
    await expect(section(page, "roles").locator("[data-role] h3")).toHaveText(["Fabrikk", "Distributør", "Grossist", "Detaljist"]);
    await expect(section(page, "patterns").getByRole("heading", { name: "Mønstre" })).toBeVisible();
    await expect(section(page, "amplification").locator("[data-covered]")).toHaveText(copy.covered(38, 41));
    await expect(section(page, "ai").locator("[data-switches] li")).toHaveText([
      "Spill 4, Grossist, fra Uke 12: Byttet til regelbasert KI (spillvakt)",
      "Spill 17, Fabrikk, fra Uke 20: Byttet til regelbasert KI (kostnadsgrense)",
    ]);
    await expect(section(page, "ai").locator("[data-guard]")).toHaveText("Spillvakten byttet 1 av 9 seter med LLM-spiller (11,1 %).");
    await expect(section(page, "ratings").locator("[data-rating-mode=rule_based] p").first()).toHaveText(
      "Regelbaserte KI-spillere: 8 svar, median 3,5.",
    );
    // Every chart SVG has its title and is hidden from assistive technology (AD-18).
    const charts = page.locator("svg[data-chart=cost-distribution]");
    expect(await charts.count()).toBe(9);
    for (const chart of await charts.all()) {
      await expect(chart).toHaveAttribute("aria-hidden", "true");
      await expect(chart.locator("title")).not.toBeEmpty();
    }
    await expectAccessible(page, viewport.phone);

    // «Vis som tabell» under each chart swaps it for its table, and back.
    const toggles = page.locator("[data-table-toggle]");
    expect(await toggles.count()).toBe(7);
    for (const toggle of await toggles.all()) {
      await expect(toggle).toHaveText(copy.showTable);
      await toggle.click();
      await expect(toggle).toHaveText(copy.showChart);
    }
    await expect(page.locator("[data-report-table=roles] tbody th")).toHaveText(["Detaljist", "Grossist", "Distributør", "Fabrikk"]);
    await expect(page.locator("[data-report-table=chain] tbody tr")).toHaveCount(41);
    await expect(page.locator("[data-report-table=funnel] tbody tr").first()).toHaveText(/Registrert\s*60/);
    if (viewport.name === "1440 px") await expectAccessible(page, false);
    else await expectReflow(page, viewport.phone);
  });
}

test("no finished game reads the spine's line and only the Trakt", async ({ page }) => {
  await loginByApi(page, "lecturer");
  const none = { ...richReport(), finished: 0, facts_games: 0, cost: null, patterns: [], ratings: [] };
  await stubbed(page, { ...none, ai: { ...none.ai, games: [], switches: [], seats: 0, ai_seats: 0, whole_game: 0 } });
  await page.goto(`/klasseokter/${SESSION}/klasserapport`);
  await expect(page.locator("[data-report-status]")).toHaveText("Ingen spill er ferdige ennå.");
  await expect(page.locator("[data-report-section]")).toHaveCount(1);
});

test("an Assistant lecturer gets the permission-denied page, as the api refuses them", async ({ page }) => {
  await loginByApi(page, "assistant");
  await page.goto(`/klasseokter/${SESSION}/klasserapport`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(nb.access.denied);
  await expect(page.locator("[data-class-report]")).toHaveCount(0);
});
