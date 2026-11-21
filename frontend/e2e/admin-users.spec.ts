import { type Browser, type BrowserContext, expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { DEMO_USERS, demoContext, latestMail, loginByApi, nextMail } from "./support/auth";
import { axe } from "./support/axe";

/** The User list and the role buttons on «Brukere og roller» (Story 3.9, FR-2, FR-3, UX-DR57,
 * UX-DR75, NFR-6), on the local stack with the mail worker. Each test that changes a role makes
 * its own fresh account from an Invitation; demo Users are never changed (their refusals are
 * answered by the test, not the api). */
const list = nb.admin.users.list;
const CSRF = { "X-Requested-With": "olspillet" };

type Viewport = { name: string; width: number; height: number; phone: boolean; text200?: boolean };

const VIEWPORTS: Viewport[] = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "200 % text", width: 1280, height: 800, phone: false, text200: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
];

async function expectAccessible(page: Page, phone: boolean) {
  const results = await axe(page);
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

/** The «Brukere» section: the page also lists Invitations in a table of its own (Story 3.10). */
const usersSection = (page: Page) => page.getByRole("region", { name: list.title, exact: true });
const userRows = (page: Page) => usersSection(page).locator("tbody tr");

type Fresh = { context: BrowserContext; address: string; first: string };

/** A fresh account with only the Admin role, made from an Invitation the demo Admin sends, and
 * logged in, in a browser context of its own. */
async function freshAdmin(page: Page, browser: Browser): Promise<Fresh> {
  const tag = `${Date.now()}${Math.floor(Math.random() * 1e6)}`;
  const address = `roller-${tag}@example.com`;
  const first = `Rolf${tag}`;
  const baseURL = test.info().project.use.baseURL;
  const adminContext = await demoContext(browser, "admin");
  const admin = adminContext.request;
  const before = await latestMail(page, address);
  const sent = await admin.post("/api/admin/invitations", { data: { email: address, role: "admin" }, headers: CSRF });
  expect(sent.status()).toBe(201);
  const token = (await nextMail(page, address, before)).text.match(/\/invitasjon#([A-Za-z0-9_-]+)/)![1];
  await adminContext.close();
  const context = await browser.newContext({ baseURL });
  const accepted = await context.request.post("/api/auth/invitation/accept", {
    data: { token, name: `${first} Testesen`, password: "et-godt-passord" },
    headers: CSRF,
  });
  expect(accepted.status()).toBe(200);
  return { context, address, first };
}

async function openUsers(page: Page, text200 = false) {
  if (text200) {
    await page.addInitScript(() => {
      document.addEventListener("DOMContentLoaded", () => {
        const style = document.createElement("style");
        style.textContent = "html { font-size: 200% !important; }";
        document.head.appendChild(style);
      });
    });
  }
  await loginByApi(page, "admin");
  await page.goto("/admin/brukere");
  await expect(page.getByRole("heading", { level: 2, name: list.title })).toBeVisible();
}

for (const vp of VIEWPORTS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("the Admin finds a User, grants Faglærer and revokes Admin, and the User is held to it at the next load", async ({
      page,
      browser,
    }) => {
      const fresh = await freshAdmin(page, browser);
      const own = await fresh.context.newPage();
      await own.goto("/laererhjem");
      await expect(own.getByRole("heading", { level: 1, name: nb.access.denied })).toBeVisible();

      await openUsers(page, vp.text200);
      await page.getByLabel(list.search).fill(fresh.address);
      await expect(userRows(page)).toHaveCount(1);
      const grant = page.getByRole("button", { name: list.grant(fresh.first, list.roles.lecturer) });
      await expect(grant).toBeVisible();
      await expect(usersSection(page).getByText(fresh.address, { exact: true })).toBeVisible();
      await expect(page.getByText(list.active, { exact: true })).toBeVisible();
      await expectAccessible(page, vp.phone);
      // The invite button is the page's one primary button; the role buttons are secondary.
      await expect(page.locator("main button.bg-ink")).toHaveCount(1);

      // No dialog: the role changes at once, the pressed button keeps focus and states its new
      // effect, and the row says what changed.
      const dialogs: string[] = [];
      page.on("dialog", (dialog) => dialogs.push(dialog.message()));
      await grant.click();
      const revokeLecturer = page.getByRole("button", { name: list.revoke(fresh.first, list.roles.lecturer) });
      await expect(revokeLecturer).toBeFocused();
      await expect(page.getByRole("status").filter({ hasText: list.granted(fresh.first, list.roles.lecturer) })).toBeVisible();
      await expect(page.getByText(`${list.roles.lecturer}, ${list.roles.admin}`, { exact: true })).toBeVisible();
      await expectAccessible(page, vp.phone);

      expect(dialogs).toEqual([]);

      await own.goto("/laererhjem");
      await expect(own.getByRole("heading", { level: 1, name: nb.homes.lecturerHome })).toBeVisible();

      await page.getByRole("button", { name: list.revoke(fresh.first, list.roles.admin) }).click();
      await expect(page.getByRole("button", { name: list.grant(fresh.first, list.roles.admin) })).toBeFocused();
      await expect(page.getByText(list.revoked(fresh.first, list.roles.admin))).toBeVisible();

      await own.goto("/admin");
      await expect(own.getByRole("heading", { level: 1, name: nb.access.denied })).toBeVisible();

      // The line speaks of the list as it was: it goes as soon as the search changes.
      await page.getByLabel(list.search).press("End");
      await page.getByLabel(list.search).pressSequentially(" ");
      await expect(page.getByText(list.revoked(fresh.first, list.roles.admin))).toHaveCount(0);
      await fresh.context.close();
    });
  });
}

