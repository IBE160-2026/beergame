import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { GROUP } from "../src/lib/number-format";
import { loginByApi } from "./support/auth";
import { expectAccessible, expectReflow, test, VIEWPORTS } from "./support/classes";

/** «Tverrinstitusjonell statistikk» (Story 14.7, cut list, FR-65, FR-5, AD-12, AD-14) on the local
 * stack, where `FEATURE_CROSS_INSTITUTION_STATS` is on: the Admin reaches it from the Admin-område;
 * the stored aggregates grouped by Institution (the api's shape,
 * `backend/tests/reports/test_cross_institution.py`) at 320 px, 1280 px with 200 % text and 1440 px,
 * every chart with «Vis som tabell», a withheld Institution said in words, an Institution that
 * differs labelled «Ulikt oppsett», no Class named; a filter refetches with its value; a Lecturer is
 * refused by the api. The stack runs with the flag on: the page's flag-off case is served a `/me`
 * that says it is off, and the api's 404 is pinned by the backend tests. */
const copy = nb.crossInstitution;
const words = nb.crossClass;
const X = "01a1f8ee-34f2-70af-8800-f79281ed7d00";
const Y = "01a1f8ee-34f2-70af-8800-f79281ed7d01";
const Z = "01a1f8ee-34f2-70af-8800-f79281ed7d02";
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

function statistics() {
  return {
    institutions: [
      { institution_id: X, name: "Høgskolen i Innlandet", sessions: 3, withheld: false, differs: ["ai_mode"] },
      { institution_id: Y, name: "NTNU", sessions: 2, withheld: false, differs: [] },
      { institution_id: Z, name: "UiA", sessions: 1, withheld: true, differs: [] },
    ],
    measures: KEYS.map(([key, unit, first, second]) => ({
      key,
      unit,
      values: [
        // The first Institution's Core-only scores were withheld in every Class session.
        { institution_id: X, value: first, withheld: first === null, sessions: first === null ? 0 : 3 },
        { institution_id: Y, value: second, withheld: false, sessions: 2 },
        { institution_id: Z, value: null, withheld: true, sessions: 0 },
      ],
      comparable: key === "core.median" ? false : null,
    })),
    filters: [],
    ready: 6,
    compared: 6,
  };
}

async function stubbed(page: Page, body: unknown) {
  await page.route("**/api/institution-statistics*", (route) => route.fulfill({ json: body }).catch(() => undefined));
}

for (const viewport of VIEWPORTS) {
  test(`three Institutions at ${viewport.name}: every measure, its table, and no page scroll`, async ({ page }) => {
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
    await loginByApi(page, "admin");
    await stubbed(page, statistics());
    await page.goto("/admin/tverrinstitusjonell-statistikk");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.title);
    await expect(page.getByText(copy.intro)).toBeVisible();
    const sections = page.locator("[data-report-section]");
    await expect(sections.locator("h2")).toHaveText(KEYS.map(([key]) => words.measures[key]!));
    const chain = page.locator("[data-compare-bars=chain-median] [data-compare-row]");
    await expect(chain).toHaveCount(3);
    await expect(chain.first()).toContainText(`Høgskolen i Innlandet: 2${GROUP}740 kr (3 Klasseøkter). Ulikt oppsett: KI-modus`);
    await expect(page.locator("[data-compare-bars=core-median] [data-compare-value]")).toHaveText([
      words.withheld,
      "71,5 (2 Klasseøkter)",
      copy.withheld,
    ]);
    await expect(page.locator("[data-compare-bars=chain-median] [data-compare-bar] rect")).toHaveCount(2);
    await expect(page.locator("[data-cross-institution-withheld]")).toHaveText([copy.withheldNote("UiA")]);
    await expect(page.locator("[data-report-section=core-median]")).toContainText(words.scoresNotComparable);
    // No Class or Class session is named.
    await expect(page.locator("main")).not.toContainText("Klasseøkt 1");
    await expectAccessible(page, viewport.phone);

    const toggles = page.locator("[data-table-toggle]");
    expect(await toggles.count()).toBe(KEYS.length);
    for (const toggle of await toggles.all()) {
      await toggle.click();
      await expect(toggle).toHaveText(words.showChart);
    }
    await expect(page.locator("[data-report-table=chain-median] tbody tr")).toHaveText([
      new RegExp(`Høgskolen i Innlandet\\s*2${GROUP}740 kr\\s*3\\s*Ulikt oppsett: KI-modus`),
      new RegExp(`NTNU\\s*1${GROUP}954 kr\\s*2\\s*${words.sameSetup}`),
      new RegExp(`UiA\\s*${copy.withheld.replace(/[().]/g, "\\$&")}\\s*0`),
    ]);
    if (viewport.name === "1440 px") await expectAccessible(page, false);
    else await expectReflow(page, viewport.phone);
  });
}

