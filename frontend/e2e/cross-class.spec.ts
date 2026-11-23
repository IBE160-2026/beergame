import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { GROUP } from "../src/lib/number-format";
import { loginByApi } from "./support/auth";
import { expectAccessible, expectReflow, freshClass, freshLecturer, test, VIEWPORTS } from "./support/classes";

/** Tverrklasse-statistikk (Story 14.3, FR-65, FR-6, NFR-6, UX-DR51, UX-DR55) on the local stack: a
 * Lecturer's own Class sessions compared on their stored aggregates (the api's shape,
 * `backend/tests/reports/test_aggregates.py`) at 320 px, 1280 px with 200 % text and 1440 px, every
 * chart with «Vis som tabell», a withheld figure said in words; one Class session reads the empty
 * line from the real api; a Student is refused; the Klasserapport draws «Fjoråret». */
const copy = nb.crossClass;
const A = "01a1f8ee-34f2-70af-8800-f79281ed7b00";
const B = "01a1f8ee-34f2-70af-8800-f79281ed7b01";
const C = "01a1f8ee-34f2-70af-8800-f79281ed7b02";
const KEYS = [
  ["chain.median", "kroner", "2740.00", "1954.40"],
  ["cost.factory.median", "kroner", "880.00", "702.50"],
  ["cost.distributor.median", "kroner", "760.00", "601.00"],
  ["cost.wholesaler.median", "kroner", "610.00", "455.25"],
  ["cost.retailer.median", "kroner", "490.00", "300.00"],
  ["amplification.factory.median", "ratio", "6.90", "6.50"],
  ["amplification.distributor.median", "ratio", "4.20", "3.95"],
  ["amplification.wholesaler.median", "ratio", "2.80", "2.61"],
  ["amplification.retailer.median", "ratio", "1.40", "1.32"],
  ["ai.seats_percent", "percent", "8.5", "5.8"],
  ["learning.submitted_percent", "percent", "91.7", "88.3"],
  ["core.median", "points", null, "71.5"],
] as const;

function comparison() {
  return {
    sessions: [
      { class_session_id: A, class_name: "class-of-1993", session_number: 1, archived: true, written_at: "2026-01-02T09:00:00Z" },
      { class_session_id: B, class_name: "class-of-1994", session_number: 1, archived: false, written_at: "2026-11-20T09:00:00Z" },
      { class_session_id: C, class_name: "class-of-1994", session_number: 2, archived: false, written_at: null },
    ],
    measures: KEYS.map(([key, unit, first, second]) => ({
      key,
      unit,
      values: [
        // The first Class session's Core-only score had fewer than 10 ready assessments: withheld.
        { class_session_id: A, value: first, withheld: first === null },
        { class_session_id: B, value: second, withheld: false },
      ],
    })),
  };
}

async function stubbed(page: Page, body: unknown) {
  await page.route("**/api/class-statistics", (route) => route.fulfill({ json: body }).catch(() => undefined));
}

for (const viewport of VIEWPORTS) {
  test(`two Class sessions compared at ${viewport.name}: every measure, its table, and no page scroll`, async ({ page }) => {
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
    await stubbed(page, comparison());
    await page.goto("/tverrklasse-statistikk");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.title);
    await expect(page.getByText(copy.intro)).toBeVisible();
    const sections = page.locator("[data-report-section]");
    await expect(sections.locator("h2")).toHaveText(KEYS.map(([key]) => copy.measures[key]!));
    const chain = page.locator("[data-compare-bars=chain-median] [data-compare-row]");
    await expect(chain).toHaveCount(2);
    await expect(chain.first()).toContainText(`class-of-1993, Klasseøkt 1: 2${GROUP}740 kr`);
    await expect(page.locator("[data-compare-bars=core-median] [data-compare-value]")).toHaveText([copy.withheld, "71,5"]);
    await expect(page.locator("[data-compare-bars=amplification-factory-median] [data-compare-value]")).toHaveText([
      "6,90×",
      "6,50×",
    ]);
    // The Class session with no aggregate yet is listed, not compared.
    await expect(page.locator("[data-cross-class-waiting] li")).toHaveText(["class-of-1994, Klasseøkt 2"]);
    await expectAccessible(page, viewport.phone);

    const toggles = page.locator("[data-table-toggle]");
    expect(await toggles.count()).toBe(KEYS.length);
    for (const toggle of await toggles.all()) {
      await toggle.click();
      await expect(toggle).toHaveText(copy.showChart);
    }
    await expect(page.locator("[data-report-table=core-median] tbody tr")).toHaveText([
      new RegExp(`class-of-1993, Klasseøkt 1\\s*${copy.withheld.replace(/[().]/g, "\\$&")}`),
      /class-of-1994, Klasseøkt 1\s*71,5/,
    ]);
    if (viewport.name === "1440 px") await expectAccessible(page, false);
    else await expectReflow(page, viewport.phone);
  });
}