test.describe("search", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("a search with no match says «Ingen treff.»", async ({ page }) => {
    await openUsers(page);
    await expect(usersSection(page).getByRole("table")).toBeVisible();
    await page.getByLabel(list.search).fill("ingen-slik-bruker-finnes");
    await expect(page.getByRole("status").filter({ hasText: list.noMatches })).toBeVisible();
    await expect(usersSection(page).getByRole("table")).toHaveCount(0);
  });
});

test.describe("own role", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("an Admin who revokes their own Admin role loses the page at once", async ({ page, browser }) => {
    const fresh = await freshAdmin(page, browser);
    const own = await fresh.context.newPage();
    await own.goto("/admin/brukere");
    await own.getByLabel(list.search).fill(fresh.address);
    await expect(userRows(own)).toHaveCount(1);
    await own.getByRole("button", { name: list.revoke(fresh.first, list.roles.admin) }).click();
    await expect(own.getByRole("heading", { level: 1, name: nb.access.denied })).toBeVisible();
    await fresh.context.close();
  });
});

test.describe("paging", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("«Vis flere» appends the next page by its cursor", async ({ page }) => {
    const row = (n: number) => ({
      id: `00000000-0000-7000-8000-00000000000${n}`,
      name: `Side ${n}`,
      email: `side${n}@example.com`,
      roles: [],
      is_active: true,
    });
    const cursors: (string | null)[] = [];
    await page.route("**/api/admin/users?*", (route) => {
      const cursor = new URL(route.request().url()).searchParams.get("cursor");
      cursors.push(cursor);
      return route.fulfill({
        json: cursor ? { items: [row(2)], next_cursor: null } : { items: [row(1)], next_cursor: "neste" },
      });
    });
    await openUsers(page);
    await expect(usersSection(page).getByRole("cell", { name: "Side 1", exact: true })).toBeVisible();
    await usersSection(page).getByRole("button", { name: list.more }).click();
    await expect(usersSection(page).getByRole("cell", { name: "Side 2", exact: true })).toBeVisible();
    await expect(usersSection(page).getByRole("cell", { name: "Side 1", exact: true })).toBeVisible();
    await expect(usersSection(page).getByRole("button", { name: list.more })).toHaveCount(0);
    expect(cursors).toContain("neste");
  });

  test("a failed «Vis flere» keeps the rows shown, says so under them, and can be pressed again", async ({ page }) => {
    const row = (n: number) => ({
      id: `00000000-0000-7000-8000-00000000000${n}`,
      name: `Side ${n}`,
      email: `side${n}@example.com`,
      roles: [],
      is_active: true,
    });
    let failNext = true;
    await page.route("**/api/admin/users?*", (route) => {
      const cursor = new URL(route.request().url()).searchParams.get("cursor");
      if (!cursor) return route.fulfill({ json: { items: [row(1)], next_cursor: "neste" } });
      if (failNext) {
        failNext = false;
        return route.fulfill({ status: 500, body: "" });
      }
      return route.fulfill({ json: { items: [row(2)], next_cursor: null } });
    });
    await openUsers(page);
    const first = usersSection(page).getByRole("cell", { name: "Side 1", exact: true });
    await expect(first).toBeVisible();
    const more = usersSection(page).getByRole("button", { name: list.more });
    await more.click();
    await expect(usersSection(page).getByRole("alert")).toHaveText(list.moreFailed);
    await expect(first).toBeVisible();
    await expect(page.getByText(nb.system.pageError)).toHaveCount(0);
    await more.click();
    await expect(usersSection(page).getByRole("cell", { name: "Side 2", exact: true })).toBeVisible();
    await expect(first).toBeVisible();
    await expect(usersSection(page).getByRole("alert")).toHaveCount(0);
  });
});

