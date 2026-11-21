import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { expectAccessible, freshClass, freshLecturer, test } from "./support/classes";

/** Information visibility on the Klasseøkt (Story 5.16, cut list, `FEATURE_INFO_VISIBILITY`, FR-83),
 * on the local stack, where the flag is on. Each test makes a fresh Lecturer and Class through the
 * api. The flag-off refusal, the old settings and the lock are pinned by `backend/tests/sessions/
 * test_info_visibility.py`; here the screen. */
const copy = nb.sessions;
const iv = copy.edit.infoVisibility;
const CSRF = { "X-Requested-With": "olspillet" };

async function newSession(lecturer: Page): Promise<string> {
  const klass = await freshClass(lecturer);
  const created = await lecturer.request.post(`/api/classes/${klass.id}/class-sessions`, { headers: CSRF });
  expect(created.status()).toBe(201);
  return (await created.json()).id as string;
}

test("two Bryter, off by default, switch on the upstream view and save", async ({ page, browser }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  await lecturer.goto(`/klasseokter/${id}`);
  const row = lecturer.locator("dl > div").filter({ hasText: copy.settings.infoVisibility });
  await expect(row).toContainText(copy.values.infoVisibilityNone);
  await lecturer.getByRole("button", { name: copy.edit.open }).click();

  const up = lecturer.getByRole("switch", { name: new RegExp(`${iv.legend} ${iv.upstream}`) });
  const down = lecturer.getByRole("switch", { name: new RegExp(`${iv.legend} ${iv.downstream}`) });
  await expect(up).toHaveAttribute("aria-checked", "false");
  await expect(down).toHaveAttribute("aria-checked", "false");
  await expect(lecturer.getByText(iv.help)).toBeVisible();
  // A switch is judged at once; it raises no error and no warning.
  const checked = lecturer.waitForResponse(`**/api/class-sessions/${id}/settings-check`);
  await up.click();
  expect((await (await checked).json()).errors).toEqual({});
  await expect(up).toHaveAttribute("aria-checked", "true");
  await expect(up).toContainText(iv.upstreamOn);
  await expect(down).toHaveAttribute("aria-checked", "false");
  await expectAccessible(lecturer, true);

  await lecturer.getByRole("button", { name: copy.save }).click();
  await expect(lecturer.getByRole("status").filter({ hasText: copy.saved })).toBeVisible();
  const stored = await (await lecturer.request.get(`/api/class-sessions/${id}`)).json();
  expect(stored.game_settings.info_visibility).toEqual({ upstream: true, downstream: false });
  await expect(row).toContainText(copy.values.infoVisibilityUpstream);
  // No longer the Classic preset.
  await expect(lecturer.getByText(copy.defaults)).toHaveCount(0);
  // Opened again, the switch holds the saved view.
  await lecturer.getByRole("button", { name: copy.edit.open }).click();
  await expect(up).toHaveAttribute("aria-checked", "true");
});

test("with the flag off nothing about Information visibility shows", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  // The server's answer with `FEATURE_INFO_VISIBILITY` off; its 422 is pinned by the api tests.
  await lecturer.route(`**/api/class-sessions/${id}`, async (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    const response = await route.fetch();
    await route.fulfill({ response, json: { ...(await response.json()), info_visibility_enabled: false } });
  });
  await lecturer.goto(`/klasseokter/${id}`);
  await expect(lecturer.getByText(copy.settings.startingInventory, { exact: true })).toBeVisible();
  await expect(lecturer.getByText(copy.settings.infoVisibility, { exact: true })).toHaveCount(0);
  await lecturer.getByRole("button", { name: copy.edit.open }).click();
  await expect(lecturer.getByRole("switch", { name: new RegExp(iv.legend) })).toHaveCount(0);
  await expect(lecturer.getByText(iv.help)).toHaveCount(0);
  // A save sends nothing about it.
  const saved = lecturer.waitForRequest(
    (request) => request.method() === "PUT" && request.url().endsWith(`/api/class-sessions/${id}`),
  );
  await lecturer.getByRole("button", { name: copy.save }).click();
  expect((await saved).postDataJSON().game_settings).not.toHaveProperty("info_visibility");
  // A live re-read after the save may still be inside the handler when the test's pages close;
  // its disposed response must not fail the test.
  await lecturer.unrouteAll({ behavior: "ignoreErrors" });
});
