import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { loginByApi } from "./support/auth";
import { expectAccessible, test } from "./support/classes";

/** Blind scoring of a Control test (Story 12.9, FR-82, AD-27, NFR-6, UX-DR9, UX-DR12, UX-DR57,
 * UX-DR78): a named scorer with no Admin role reaches «Sensur av Kontrolltest» from their own
 * Hjem, reads the answers as «Svar N» with «Vurdert»/«Ikke vurdert» in text and no name, opens one
 * (question, answer, the Scoring guide and its scale, no AI step), picks a step on the Valgknapper
 * by keyboard and presses «Lagre vurdering» under the line that it cannot be changed (no dialog);
 * then their score and the AI's step show. A second «Lagre vurdering» from a stale page is refused
 * in words. At 320, 360 and 1440 px with axe. The Admin's «Sensorer» page names a scorer. These use
 * stand-ins with the api's shapes; access, blindness, the single write and the audit rows are
 * `backend/tests/assessment/test_human_scores.py`. */
const SESSION = "01a20500-0000-7000-8000-000000000001";
const ANSWER = "5f0c2a9e41d7b3c8a6e1f2d4b7c9a0e3";
const OTHER = "9b1e7d3a2c4f6e8d0a1b3c5d7e9f1a2b";
const copy = nb.scoring;

const VIEWPORTS = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
];

const TEST = { id: SESSION, name: "Kontrolltest høst", test_deadline: "2026-11-20T22:59:00Z", open: true };
const LIST = {
  test: TEST,
  can_score: true,
  entries: [
    { ref: ANSWER, number: 1, type: "long", question: "Utkast: Forklar hvorfor ordrene svinger.", scored: false },
    { ref: OTHER, number: 2, type: "adapted", question: "Utkast: Hvorfor bestilte du 16 i Uke 7?", scored: true },
  ],
};
const SCALE = ["Utkast: mangler", "Utkast: svakt", "Utkast: delvis", "Utkast: godt", "Utkast: svært godt"].map(
  (label, step) => ({ step, label }),
);
const ITEM = {
  test: TEST,
  ref: ANSWER,
  number: 1,
  type: "long",
  question: "Utkast: Forklar hvorfor ordrene svinger.",
  answer: "Hvert ledd bestiller på det det ser, og forsinkelsen gjør at varene kommer for sent.",
  facts: [],
  guide_title: "Utkast: langsvar om forsinkelse",
  guide_text: "Utkast: se etter at svaret forklarer forsinkelsen.",
  criteria: [
    { code: "F1", weight: 50, text: "Utkast: nevner forsinkelsen" },
    { code: "F2", weight: 50, text: "Utkast: forklarer følgen" },
  ],
  scale: SCALE,
  can_score: true,
  own_score: null,
  ai: null,
};
const SCORED = { ...ITEM, own_score: { score: 3, submitted_at: "2026-11-21T08:00:00Z" }, ai: { step: 2, label: "Utkast: delvis" } };
const REFUSED = { error: { code: "human_score_exists", message: "x", fields: {} } };

/** The scorer's pages with the api's answers stood in; `post` answers «Lagre vurdering». */
async function standIn(page: Page, post?: { status: number; json: unknown }) {
  await loginByApi(page, "student");
  let posted = false;
  await page.route("**/api/scoring", (route) => route.fulfill({ status: 200, json: { tests: [TEST] } }));
  await page.route(`**/api/scoring/${SESSION}`, (route) =>
    route.fulfill({ status: 200, json: posted ? { ...LIST, entries: [{ ...LIST.entries[0], scored: true }, LIST.entries[1]] } : LIST }),
  );
  await page.route(`**/api/scoring/${SESSION}/answers/${ANSWER}`, (route) => {
    if (route.request().method() === "POST") {
      posted = true;
      return route.fulfill(post ?? { status: 201, json: SCORED });
    }
    return route.fulfill({ status: 200, json: posted ? SCORED : ITEM });
  });
}

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

