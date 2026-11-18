import { expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { answerTo, demoContext, loginByApi, untilHydrated } from "./support/auth";
import { expectAccessible, freshLecturer, VIEWPORTS } from "./support/classes";

/** The Lærerhjem and «Lag Klasse» (Story 4.1, FR-5, FR-6, UX-DR11, UX-DR56, NFR-6), on the local
 * stack. Each test makes a fresh Lecturer from an Invitation, so the demo Lecturer's Classes stay
 * as the seed left them; the seeded Institution «Demohøgskolen» is the one chosen. */
const home = nb.classes.home;
const create = nb.classes.create;
const errors = nb.classes.errors;
const DEMO_INSTITUTION = "Demohøgskolen";

const nameField = (page: Page) => page.getByLabel(create.name, { exact: true });
const institutionField = (page: Page) => page.getByLabel(create.institution, { exact: true });
const codeField = (page: Page) => page.getByLabel(create.courseCode, { exact: true });
const saveButton = (page: Page) => page.getByRole("button", { name: create.submit });

for (const vp of VIEWPORTS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("a new Lecturer goes from the empty Lærerhjem through «Lag Klasse» to the Class and back", async ({
      page,
      browser,
    }) => {
      const lecturer = await freshLecturer(page, browser, vp.text200);
      await lecturer.goto("/");
      await expect(lecturer).toHaveURL(/\/laererhjem$/);
      await expect(lecturer.getByText(home.empty)).toBeVisible();
      // «Ny Klasse» is the only action on the empty Lærerhjem.
      await expect(lecturer.locator("main a, main button")).toHaveCount(1);
      await expect(lecturer.getByRole("link", { name: home.newClass })).toBeVisible();
      await expect(lecturer.getByRole("heading", { name: home.title })).toHaveCount(0);
      await expectAccessible(lecturer, vp.phone);

      await lecturer.getByRole("link", { name: home.newClass }).click();
      await expect(lecturer).toHaveURL(/\/klasser\/ny$/);
      await expect(lecturer.getByRole("heading", { level: 1, name: create.title })).toBeVisible();
      await untilHydrated(lecturer);
      await expectAccessible(lecturer, vp.phone);
      await expect(lecturer.locator("main button.bg-ink")).toHaveCount(1);

      // Nothing filled in: both required fields are refused, focus goes to the first.
      await saveButton(lecturer).click();
      await expect(lecturer.getByText(errors.name_empty)).toBeVisible();
      await expect(lecturer.getByText(errors.institution_missing)).toBeVisible();
      await expect(nameField(lecturer)).toHaveAttribute("aria-invalid", "true");
      await expect(institutionField(lecturer)).toHaveAttribute("aria-invalid", "true");
      await expect(nameField(lecturer)).toBeFocused();
      await expect(lecturer).toHaveURL(/\/klasser\/ny$/);
      await expectAccessible(lecturer, vp.phone);

      // Each reason goes as its field is put right.
      const name = `class-of-${Date.now() % 100000}`;
      await nameField(lecturer).fill(name);
      await expect(lecturer.getByText(errors.name_empty)).toHaveCount(0);
      await expect(lecturer.getByText(errors.institution_missing)).toBeVisible();
      await institutionField(lecturer).selectOption({ label: DEMO_INSTITUTION });
      await expect(lecturer.getByText(errors.institution_missing)).toHaveCount(0);
      await codeField(lecturer).fill(" IBE160 ");

      const created = answerTo(lecturer, "/api/classes");
      await saveButton(lecturer).click();
      expect((await created).status()).toBe(201);
      await expect(lecturer).toHaveURL(/\/klasser\/[0-9a-f-]{36}$/);
      await expect(lecturer.getByRole("heading", { level: 1, name })).toBeVisible();
      await expect(lecturer.getByText(nb.classes.page.facts("IBE160", DEMO_INSTITUTION))).toBeVisible();
      await expectAccessible(lecturer, vp.phone);

      // The Lærerhjem now lists it, keeps «Ny Klasse» and has the places for what is waiting.
      await lecturer.getByRole("link", { name: nb.homes.lecturerHome }).click();
      await expect(lecturer).toHaveURL(/\/laererhjem$/);
      const list = lecturer.getByRole("region", { name: home.title });
      await expect(list.getByRole("link", { name: home.label(name, "IBE160") })).toBeVisible();
      await expect(lecturer.getByRole("link", { name: home.newClass })).toBeVisible();
      await expect(lecturer.getByText(home.waiting, { exact: true })).toBeVisible();
      await expect(lecturer.getByText(home.deadline, { exact: true })).toBeVisible();
      await expectAccessible(lecturer, vp.phone);
      await lecturer.context().close();
    });
  });
}

