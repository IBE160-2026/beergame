import AxeBuilder from "@axe-core/playwright";
import { type APIRequestContext, type Browser, expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { answerTo, demoContext, latestMail, nextMail } from "./support/auth";

/** «Du er invitert» (Story 3.8, FR-1, FR-4, UX-DR61, UX-DR75, NFR-6), on the local stack with the
 * mail worker. Each test invites its own fresh address, so runs never meet and no demo User
 * changes. */
const copy = nb.auth.invitation;
const WCAG_21_AA = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];
const CSRF = { "X-Requested-With": "olspillet" };
const PASSWORD = "mitt-nye-passord";

const VIEWPORTS = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
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

/** The Admin's own api session, in a browser context apart from the page's, which plays the
 * invitee. */
async function adminApi(browser: Browser): Promise<APIRequestContext> {
  return (await demoContext(browser, "admin")).request;
}

/** Send an Invitation as the Admin and return the path of the link its mail carries. */
async function invite(page: Page, request: APIRequestContext, email: string, role: "lecturer" | "admin") {
  const before = await latestMail(page, email);
  const response = await request.post("/api/admin/invitations", { data: { email, role }, headers: CSRF });
  expect(response.status()).toBe(201);
  const mail = await nextMail(page, email, before);
  const link = mail.text.match(/https?:\/\/[^/\s]+(\/invitasjon#[A-Za-z0-9_-]+)/);
  expect(link).not.toBeNull();
  return link![1];
}

function freshAddress(tag: string) {
  return `invitasjon-${tag}-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`;
}

for (const vp of VIEWPORTS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("a mailed Invitation becomes an account, a second one adds a role, and a used link offers a new one", async ({
      page,
      browser,
    }) => {
      const request = await adminApi(browser);
      const address = freshAddress(vp.name.replace(/\W+/g, ""));
      const lecturerLink = await invite(page, request, address, "lecturer");

      // A new account: the address prefilled and read-only, the password rule before typing.
      await page.goto(lecturerLink);
      await expect(page.getByRole("heading", { level: 1, name: copy.title })).toBeVisible();
      const email = page.getByLabel(copy.email);
      await expect(email).toHaveValue(address);
      await expect(email).toHaveAttribute("readonly", "");
      const password = page.getByLabel(copy.password);
      await expect(password).toHaveAccessibleDescription(copy.passwordRule);
      await expect(page.getByText(copy.validity(14))).toBeVisible();
      await expect(page.locator("main button")).toHaveCount(1);
      await expectAccessible(page, vp.phone);

      // Reasons after the first press; they clear as the fields are typed.
      await page.getByRole("button", { name: copy.submit }).click();
      const name = page.getByLabel(copy.name);
      await expect(name).toHaveAccessibleDescription(copy.errors.nameEmpty);
      await expect(name).toBeFocused();
      await expectAccessible(page, vp.phone);
      await name.fill("Ny Faglærer");
      await expect(name).not.toHaveAttribute("aria-invalid", "true");
      await password.fill(PASSWORD);
      const created = answerTo(page, "/api/auth/invitation/accept");
      await page.getByRole("button", { name: copy.submit }).click();
      expect((await created).status()).toBe(200);
      await expect(page).toHaveURL(/\/laererhjem$/);
      await expect(page.getByRole("button", { name: nb.auth.session.logout })).toBeVisible();

      // An Admin Invitation to the same address: the page asks for the account's password.
      const adminLink = await invite(page, request, address, "admin");
      await page.context().clearCookies();
      await page.goto(adminLink);
      await expect(page.getByText(copy.existing.lead(copy.roles.admin))).toBeVisible();
      await expect(page.getByLabel(copy.existing.email)).toHaveValue(address);
      await expect(page.getByLabel(copy.name)).toHaveCount(0);
      await expect(page.locator("main button")).toHaveCount(1);
      await expectAccessible(page, vp.phone);
      await page.getByLabel(copy.existing.password).fill("feil-passord");
      const refused = answerTo(page, "/api/auth/invitation/accept-login");
      await page.getByRole("button", { name: copy.existing.submit }).click();
      expect((await refused).status()).toBe(401);
      await expect(page.getByText(nb.auth.login.invalidCredentials)).toBeVisible();
      await page.getByLabel(copy.existing.password).fill(PASSWORD);
      const added = answerTo(page, "/api/auth/invitation/accept-login");
      await page.getByRole("button", { name: copy.existing.submit }).click();
      expect((await added).status()).toBe(200);
      // Admin and Lecturer land on the Lærerhjem, with the link to the Admin-område.
      await expect(page).toHaveURL(/\/laererhjem$/);
      await expect(page.getByRole("link", { name: nb.navigation.toAdminArea })).toBeVisible();

      // The used link: one action, and the same answer for any link.
      await page.context().clearCookies();
      await page.goto(lecturerLink);
      await expect(page.getByText(copy.invalid)).toBeVisible();
      await expect(page.locator("main button")).toHaveCount(1);
      await expectAccessible(page, vp.phone);
      await page.getByRole("button", { name: copy.requestNew }).click();
      await expect(page.getByText(copy.requested)).toBeFocused();
      await expectAccessible(page, vp.phone);
    });
  });
}

test.describe("Admin Invitation", () => {
  test("a new Admin lands on the Admin-område", async ({ page, browser }) => {
    const request = await adminApi(browser);
    const link = await invite(page, request, freshAddress("admin"), "admin");
    await page.goto(link);
    await page.getByLabel(copy.name).fill("Ny Admin");
    await page.getByLabel(copy.password).fill(PASSWORD);
    const created = answerTo(page, "/api/auth/invitation/accept");
    await page.getByRole("button", { name: copy.submit }).click();
    expect((await created).status()).toBe(200);
    await expect(page).toHaveURL(/\/admin$/);
  });
});

test.describe("account made meanwhile", () => {
  test("a new-account form whose address gains an account switches to the login that adds the role", async ({
    page,
    browser,
  }) => {
    const request = await adminApi(browser);
    const address = freshAddress("meanwhile");
    const lecturerLink = await invite(page, request, address, "lecturer");
    await page.goto(lecturerLink);
    await expect(page.getByLabel(copy.name)).toBeVisible();

    // Meanwhile the address takes an Admin Invitation in another tab.
    const adminLink = await invite(page, request, address, "admin");
    const other = await browser.newContext({ baseURL: test.info().project.use.baseURL });
    const accepted = await other.request.post("/api/auth/invitation/accept", {
      data: { token: adminLink.split("#")[1], name: "Ny Admin", password: PASSWORD },
      headers: CSRF,
    });
    expect(accepted.status()).toBe(200);
    await other.close();

    await page.getByLabel(copy.name).fill("Ny Faglærer");
    await page.getByLabel(copy.password).fill(PASSWORD);
    const refused = answerTo(page, "/api/auth/invitation/accept");
    await page.getByRole("button", { name: copy.submit }).click();
    expect((await refused).status()).toBe(409);
    await expect(page.getByText(copy.existing.lead(copy.roles.lecturer))).toBeVisible();
    await expect(page.getByRole("button", { name: copy.existing.submit })).toBeVisible();
  });
});

test.describe("unknown link", () => {
  test("a link with no token shows the expired-or-used state", async ({ page }) => {
    await page.goto("/invitasjon");
    await expect(page.getByText(copy.invalid)).toBeVisible();
    await expect(page.getByRole("button", { name: copy.requestNew })).toBeVisible();
  });
});
