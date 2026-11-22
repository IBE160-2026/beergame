import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { expectAccessible, freshClass, freshLecturer, test } from "./support/classes";

/** Marking the Klasseøkt obligatory with its required share, and setting «Ventetid før KI tar
 * over» (Story 5.7, FR-17, FR-36, UX-DR12, UX-DR48, UX-DR49, UX-DR78), on the local stack. Each
 * test makes a fresh Lecturer and Class through the api. The rules, the lock, the notices and the
 * digest mail are pinned through the routes by `backend/tests/sessions/test_obligatory.py`; here
 * the screen. */
/** The Klasseøkt's setting switches: the Debrief quiz's own (Story 9.10, read through the real
 * api, so the Lecturer may exclude) and KI-vurdering (Story 12.1, open until the Testfrist) are
 * left out. */
const settingSwitches = (page: Page) =>
  page.locator("[role='switch']:not([data-quiz-exclusions] [role='switch']):not([data-ai-assessment] [role='switch'])");

const copy = nb.sessions;
const c = copy.choices;
const CSRF = { "X-Requested-With": "olspillet" };

async function newSession(lecturer: Page): Promise<string> {
  const klass = await freshClass(lecturer);
  const created = await lecturer.request.post(`/api/classes/${klass.id}/class-sessions`, { headers: CSRF });
  expect(created.status()).toBe(201);
  return (await created.json()).id as string;
}

async function stored(lecturer: Page, id: string) {
  return (await lecturer.request.get(`/api/class-sessions/${id}`)).json();
}

/** The session as the server would answer in another state; the api tests pin the real one. */
async function answerWith(lecturer: Page, id: string, changes: Record<string, unknown>) {
  await lecturer.route(`**/api/class-sessions/${id}`, async (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    const response = await route.fetch();
    await route.fulfill({ response, json: { ...(await response.json()), ...changes } });
  });
}

/** Counts the saves the page sends. */
function countSaves(lecturer: Page, id: string): () => number {
  let saves = 0;
  lecturer.on("request", (request) => {
    if (request.method() === "PUT" && request.url().endsWith(`/api/class-sessions/${id}`)) saves += 1;
  });
  return () => saves;
}

const bryter = (page: Page) => page.getByRole("switch", { name: new RegExp(`^${c.obligatory}`) });
const share = (page: Page) => page.getByRole("textbox", { name: c.share });
const ventetid = (page: Page) => page.getByRole("textbox", { name: nb.terms.inactivityLimit });

test("Obligatorisk is switched on by keyboard, with its share, and takes effect on save", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  await lecturer.goto(`/klasseokter/${id}`);

  const toggle = bryter(lecturer);
  await expect(toggle).toHaveAttribute("aria-checked", "false");
  await expect(toggle).toHaveAccessibleName(`${c.obligatory} ${c.obligatoryNo}`);
  await expect(share(lecturer)).toHaveCount(0);
  // Space on the focused Bryter: on, with its label as the whole confirmation and no dialog.
  await toggle.focus();
  await lecturer.keyboard.press("Space");
  await expect(toggle).toHaveAttribute("aria-checked", "true");
  await expect(toggle).toHaveAccessibleName(`${c.obligatory} ${c.obligatoryYes}`);
  await expect(toggle).toHaveAccessibleDescription(c.obligatoryHelp);
  await expect(lecturer.getByRole("dialog")).toHaveCount(0);
  await expect(share(lecturer)).toHaveValue("80");
  // Enter toggles it too.
  await lecturer.keyboard.press("Enter");
  await expect(toggle).toHaveAttribute("aria-checked", "false");
  await lecturer.keyboard.press("Enter");
  await expect(toggle).toHaveAttribute("aria-checked", "true");
  // The tap target is 44 px at least.
  expect((await toggle.boundingBox())?.height).toBeGreaterThanOrEqual(44);
  // Nothing is stored before «Lagre Klasseøkt».
  expect((await stored(lecturer, id)).obligatory).toBe(false);

  await share(lecturer).fill("75");
  await lecturer.getByRole("button", { name: copy.save }).click();
  await expect(lecturer.getByRole("status").filter({ hasText: copy.saved })).toBeVisible();
  const after = await stored(lecturer, id);
  expect([after.obligatory, after.required_share_percent]).toEqual([true, 75]);
  await lecturer.reload();
  await expect(bryter(lecturer)).toHaveAttribute("aria-checked", "true");
  await expect(share(lecturer)).toHaveValue("75");

  // Off again by a press; the stored share stays.
  await bryter(lecturer).click();
  await expect(share(lecturer)).toHaveCount(0);
  await lecturer.getByRole("button", { name: copy.save }).click();
  await expect(lecturer.getByRole("status").filter({ hasText: copy.saved })).toBeVisible();
  const off = await stored(lecturer, id);
  expect([off.obligatory, off.required_share_percent]).toEqual([false, 75]);
});

