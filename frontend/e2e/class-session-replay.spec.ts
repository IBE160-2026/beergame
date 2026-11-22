import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { expectAccessible, freshClass, freshLecturer, test, VIEWPORTS } from "./support/classes";

/** The Klasseøkt's «Replay-scenario» block (Stories 10.1 and 10.2, FR-49, FR-72, NFR-6), on the
 * local stack. Each test makes a fresh Lecturer and Class through the api. The template's
 * derivation, its pin at the lock, the stored choice, the own template's rules and warnings are
 * pinned by `backend/tests/sessions/test_replay_{scenario,own}.py` and
 * `backend/tests/engine/test_scenario.py`; here the screen. */
const copy = nb.sessions.replay;
const s = nb.sessions;
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

const field = (page: Page, id: string) => page.locator(`input#${id}`);

/** Chooses «Eget scenario» and waits for the api's first judgement (the Classic Guided Weeks). */
async function chooseOwn(page: Page) {
  await block(page).getByRole("radio", { name: copy.own }).check();
  await expect(block(page).getByText(copy.warnings.guided("4"), { exact: false })).toBeVisible();
}

test("an own scenario opens on the Game settings, warns, refuses inline and is saved", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  await lecturer.goto(`/klasseokter/${id}`);
  await expect(block(lecturer).getByRole("radio", { name: copy.standard })).toBeChecked();
  await chooseOwn(lecturer);

  // Prefilled from the Class session's Game settings, the seed aside.
  await expect(field(lecturer, "replay-weeks")).toHaveValue("36");
  await expect(field(lecturer, "replay-weeks-to")).toHaveValue("");
  await expect(field(lecturer, "replay-order_delay")).toHaveValue("2");
  await expect(field(lecturer, "replay-demand-change_week")).toHaveValue("5");
  await expect(lecturer.locator("input#replay-demand-seed")).toHaveCount(0);

  // Out of range: the reason with the range under the field.
  await field(lecturer, "replay-order_delay").fill("9");
  await field(lecturer, "replay-order_delay").blur();
  await expect(block(lecturer).getByText(s.edit.errors.outOfRange("1", "3"))).toBeVisible();

  // Shorter than the Class game's: a warning that names the change; it does not block.
  await field(lecturer, "replay-order_delay").fill("1");
  await field(lecturer, "replay-order_delay").blur();
  const shorter = `${copy.warnings.delay(s.settings.orderDelay, "1", "2")} ${copy.warnings.easier}`;
  await expect(block(lecturer).getByText(shorter)).toBeVisible();
  await expect(block(lecturer).getByText(s.edit.errors.outOfRange("1", "3"))).toHaveCount(0);
  await field(lecturer, "replay-guided_weeks").fill("0");
  await field(lecturer, "replay-weeks").fill("30");
  await field(lecturer, "replay-weeks-to").fill("40");
  await field(lecturer, "replay-weeks-to").blur();
  await expect(block(lecturer).getByText(copy.warnings.guided("4"), { exact: false })).toHaveCount(0);

  await lecturer.getByRole("button", { name: s.save }).click();
  await expect(lecturer.getByText(s.saved)).toBeVisible();

  await lecturer.reload();
  await expect(block(lecturer).getByRole("radio", { name: copy.own })).toBeChecked();
  await expect(field(lecturer, "replay-weeks")).toHaveValue("30");
  await expect(field(lecturer, "replay-weeks-to")).toHaveValue("40");
  await expect(field(lecturer, "replay-order_delay")).toHaveValue("1");
  await expect(block(lecturer).getByText(shorter)).toBeVisible();
  const stored = await (await lecturer.request.get(`/api/class-sessions/${id}`)).json();
  expect([stored.replay_scenario, stored.replay_template.weeks]).toEqual(["own", { minimum: 30, maximum: 40 }]);
});

test("several wrong fields each show their own reason, a reversed range under its second field", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  await lecturer.goto(`/klasseokter/${id}`);
  await chooseOwn(lecturer);
  await field(lecturer, "replay-weeks").fill("40");
  await field(lecturer, "replay-weeks-to").fill("30");
  await field(lecturer, "replay-order_delay").fill("9");
  await field(lecturer, "replay-demand-change_week").fill("99");
  await field(lecturer, "replay-demand-change_week").blur();

  const reversed = s.edit.errors.rangeInverted("40");
  await expect(block(lecturer).getByText(s.edit.errors.outOfRange("1", "3"))).toBeVisible();
  await expect(block(lecturer).getByText(reversed)).toBeVisible();
  await expect(block(lecturer).getByText(/Etterspørselen må endres i en uke fra/)).toBeVisible();
  // The reversed range stands under «høyst», tied to that field, and nowhere says «fra 40 til 30».
  await expect(field(lecturer, "replay-weeks-to")).toHaveAccessibleDescription(new RegExp(reversed));
  await expect(block(lecturer).getByText(s.edit.errors.outOfRange("40", "30"))).toHaveCount(0);
});

