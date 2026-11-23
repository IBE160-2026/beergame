import { expect, type Locator, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { expectAccessible, freshClass, freshLecturer, test } from "./support/classes";

/** «Spørsmål og vekter» on the Klasseøkt (Story 11.1, FR-52, FR-53, UX-DR49), on the local stack:
 * the draft question set with its Vekt fields, «Ta ut» and the Adapted line; the live sum that
 * blocks «Lagre vekter» until it is 100 %; the warning for a quantity item taken out; and the
 * read-only block after the lock (the local-only `POST /api/dev/class-sessions/{id}/lock`). The
 * api's rules (422 `weights_not_100`, 409 `session_locked`, the Assistant's 403, the pin, the
 * production refusal) are pinned by `backend/tests/question_set/test_question_set.py`. */
const copy = nb.tests.questionSet;
const CSRF = { "X-Requested-With": "olspillet" };
const QUANTITY = "startoppgave-sende";
const LONG = "langsvar-forsinkelse";

async function newSession(lecturer: Page): Promise<string> {
  const klass = await freshClass(lecturer);
  const created = await lecturer.request.post(`/api/classes/${klass.id}/class-sessions`, { headers: CSRF });
  expect(created.status()).toBe(201);
  return (await created.json()).id;
}

const block = (page: Page) => page.locator("[data-question-set]");
const row = (page: Page, id: string) => block(page).locator(`[data-question="${id}"]`);
const weight = (r: Locator) => r.getByRole("textbox");
const sum = (page: Page) => block(page).locator("[data-question-sum]");

test("an owner reviews the draft set, the sum blocks the save until 100 % and the save is read back", async ({
  page,
  browser,
}) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  await lecturer.goto(`/klasseokter/${id}`);
  await expect(block(lecturer).getByRole("heading", { name: copy.heading })).toBeVisible();
  await expect(block(lecturer).getByText(copy.draft)).toBeVisible();
  // Each question with its type, its Vekt and «Ta ut»; one line for the Adapted items at 30 %.
  const quantity = row(lecturer, QUANTITY);
  await expect(quantity.getByText(copy.types.number, { exact: false })).toBeVisible();
  await expect(weight(quantity)).toHaveValue("3");
  const title = (await quantity.locator("p").first().textContent()) ?? "";
  await expect(weight(quantity)).toHaveAccessibleName(`${title} ${copy.weight}`);
  await expect(quantity.getByRole("button", { name: copy.takeOut })).toBeVisible();
  const adapted = block(lecturer).locator("[data-question-adapted]");
  await expect(adapted.getByText(copy.adaptedTitle)).toBeVisible();
  await expect(adapted.getByRole("textbox")).toHaveValue("30");
  await expect(sum(lecturer)).toHaveText(copy.sum(100));
  await expect(sum(lecturer)).toHaveAttribute("role", "status");

  // A quantity item out: warned, not blocked, but the sum is 97 % and the save unavailable.
  await quantity.getByRole("button", { name: copy.takeOut }).click();
  await expect(quantity.getByText(copy.takenOut)).toBeVisible();
  await expect(block(lecturer).locator("[data-question-warning]")).toHaveText(copy.quantityWarning);
  await expect(sum(lecturer)).toHaveText(copy.sum(97));
  const save = block(lecturer).getByRole("button", { name: copy.save });
  await expect(save).toHaveAttribute("aria-disabled", "true");
  // A field the api would refuse says so on leaving it.
  await weight(row(lecturer, LONG)).fill("abc");
  await weight(row(lecturer, LONG)).blur();
  await expect(row(lecturer, LONG).getByText(copy.invalidWeight)).toBeVisible();
  // Its 3 % moved to a long answer: 100 %, and the save goes through.
  await weight(row(lecturer, LONG)).fill("13");
  await expect(sum(lecturer)).toHaveText(copy.sum(100));
  await expect(save).not.toHaveAttribute("aria-disabled", "true");
  await save.click();
  await expect(block(lecturer).getByRole("status").filter({ hasText: copy.saved })).toBeVisible();
  const stored = await (await lecturer.request.get(`/api/class-sessions/${id}/question-set`)).json();
  expect(stored.items.find((i: { id: string }) => i.id === QUANTITY).excluded).toBe(true);
  expect(stored.items.find((i: { id: string }) => i.id === LONG).weight).toBe(13);
  await lecturer.reload();
  await expect(weight(row(lecturer, LONG))).toHaveValue("13");
  await expect(row(lecturer, QUANTITY).getByRole("button", { name: copy.putBack })).toBeVisible();
});

