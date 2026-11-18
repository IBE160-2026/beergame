import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, type Route, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { DEMO_PASSWORD, DEMO_USERS, loginByApi } from "./support/auth";

/**
 * Story 3.4: loading, offline, page error, action error and an ended session. Slow and offline
 * states come from Playwright routing, `setOffline` and the page clock; nothing waits in real time.
 */

const WCAG_21_AA = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

const VIEWPORTS = [
  { name: "320 px", width: 320, height: 640 },
  { name: "1440 px", width: 1440, height: 900 },
];

const ME = "**/api/auth/me";
const sys = nb.system;
// 21:14 in Oslo (UTC+1 in November): «Sist oppdatert 21:14».
const NOW = new Date("2026-11-18T20:14:00Z");

async function expectAccessible(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(WCAG_21_AA).analyze();
  expect(results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`)).toEqual(
    [],
  );
  const scrolls = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(scrolls).toBe(false);
}

const line = (page: Page) => page.locator("main [data-connection-notice]");
const logout = (page: Page) => page.getByRole("banner").getByRole("button", { name: nb.auth.session.logout });

/** Counts the requests to `url` the page sends from now on. */
function countRequests(page: Page, url: string, method = "GET") {
  const sent = { n: 0 };
  page.on("request", (r) => {
    if (new URL(r.url()).pathname === url && r.method() === method) sent.n += 1;
  });
  return sent;
}

for (const vp of VIEWPORTS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("a slow page shows the Skjelett, «Laster …» after 1 s and the page error after 10 s", async ({ page }) => {
      // The page clock stands still from here; only `runFor` moves it.
      await page.clock.install({ time: NOW });
      await page.clock.pauseAt(new Date(NOW.getTime() + 1_000));
      await loginByApi(page, "admin");
      // `/me` hangs while `hold` is set; a request that hung keeps hanging.
      let hold = true;
      await page.route(ME, (route: Route) => (hold ? undefined : route.continue()));
      await page.goto("/admin");

      const skeleton = page.locator("main [data-skeleton]");
      await expect(skeleton).toBeVisible();
      await expect(page.getByText(sys.loading)).toHaveCount(0);
      await expect(page.getByRole("heading", { level: 1 })).toHaveCount(0);
      await page.clock.runFor(999);
      await expect(page.getByText(sys.loading)).toHaveCount(0);
      await page.clock.runFor(1);
      await expect(page.getByRole("status").filter({ hasText: sys.loading })).toBeVisible();

      await page.clock.runFor(8_999);
      await expect(line(page)).toHaveText("");
      await expect(skeleton).toBeVisible();
      await page.clock.runFor(1);
      await expect(line(page)).toContainText(sys.pageError);
      await expect(skeleton).toHaveCount(0);
      // axe needs running timers.
      await page.clock.resume();
      await expectAccessible(page);

      // «Prøv igjen» drops the hanging request and asks again, in place.
      hold = false;
      await line(page).getByRole("button", { name: sys.retry }).click();
      await expect(page.getByRole("heading", { level: 1, name: nb.homes.adminArea })).toBeVisible();
      await expect(line(page)).toHaveText("");
    });

    test("a page whose request fails shows «Siden kunne ikke lastes.» and «Prøv igjen»", async ({ page }) => {
      await loginByApi(page, "lecturer");
      await page.route(ME, (route: Route) =>
        route.fulfill({ status: 500, json: { error: { code: "internal_error", message: "x" } } }),
      );
      await page.goto("/laererhjem");
      await expect(line(page)).toContainText(sys.pageError);
      await expectAccessible(page);

      await page.unroute(ME);
      const sent = countRequests(page, "/api/auth/me");
      await line(page).getByRole("button", { name: sys.retry }).click();
      await expect(page.getByRole("heading", { level: 1, name: nb.homes.lecturerHome })).toBeVisible();
      expect(sent.n).toBe(1);
    });

    test("offline shows «Frakoblet. …» with the time, and back online refreshes in place", async ({ page, context }) => {
      await page.clock.install({ time: NOW });
      await loginByApi(page, "admin");
      await page.goto("/admin");
      await expect(page.getByRole("heading", { level: 1, name: nb.homes.adminArea })).toBeVisible();
      await logout(page).focus();

      await context.setOffline(true);
      await expect(line(page)).toHaveText(`${sys.offline} ${sys.lastUpdated("21:14")}`);
      await expect(line(page)).toHaveAttribute("role", "status");
      await expectAccessible(page);

      const refetch = page.waitForRequest((r) => new URL(r.url()).pathname === "/api/auth/me");
      await context.setOffline(false);
      await expect(line(page)).toHaveText(sys.reconnected);
      await refetch;
      await expect(logout(page)).toBeFocused();

      await page.clock.runFor(5_000);
      await expect(line(page)).toHaveText("");
      await expect(logout(page)).toBeFocused();
    });

    test("text typed on «Logg inn» stays through offline, and nothing is sent on return", async ({ page, context }) => {
      const sent = countRequests(page, "/api/auth/login", "POST");
      await page.goto("/logg-inn");
      const email = page.getByLabel(nb.auth.login.email);
      await email.fill("kari@example.com");

      await context.setOffline(true);
      await expect(line(page)).toHaveText(sys.offline);
      await expect(email).toHaveValue("kari@example.com");
      await expectAccessible(page);

      await context.setOffline(false);
      await expect(line(page)).toHaveText(sys.reconnected);
      await expect(email).toHaveValue("kari@example.com");
      expect(sent.n).toBe(0);
    });

    test("an action that fails shows its line beside the button, which keeps focus", async ({ page }) => {
      await loginByApi(page, "admin");
      await page.goto("/admin");
      await expect(page.getByRole("heading", { level: 1, name: nb.homes.adminArea })).toBeVisible();
      await page.route("**/api/auth/logout", (route: Route) => route.fulfill({ status: 500, body: "" }));

      await logout(page).focus();
      await page.keyboard.press("Enter");
      const alert = page.getByRole("banner").getByRole("alert");
      await expect(alert).toHaveText(nb.auth.session.logoutFailed);
      await expect(logout(page)).toBeFocused();
      await expect(logout(page)).not.toHaveAttribute("aria-disabled");
      await expect(page).toHaveURL(/\/admin$/);
      await expectAccessible(page);
    });

    test("an ended session opens «Logg inn» with focus on the message, and login returns", async ({ page, context }) => {
      await loginByApi(page, "admin");
      const [cookie] = (await context.cookies()).filter((c) => c.name === "olspillet_session");
      await context.addCookies([{ ...cookie, value: "utgatt" }]);

      await page.goto("/admin");
      await expect(page).toHaveURL(/\/logg-inn\?neste=%2Fadmin&utlopt=1$/);
      const note = page.getByText(nb.auth.login.sessionExpired);
      await expect(note).toBeFocused();
      await expect(note).not.toHaveAttribute("role");
      await expectAccessible(page);

      await page.getByLabel(nb.auth.login.email).fill(DEMO_USERS.admin.email);
      await page.getByLabel(nb.auth.login.password).fill(DEMO_PASSWORD);
      await page.getByRole("button", { name: nb.auth.login.submit }).click();
      await expect(page).toHaveURL(/\/admin$/);
      await expect(page.getByRole("heading", { level: 1, name: nb.homes.adminArea })).toBeVisible();
    });
  });
}

test("an action pressed offline fails at once and is not sent when the connection returns", async ({ page, context }) => {
  await loginByApi(page, "admin");
  await page.goto("/admin");
  await expect(page.getByRole("heading", { level: 1, name: nb.homes.adminArea })).toBeVisible();
  const sent = countRequests(page, "/api/auth/logout", "POST");

  await context.setOffline(true);
  await logout(page).click();
  await expect(page.getByRole("banner").getByRole("alert")).toHaveText(nb.auth.session.logoutFailed);
  // The offline press itself counts as a (failed) request; from here on nothing may be sent.
  sent.n = 0;
  const refetch = page.waitForRequest((r) => new URL(r.url()).pathname === "/api/auth/me");
  await context.setOffline(false);
  await refetch;
  await expect(line(page)).toHaveText(sys.reconnected);
  expect(sent.n).toBe(0);
  await expect(page).toHaveURL(/\/admin$/);
});

test("a session that ends while a page is open sends the next request to «Logg inn»", async ({ page, context }) => {
  await loginByApi(page, "lecturer");
  await page.goto("/laererhjem?fane=1");
  await expect(page.getByRole("heading", { level: 1, name: nb.homes.lecturerHome })).toBeVisible();
  const [cookie] = (await context.cookies()).filter((c) => c.name === "olspillet_session");
  await context.addCookies([{ ...cookie, value: "utgatt" }]);

  // Coming back online refetches `/me`, which finds the session ended.
  await context.setOffline(true);
  await context.setOffline(false);
  await expect(page).toHaveURL(/\/logg-inn\?neste=%2Flaererhjem%3Ffane%3D1&utlopt=1$/);
  await expect(page.getByText(nb.auth.login.sessionExpired)).toBeFocused();
});

test("a return address off the site is ignored after login", async ({ page }) => {
  await page.goto("/logg-inn?neste=%2F%2Fevil.example%2Fadmin");
  await page.getByLabel(nb.auth.login.email).fill(DEMO_USERS.lecturer.email);
  await page.getByLabel(nb.auth.login.password).fill(DEMO_PASSWORD);
  await page.getByRole("button", { name: nb.auth.login.submit }).click();
  await expect(page).toHaveURL(/127\.0\.0\.1:8080\/laererhjem$/);
});

test("with reduced motion no state change is animated", async ({ page, context }) => {
  // A transition the page could gain later: it runs normally, and not under reduced motion.
  const style = "[data-connection-notice] > div { transition: opacity 200ms; }";
  const duration = () =>
    line(page)
      .locator("> div")
      .evaluate((el) => getComputedStyle(el).transitionDuration);
  await page.goto("/logg-inn");
  await page.addStyleTag({ content: style });
  await context.setOffline(true);
  await expect(line(page)).toHaveText(sys.offline);
  expect(await duration()).toBe("0.2s");
  await context.setOffline(false);

  await page.emulateMedia({ reducedMotion: "reduce" });
  await context.setOffline(true);
  await expect(line(page)).toHaveText(sys.offline);
  expect(await duration()).toBe("0s");
  await context.setOffline(false);
  await expect(line(page)).toHaveText(sys.reconnected);
});

test("`/` and the not-found page show the page error when the session cannot be read", async ({ page }) => {
  await loginByApi(page, "student");
  await page.route(ME, (route: Route) => route.fulfill({ status: 500, body: "" }));
  for (const path of ["/", "/finnes-ikke"]) {
    await page.goto(path);
    await expect(line(page)).toContainText(sys.pageError);
  }
  await page.unroute(ME);
  await line(page).getByRole("button", { name: sys.retry }).click();
  await expect(page.getByRole("heading", { level: 1, name: nb.access.notFound })).toBeVisible();
  await expect(page.getByRole("link", { name: nb.navigation.toHome })).toBeVisible();
});

test("a visitor who is not logged in comes back to the same address, query included", async ({ page }) => {
  await page.goto("/laererhjem?fane=1");
  await expect(page).toHaveURL(/\/logg-inn\?neste=%2Flaererhjem%3Ffane%3D1$/);
  await page.getByLabel(nb.auth.login.email).fill(DEMO_USERS.lecturer.email);
  await page.getByLabel(nb.auth.login.password).fill(DEMO_PASSWORD);
  await page.getByRole("button", { name: nb.auth.login.submit }).click();
  await expect(page).toHaveURL(/\/laererhjem\?fane=1$/);
});
