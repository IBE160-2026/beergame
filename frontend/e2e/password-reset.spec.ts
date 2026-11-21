import { type Browser, expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { demoContext, latestMail, nextMail, untilHydrated } from "./support/auth";
import { axe } from "./support/axe";

/** «Glemt passord» and «Nytt passord» (Story 3.6, UX-DR61, NFR-6), on the local stack with
 * `worker-batch` sending the mock mail. A reset ends every session of its User (Issue #73), so
 * each test resets a fresh account made from an Invitation, never a demo User: tests that are
 * logged in as one at the same time keep their session. */
const forgot = nb.auth.forgot;
const reset = nb.auth.reset;
const CSRF = { "X-Requested-With": "olspillet" };
const FIRST_PASSWORD = "et-godt-passord";
const NEW_PASSWORD = "et-nytt-godt-passord";

type Roles = "admin" | "lecturer" | "adminLecturer";
const HOME: Record<Roles, string> = { admin: "/admin", lecturer: "/laererhjem", adminLecturer: "/laererhjem" };

const VIEWPORTS: { name: string; width: number; height: number; role: Roles; phone: boolean }[] = [
  { name: "320 px", width: 320, height: 640, role: "admin", phone: true },
  { name: "360 px", width: 360, height: 740, role: "lecturer", phone: true },
  { name: "1440 px", width: 1440, height: 900, role: "adminLecturer", phone: false },
];

/** A fresh account with `roles`, made from an Invitation the demo Admin sends (and, for both
 * staff roles, a grant of Admin on top). Nothing stays logged in. */
async function freshUser(page: Page, browser: Browser, roles: Roles) {
  const tag = `${Date.now()}${Math.floor(Math.random() * 1e6)}`;
  const email = `nytt-passord-${tag}@example.com`;
  const baseURL = test.info().project.use.baseURL;
  const adminContext = await demoContext(browser, "admin");
  const admin = adminContext.request;
  const before = await latestMail(page, email);
  const invited = roles === "admin" ? "admin" : "lecturer";
  const sent = await admin.post("/api/admin/invitations", { data: { email, role: invited }, headers: CSRF });
  expect(sent.status()).toBe(201);
  const token = (await nextMail(page, email, before)).text.match(/\/invitasjon#([A-Za-z0-9_-]+)/)![1];
  const userContext = await browser.newContext({ baseURL });
  const accepted = await userContext.request.post("/api/auth/invitation/accept", {
    data: { token, name: `Petra${tag} Testesen`, password: FIRST_PASSWORD },
    headers: CSRF,
  });
  expect(accepted.status()).toBe(200);
  const { user } = (await accepted.json()) as { user: { id: string } };
  await userContext.close();
  if (roles === "adminLecturer") {
    const granted = await admin.post(`/api/admin/users/${user.id}/roles`, { data: { role: "admin" }, headers: CSRF });
    expect(granted.status()).toBe(200);
  }
  await adminContext.close();
  return { email, home: HOME[roles] };
}

async function expectAccessible(page: Page, phone: boolean) {
  const results = await axe(page);
  expect(results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`)).toEqual(
    [],
  );
  const scrolls = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
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

/** The reset link of a mail, as a path on this site. */
function linkOf(mailText: string): string {
  const match = mailText.match(/https?:\/\/\S+\/nytt-passord#[A-Za-z0-9_-]+/);
  expect(match, "the mail holds a reset link").not.toBeNull();
  const url = new URL(match![0]);
  return `${url.pathname}${url.hash}`;
}

for (const vp of VIEWPORTS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("asks for a link, sets a new password once, and logs in with it", async ({ page, browser }) => {
      const user = await freshUser(page, browser, vp.role);
      const before = await latestMail(page, user.email);

      await page.goto("/logg-inn");
      await page.getByRole("link", { name: nb.auth.login.forgotPassword }).click();
      await expect(page).toHaveURL(/\/glemt-passord$/);
      await expect(page.getByRole("heading", { level: 1, name: forgot.title })).toBeVisible();
      await expectAccessible(page, vp.phone);

      await untilHydrated(page);
      await page.getByLabel(forgot.email).fill(user.email);
      await page.getByRole("button", { name: forgot.submit }).click();
      await expect(page.getByText(forgot.sent)).toBeFocused();
      await expectAccessible(page, vp.phone);

      const mail = await nextMail(page, user.email, before);
      expect(mail.subject).toBe("Nytt passord til ØL-spillet");
      expect(mail.text.startsWith("ØL-spillet")).toBe(true);
      const link = linkOf(mail.text);

      await page.goto(link);
      await expect(page.getByRole("heading", { level: 1, name: reset.title })).toBeVisible();
      await expect(page.getByText(reset.lead(user.email))).toBeVisible();
      await expectAccessible(page, vp.phone);

      const password = page.getByLabel(reset.password);
      await password.fill("kort");
      await page.getByRole("button", { name: reset.submit }).click();
      await expect(password).toHaveAttribute("aria-invalid", "true");
      await expect(password).toHaveAccessibleDescription(`${reset.passwordRule} ${reset.errors.passwordShort}`);
      await expectAccessible(page, vp.phone);

      await password.fill(NEW_PASSWORD);
      await page.getByRole("button", { name: reset.submit }).click();
      await expect(page.getByText(reset.done)).toBeFocused();
      await expect(page.getByLabel(nb.auth.login.email)).toHaveValue(user.email);
      await expectAccessible(page, vp.phone);

      await page.getByLabel(nb.auth.login.password).fill(NEW_PASSWORD);
      await page.getByRole("button", { name: nb.auth.login.submit }).click();
      await expect(page).toHaveURL(new RegExp(`${user.home}$`));

      // The link works once: opened again it says so, and «Send ny lenke» goes back.
      await page.goto(link);
      await expect(page.getByText(reset.invalid)).toBeVisible();
      await expectAccessible(page, vp.phone);
      await page.getByRole("link", { name: reset.sendNew }).click();
      await expect(page).toHaveURL(/\/glemt-passord$/);
    });
  });
}

test("an unknown address gets the same answer", async ({ page }) => {
  await page.goto("/glemt-passord");
  await untilHydrated(page);
  await page.getByLabel(forgot.email).fill(`ingen.${Date.now()}@example.com`);
  const answer = page.waitForResponse((r) => r.url().endsWith("/api/auth/password-reset"));
  await page.getByRole("button", { name: forgot.submit }).click();
  expect((await answer).status()).toBe(202);
  await expect(page.getByText(forgot.sent)).toBeVisible();
});

test("a link with no token or an unknown one shows the expired state", async ({ page }) => {
  for (const path of ["/nytt-passord", "/nytt-passord#ukjent-lenke"]) {
    await page.goto(path);
    await expect(page.getByText(reset.invalid)).toBeVisible();
    await expect(page.getByLabel(reset.password)).toHaveCount(0);
  }
});

test("a link spent while the form is open shows the expired state on save", async ({ page, browser }) => {
  const user = await freshUser(page, browser, "lecturer");
  const before = await latestMail(page, user.email);
  const asked = await page.request.post("/api/auth/password-reset", {
    data: { email: user.email },
    headers: CSRF,
  });
  expect(asked.status()).toBe(202);
  const link = linkOf((await nextMail(page, user.email, before)).text);

  await page.goto(link);
  await expect(page.getByLabel(reset.password)).toBeVisible();
  // Spent elsewhere, for example in another tab.
  const spent = await page.request.post("/api/auth/password-reset/confirm", {
    data: { token: link.split("#")[1], password: NEW_PASSWORD },
    headers: CSRF,
  });
  expect(spent.status()).toBe(200);

  await page.getByLabel(reset.password).fill(NEW_PASSWORD);
  await page.getByRole("button", { name: reset.submit }).click();
  await expect(page.getByText(reset.invalid)).toBeVisible();
  await expect(page.getByRole("link", { name: reset.sendNew })).toBeVisible();
  await expect(page.getByText(reset.failed)).toHaveCount(0);
});
