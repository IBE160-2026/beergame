import { expect, type Page } from "@playwright/test";

import { nb } from "../../src/copy/nb";

/**
 * The test login for Playwright tests and visual checks (Story 3.2). The local stack
 * (`docker compose`, `APP_ENV=local`) seeds these accounts on an empty database
 * (`backend/app/modules/identity/seed.py`); the README lists them too. Role → account.
 */
export const DEMO_PASSWORD = "olspillet-demo";

export const DEMO_USERS = {
  admin: { email: "admin@example.com", name: "Demo Admin" },
  lecturer: { email: "faglaerer@example.com", name: "Demo Faglærer" },
} as const;

export type DemoRole = keyof typeof DEMO_USERS;

/** Log in as the demo User of `role` through the «Logg inn» page; waits until the User is in. */
export async function loginAs(page: Page, role: DemoRole) {
  const user = DEMO_USERS[role];
  await page.goto("/logg-inn");
  await page.getByLabel(nb.auth.login.email).fill(user.email);
  await page.getByLabel(nb.auth.login.password).fill(DEMO_PASSWORD);
  await page.getByRole("button", { name: nb.auth.login.submit }).click();
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
