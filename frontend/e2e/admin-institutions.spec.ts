import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { loginByApi } from "./support/auth";

/** «Institusjoner» in the Admin-område (Story 3.11, FR-3, FR-72, NFR-6), on the local stack. The
 * database is shared between runs, so every test makes names of its own; the empty state is
 * answered by the test, not the api. */
const copy = nb.admin.institutions;
const WCAG_21_AA = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

type Viewport = { name: string; width: number; height: number; phone: boolean };

const VIEWPORTS: Viewport[] = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
];

async function expectAccessible(page: Page, phone: boolean) {
  const results = await new AxeBuilder({ page }).withTags(WCAG_21_AA).analyze();
  expect(results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`)).toEqual([]);
  const scrolls = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  expect(scrolls).toBe(false);
  if (!phone) return;
  const small = await page.evaluate(() =>
    [...document.querySelectorAll<HTMLElement>("main a, main button, main input")]
      .filter((el) => el.offsetParent !== null)
      .map((el) => ({ name: el.id || el.textContent?.trim(), ...el.getBoundingClientRect().toJSON() }))
      .filter((b) => b.height < 44 || b.width < 44),
  );
  expect(small).toEqual([]);
}

const tag = () => `${Date.now()}${Math.floor(Math.random() * 1e6)}`;
const listSection = (page: Page) => page.getByRole("region", { name: copy.list.title });
const nameField = (page: Page) => page.getByLabel(copy.create.name, { exact: true });
const createButton = (page: Page) => page.getByRole("button", { name: copy.create.submit });

for (const vp of VIEWPORTS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("the Admin opens «Institusjoner» from the Admin-område, creates one and renames it", async ({ page }) => {
      await loginByApi(page, "admin");
      await page.goto("/admin");
      await page.getByRole("link", { name: nb.admin.sections.institutions }).click();
      await expect(page).toHaveURL(/\/admin\/institusjoner$/);
      await expect(page.getByRole("heading", { level: 1, name: copy.title })).toBeVisible();

      const name = `Høgskolen ${tag()}`;
      const dialogs: string[] = [];
      page.on("dialog", (dialog) => dialogs.push(dialog.message()));
      await nameField(page).fill(`  ${name} `);
      await createButton(page).click();
      const created = page.getByRole("status").filter({ hasText: copy.create.created(name) });
      await expect(created).toBeFocused();
      await expect(nameField(page)).toHaveValue("");
      // The new one stands in the list (on page one: newest first), with its creation date.
      // Other tests create rows at the same time, so it need not be the very first.
      const row = listSection(page).locator("tbody tr").filter({ hasText: name });
      await expect(row.getByText(name, { exact: true })).toBeVisible();
      await expect(row).toContainText(/\d{1,2}\. [a-zæøå]+\.? \d{4}/);
      await expectAccessible(page, vp.phone);
      await expect(page.locator("main button.bg-ink")).toHaveCount(1);

      // The result line goes as soon as the form changes.
      await nameField(page).fill("x");
      await expect(created).toHaveCount(0);

      // The same name in other case: the Tekstfelt's invalid state with its reason, nothing stored.
      await nameField(page).fill(name.toUpperCase());
      await createButton(page).click();
      const taken = page.getByText(copy.errors.institution_name_taken);
      await expect(taken).toBeVisible();
      await expect(nameField(page)).toHaveAttribute("aria-invalid", "true");
      await expect(listSection(page).getByText(name.toUpperCase(), { exact: true })).toHaveCount(0);
      await expectAccessible(page, vp.phone);
      // The reason goes as the name is typed.
      await nameField(page).press("End");
      await nameField(page).pressSequentially(" 2");
      await expect(taken).toHaveCount(0);
      await expect(nameField(page)).not.toHaveAttribute("aria-invalid", "true");

      // An empty name.
      await nameField(page).fill("");
      await createButton(page).click();
      await expect(page.getByText(copy.errors.name_empty)).toBeVisible();
      await expect(nameField(page)).toBeFocused();

      // Rename inline: the field is prefilled, the row says what changed, focus returns.
      await page.getByRole("button", { name: copy.rename.open(name) }).click();
      const field = page.getByLabel(copy.rename.field(name));
      await expect(field).toHaveValue(name);
      await expect(field).toBeFocused();
      await expectAccessible(page, vp.phone);
      const renamed = `${name} Bø`;
      await field.fill(renamed);
      await page.getByRole("button", { name: copy.rename.save }).click();
      await expect(page.getByRole("button", { name: copy.rename.open(renamed) })).toBeFocused();
      await expect(page.getByRole("status").filter({ hasText: copy.rename.renamed(name, renamed) })).toBeVisible();
      await expect(listSection(page).getByText(renamed, { exact: true })).toBeVisible();

      // «Avbryt» closes the form with nothing changed.
      await page.getByRole("button", { name: copy.rename.open(renamed) }).click();
      await page.getByLabel(copy.rename.field(renamed)).fill("Noe annet");
      await page.getByRole("button", { name: copy.rename.cancel }).click();
      await expect(page.getByRole("button", { name: copy.rename.open(renamed) })).toBeFocused();
      await expect(listSection(page).getByText("Noe annet", { exact: true })).toHaveCount(0);
      expect(dialogs).toEqual([]);
    });
  });
}

test.describe("states", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("with no Institution the list says so and the create form is the one action", async ({ page }) => {
    await page.route("**/api/admin/institutions*", (route) =>
      route.request().method() === "GET"
        ? route.fulfill({ json: { items: [], next_cursor: null } })
        : route.fallback(),
    );
    await loginByApi(page, "admin");
    await page.goto("/admin/institusjoner");
    await expect(page.getByText(copy.list.empty)).toBeVisible();
    await expect(listSection(page).getByRole("table")).toHaveCount(0);
    await expect(page.locator("main button")).toHaveCount(1);
    await expect(createButton(page)).toBeVisible();
    await expectAccessible(page, false);
  });

  test("a taken name when renaming shows the reason under the rename field", async ({ page }) => {
    await loginByApi(page, "admin");
    await page.goto("/admin/institusjoner");
    const first = `Alfa ${tag()}`;
    const second = `Beta ${tag()}`;
    for (const name of [first, second]) {
      await nameField(page).fill(name);
      await createButton(page).click();
      await expect(page.getByRole("status").filter({ hasText: copy.create.created(name) })).toBeVisible();
    }
    await page.getByRole("button", { name: copy.rename.open(second) }).click();
    const field = page.getByLabel(copy.rename.field(second));
    await field.fill(first.toLowerCase());
    await page.getByRole("button", { name: copy.rename.save }).click();
    await expect(page.getByText(copy.errors.institution_name_taken)).toBeVisible();
    await expect(field).toHaveAttribute("aria-invalid", "true");
    await expect(field).toBeFocused();
  });

  test("a new action ends the result line of the other part of the page", async ({ page }) => {
    await loginByApi(page, "admin");
    await page.goto("/admin/institusjoner");
    const name = `Gamma ${tag()}`;
    await nameField(page).fill(name);
    await createButton(page).click();
    const created = page.getByRole("status").filter({ hasText: copy.create.created(name) });
    await expect(created).toBeVisible();
    // A rename starts: the create line goes.
    await page.getByRole("button", { name: copy.rename.open(name) }).click();
    await expect(created).toHaveCount(0);
    const renamed = `${name} Bø`;
    await page.getByLabel(copy.rename.field(name)).fill(renamed);
    await page.getByRole("button", { name: copy.rename.save }).click();
    const renamedLine = page.getByRole("status").filter({ hasText: copy.rename.renamed(name, renamed) });
    await expect(renamedLine).toBeVisible();
    // A create starts: the row's line goes.
    const next = `Delta ${tag()}`;
    await nameField(page).fill(next);
    await createButton(page).click();
    await expect(page.getByRole("status").filter({ hasText: copy.create.created(next) })).toBeVisible();
    await expect(renamedLine).toHaveCount(0);
  });

  test("«Vis flere Institusjoner» appends the next page by its cursor", async ({ page }) => {
    const row = (n: number) => ({
      id: `00000000-0000-7000-8000-00000000000${n}`,
      name: `Side ${n}`,
      created_at: "2026-11-18T12:00:00Z",
    });
    const cursors: (string | null)[] = [];
    await page.route("**/api/admin/institutions*", (route) => {
      if (route.request().method() !== "GET") return route.fallback();
      const cursor = new URL(route.request().url()).searchParams.get("cursor");
      cursors.push(cursor);
      return route.fulfill({
        json: cursor ? { items: [row(2)], next_cursor: null } : { items: [row(1)], next_cursor: "neste" },
      });
    });
    await loginByApi(page, "admin");
    await page.goto("/admin/institusjoner");
    const section = listSection(page);
    await expect(section.getByText("Side 1", { exact: true })).toBeVisible();
    await section.getByRole("button", { name: copy.list.more }).click();
    await expect(section.getByText("Side 2", { exact: true })).toBeVisible();
    await expect(section.getByText("Side 1", { exact: true })).toBeVisible();
    await expect(section.getByRole("button", { name: copy.list.more })).toHaveCount(0);
    expect(cursors).toContain("neste");
  });

  test("a Lecturer gets the permission-denied page and no form", async ({ page }) => {
    await loginByApi(page, "lecturer");
    await page.goto("/admin/institusjoner");
    await expect(page.getByRole("heading", { level: 1, name: nb.access.denied })).toBeVisible();
    await expect(createButton(page)).toHaveCount(0);
  });
});
