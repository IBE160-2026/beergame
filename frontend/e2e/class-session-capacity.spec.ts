import { expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { expectAccessible, freshClass, freshLecturer } from "./support/classes";

/** A shipping capacity on the Klasseøkt (Story 5.15, cut list, `FEATURE_CAPACITY`, FR-12), on the
 * local stack, where the flag is on. Each test makes a fresh Lecturer and Class through the api.
 * The ranges, the flag-off refusal and the lock are pinned by `backend/tests/sessions/
 * test_capacity.py`; here the screen. */
const copy = nb.sessions;
const c = copy.edit.capacity;
const CSRF = { "X-Requested-With": "olspillet" };

async function newSession(lecturer: Page): Promise<string> {
  const klass = await freshClass(lecturer);
  const created = await lecturer.request.post(`/api/classes/${klass.id}/class-sessions`, { headers: CSRF });
  expect(created.status()).toBe(201);
  return (await created.json()).id as string;
}

test("a capacity below peak demand warns, saves, and marks the capped Role", async ({ page, browser }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  await lecturer.goto(`/klasseokter/${id}`);
  const row = lecturer.locator("dl > div").filter({ hasText: copy.settings.capacity });
  await expect(row).toContainText(copy.values.capacityNone);
  await lecturer.getByRole("button", { name: copy.edit.open }).click();

  // Off by default; on, it offers every Role or one.
  const toggle = lecturer.getByRole("switch", { name: new RegExp(c.legend) });
  await expect(toggle).toHaveAttribute("aria-checked", "false");
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-checked", "true");
  await expect(lecturer.getByText(c.help)).toBeVisible();
  await lecturer.getByRole("radio", { name: c.one }).check();
  await lecturer.getByLabel(c.role, { exact: true }).selectOption("retailer");

  const units = lecturer.getByLabel(c.units, { exact: true });
  await units.fill("0");
  await units.blur();
  await expect(units).toHaveAttribute("aria-invalid", "true");
  await expect(lecturer.getByText(copy.edit.errors.outOfRange("1", "100"))).toBeVisible();
  await units.fill("6");
  const checked = lecturer.waitForResponse(`**/api/class-sessions/${id}/settings-check`);
  await units.blur();
  await checked;
  const warning = copy.edit.warnings.capacity("6", "8");
  await expect(lecturer.getByText(warning)).toBeVisible();
  await expect(units).not.toHaveAttribute("aria-invalid", "true");
  await expectAccessible(lecturer, true);

  await lecturer.getByRole("button", { name: copy.save }).click();
  await expect(lecturer.getByRole("status").filter({ hasText: copy.saved })).toBeVisible();
  const stored = await (await lecturer.request.get(`/api/class-sessions/${id}`)).json();
  expect(stored.game_settings.capacity).toEqual({ retailer: 6 });
  // The list, the warning under it, the help line and «Kjeden ved start» in text.
  await expect(lecturer.getByText("6 per uke for Detaljist")).toBeVisible();
  await expect(lecturer.getByText(warning)).toBeVisible();
  await expect(lecturer.getByText(c.help)).toBeVisible();
  await expect(lecturer.getByText(/Detaljist kan sende høyst 6 per uke\./)).toBeVisible();
  // The drawn mark under the capped Role, beside its text alternative.
  await expect(lecturer.locator("figure svg").getByText(copy.chain.capped(6), { exact: true })).toHaveCount(1);
});

test("with the flag off nothing about capacity shows", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  // The server's answer with `FEATURE_CAPACITY` off; its 422 is pinned by the api tests.
  await lecturer.route(`**/api/class-sessions/${id}`, async (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    const response = await route.fetch();
    await route.fulfill({ response, json: { ...(await response.json()), capacity_enabled: false } });
  });
  await lecturer.goto(`/klasseokter/${id}`);
  await expect(lecturer.getByText(copy.settings.startingInventory, { exact: true })).toBeVisible();
  await expect(lecturer.getByText(copy.settings.capacity, { exact: true })).toHaveCount(0);
  await lecturer.getByRole("button", { name: copy.edit.open }).click();
  await expect(lecturer.getByRole("switch", { name: new RegExp(c.legend) })).toHaveCount(0);
  await expect(lecturer.getByText(c.help)).toHaveCount(0);
  await expect(lecturer.locator("figure svg").getByText(/^Maks /)).toHaveCount(0);
});
