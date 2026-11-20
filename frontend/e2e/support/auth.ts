import { type APIRequestContext, type Browser, type BrowserContext, expect, type Page, test } from "@playwright/test";

import { nb } from "../../src/copy/nb";

/**
 * The test login for Playwright tests and visual checks (Story 3.2). The local stack
 * (`docker compose`, `APP_ENV=local`) seeds these accounts on an empty database
 * (`backend/app/modules/identity/seed.py`); the README lists them too. Role → account.
 */
export const DEMO_PASSWORD = "olspillet-demo";

export const DEMO_USERS = {
  admin: { email: "admin@example.com", name: "Demo Admin", home: "/admin" },
  lecturer: { email: "faglaerer@example.com", name: "Demo Faglærer", home: "/laererhjem" },
  // Story 3.3: both staff roles (lands on the Lærerhjem), and a User with no account role (Hjem).
  adminLecturer: { email: "admin-faglaerer@example.com", name: "Demo Admin og Faglærer", home: "/laererhjem" },
  student: { email: "student@example.com", name: "Demo Student", home: "/hjem" },
  // Story 4.9: no account role, Assistant lecturer of the demo Class «class-of-1994».
  assistant: { email: "assistent@example.com", name: "Demo Assistent", home: "/laererhjem" },
} as const;

export type DemoRole = keyof typeof DEMO_USERS;

/** Wait until React has hydrated the first element matching `selector`, which the server
 * rendered. A press before that reaches the bare HTML: a form then posts to the page itself and
 * the page reloads, as it should, but a test that means to drive the app has lost its press.
 * React marks every element it hydrates with its props; polled from here, so a page clock the
 * test installed does not stop the wait. */
export async function untilHydrated(page: Page, selector = "main form") {
  await expect
    .poll(() =>
      page
        .locator(selector)
        .first()
        .evaluate((el) => Object.keys(el).some((key) => key.startsWith("__reactProps$"))),
    )
    .toBe(true);
}

/** Wait until every web font the page's current layout asks for has loaded. Until then the text
 * is set in a fallback face with other widths and line heights, so a measured box, a wrap or a
 * horizontal scroll can change once the font swaps in; under load the font arrives late. The
 * layout is forced first, so the fonts it needs are requested before `fonts.ready` is read. */
export async function untilFontsLoaded(page: Page) {
  await page.evaluate(async () => {
    document.body.getBoundingClientRect();
    await document.fonts.ready;
  });
}

/** The answer to the next `method` request to the api path `path`. Start it before the press that
 * sends the request, and await it after: a step that hashes a password can take longer than an
 * assertion's 5 s on a busy machine, and an assertion should look only once the answer is in. */
export function answerTo(page: Page, path: string, method = "POST") {
  return page.waitForResponse((r) => new URL(r.url()).pathname === path && r.request().method() === method);
}

/** Log in as the demo User of `role` through the «Logg inn» page; waits until the User is on
 * their home. */
export async function loginAs(page: Page, role: DemoRole) {
  const user = DEMO_USERS[role];
  await page.goto("/logg-inn");
  await untilHydrated(page);
  await page.getByLabel(nb.auth.login.email).fill(user.email);
  await page.getByLabel(nb.auth.login.password).fill(DEMO_PASSWORD);
  await page.getByRole("button", { name: nb.auth.login.submit }).click();
  await expect(page).toHaveURL(new RegExp(`${user.home}$`));
  await expect(page.getByRole("button", { name: nb.auth.session.logout })).toBeVisible();
  return user;
}

/** The environment variable through which `global-setup.ts` hands the demo sessions over. */
export const SESSIONS_ENV = "E2E_DEMO_SESSIONS";

type SessionCookie = Awaited<ReturnType<BrowserContext["storageState"]>>["cookies"][number];

/** The session cookie of the demo User of `role`, from the one login `global-setup.ts` made. */
export function demoSession(role: DemoRole): SessionCookie {
  const sessions = JSON.parse(process.env[SESSIONS_ENV] ?? "{}") as Partial<Record<DemoRole, SessionCookie>>;
  const cookie = sessions[role];
  if (!cookie) throw new Error(`no demo session for ${role}: is the global setup configured?`);
  return cookie;
}

/** Log in as `role` without «Logg inn»: the page's browser context takes the demo User's session
 * cookie. Parallel workers share that one session instead of each logging in (see
 * `global-setup.ts`). */
export async function loginByApi(page: Page, role: DemoRole) {
  await page.context().addCookies([demoSession(role)]);
  return DEMO_USERS[role];
}

/** A browser context of its own, logged in as the demo User of `role`, for a second actor. */
export function demoContext(browser: Browser, role: DemoRole): Promise<BrowserContext> {
  return browser.newContext({
    baseURL: test.info().project.use.baseURL,
    storageState: { cookies: [demoSession(role)], origins: [] },
  });
}

export type DevMail = { subject: string; text: string; html: string; sent_at: string };

/** Whatever reads the dev mailbox: a page or a browser context. */
type Mailbox = { request: APIRequestContext };

/** The newest mail sent to `email`, from the local dev mailbox (Story 3.6), or null. Locally every
 * mail is the `[email:mock]` sender, which logs ids only; this route renders the mail again. */
export async function latestMail(page: Mailbox, email: string): Promise<DevMail | null> {
  const response = await page.request.get("/api/dev/mailbox/latest", { params: { to: email } });
  if (response.status() === 404) return null;
  expect(response.status()).toBe(200);
  return (await response.json()) as DevMail;
}

/** Wait for a mail to `email` newer than `before` (the newest mail before the action, or null)
 * and return it. Compares only the worker's own send times, never with this machine's clock. */
export async function nextMail(page: Mailbox, email: string, before: DevMail | null): Promise<DevMail> {
  let mail: DevMail | null = null;
  await expect
    .poll(
      async () => {
        mail = await latestMail(page, email);
        return mail !== null && mail.sent_at !== before?.sent_at;
      },
      { timeout: 15_000, intervals: [200, 300, 500] },
    )
    .toBe(true);
  return mail!;
}
