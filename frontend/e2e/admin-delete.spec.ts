import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { loginByApi } from "./support/auth";
import { expectAccessible, freshClass, freshLecturerWithAddress, test, VIEWPORTS } from "./support/classes";

/** Deleting a User on the Institution's instruction on «Brukere og roller» (Story 15.2, FR-76,
 * FR-2, UX-DR9, NFR-6), on the local stack. Every User a test deletes is a fresh Lecturer made
 * from an Invitation; demo Users are never pressed. */
const list = nb.admin.users.list;
const remove = list.delete;
const REFERENCE = "Sak 2026/0042";

const usersSection = (page: Page) => page.getByRole("region", { name: list.title, exact: true });

/** The first name `freshLecturerWithAddress` gave the Lecturer of `address`. */
function firstOf(address: string): string {
  return `Lene${address.match(/^klasse-(\d+)@/)![1]}`;
}

async function openRow(page: Page, address: string) {
  await loginByApi(page, "admin");
  await page.goto("/admin/brukere");
  await expect(page.getByRole("heading", { level: 2, name: list.title })).toBeVisible();
  await page.getByLabel(list.search).fill(address);
  await expect(usersSection(page).locator("tbody tr")).toHaveCount(1);
}

for (const vp of VIEWPORTS.filter((v) => !v.text200)) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("the Admin deletes a User with the instruction's reference, in one press", async ({ page, browser }) => {
      const fresh = await freshLecturerWithAddress(page, browser);
      const first = firstOf(fresh.address);
      expect((await fresh.page.request.get("/api/auth/me")).status()).toBe(200);
      await openRow(page, fresh.address);

      const open = page.getByRole("button", { name: remove.open(first), exact: true });
      await expect(open).toHaveAttribute("aria-expanded", "false");
      await open.click();
      await expect(page.getByRole("button", { name: remove.close })).toHaveAttribute("aria-expanded", "true");
      const submit = page.getByRole("button", { name: remove.submit(first) });
      const field = page.getByLabel(remove.reference);

      // No reference: the field says why, and nothing is sent.
      let sent = 0;
      page.on("request", (request) => {
        if (request.url().endsWith("/delete")) sent += 1;
      });
      await submit.click();
      await expect(page.getByText(remove.errors.reference_empty)).toBeVisible();
      await expect(field).toBeFocused();
      expect(sent).toBe(0);

      // A reference that names the User is refused by the api, beside the field.
      await field.fill(`Instruks om ${first}`);
      await submit.click();
      await expect(page.getByText(remove.errors.reference_names_user)).toBeVisible();
      expect(sent).toBe(1);

      await field.fill(REFERENCE);
      await expectAccessible(page, vp.phone);

      // One press deletes: no dialog, the row goes and the line above the list says so.
      const dialogs: string[] = [];
      page.on("dialog", (dialog) => dialogs.push(dialog.message()));
      await submit.click();
      const line = page.getByRole("status").filter({ hasText: remove.deleted(first) });
      await expect(line).toBeFocused();
      await expect(usersSection(page).locator("tbody tr")).toHaveCount(0);
      // The search still names the deleted User, and says it finds no one now.
      await expect(usersSection(page).getByText(list.noMatches)).toBeVisible();
      expect(dialogs).toEqual([]);
      await expectAccessible(page, vp.phone);

      // The User is out at once, and no search finds them again.
      expect((await fresh.page.request.get("/api/auth/me")).status()).toBe(401);
      await page.reload();
      await page.getByLabel(list.search).fill(fresh.address);
      await expect(page.getByText(list.noMatches)).toBeVisible();
    });
  });
}

test("a Lecturer who owns a Class is not deleted, with the revoke's own sentence", async ({ page, browser }) => {
  const fresh = await freshLecturerWithAddress(page, browser);
  const first = firstOf(fresh.address);
  await freshClass(fresh.page);
  await openRow(page, fresh.address);
  await page.getByRole("button", { name: remove.open(first), exact: true }).click();
  await page.getByLabel(remove.reference).fill(REFERENCE);
  await page.getByRole("button", { name: remove.submit(first) }).click();
  await expect(page.getByRole("alert").filter({ hasText: list.blocked(first, 1) })).toBeVisible();
  await expect(usersSection(page).locator("tbody tr")).toHaveCount(1);
  expect((await fresh.page.request.get("/api/auth/me")).status()).toBe(200);
});