test("the Admin reaches it from the Admin-område and reads the real api", async ({ page }) => {
  await loginByApi(page, "admin");
  await page.goto("/admin");
  await page.getByRole("link", { name: nb.admin.sections.crossInstitution }).click();
  await expect(page).toHaveURL(/\/admin\/tverrinstitusjonell-statistikk$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.title);
  // The stack's own aggregates, or none yet: either way the page answers.
  await expect(page.locator("[data-cross-institution], [data-cross-institution-empty]")).toBeVisible();
});

test("no aggregate: the empty line", async ({ page }) => {
  await loginByApi(page, "admin");
  await stubbed(page, { institutions: [], measures: [], filters: [], ready: 0, compared: 0 });
  await page.goto("/admin/tverrinstitusjonell-statistikk");
  await expect(page.locator("[data-cross-institution-empty]")).toHaveText(copy.empty);
  await expectAccessible(page, false);
});

test("a Lecturer gets the permission-denied page and the api refuses them", async ({ page }) => {
  await loginByApi(page, "lecturer");
  const response = await page.request.get("/api/institution-statistics");
  expect(response.status()).toBe(403);
  await page.goto("/admin/tverrinstitusjonell-statistikk");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(nb.access.denied);
  await expect(page.locator("[data-cross-institution]")).toHaveCount(0);
});

test("a filter refetches with its value and says how many Class sessions it compares", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await loginByApi(page, "admin");
  const LLM = "a1b2c3d4e5f60718";
  const asked: (string | null)[] = [];
  await page.route("**/api/institution-statistics*", (route) => {
    const aiMode = new URL(route.request().url()).searchParams.get("ai_mode");
    asked.push(aiMode);
    const base = statistics();
    const chosen = aiMode === LLM;
    const body = {
      ...base,
      institutions: chosen ? base.institutions.slice(1, 2) : base.institutions,
      measures: base.measures.map((m) => ({ ...m, values: chosen ? m.values.slice(1, 2) : m.values })),
      compared: chosen ? 2 : 6,
      filters: [
        {
          dimension: "ai_mode",
          all_count: 6,
          options: [
            { value: LLM, label: "llm", ordinal: 0, count: 2, selected: chosen },
            { value: "0f1e2d3c4b5a6978", label: "rule_based", ordinal: 0, count: 4, selected: false },
          ],
        },
      ],
    };
    return route.fulfill({ json: body }).catch(() => undefined);
  });
  await page.goto("/admin/tverrinstitusjonell-statistikk");
  const llm = page.locator("[data-filter-group=ai_mode] [data-filter=a1b2c3d4e5f60718]");
  await expect(llm).toHaveAttribute("aria-pressed", "false");
  await llm.click();
  await expect(llm).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator("[data-cross-institution-announce]")).toHaveText(copy.comparing(2, 6));
  await expect(page.locator("[data-compare-bars=chain-median] [data-compare-row]")).toHaveCount(1);
  expect(asked).toContain(LLM);
  await expectAccessible(page, false);
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

test("with the flag off the page does not exist and the Admin-område has no link", async ({ page }) => {
  await loginByApi(page, "admin");
  await page.route("**/api/auth/me", async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    await route.fulfill({ response, json: { ...body, user: { ...body.user, cross_institution_stats: false } } });
  });
  await page.goto("/admin/tverrinstitusjonell-statistikk");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(nb.access.notFound);
  await page.goto("/admin");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(nb.homes.adminArea);
  await expect(page.getByRole("link", { name: nb.admin.sections.crossInstitution })).toHaveCount(0);
  await page.unrouteAll({ behavior: "ignoreErrors" });
});
