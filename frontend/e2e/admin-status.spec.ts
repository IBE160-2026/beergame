import AxeBuilder from "@axe-core/playwright";
import { type Browser, type BrowserContext, expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import {
  answerTo,
  DEMO_USERS,
  demoContext,
  latestMail,
  loginByApi,
  nextMail,
  untilFontsLoaded,
  untilHydrated,
} from "./support/auth";

/** Deactivating and reactivating a User, and the Invitation list with its resend, on «Brukere og
 * roller» (Story 3.10, FR-1, FR-3, UX-DR57, UX-DR61, NFR-6), on the local stack with the mail
 * worker. Every User a test deactivates is a fresh account made from an Invitation; demo Users
 * are never deactivated. */
const list = nb.admin.users.list;
const invitations = nb.admin.users.invitations;
const WCAG_21_AA = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];
const CSRF = { "X-Requested-With": "olspillet" };
const PASSWORD = "et-godt-passord";

const VIEWPORTS = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
];

async function expectAccessible(page: Page, phone: boolean) {
  // The reflow and tap-target checks below measure the layout: measure it in the product's font.
  await untilFontsLoaded(page);
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

const usersSection = (page: Page) => page.getByRole("region", { name: list.title, exact: true });
const invitationsSection = (page: Page) => page.getByRole("region", { name: invitations.title, exact: true });

/** The demo Admin's api, in a browser context of its own. */
function adminApi(browser: Browser): Promise<BrowserContext> {
  return demoContext(browser, "admin");
}

/** Send a Lecturer Invitation to a fresh address and return the address and its mailed token. */
async function invite(page: Page, browser: Browser, prefix: string) {
  const tag = `${Date.now()}${Math.floor(Math.random() * 1e6)}`;
  const address = `${prefix}-${tag}@example.com`;
  const admin = await adminApi(browser);
  const before = await latestMail(page, address);
  const sent = await admin.request.post("/api/admin/invitations", {
    data: { email: address, role: "lecturer" },
    headers: CSRF,
  });
  expect(sent.status()).toBe(201);
  await admin.close();
  const mail = await nextMail(page, address, before);
  const token = mail.text.match(/\/invitasjon#([A-Za-z0-9_-]+)/)![1];
  return { address, tag, token, mail };
}

/** A fresh Lecturer, made from an Invitation and logged in, in a browser context of its own. */
async function freshLecturer(page: Page, browser: Browser) {
  const { address, tag, token } = await invite(page, browser, "status");
  const first = `Stine${tag}`;
  const context = await browser.newContext({ baseURL: test.info().project.use.baseURL });
  const accepted = await context.request.post("/api/auth/invitation/accept", {
    data: { token, name: `${first} Testesen`, password: PASSWORD },
    headers: CSRF,
  });
  expect(accepted.status()).toBe(200);
  return { context, address, first };
}

async function openUsers(page: Page) {
  await loginByApi(page, "admin");
  await page.goto("/admin/brukere");
  await expect(page.getByRole("heading", { level: 2, name: list.title })).toBeVisible();
}

for (const vp of VIEWPORTS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("the Admin deactivates a User, who is out at once, and reactivates them", async ({ page, browser }) => {
      const fresh = await freshLecturer(page, browser);
      expect((await fresh.context.request.get("/api/auth/me")).status()).toBe(200);

      await openUsers(page);
      await page.getByLabel(list.search).fill(fresh.address);
      await expect(usersSection(page).locator("tbody tr")).toHaveCount(1);
      const deactivate = page.getByRole("button", { name: list.deactivate(fresh.first) });
      await expect(deactivate).toBeVisible();
      await expectAccessible(page, vp.phone);
      await expect(page.locator("main button.bg-ink")).toHaveCount(1);

      // No dialog: the status changes at once, the pressed button keeps focus and states its new
      // effect, and the row says what changed.
      const dialogs: string[] = [];
      page.on("dialog", (dialog) => dialogs.push(dialog.message()));
      await deactivate.click();
      const reactivate = page.getByRole("button", { name: list.reactivate(fresh.first) });
      await expect(reactivate).toBeFocused();
      await expect(page.getByRole("status").filter({ hasText: list.deactivatedLine(fresh.first) })).toBeVisible();
      await expect(usersSection(page).getByText(list.deactivated, { exact: true })).toBeVisible();
      expect(dialogs).toEqual([]);
      await expectAccessible(page, vp.phone);

      // The live cookie is rejected at once, and the right password names the deactivation.
      expect((await fresh.context.request.get("/api/auth/me")).status()).toBe(401);
      const own = await fresh.context.newPage();
      await own.goto("/logg-inn");
      // A press before hydration reaches the bare form, which posts to the page and loses it.
      await untilHydrated(own);
      await own.getByLabel(nb.auth.login.email).fill(fresh.address);
      await own.getByLabel(nb.auth.login.password).fill(PASSWORD);
      const refused = answerTo(own, "/api/auth/login");
      await own.getByRole("button", { name: nb.auth.login.submit }).click();
      expect((await refused).status()).toBe(403);
      await expect(own.getByText(nb.auth.login.deactivated)).toBeVisible();

      await reactivate.click();
      await expect(deactivate).toBeFocused();
      await expect(page.getByRole("status").filter({ hasText: list.reactivatedLine(fresh.first) })).toBeVisible();
      const accepted = answerTo(own, "/api/auth/login");
      await own.getByRole("button", { name: nb.auth.login.submit }).click();
      expect((await accepted).status()).toBe(200);
      await expect(own).toHaveURL(/\/laererhjem$/);
      await fresh.context.close();
    });

    test("the Invitation list shows each Invitation and resends an open one with a new link", async ({
      page,
      browser,
    }) => {
      const { address, token: oldToken } = await invite(page, browser, "liste");
      await openUsers(page);
      const section = invitationsSection(page);
      const resend = section.getByRole("button", { name: invitations.resend(address) });
      await expect(resend).toBeVisible();
      await expect(section.getByText(invitations.status.open, { exact: true }).first()).toBeVisible();
      await expectAccessible(page, vp.phone);

      const before = await latestMail(page, address);
      await resend.click();
      await expect(resend).toBeFocused();
      await expect(section.getByRole("status").filter({ hasText: invitations.resent(address, 14) })).toBeVisible();
      const mail = await nextMail(page, address, before);
      const newToken = mail.text.match(/\/invitasjon#([A-Za-z0-9_-]+)/)![1];
      expect(newToken).not.toBe(oldToken);
      const check = (token: string) =>
        page.request.post("/api/auth/invitation/check", { data: { token }, headers: CSRF });
      expect((await check(oldToken)).status()).toBe(410);
      expect((await check(newToken)).status()).toBe(200);

      // The list read again: the row now holds the new Invitation, so a second resend works.
      const again = await latestMail(page, address);
      await resend.click();
      const third = (await nextMail(page, address, again)).text.match(/\/invitasjon#([A-Za-z0-9_-]+)/)![1];
      expect((await check(newToken)).status()).toBe(410);
      expect((await check(third)).status()).toBe(200);
      await expect(section.getByRole("alert")).toHaveCount(0);
    });
  });
}

test.describe("Invitation states", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("an accepted Invitation offers no resend, and a renewal request says so", async ({ page, browser }) => {
    const fresh = await freshLecturer(page, browser);
    await fresh.context.close();
    await page.route("**/api/admin/invitations", (route) =>
      route.request().method() === "GET"
        ? route.fulfill({
            json: {
              items: [
                {
                  id: "00000000-0000-7000-8000-000000000001",
                  email: "utlopt@example.com",
                  role: "admin",
                  status: "expired",
                  expires_at: "2026-11-02T11:00:00Z",
                  accepted_at: null,
                  account_deactivated: false,
                  renewal_requested: true,
                },
                {
                  id: "00000000-0000-7000-8000-000000000002",
                  email: "deaktivert@example.com",
                  role: "lecturer",
                  status: "expired",
                  expires_at: "2026-11-03T11:00:00Z",
                  accepted_at: null,
                  account_deactivated: true,
                  renewal_requested: false,
                },
              ],
              next_cursor: null,
            },
          })
        : route.continue(),
    );
    await openUsers(page);
    const section = invitationsSection(page);
    const expired = section.getByRole("row").filter({ hasText: "utlopt@example.com" });
    await expect(expired.getByText(invitations.status.expired, { exact: true })).toBeVisible();
    await expect(section.getByText(invitations.renewalRequested)).toBeVisible();
    await expect(section.getByText("2. nov. 2026")).toBeVisible();
    await expect(section.getByRole("button", { name: invitations.resend("utlopt@example.com") })).toBeVisible();
    // The address of a deactivated User: the api would refuse a resend, so the row offers none.
    const deactivated = section.getByRole("row").filter({ hasText: "deaktivert@example.com" });
    await expect(deactivated.getByText(invitations.accountDeactivated)).toBeVisible();
    await expect(deactivated.getByRole("button")).toHaveCount(0);

    // The real list: the fresh account's Invitation is accepted, has no resend button, and states
    // when it was accepted instead of an expiry.
    await page.unroute("**/api/admin/invitations");
    await page.reload();
    const row = invitationsSection(page).getByRole("row").filter({ hasText: fresh.address });
    await expect(row.getByText(invitations.status.accepted, { exact: true })).toBeVisible();
    await expect(row.getByText(/^Akseptert \d{1,2}\. \S+ \d{4}$/)).toBeVisible();
    await expect(row.getByRole("button")).toHaveCount(0);
  });

  test("the resend buttons have one width and never wrap at 1280 px", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    const item = (n: number, email: string) => ({
      id: `00000000-0000-7000-8000-00000000001${n}`,
      email,
      role: "lecturer",
      status: n === 1 ? "open" : "expired",
      expires_at: "2026-12-02T11:00:00Z",
      accepted_at: null,
      account_deactivated: false,
      renewal_requested: n === 2,
    });
    const emails = ["kari.nordmann@example.com", "ola@example.com", "ingrid.lie-johannessen.lang.adresse@example.com"];
    await page.route("**/api/admin/invitations", (route) =>
      route.request().method() === "GET"
        ? route.fulfill({ json: { items: emails.map((e, i) => item(i + 1, e)), next_cursor: null } })
        : route.continue(),
    );
    await openUsers(page);
    const buttons = invitationsSection(page).getByRole("button", { name: /^Send ny invitasjon til / });
    await expect(buttons).toHaveCount(3);
    // Measured in the product's font: the fallback face sets the label at another width.
    await untilFontsLoaded(page);
    const boxes = await buttons.evaluateAll((els) =>
      els.map((el) => {
        const box = el.getBoundingClientRect();
        // One line of text keeps the button at its minimum height; a wrapped label grows it.
        return { width: Math.round(box.width), wraps: box.height > parseFloat(getComputedStyle(el).minHeight) + 1 };
      }),
    );
    expect(new Set(boxes.map((b) => b.width)).size).toBe(1);
    expect(boxes.map((b) => b.wraps)).toEqual([false, false, false]);
  });

  test("the invite form refuses the address of a deactivated User beside the field", async ({ page, browser }) => {
    const fresh = await freshLecturer(page, browser);
    await fresh.context.close();
    const admin = await adminApi(browser);
    const found = await admin.request.get(`/api/admin/users?q=${encodeURIComponent(fresh.address)}`);
    const [user] = (await found.json()).items;
    expect((await admin.request.post(`/api/admin/users/${user.id}/deactivate`, { headers: CSRF })).status()).toBe(200);
    await admin.close();

    await openUsers(page);
    const field = page.getByLabel(nb.admin.users.invite.email, { exact: true });
    await field.fill(fresh.address);
    await page.getByRole("button", { name: nb.admin.users.invite.submit }).click();
    await expect(field).toHaveAttribute("aria-invalid", "true");
    await expect(field).toBeFocused();
    await expect(page.getByText(nb.admin.users.invite.errors.accountDeactivated)).toBeVisible();
    await expect(page.getByText(nb.admin.users.invite.failed)).toHaveCount(0);
  });

  test("an Invitation sent from the form appears in the list at once", async ({ page }) => {
    const address = `skjema-${Date.now()}${Math.floor(Math.random() * 1e6)}@example.com`;
    await openUsers(page);
    await expect(invitationsSection(page).getByRole("table")).toBeVisible();
    await page.getByLabel(nb.admin.users.invite.email, { exact: true }).fill(address);
    await page.getByRole("button", { name: nb.admin.users.invite.submit }).click();
    await expect(invitationsSection(page).getByRole("button", { name: invitations.resend(address) })).toBeVisible();
  });

  test("an Admin who presses their own deactivate button is told why nothing changed", async ({ page }) => {
    // The demo Admin must never be deactivated: the api's refusal is answered by the test, so a
    // broken server-side check cannot lock the shared account out.
    await page.route("**/api/admin/users/*/deactivate", (route) =>
      route.fulfill({
        status: 409,
        json: { error: { code: "last_admin", message: "The product would be left without an active Admin.", fields: {} } },
      }),
    );
    await openUsers(page);
    await page.getByLabel(list.search).fill(DEMO_USERS.admin.email);
    await expect(usersSection(page).locator("tbody tr")).toHaveCount(1);
    const own = page.getByRole("button", { name: list.deactivate("Demo") });
    await own.click();
    await expect(page.getByRole("alert").filter({ hasText: list.deactivateSelf })).toBeVisible();
    await expect(own).toBeFocused();
    // The demo Admin is still active.
    await expect(usersSection(page).getByText(list.active, { exact: true })).toBeVisible();
  });
});