test("a fresh Lecturer with one Class session reads that there is nothing to compare with", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  try {
    const klass = await freshClass(lecturer);
    const made = await lecturer.request.post(`/api/classes/${klass.id}/class-sessions`, {
      headers: { "X-Requested-With": "olspillet" },
    });
    expect(made.ok()).toBe(true);
    // The real api: one Class session of the Lecturer's own, none of anyone else's.
    const answer = await (await lecturer.request.get("/api/class-statistics")).json();
    expect(answer.sessions).toHaveLength(1);
    expect(answer.measures).toEqual([]);
    await lecturer.goto("/tverrklasse-statistikk");
    await expect(lecturer.locator("[data-cross-class-empty]")).toHaveText(copy.empty);
  } finally {
    await lecturer.context().close();
  }
});

test("one Class session from the api: the empty line", async ({ page }) => {
  await loginByApi(page, "lecturer");
  await stubbed(page, { sessions: comparison().sessions.slice(1, 2), measures: [] });
  await page.goto("/tverrklasse-statistikk");
  await expect(page.locator("[data-cross-class-empty]")).toHaveText(copy.empty);
  await expectAccessible(page, false);
});

test("a Student gets the permission-denied page, as the api refuses them", async ({ page }) => {
  await loginByApi(page, "student");
  await page.goto("/tverrklasse-statistikk");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(nb.access.denied);
  await expect(page.locator("[data-cross-class]")).toHaveCount(0);
});

test("the Klasserapport draws «Fjoråret» from the previous Class session's stored median", async ({ page }) => {
  const SESSION = "01a1f8ee-34f2-70af-8800-f79281ed7c00";
  const spread = { values: ["1500.00", "1954.00", "2600.00"], median: "1954.00", lower_quartile: "1500.00", upper_quartile: "2600.00" };
  const roles = ["retailer", "wholesaler", "distributor", "factory"].map((role) => ({
    role,
    distribution: spread,
    holding_cost: "100.00",
    backorder_cost: "100.00",
    total_cost: "200.00",
  }));
  await loginByApi(page, "lecturer");
  await page.route(`**/api/class-sessions/${SESSION}/class-report`, (route) =>
    route
      .fulfill({
        json: {
          class_session_id: SESSION,
          class_id: "01a1f8ee-34f2-70af-8800-f79281ed7c01",
          class_name: "class-of-1994",
          session_number: 2,
          games: 3,
          finished: 3,
          facts_games: 0,
          funnel: [{ stage: "registered", count: 12 }],
          cost: {
            chain: spread,
            holding_cost: "949.40",
            backorder_cost: "1063.10",
            roles,
            games: spread.values.map((v, i) => ({ number: i + 1, chain_cost: v })),
            previous_median: "2740.00",
          },
          amplification: [],
          patterns: [],
          ai: { seats: 12, ai_seats: 0, whole_game: 0, ai_percent: "0.0", games: [], switches: [], llm_seats: 0, guard_switched: 0, guard_percent: null },
          ratings: [],
        },
      })
      .catch(() => undefined),
  );
  await page.goto(`/klasseokter/${SESSION}/klasserapport`);
  const chain = page.locator("[data-report-section=chain]");
  await expect(chain.locator("[data-chain-summary]")).toHaveText(
    `Median 1${GROUP}954. Midterste halvdel 1${GROUP}500–2${GROUP}600. Fjoråret 2${GROUP}740.`,
  );
  await expect(chain.locator("svg [data-mark=previous] text")).toHaveText(`Fjoråret 2${GROUP}740`);
  await expect(page.locator("[data-cross-class-link]")).toHaveAttribute("href", "/tverrklasse-statistikk");
});
