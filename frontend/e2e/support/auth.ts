import { expect, type Page } from "@playwright/test";

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
} as const;

export type DemoRole = keyof typeof DEMO_USERS;

/** Log in as the demo User of `role` through the «Logg inn» page; waits until the User is on
 * their home. */
export async function loginAs(page: Page, role: DemoRole) {
  const user = DEMO_USERS[role];
  await page.goto("/logg-inn");
  await page.getByLabel(nb.auth.login.email).fill(user.email);
  await page.getByLabel(nb.auth.login.password).fill(DEMO_PASSWORD);
  await page.getByRole("button", { name: nb.auth.login.submit }).click();
  await expect(page).toHaveURL(new RegExp(`${user.home}$`));
  await expect(page.getByRole("button", { name: nb.auth.session.logout })).toBeVisible();
  return user;
}

/** Log in as `role` through the API only: faster when a test does not look at «Logg inn». The
 * cookie lands in the page's browser context. */
export async function loginByApi(page: Page, role: DemoRole) {
  const user = DEMO_USERS[role];
  const response = await page.request.post("/api/auth/login", {
    data: { email: user.email, password: DEMO_PASSWORD },
    headers: { "X-Requested-With": "olspillet" },
  });
  expect(response.status()).toBe(200);
  return user;
}

export type DevMail = { subject: string; text: string; html: string; sent_at: string };

/** The newest mail sent to `email`, from the local dev mailbox (Story 3.6), or null. Locally every
 * mail is the `[email:mock]` sender, which logs ids only; this route renders the mail again. */
export async function latestMail(page: Page, email: string): Promise<DevMail | null> {
  const response = await page.request.get("/api/dev/mailbox/latest", { params: { to: email } });
  if (response.status() === 404) return null;
  expect(response.status()).toBe(200);
  return (await response.json()) as DevMail;
}

/** Wait for a mail to `email` newer than `before` (the newest mail before the action, or null)
 * and return it. Compares only the worker's own send times, never with this machine's clock. */
export async function nextMail(page: Page, email: string, before: DevMail | null): Promise<DevMail> {
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