for (const vp of VIEWPORTS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("the list: «Svar N», type and question, scored or not in text, no name; axe passes", async ({ page }) => {
      await standIn(page);
      await page.goto(`/sensur/${SESSION}`);
      await expect(page.getByRole("heading", { level: 1 })).toHaveText(TEST.name);
      const rows = page.locator("[data-answer]");
      await expect(rows).toHaveCount(2);
      await expect(rows.nth(0).getByRole("link")).toHaveText("Svar 1");
      await expect(rows.nth(0)).toContainText(`${copy.list.types.long}: ${LIST.entries[0].question}`);
      await expect(rows.nth(0).locator("[data-scored]")).toHaveText(copy.list.notScored);
      await expect(rows.nth(1).locator("[data-scored]")).toHaveText(copy.list.scored);
      await expect(page.locator("[data-progress]")).toHaveText("1 av 2 vurdert");
      await expectAccessible(page, vp.phone);
    });

    test("an answer: the question, the text, the guide and its scale, no AI step; scored by keyboard; axe passes", async ({ page }) => {
      await standIn(page);
      await page.goto(`/sensur/${SESSION}/${ANSWER}`);
      await expect(page.getByRole("heading", { level: 1 })).toHaveText("Svar 1");
      const main = page.getByRole("main");
      await expect(main.locator("[data-answer-text]")).toHaveText(ITEM.answer);
      await expect(main).toContainText(ITEM.guide_title);
      await expect(main).toContainText("F1 (vekt 50): Utkast: nevner forsinkelsen");
      await expect(main.locator("[data-ai-score]")).toHaveText(copy.item.aiHidden);
      await expect(main).not.toContainText("KI-vurderingen:");
      // The consequence stands above the primary button, which says what it does.
      const consequence = await main.locator("[data-consequence]").boundingBox();
      const button = main.getByRole("button", { name: copy.item.submit });
      expect((await button.boundingBox())!.y).toBeGreaterThan(consequence!.y);
      await expectAccessible(page, vp.phone);

      // The scale is Valgknapper: the arrow keys move the choice.
      await page.getByRole("radio", { name: `0: ${SCALE[0].label}` }).focus();
      await page.keyboard.press("Space");
      for (let i = 0; i < 3; i++) await page.keyboard.press("ArrowRight");
      await expect(page.getByRole("radio", { name: `3: ${SCALE[3].label}` })).toBeChecked();
      await button.click();
      await expect(page.getByRole("dialog")).toHaveCount(0);
      const own = main.locator("[data-own-score]");
      await expect(own).toContainText("Din vurdering: 3 av 4, Utkast: godt.");
      await expect(own.locator("[data-ai-score]")).toHaveText("KI-vurderingen: 2 av 4, Utkast: delvis.");
      await expect(main.getByRole("button", { name: copy.item.submit })).toHaveCount(0);
      await expectAccessible(page, vp.phone);
    });

    test("a second «Lagre vurdering» from a stale page is refused in words; axe passes", async ({ page }) => {
      await standIn(page, { status: 409, json: REFUSED });
      await page.goto(`/sensur/${SESSION}/${ANSWER}`);
      await page.getByRole("radio", { name: `1: ${SCALE[1].label}` }).check();
      await page.getByRole("button", { name: copy.item.submit }).click();
      const main = page.getByRole("main");
      await expect(main.getByRole("alert")).toHaveText(copy.item.errors.human_score_exists);
      // The page reads the answer again: the score saved first stands, with the AI's step.
      await expect(main.locator("[data-own-score]")).toContainText("Din vurdering: 3 av 4");
      await expectAccessible(page, vp.phone);
    });
  });
}

test("Hjem carries «Sensur av Kontrolltest» for a named scorer with no Admin role", async ({ page }) => {
  await standIn(page);
  await page.goto("/hjem");
  const link = page.getByRole("link", { name: copy.homeLink });
  await expect(link).toBeVisible();
  await link.click();
  await expect(page).toHaveURL(/\/sensur$/u);
  await page.getByRole("link", { name: copy.tests.open(TEST.name) }).click();
  await expect(page).toHaveURL(new RegExp(`/sensur/${SESSION}$`, "u"));
  await expect(page.locator("[data-answer]")).toHaveCount(2);
});

test("a User who scores nothing has no Lenke on their home", async ({ page }) => {
  await loginByApi(page, "student");
  await page.route("**/api/scoring", (route) => route.fulfill({ status: 200, json: { tests: [] } }));
  await page.goto("/hjem");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(nb.homes.home);
  await expect(page.getByRole("link", { name: copy.homeLink })).toHaveCount(0);
});

for (const vp of VIEWPORTS.filter((each) => each.width !== 360)) {
  test(`the Admin names a scorer on «Sensorer», ${vp.name}; axe passes`, async ({ page }) => {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    await loginByApi(page, "admin");
    const empty = { test: TEST, answers: 12, scorers: [] };
    const named = {
      ...empty,
      scorers: [{ user_id: "01a20500-0000-7000-8000-0000000000b1", name: "Sara Sensor", email: "sensor@example.com", named_at: "2026-11-21T08:00:00Z", scored: 3 }],
    };
    await page.route(`**/api/admin/control-tests/${SESSION}/scorers`, (route) =>
      route.request().method() === "POST"
        ? route.fulfill(
            (route.request().postDataJSON() as { email: string }).email === "ts@example.com"
              ? { status: 422, json: { error: { code: "invalid_request", message: "x", fields: { email: "test_student" } } } }
              : { status: 200, json: named },
          )
        : route.fulfill({ status: 200, json: empty }),
    );
    await page.goto(`/admin/kontrolltest/${SESSION}`);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(`${copy.scorers.title}: ${TEST.name}`);
    await expect(page.getByRole("main")).toContainText(copy.scorers.empty);
    const field = page.getByLabel(copy.scorers.email);
    await field.fill("ts@example.com");
    await page.getByRole("button", { name: copy.scorers.add }).click();
    await expect(page.getByRole("main")).toContainText(copy.scorers.errors.test_student);
    await field.fill("sensor@example.com");
    await page.getByRole("button", { name: copy.scorers.add }).click();
    await expect(page.locator("form [role=status]")).toHaveText(copy.scorers.added("sensor@example.com"));
    const row = page.locator('[data-scorer="sensor@example.com"]');
    await expect(row).toContainText("Sara Sensor");
    await expect(row).toContainText("3 av 12 vurdert");
    await expect(page.getByRole("link", { name: copy.scorers.readAnswers })).toHaveAttribute("href", `/sensur/${SESSION}`);
    await expectAccessible(page, vp.phone);
  });
}