test.describe("refusals", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("a revoke blocked by owned Classes names the first name and the count, and keeps the role", async ({ page }) => {
    // No Class exists before Epic 4: the test answers as a registered blocker would make the api.
    await page.route("**/api/admin/users/*/roles/lecturer", (route) =>
      route.fulfill({
        status: 409,
        json: { error: { code: "role_revoke_blocked", message: "", fields: { classes: 2 } } },
      }),
    );
    await openUsers(page);
    await page.getByLabel(list.search).fill(DEMO_USERS.lecturer.name);
    await expect(userRows(page)).toHaveCount(1);
    const button = page.getByRole("button", { name: list.revoke("Demo", list.roles.lecturer) });
    await button.click();
    await expect(page.locator("main").getByRole("alert")).toHaveText(
      "Demo eier 2 Klasser. Legg til en annen Faglærer eller arkiver Klassene først.",
    );
    await expect(button).toBeFocused();
    await expect(usersSection(page).getByRole("cell", { name: list.roles.lecturer, exact: true })).toBeVisible();
  });

  test("revoking the last active Admin is refused with its reason", async ({ page }) => {
    await page.route("**/api/admin/users/*/roles/admin", (route) =>
      route.fulfill({ status: 409, json: { error: { code: "last_admin", message: "", fields: {} } } }),
    );
    await openUsers(page);
    await page.getByLabel(list.search).fill(DEMO_USERS.admin.email);
    await expect(userRows(page)).toHaveCount(1);
    await expect(usersSection(page).getByRole("cell", { name: DEMO_USERS.admin.email, exact: true })).toBeVisible();
    await page.getByRole("button", { name: list.revoke("Demo", list.roles.admin) }).click();
    await expect(page.locator("main").getByRole("alert")).toHaveText(list.lastAdmin("Demo"));
  });
});

test.describe("not an Admin", () => {
  test("a Lecturer sees no User list", async ({ page }) => {
    await loginByApi(page, "lecturer");
    await page.goto("/admin/brukere");
    await expect(page.getByRole("heading", { level: 1, name: nb.access.denied })).toBeVisible();
    await expect(page.getByLabel(list.search)).toHaveCount(0);
    const response = await page.request.get("/api/admin/users");
    expect(response.status()).toBe(403);
  });
});