test.describe("refusals", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("another Lecturer's Class, an unknown one and a bad address are the same permission-denied page", async ({
    page,
    browser,
  }) => {
    const demo = await demoContext(browser, "lecturer");
    const listed = await demo.request.get("/api/classes");
    expect(listed.status()).toBe(200);
    const seeded = ((await listed.json()).items as { id: string; name: string }[]).find(
      (item) => item.name === "class-of-1994",
    )!;
    expect(seeded).toBeDefined();
    await demo.close();

    const lecturer = await freshLecturer(page, browser);
    for (const address of [
      `/klasser/${seeded.id}`,
      "/klasser/00000000-0000-7000-8000-000000000000",
      "/klasser/ikke-en-klasse",
      "/klasser/institutions",
    ]) {
      await lecturer.goto(address);
      await expect(lecturer.getByRole("heading", { level: 1, name: nb.access.denied })).toBeVisible();
      await expect(lecturer.getByRole("link", { name: nb.navigation.toLecturerHome })).toBeVisible();
      await expect(lecturer.getByText(seeded.name)).toHaveCount(0);
    }
    await lecturer.context().close();
  });

  test("the demo Lecturer's seeded Class stands on the Lærerhjem and opens", async ({ page }) => {
    await loginByApi(page, "lecturer");
    await page.goto("/laererhjem");
    const link = page.getByRole("region", { name: home.title }).getByRole("link", { name: home.label("class-of-1994", "IBE160") });
    await expect(link.first()).toBeVisible();
    await link.first().click();
    await expect(page.getByRole("heading", { level: 1, name: "class-of-1994" })).toBeVisible();
  });

  test("a Student never sees «Lag Klasse»", async ({ page }) => {
    await loginByApi(page, "student");
    await page.goto("/klasser/ny");
    await expect(page.getByRole("heading", { level: 1, name: nb.access.denied })).toBeVisible();
    await expect(page.locator("main form")).toHaveCount(0);
  });

  test("an Institution refused by the api shows its reason beside the field, not the failure line", async ({
    page,
  }) => {
    await page.route("**/api/classes", (route) =>
      route.request().method() === "POST"
        ? route.fulfill({
            status: 422,
            json: { error: { code: "invalid_request", message: "", fields: { institution_id: "institution_unknown" } } },
          })
        : route.fallback(),
    );
    await loginByApi(page, "lecturer");
    await page.goto("/klasser/ny");
    await untilHydrated(page);
    await nameField(page).fill("Borte");
    await institutionField(page).selectOption({ label: DEMO_INSTITUTION });
    await saveButton(page).click();
    await expect(page.getByText(errors.institution_unknown)).toBeVisible();
    await expect(institutionField(page)).toHaveAttribute("aria-invalid", "true");
    await expect(institutionField(page)).toBeFocused();
    await expect(page.getByText(create.failed)).toHaveCount(0);
    await expect(nameField(page)).not.toHaveAttribute("aria-invalid", "true");
  });

  test("a failed save says so under the form and keeps what was typed", async ({ page }) => {
    await page.route("**/api/classes", (route) =>
      route.request().method() === "POST"
        ? route.fulfill({ status: 500, json: { error: { code: "unknown_error", message: "", fields: {} } } })
        : route.fallback(),
    );
    await loginByApi(page, "lecturer");
    await page.goto("/klasser/ny");
    await untilHydrated(page);
    await nameField(page).fill("Ikke lagret");
    await institutionField(page).selectOption({ label: DEMO_INSTITUTION });
    await saveButton(page).click();
    await expect(page.getByRole("alert").filter({ hasText: create.failed })).toBeVisible();
    await expect(nameField(page)).toHaveValue("Ikke lagret");
    // The line goes as soon as the form changes.
    await nameField(page).fill("Ikke lagret 2");
    await expect(page.getByText(create.failed)).toHaveCount(0);
  });
});