test("read only, an own scenario stands as a list with its warnings and no controls", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  const template = { order_delay: 1, weeks: 30, guided_weeks: 0, demand: { kind: "step", start: 4, new_level: 8, change_week: 8, spread: 0 } };
  const saved = await lecturer.request.put(`/api/class-sessions/${id}`, {
    headers: CSRF,
    data: { ai_mode: "rule_based", replay_scenario: "own", replay_template: template },
  });
  expect(saved.status()).toBe(200);
  // As an Assistant lecturer reads it (`can_manage` false).
  await lecturer.route(`**/api/class-sessions/${id}`, async (route) => {
    const response = await route.fetch();
    await route.fulfill({ response, json: { ...(await response.json()), can_manage: false } });
  });
  await lecturer.goto(`/klasseokter/${id}`);
  await expect(block(lecturer).getByText(copy.own, { exact: true })).toBeVisible();
  await expect(block(lecturer).getByRole("radio")).toHaveCount(0);
  await expect(block(lecturer).getByRole("textbox")).toHaveCount(0);
  await expect(row(lecturer, s.settings.orderDelay).first()).toHaveText("1");
  await expect(block(lecturer).getByText(`${copy.warnings.delay(s.settings.orderDelay, "1", "2")} ${copy.warnings.easier}`)).toBeVisible();
  await expect(block(lecturer).getByText(copy.hiddenOwnNone)).toBeVisible();
  await lecturer.unrouteAll({ behavior: "ignoreErrors" });
});

/* Story 10.9 (cut list, `FEATURE_INFO_VISIBILITY`, FR-83): the Replay's own Information visibility.
 * The local stack has the flag on; the flag-off 422, the kept view and the play side are pinned by
 * `backend/tests/sessions/test_replay_info_visibility.py` and `backend/tests/replay/test_info_visibility.py`. */
const iv = s.edit.infoVisibility;
const replaySwitch = (page: Page, label: string) =>
  block(page).getByRole("switch", { name: new RegExp(`${iv.legend} ${label}`) });

test("the Replay's own views open on the Class session's, warn when more, and are saved", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  await lecturer.goto(`/klasseokter/${id}`);
  await chooseOwn(lecturer);
  const up = replaySwitch(lecturer, iv.upstream);
  await expect(up).toHaveAttribute("aria-checked", "false");
  await expect(replaySwitch(lecturer, iv.downstream)).toHaveAttribute("aria-checked", "false");
  await expect(block(lecturer).getByText(copy.infoVisibilityHelp)).toBeVisible();

  // Switched on: judged at once, a warning that names the view; it does not block.
  const checked = lecturer.waitForResponse(`**/api/class-sessions/${id}/replay-scenario-check`);
  await up.click();
  await checked;
  const more = `${copy.warnings.upstreamVisible} ${copy.warnings.easier}`;
  await expect(block(lecturer).getByText(more)).toBeVisible();

  await lecturer.getByRole("button", { name: s.save }).click();
  await expect(lecturer.getByText(s.saved)).toBeVisible();
  const stored = await (await lecturer.request.get(`/api/class-sessions/${id}`)).json();
  expect(stored.replay_template.info_visibility).toEqual({ upstream: true, downstream: false });
  expect(stored.game_settings.info_visibility).toEqual({ upstream: false, downstream: false });
  await lecturer.reload();
  await expect(replaySwitch(lecturer, iv.upstream)).toHaveAttribute("aria-checked", "true");
  await expect(block(lecturer).getByText(more)).toBeVisible();
});

for (const vp of [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
]) {
  test.describe(`the Replay's views with the flag off, ${vp.name}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("show nothing, send nothing and pass axe", async ({ page, browser }) => {
      const lecturer = await freshLecturer(page, browser);
      const id = await newSession(lecturer);
      // The server's answer with `FEATURE_INFO_VISIBILITY` off; its 422 is pinned by the api tests.
      await lecturer.route(`**/api/class-sessions/${id}`, async (route) => {
        if (route.request().method() !== "GET") return route.fallback();
        const response = await route.fetch();
        await route.fulfill({ response, json: { ...(await response.json()), info_visibility_enabled: false } });
      });
      await lecturer.goto(`/klasseokter/${id}`);
      const checked = lecturer.waitForRequest((request) => request.url().endsWith("/replay-scenario-check"));
      await chooseOwn(lecturer);
      expect((await checked).postDataJSON().replay_template).not.toHaveProperty("info_visibility");
      await expect(block(lecturer).getByRole("switch")).toHaveCount(0);
      await expect(block(lecturer).getByText(copy.infoVisibilityHelp)).toHaveCount(0);
      await expect(block(lecturer).getByText(iv.legend, { exact: true })).toHaveCount(0);
      await expectAccessible(lecturer, vp.phone);
      await lecturer.unrouteAll({ behavior: "ignoreErrors" });
    });
  });
}

for (const vp of VIEWPORTS) {
  test.describe(`the own Replay scenario form, ${vp.name}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("passes axe in one column below 1024 px", async ({ page, browser }) => {
      const lecturer = await freshLecturer(page, browser, vp.text200);
      const id = await newSession(lecturer);
      await lecturer.goto(`/klasseokter/${id}`);
      await chooseOwn(lecturer);
      await expectAccessible(lecturer, vp.phone);
      if (vp.width < 1024) {
        const [weeks, to] = [await field(lecturer, "replay-weeks").boundingBox(), await field(lecturer, "replay-weeks-to").boundingBox()];
        expect(to!.y).toBeGreaterThan(weeks!.y);
      }
    });
  });
}
