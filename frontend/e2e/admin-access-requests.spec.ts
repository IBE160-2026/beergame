import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { loginByApi } from "./support/auth";

/** The open requests for lecturer access on «Brukere og roller» (Story 3.13, FR-1, FR-3), on the
 * local stack. Each test files its own request with a fresh name and address and answers it, so
 * runs never meet and the shared list ends as it began. */
const requests = nb.admin.users.requests;
const invite = nb.admin.users.invite;
const audit = nb.admin.audit;
const WCAG_21_AA = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

async function fileRequest(page: Page, tag: string) {
  const stamp = `${Date.now()}-${Math.floor(Math.random() * 1e6)}`;
  const body = { name: `Lærer ${tag} ${stamp}`, email: `foresporsel-${tag}-${stamp}@example.com`, institution: "USN" };
  const response = await page.request.post("/api/auth/access-request", {
    data: body,
    headers: { "X-Requested-With": "olspillet" },
  });
  expect(response.status()).toBe(202);
  return body;
}

function rowOf(page: Page, name: string) {
  return page.getByRole("row").filter({ hasText: name });
}

for (const vp of [
  { name: "320 px", width: 320, height: 640 },
  { name: "1440 px", width: 1440, height: 900 },
]) {
  test(`the Admin invites from a request, prefilled as Faglærer (${vp.name})`, async ({ page }) => {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    const filed = await fileRequest(page, "inviter");
    await loginByApi(page, "admin");
    await page.goto("/admin/brukere");
    const row = rowOf(page, filed.name);
    await expect(row).toContainText(filed.email);
    await expect(row).toContainText("USN");
    const results = await new AxeBuilder({ page }).withTags(WCAG_21_AA).analyze();
    expect(results.violations.map((v) => v.id)).toEqual([]);
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth),
    ).toBe(false);

    await row.getByRole("button", { name: requests.invite(filed.name) }).click();
    const email = page.getByLabel(invite.email, { exact: true });
    await expect(email).toBeFocused();
    await expect(email).toHaveValue(filed.email);
    await expect(page.getByRole("radio", { name: invite.roles.lecturer })).toBeChecked();
    await expect(page.getByText(invite.fromRequest(filed.name))).toBeVisible();

    await page.getByRole("button", { name: invite.submit }).click();
    await expect(page.getByText(invite.sent(filed.email, invite.roles.lecturer, 14))).toBeFocused();
    await expect(rowOf(page, filed.name)).toHaveCount(0);
    await expect(page.getByText(invite.fromRequest(filed.name))).toHaveCount(0);
    if (vp.width < 1000) return;

    // The one audit row names both the Invitation and the request.
    await page.goto("/admin/revisjonslogg");
    const event = page.getByRole("row").filter({ hasText: `Forespørsel fra ${filed.name}` });
    await expect(event).toContainText(audit.actions["access_request.invited"]);
    await expect(event).toContainText(`Invitasjon til ${filed.email}`);
  });
}

test("the Admin dismisses a request, and the dismissal stands in the audit log", async ({ page }) => {
  const filed = await fileRequest(page, "avvis");
  await loginByApi(page, "admin");
  await page.goto("/admin/brukere");
  await rowOf(page, filed.name).getByRole("button", { name: requests.dismiss(filed.name) }).click();
  await expect(page.getByRole("status").filter({ hasText: requests.dismissed(filed.name) })).toBeVisible();
  await expect(rowOf(page, filed.name)).toHaveCount(0);

  await page.goto("/admin/revisjonslogg");
  const event = page.getByRole("row").filter({ hasText: `Forespørsel fra ${filed.name}` });
  await expect(event).toContainText(audit.actions["access_request.dismissed"]);
  await expect(event).toContainText("Demo Admin");
});
