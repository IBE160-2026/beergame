import { expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { expectAccessible, freshClass, freshLecturer } from "./support/classes";

/** Changing the Game settings on the Klasseøkt (Story 5.3, FR-12, NFR-6, UX-DR48), on the local
 * stack. Each test makes a fresh Lecturer and Class through the api. Every range error and warning
 * is pinned through the routes by `backend/tests/sessions/test_settings.py`; here the screen. */
const copy = nb.sessions;
const edit = copy.edit;
const CSRF = { "X-Requested-With": "olspillet" };

async function openSession(lecturer: Page): Promise<string> {
  const klass = await freshClass(lecturer);
  const created = await lecturer.request.post(`/api/classes/${klass.id}/class-sessions`, { headers: CSRF });
  expect(created.status()).toBe(201);
  const id = (await created.json()).id as string;
  await lecturer.goto(`/klasseokter/${id}`);
  return id;
}

const field = (page: Page, label: string) => page.getByLabel(label, { exact: true });

test("an out-of-range delay is shown on leaving the field and blocks the save", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await openSession(lecturer);
  await lecturer.getByRole("button", { name: edit.open }).click();
  // The block opens in place with focus on the first field.
  await expect(field(lecturer, copy.settings.startingInventory)).toBeFocused();
  await expect(field(lecturer, copy.settings.holdingCost)).toHaveValue("0,50");

  const delay = field(lecturer, copy.settings.orderDelay);
  await delay.fill("4");
  const checked = lecturer.waitForResponse(`**/api/class-sessions/${id}/settings-check`);
  await delay.blur();
  await checked;
  await expect(delay).toHaveAttribute("aria-invalid", "true");
  await expect(delay).toHaveAccessibleDescription(edit.errors.outOfRange("1", "3"));
  // A Demand-pattern rule another field breaks (the demand change after the last Week) stands
  // under the change Week's field (Story 5.4).
  const weeks = field(lecturer, copy.settings.weeks);
  const outside = edit.errors.demandChangeOutside("1", "4");
  await weeks.fill("4");
  await weeks.blur();
  await expect(field(lecturer, edit.demand.changeWeek)).toHaveAccessibleDescription(outside);
  await weeks.fill("36");
  await weeks.blur();
  await expect(lecturer.getByText(outside)).toHaveCount(0);

  await lecturer.getByRole("button", { name: copy.save }).click();
  await expect(lecturer.getByRole("alert").filter({ hasText: edit.refused })).toBeVisible();
  await expect(delay).toHaveValue("4");
  const stored = await (await lecturer.request.get(`/api/class-sessions/${id}`)).json();
  expect(stored.game_settings.order_delay).toBe(2);
});

test("a warning never blocks, and a saved change redraws the chain and names the calibration", async ({
  page,
  browser,
}) => {
  const lecturer = await freshLecturer(page, browser);
  await openSession(lecturer);
  await expect(lecturer.getByText(copy.defaults)).toBeVisible();
  await lecturer.getByRole("button", { name: edit.open }).click();

  const backorder = field(lecturer, copy.settings.backorderCost);
  await backorder.fill("0,50");
  await backorder.blur();
  const warning = edit.warnings.backorder("0,50", "0,50");
  await expect(lecturer.getByText(warning)).toBeVisible();
  await expect(backorder).not.toHaveAttribute("aria-invalid", "true");
  // Read with the field, after its hint.
  await expect(backorder).toHaveAccessibleDescription(`${edit.costHint} ${warning}`);
  await field(lecturer, copy.settings.startingInventory).fill("15");

  await lecturer.getByRole("button", { name: copy.save }).click();
  await expect(lecturer.getByRole("status").filter({ hasText: copy.saved })).toBeVisible();
  await expect(lecturer.getByText(copy.defaults)).toHaveCount(0);
  await expect(
    lecturer.getByRole("heading", {
      name: copy.settingsTitleChanged,
      exact: true,
    }),
  ).toBeVisible();
  await expect(lecturer.getByText(/kalibrert for Klassisk: Startlager 12/)).toBeVisible();
  await expect(lecturer.getByText(/starter med Lager 15 hver/)).toBeVisible();
  // The save closes the block: the list holds the saved values and the warning under its setting.
  await expect(field(lecturer, copy.settings.backorderCost)).toHaveCount(0);
  await expect(lecturer.getByText(warning)).toBeVisible();
  await expect(lecturer.getByRole("button", { name: edit.open })).toBeVisible();

  // Opened again and cancelled, focus returns to the opener.
  await lecturer.getByRole("button", { name: edit.open }).click();
  await lecturer.getByRole("button", { name: edit.cancel }).click();
  await expect(lecturer.getByRole("button", { name: edit.open })).toBeFocused();

  // The note on the delay sources speaks of Classic's delays: it goes with them (Issue #101).
  await expect(lecturer.getByText(copy.delaySources)).toBeVisible();
  await lecturer.getByRole("button", { name: edit.open }).click();
  await field(lecturer, copy.settings.shippingDelay).fill("3");
  await lecturer.getByRole("button", { name: copy.save }).click();
  await expect(lecturer.getByRole("status").filter({ hasText: copy.saved })).toBeVisible();
  await expect(lecturer.getByText(copy.delaySources)).toHaveCount(0);
});

test("a session that has started shows the settings read-only", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const klass = await freshClass(lecturer);
  const created = await lecturer.request.post(`/api/classes/${klass.id}/class-sessions`, { headers: CSRF });
  const id = (await created.json()).id as string;
  // The server's answer after the Start date; the 409 itself is pinned by the api tests.
  await lecturer.route(`**/api/class-sessions/${id}`, async (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    const response = await route.fetch();
    await route.fulfill({
      response,
      json: { ...(await response.json()), locked: true },
    });
  });
  await lecturer.goto(`/klasseokter/${id}`);
  await expect(lecturer.getByText(nb.sessions.lock.pending)).toBeVisible();
  await expect(lecturer.getByRole("button", { name: edit.open })).toHaveCount(0);
  await expect(lecturer.getByRole("textbox", { name: copy.settings.orderDelay })).toHaveCount(0);
});

const SIZES = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
  // 1280 × 800 at 400 % zoom lays out as 320 × 200 CSS px.
  { name: "400 % zoom", width: 320, height: 200, phone: true },
];

for (const vp of SIZES) {
  test.describe(`the settings block, ${vp.name}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("passes axe with an error and a warning showing", async ({ page, browser }) => {
      const lecturer = await freshLecturer(page, browser);
      const id = await openSession(lecturer);
      await lecturer.getByRole("button", { name: edit.open }).click();
      await field(lecturer, copy.settings.shippingDelay).fill("4");
      await field(lecturer, copy.settings.supplyLine).fill("5");
      const checked = lecturer.waitForResponse(`**/api/class-sessions/${id}/settings-check`);
      await field(lecturer, copy.settings.supplyLine).blur();
      await checked;
      await expect(lecturer.getByText(edit.errors.outOfRange("1", "3"))).toBeVisible();
      await expect(lecturer.getByText(edit.warnings.supplyLine("5", "4"))).toBeVisible();
      await expectAccessible(lecturer, vp.phone);
    });
  });
}