test("a share out of range is refused inline and nothing is sent", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  const saves = countSaves(lecturer, id);
  await lecturer.goto(`/klasseokter/${id}`);
  await bryter(lecturer).click();
  for (const value of ["0", "101", "80,5", ""]) {
    await share(lecturer).fill(value);
    await share(lecturer).blur();
    await expect(share(lecturer)).toHaveAccessibleDescription(`${c.shareHint} ${c.shareError}`);
  }
  await lecturer.getByRole("button", { name: copy.save }).click();
  await expect(share(lecturer)).toHaveAttribute("aria-invalid", "true");
  expect(saves()).toBe(0);
  await share(lecturer).fill("100");
  await share(lecturer).blur();
  await expect(share(lecturer)).not.toHaveAttribute("aria-invalid", "true");
});

test("«Ventetid før KI tar over» takes whole hours from 20 and says why otherwise", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  const saves = countSaves(lecturer, id);
  await lecturer.goto(`/klasseokter/${id}`);
  // Closed, the list says the stored limit.
  await expect(lecturer.getByText(copy.values.inactivityLimit(24))).toBeVisible();
  await lecturer.getByRole("button", { name: copy.edit.open }).click();
  const field = ventetid(lecturer);
  await expect(field).toHaveValue("24");
  // The help line is always there.
  await expect(field).toHaveAccessibleDescription(copy.edit.inactivityHint);

  for (const value of ["19", "2,5", ""]) {
    await field.fill(value);
    await field.blur();
    await expect(lecturer.getByRole("alert").filter({ hasText: copy.edit.inactivityError })).toBeVisible();
    await expect(field).toHaveAttribute("aria-invalid", "true");
  }
  // Pressing the button with a wrong value sends nothing.
  await field.fill("12");
  await lecturer.getByRole("button", { name: copy.save }).click();
  await expect(lecturer.getByRole("alert").filter({ hasText: copy.edit.inactivityError })).toBeVisible();
  expect(saves()).toBe(0);

  await field.fill("48");
  await field.blur();
  await expect(lecturer.getByRole("alert").filter({ hasText: copy.edit.inactivityError })).toHaveCount(0);
  await lecturer.getByRole("button", { name: copy.save }).click();
  await expect(lecturer.getByRole("status").filter({ hasText: copy.saved })).toBeVisible();
  expect((await stored(lecturer, id)).inactivity_limit_hours).toBe(48);
  await expect(lecturer.getByText(copy.values.inactivityLimit(48))).toBeVisible();
});

test("the api's refusal of the values shows under the field", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  await lecturer.route(`**/api/class-sessions/${id}`, async (route) => {
    if (route.request().method() !== "PUT") return route.fallback();
    await route.fulfill({
      status: 422,
      json: {
        error: {
          code: "invalid_session_values",
          message: "x",
          fields: { required_share_percent: "out_of_range" },
        },
      },
    });
  });
  await lecturer.goto(`/klasseokter/${id}`);
  await bryter(lecturer).click();
  await lecturer.getByRole("button", { name: copy.save }).click();
  await expect(lecturer.getByRole("alert").filter({ hasText: c.valuesRefused })).toBeVisible();
  await expect(share(lecturer)).toHaveAttribute("aria-invalid", "true");
  await expect(bryter(lecturer)).toHaveAttribute("aria-checked", "true");
});

test("a session that has started shows the mark, the share and the limit as text", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  await answerWith(lecturer, id, { locked: true, obligatory: true, required_share_percent: 70 });
  await lecturer.goto(`/klasseokter/${id}`);
  await expect(settingSwitches(lecturer)).toHaveCount(0);
  await expect(lecturer.getByText(c.obligatoryYes, { exact: true })).toBeVisible();
  await expect(lecturer.getByText(c.shareValue(70))).toBeVisible();
  await expect(lecturer.getByRole("button", { name: copy.edit.open })).toHaveCount(0);
  await expect(ventetid(lecturer)).toHaveCount(0);
  await expect(lecturer.getByText(copy.values.inactivityLimit(24))).toBeVisible();
});

test("an Assistant reads the mark and the share as text, with no control", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  await answerWith(lecturer, id, { can_manage: false, obligatory: true, required_share_percent: 90 });
  await lecturer.goto(`/klasseokter/${id}`);
  await expect(lecturer.getByText(c.shareValue(90))).toBeVisible();
  await expect(settingSwitches(lecturer)).toHaveCount(0);
  await expect(share(lecturer)).toHaveCount(0);
  await expect(lecturer.getByRole("button", { name: copy.edit.open })).toHaveCount(0);
  await expect(lecturer.getByRole("button", { name: copy.save })).toHaveCount(0);
});

const SIZES = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
  // 1280 × 800 at 400 % zoom lays out as 320 × 200 CSS px.
  { name: "400 % zoom", width: 320, height: 200, phone: true },
];

for (const vp of SIZES) {
  test.describe(`Obligatorisk and Ventetid, ${vp.name}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("pass axe with the Bryter on, the share and an error under the Ventetid", async ({ page, browser }) => {
      const lecturer = await freshLecturer(page, browser);
      const id = await newSession(lecturer);
      await lecturer.goto(`/klasseokter/${id}`);
      await bryter(lecturer).click();
      await expect(share(lecturer)).toBeVisible();
      await lecturer.getByRole("button", { name: copy.edit.open }).click();
      await ventetid(lecturer).fill("19");
      await ventetid(lecturer).blur();
      await expect(lecturer.getByRole("alert").filter({ hasText: copy.edit.inactivityError })).toBeVisible();
      await expectAccessible(lecturer, vp.phone);
    });
  });
}
