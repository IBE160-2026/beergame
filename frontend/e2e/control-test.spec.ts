import { expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { answerTo, loginByApi } from "./support/auth";
import { expectAccessible } from "./support/classes";

/** The Control test set up in the operator's own Institution (Story 12.7, FR-82, AD-27, UX-DR57),
 * on the local stack: the operator mark on «Institusjoner», Admin-område → «Kontrolltest» with
 * «Teller aldri med i en Klasseøkt.», the create form and the list with the pinned Scoring guide
 * version and model config, and the Control test's Class and Klasseøkt opened by the Admin as
 * their owner. The mark is one per database, so the tests run one after another; each marks an
 * Institution of its own first. The api's rules (one mark, the refusals, the pins, the exclusion
 * from every list) are pinned by `backend/tests/sessions/test_control_test.py`. */
const copy = nb.admin.controlTests;
const institutions = nb.admin.institutions;

test.describe.configure({ mode: "serial" });

const VIEWPORTS = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
];

const tag = () => `${Date.now()}${Math.floor(Math.random() * 1e6)}`;

async function markFresh(page: Page): Promise<string> {
  const name = `Operatøren ${tag()}`;
  await page.goto("/admin/institusjoner");
  await page.getByLabel(institutions.create.name, { exact: true }).fill(name);
  await page.getByRole("button", { name: institutions.create.submit }).click();
  await expect(page.getByRole("status").filter({ hasText: institutions.create.created(name) })).toBeVisible();
  const row = page.getByRole("region", { name: institutions.list.title }).locator("tbody tr").filter({ hasText: name });
  await row.getByRole("button", { name: institutions.operator.mark(name) }).click();
  await expect(row.getByRole("status")).toHaveText(institutions.operator.marked(name));
  await expect(row.getByText(institutions.operator.label, { exact: true })).toBeVisible();
  return name;
}

for (const vp of VIEWPORTS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("the Admin marks the operator's Institution and sets up a Control test", async ({ page }) => {
      await loginByApi(page, "admin");
      const operator = await markFresh(page);
      await expectAccessible(page, vp.phone);

      await page.goto("/admin");
      await page.getByRole("link", { name: nb.admin.sections.controlTests }).click();
      await expect(page).toHaveURL(/\/admin\/kontrolltest$/);
      await expect(page.getByRole("heading", { level: 1, name: copy.title })).toBeVisible();
      await expect(page.getByText(copy.never, { exact: true })).toBeVisible();
      await expect(page.getByText(copy.operator(operator), { exact: true })).toBeVisible();
      await expectAccessible(page, vp.phone);

      // An empty name is refused beside the field, and nothing is sent.
      await page.getByRole("button", { name: copy.create.submit }).click();
      await expect(page.getByText(copy.create.errors.name_empty)).toBeVisible();

      const name = `Kontrolltest ${tag()}`;
      await page.getByLabel(copy.create.name, { exact: true }).fill(name);
      const guide = page.getByRole("group", { name: copy.create.guide });
      const config = page.getByRole("group", { name: copy.create.config });
      await expect(guide.getByRole("radio").first()).toBeChecked();
      await expect(config.getByRole("radio").first()).toBeChecked();
      const guideLabel = (await guide.locator("label").first().innerText()).trim();
      await expect(page.getByText(copy.create.pinned)).toBeVisible();
      const created = answerTo(page, "/api/admin/control-tests");
      await page.getByRole("button", { name: copy.create.submit }).click();
      expect((await created).status()).toBe(201);
      await expect(page.getByRole("status").filter({ hasText: copy.create.created(name) })).toBeFocused();
      const item = page.getByRole("listitem").filter({ has: page.getByRole("heading", { name }) });
      await expect(item).toContainText(copy.list.guide);
      await expect(item).toContainText(guideLabel);
      await expect(item).toContainText(copy.list.config);
      await expect(item).toContainText(operator);
      await expectAccessible(page, vp.phone);

      // Its Class: the ordinary page, for the Admin as its owner, with no second Class session
      // and no other staff.
      await item.getByRole("link", { name: copy.list.openClass(name) }).click();
      await expect(page.getByRole("heading", { level: 1, name })).toBeVisible();
      await expect(page.getByText(nb.classes.page.controlTest)).toBeVisible();
      await expect(page.getByRole("link", { name: copy.title })).toBeVisible();
      await expect(page.getByRole("link", { name: nb.classes.page.staff })).toHaveCount(0);
      await expect(page.getByRole("button", { name: nb.sessions.list.create })).toHaveCount(0);
      await expect(page.getByRole("button", { name: nb.sessions.list.rerun.open })).toHaveCount(0);
      await expect(page.getByRole("heading", { name: nb.classes.roster.title })).toBeVisible();
      await expectAccessible(page, vp.phone);

      // Its Klasseøkt: «Sensorveiledning» is read-only, pinned when the Control test was made.
      await page.goto("/admin/kontrolltest");
      await page
        .getByRole("listitem")
        .filter({ has: page.getByRole("heading", { name }) })
        .getByRole("link", { name: copy.list.openSession(name) })
        .click();
      await expect(page.getByText(nb.classes.page.controlTest)).toBeVisible();
      await expect(page.locator("[data-scoring-guide]").getByText(nb.tests.scoringGuide.controlTest)).toBeVisible();
      if (!vp.phone) await expectAccessible(page, vp.phone);
    });

    test("with no operator Institution the page says what to do first", async ({ page }) => {
      await loginByApi(page, "admin");
      await page.route("**/api/admin/control-tests", async (route) => {
        const response = await route.fetch();
        const body = await response.json();
        await route.fulfill({ response, json: { ...body, operator_institution: null } });
      });
      try {
        await page.goto("/admin/kontrolltest");
        await expect(page.getByText(copy.noOperator)).toBeVisible();
        await expect(page.getByRole("button", { name: copy.create.submit })).toHaveCount(0);
        await expect(page.getByRole("link", { name: copy.toInstitutions })).toHaveAttribute("href", "/admin/institusjoner");
        await expectAccessible(page, vp.phone);
      } finally {
        await page.unrouteAll({ behavior: "ignoreErrors" });
      }
    });
  });
}
