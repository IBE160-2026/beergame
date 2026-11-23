import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { loginByApi } from "./support/auth";
import { expectAccessible, test } from "./support/classes";

/** The results of a Control test (Story 12.10, FR-82, FR-81, NFR-6, UX-DR57): the Admin opens
 * «Resultater» from «Sensorer» and reads «Teller aldri med i en Klasseøkt.», the pinned Scoring
 * guide version and model config, whether the guide is checked or the numbers are preliminary
 * (and what is missing, in words), the five measures as labelled numbers, agreement by answer
 * length, and every answer's human and AI steps side by side in an HTML table. Preliminary and
 * complete at 320, 360 and 1440 px with axe. These use stand-ins with the api's shapes; the
 * measures, the checked mark and access are `backend/tests/assessment/test_control_results.py`
 * and `backend/tests/analysis/test_agreement.py`. */
const SESSION = "01a20500-0000-7000-8000-000000000001";
const copy = nb.scoring.results;

const VIEWPORTS = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
];

const TEST = { id: SESSION, name: "Kontrolltest høst", test_deadline: "2026-11-20T22:59:00Z", open: true };
const BANDS = [
  { band: "short", min_words: 0, max_words: 49, pairs: 3, exact: 0.6667, within_one: 1 },
  { band: "medium", min_words: 50, max_words: 149, pairs: 1, exact: 0, within_one: 0 },
  { band: "long", min_words: 150, max_words: null, pairs: 0, exact: null, within_one: null },
];
const PRELIMINARY = {
  test: TEST,
  scoring_guide: { version: 1, edited: false },
  ai_config: { name: "mock-b", model_version: "mock-1" },
  scorers: [{ name: "Sara Sensor" }, { name: "Per Sensor" }],
  rows: [
    { number: 1, type: "long", question: "q", words: 12, human: [3, null], ai: 3 },
    { number: 2, type: "long", question: "q", words: 80, human: [0, null], ai: 2 },
    { number: 3, type: "adapted", question: "q", words: 30, human: [2, null], ai: 2 },
    { number: 4, type: "adapted", question: "q", words: 9, human: [1, null], ai: null },
  ],
  missing: 4,
  ai_missing: 1,
  open_attempts: 1,
  complete: false,
  checked: false,
  withheld: false,
  measures: { pairs: 3, exact: 0.6667, within_one: 0.6667, offset: 0.6667, compression: 0.4472, by_length: BANDS },
};
const COMPLETE = {
  ...PRELIMINARY,
  scorers: [{ name: "Sara Sensor" }],
  rows: PRELIMINARY.rows.map((row) => ({ ...row, human: [row.human[0]] })),
  missing: 0,
  ai_missing: 0,
  open_attempts: 0,
  complete: true,
  checked: true,
  measures: { ...PRELIMINARY.measures, pairs: 4, exact: 0.75, within_one: 0.75, offset: -0.25 },
};

async function standIn(page: Page, body: unknown) {
  await loginByApi(page, "admin");
  await page.route(`**/api/admin/control-tests/${SESSION}/results`, (route) => route.fulfill({ status: 200, json: body }));
}

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

for (const vp of VIEWPORTS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("preliminary: what is missing in words, the measures labelled, the scores side by side; axe passes", async ({ page }) => {
      await standIn(page, PRELIMINARY);
      await page.goto(`/admin/kontrolltest/${SESSION}/resultater`);
      await expect(page.getByRole("heading", { level: 1 })).toHaveText(`${copy.title}: ${TEST.name}`);
      const main = page.getByRole("main");
      await expect(main).toContainText(nb.admin.controlTests.never);
      await expect(main).toContainText("Versjon 1, standard");
      await expect(main).toContainText("mock-b (mock-1)");
      const status = main.locator("[data-results-status]");
      await expect(status).toHaveAttribute("data-results-status", "preliminary");
      await expect(status).toContainText(copy.preliminary);
      await expect(status).toContainText("4 vurderinger mangler.");
      await expect(status).toContainText("1 test er ikke levert ennå.");
      await expect(status).toContainText("KI-vurderingen mangler for 1 svar.");
      await expect(main.locator('[data-measure="exact"]')).toContainText(`${copy.measures.exact}66,7 %`);
      await expect(main.locator('[data-measure="within-one"]')).toContainText("66,7 %");
      await expect(main.locator('[data-measure="offset"]')).toContainText("+0,67 trinn");
      await expect(main.locator('[data-measure="compression"]')).toContainText("0,45");
      await expect(main.locator('[data-band="long"]')).toContainText(copy.measures.none);
      const table = main.locator("table[data-side-by-side]");
      await expect(table.getByRole("columnheader")).toHaveText(["Svar", "Type", "Ord", "Sara Sensor", "Per Sensor", "KI"]);
      await expect(table.locator('[data-row="2"]').getByRole("cell")).toHaveText(["Langsvar", "80", "0", "Ikke vurdert", "2"]);
      await expect(table.locator('[data-row="4"] [data-ai]')).toHaveText(copy.table.aiMissing);
      // The page itself never scrolls sideways; only the table's own region may.
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(overflow).toBeLessThanOrEqual(0);
      await expectAccessible(page, vp.phone);
    });

    test("complete: the guide is checked, nothing is missing; axe passes", async ({ page }) => {
      await standIn(page, COMPLETE);
      await page.goto(`/admin/kontrolltest/${SESSION}/resultater`);
      const status = page.locator("[data-results-status]");
      await expect(status).toHaveAttribute("data-results-status", "checked");
      await expect(status).toHaveText(copy.checked);
      await expect(page.getByRole("main")).not.toContainText(copy.preliminary);
      await expect(page.locator('[data-measure="offset"]')).toContainText("−0,25 trinn");
      await expect(page.locator("table[data-side-by-side] [data-row]")).toHaveCount(4);
      await expectAccessible(page, vp.phone);
    });
  });
}

test("a named Admin who still scores sees no AI step and no measures", async ({ page }) => {
  await standIn(page, {
    ...PRELIMINARY,
    withheld: true,
    measures: null,
    rows: PRELIMINARY.rows.map((row) => ({ ...row, ai: null })),
  });
  await page.goto(`/admin/kontrolltest/${SESSION}/resultater`);
  await expect(page.locator("[data-results-withheld]")).toHaveText(copy.withheld);
  await expect(page.locator("[data-measure]")).toHaveCount(0);
  await expect(page.locator("table[data-side-by-side] [data-ai]").first()).toHaveText(copy.table.hidden);
});

test("«Sensorer» and the Kontrolltest list lead to «Resultater»", async ({ page }) => {
  await standIn(page, COMPLETE);
  await page.route(`**/api/admin/control-tests/${SESSION}/scorers`, (route) =>
    route.fulfill({ status: 200, json: { test: TEST, answers: 4, scorers: [] } }),
  );
  await page.goto(`/admin/kontrolltest/${SESSION}`);
  await page.getByRole("link", { name: copy.title, exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/admin/kontrolltest/${SESSION}/resultater$`, "u"));
  await expect(page.locator("[data-results-status]")).toHaveText(copy.checked);
});
