import { expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { answerTo, DEMO_PASSWORD, DEMO_USERS, type DemoRole, loginByApi, untilHydrated } from "./support/auth";
import { axe } from "./support/axe";

const copy = nb.auth.login;
const COOKIE = "olspillet_session";

const VIEWPORTS: { name: string; width: number; height: number; role: DemoRole }[] = [
  { name: "320 px", width: 320, height: 640, role: "admin" },
  { name: "360 px", width: 360, height: 740, role: "lecturer" },
  { name: "1440 px", width: 1440, height: 900, role: "admin" },
];

async function expectAccessible(page: Page) {
  const results = await axe(page);
  expect(results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`)).toEqual(
    [],
  );
  const scrolls = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(scrolls).toBe(false);
}

/** Tab until `name` has focus (at most `max` presses), so the test uses the keyboard only. */
async function tabTo(page: Page, name: string, max = 8) {
  for (let i = 0; i < max; i++) {
    await page.keyboard.press("Tab");
    const focused = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement | null;
      return el?.id || el?.textContent?.trim() || "";
    });
    if (focused === name) return;
  }
  throw new Error(`Tab never reached ${name}`);
}

async function sessionCookie(page: Page) {
  return (await page.context().cookies()).find((c) => c.name === COOKIE);
}

for (const vp of VIEWPORTS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("wrong password, right password and «Logg ut», by keyboard alone", async ({ page }) => {
      const user = DEMO_USERS[vp.role];
      await page.goto("/logg-inn");
      await untilHydrated(page);

      // Wrong password: one line that names neither field, the input is kept.
      await tabTo(page, "email");
      await page.keyboard.type(user.email);
      await page.keyboard.press("Tab");
      await page.keyboard.type("feil-passord");
      // The api hashes the password before it answers, which can outlast an assertion under load.
      const refused = answerTo(page, "/api/auth/login");
      await page.keyboard.press("Enter");
      expect((await refused).status()).toBe(401);
      await expect(page.locator("form").getByRole("alert")).toHaveText(copy.invalidCredentials);
      await expect(page.getByLabel(copy.email)).toHaveValue(user.email);
      await expect(page.getByLabel(copy.email)).toBeFocused();
      expect(await sessionCookie(page)).toBeUndefined();
      await expectAccessible(page);

      // Right password: the session cookie is set and the User is on their own home.
      await page.keyboard.press("Tab");
      await page.keyboard.press("ControlOrMeta+A");
      await page.keyboard.type(DEMO_PASSWORD);
      const accepted = answerTo(page, "/api/auth/login");
      await page.keyboard.press("Enter");
      expect((await accepted).status()).toBe(200);
      await expect(page).toHaveURL(new RegExp(`${user.home}$`));
      await expect(page.getByRole("banner").getByText(user.name)).toBeVisible();
      const cookie = await sessionCookie(page);
      expect(cookie).toMatchObject({ httpOnly: true, secure: true, sameSite: "Lax", path: "/" });
      await expectAccessible(page);

      // «Logg ut»: the cookie is cleared and «Logg inn» shows again.
      await tabTo(page, nb.auth.session.logout);
      await page.keyboard.press("Enter");
      await expect(page).toHaveURL(/\/logg-inn$/);
      await expect(page.getByRole("heading", { level: 1, name: copy.title })).toBeVisible();
      expect(await sessionCookie(page)).toBeUndefined();
      await expectAccessible(page);

      // Back in the same tab, without a reload: nothing of the old session is left in the cache,
      // and the home sends the visitor back to «Logg inn», with the way back to it.
      await page.goBack();
      await expect(page).toHaveURL(new RegExp(`/logg-inn\\?neste=${encodeURIComponent(user.home)}$`));
      await expect(page.getByText(user.name)).toHaveCount(0);
      await expect(page.getByRole("button", { name: nb.auth.session.logout })).toHaveCount(0);
    });

    test("too many failed logins are refused with «For mange forsøk»", async ({ page }) => {
      // A fresh address per run, so only this account reaches its limit.
      const email = `sperret.${vp.width}.${Date.now()}@example.com`;
      let status = 0;
      for (let i = 0; i < 50 && status !== 429; i++) {
        const response = await page.request.post("/api/auth/login", {
          data: { email, password: "feil" },
          headers: { "X-Requested-With": "olspillet" },
        });
        status = response.status();
      }
      expect(status).toBe(429);

      await page.goto("/logg-inn");
      await untilHydrated(page);
      await tabTo(page, "email");
      await page.keyboard.type(email);
      await page.keyboard.press("Tab");
      await page.keyboard.type("hva som helst");
      await page.keyboard.press("Enter");
      await expect(page.locator("form").getByRole("alert")).toHaveText(copy.rateLimited);
      await expectAccessible(page);
    });
  });
}

test("the API refuses a mutation without the CSRF header", async ({ request }) => {
  const response = await request.post("/api/auth/login", {
    data: { email: DEMO_USERS.admin.email, password: DEMO_PASSWORD },
  });
  expect(response.status()).toBe(403);
  expect((await response.json()).error.code).toBe("csrf_header_missing");
});

test("the API login helper gives the browser a session", async ({ page }) => {
  const user = await loginByApi(page, "lecturer");
  await page.goto("/");
  await expect(page).toHaveURL(/\/laererhjem$/);
  await expect(page.getByRole("banner").getByText(user.name)).toBeVisible();
});