test("after the lock the block stands as text and the api refuses a change", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  const locked = await lecturer.request.post(`/api/dev/class-sessions/${id}/lock`, { headers: CSRF });
  expect(locked.status()).toBe(200);
  await lecturer.goto(`/klasseokter/${id}`);
  await expect(block(lecturer).getByText(copy.closed)).toBeVisible();
  await expect(block(lecturer).getByRole("textbox")).toHaveCount(0);
  await expect(block(lecturer).getByRole("button")).toHaveCount(0);
  await expect(row(lecturer, LONG).getByText(copy.weightText(10))).toBeVisible();
  await expect(sum(lecturer)).toHaveText(copy.sum(100));
  const current = await (await lecturer.request.get(`/api/class-sessions/${id}/question-set`)).json();
  const refused = await lecturer.request.put(`/api/class-sessions/${id}/question-set`, {
    data: {
      weights: Object.fromEntries(current.items.map((i: { id: string; weight: number }) => [i.id, i.weight])),
      excluded: [],
      adapted_weight: 30,
    },
    headers: CSRF,
  });
  expect(refused.status()).toBe(409);
  expect((await refused.json()).error.code).toBe("session_locked");
});

test("an Assistant reads the block as text", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  // The server's answer to an Assistant lecturer (`question_set.change` is the owners' only).
  await lecturer.route(`**/api/class-sessions/${id}/question-set`, async (route) => {
    const response = await route.fetch();
    await route.fulfill({ response, json: { ...(await response.json()), can_change: false } });
  });
  try {
    await lecturer.goto(`/klasseokter/${id}`);
    await expect(block(lecturer).getByText(copy.assistant)).toBeVisible();
    await expect(block(lecturer).getByRole("textbox")).toHaveCount(0);
    await expect(row(lecturer, LONG).getByText(copy.weightText(10))).toBeVisible();
  } finally {
    await lecturer.unrouteAll({ behavior: "ignoreErrors" });
  }
});

const SIZES = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
];

for (const vp of SIZES) {
  test.describe(`Spørsmål og vekter, ${vp.name}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("editable, warned and locked pass axe", async ({ page, browser }) => {
      const lecturer = await freshLecturer(page, browser);
      const id = await newSession(lecturer);
      await lecturer.goto(`/klasseokter/${id}`);
      await expect(sum(lecturer)).toHaveText(copy.sum(100));
      if (vp.phone) {
        // One column: the Vekt field sits under its question, as wide as the row.
        const r = row(lecturer, LONG);
        const titleBox = await r.locator("p").first().boundingBox();
        const fieldBox = await weight(r).boundingBox();
        expect(titleBox && fieldBox && fieldBox.y > titleBox.y + titleBox.height - 1).toBe(true);
      }
      await row(lecturer, QUANTITY).getByRole("button", { name: copy.takeOut }).click();
      await expect(block(lecturer).locator("[data-question-warning]")).toHaveText(copy.quantityWarning);
      await expectAccessible(lecturer, vp.phone);

      const locked = await newSession(lecturer);
      expect((await lecturer.request.post(`/api/dev/class-sessions/${locked}/lock`, { headers: CSRF })).status()).toBe(200);
      await lecturer.goto(`/klasseokter/${locked}`);
      await expect(block(lecturer).getByText(copy.closed)).toBeVisible();
      await expectAccessible(lecturer, vp.phone);
    });
  });
}
