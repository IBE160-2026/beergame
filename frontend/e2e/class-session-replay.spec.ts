import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { expectAccessible, freshClass, freshLecturer, test } from "./support/classes";

/** The Klasseøkt's «Replay-scenario» block (Story 10.1, FR-49, FR-72, NFR-6), on the local stack.
 * Each test makes a fresh Lecturer and Class through the api. The template's derivation, its pin
 * at the lock and the stored choice are pinned by `backend/tests/sessions/test_replay_scenario.py`
 * and `backend/tests/engine/test_scenario.py`; here the screen. */
const copy = nb.sessions.replay;
const CSRF = { "X-Requested-With": "olspillet" };

async function newSession(lecturer: Page): Promise<string> {
  const klass = await freshClass(lecturer);
  const created = await lecturer.request.post(`/api/classes/${klass.id}/class-sessions`, { headers: CSRF });
  expect(created.status()).toBe(201);
  return (await created.json()).id as string;
}

const block = (page: Page) => page.getByRole("region", { name: copy.title });

/** The value next to a row's label in the block's list. */
const row = (page: Page, label: string) =>
  block(page).locator("div", { has: page.getByRole("term").filter({ hasText: label }) }).getByRole("definition");

test("the block describes the default scenario from the Game settings as they stand", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  await lecturer.goto(`/klasseokter/${id}`);

  await expect(block(lecturer).getByText(copy.standard, { exact: true })).toBeVisible();
  await expect(row(lecturer, copy.demand)).toHaveText(copy.spread(copy.stepDemand(4, 8), 2));
  await expect(row(lecturer, copy.changeWeek)).toHaveText(copy.weekRange(5, 12));
  await expect(row(lecturer, copy.weeks)).toHaveText(copy.range(30, 40));
  await expect(row(lecturer, copy.guidedWeeks)).toHaveText(copy.none);
  await expect(block(lecturer).getByText(copy.hiddenBoth)).toBeVisible();

  // Edited before the Start date: the block follows the new settings (a larger spread is kept).
  const saved = await lecturer.request.put(`/api/class-sessions/${id}`, {
    headers: CSRF,
    data: {
      ai_mode: "rule_based",
      game_settings: { demand: { kind: "random", mean: 6, spread: 3 }, demand_seed: 1 },
    },
  });
  expect(saved.status()).toBe(200);
  await lecturer.reload();
  await expect(row(lecturer, copy.demand)).toHaveText(copy.spread(copy.randomDemand(6), 3));
  await expect(block(lecturer).getByRole("term").filter({ hasText: copy.changeWeek })).toHaveCount(0);
  await expect(block(lecturer).getByText(copy.hiddenWeeks)).toBeVisible();
});

for (const vp of [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
]) {
  test.describe(`the Replay block, ${vp.name}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("passes axe", async ({ page, browser }) => {
      const lecturer = await freshLecturer(page, browser);
      const id = await newSession(lecturer);
      await lecturer.goto(`/klasseokter/${id}`);
      await expect(row(lecturer, copy.weeks)).toHaveText(copy.range(30, 40));
      await expectAccessible(lecturer, vp.phone);
    });
  });
}
