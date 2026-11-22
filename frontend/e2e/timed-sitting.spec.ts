import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { loginByApi } from "./support/auth";
import { expectAccessible, freshClass, freshLecturer, test } from "./support/classes";

/** One timed sitting of the Individual test (Story 11.12, FR-51, UX-DR9, UX-DR12, UX-DR49, UX-DR65).
 * The Klasseøkt's block «Tidsgrense på testen» runs on the local stack: switched on with minutes,
 * refused out of range with the range shown, saved with «Lagre Klasseøkt» and read back. The
 * Student's statement with the limit, the running time fixed at the top, the one five-minute line,
 * the time up and the test handed in at the sitting's end use stand-ins with the api's shapes at
 * 360 and 1440 px with axe; the api's rules (the sitting's end, `sitting_ended`, the sweep) are
 * `backend/tests/individual_test/test_timed_sitting.py`. */
const SESSION = "01a1f8ee-33b9-75e6-9502-79db27b37c0e";
const CSRF = { "X-Requested-With": "olspillet" };
const copy = nb.tests.individual;
const timed = copy.timed;
const sitting = nb.tests.sitting;
const DEADLINE = "2099-12-18T22:59:00Z";
const MINUTE = 60_000;

const PLAIN = { table: null, column: null, wording: null, answer: null };
const ITEMS = Array.from({ length: 12 }, (_, i) => ({
  id: `langsvar-${i + 1}`,
  number: i + 1,
  type: "long",
  title: `Utkast: spørsmål ${i + 1}, forklar svingningene ut fra kjedens struktur.`,
  options: [],
  ...PLAIN,
}));

/** The test as the api gives it with the server's clock at `now`, the sitting ending `left` ms later. */
function openTimed(left: number) {
  const now = new Date();
  const ends = new Date(now.getTime() + left).toISOString();
  return {
    state: "open",
    test_deadline: DEADLINE,
    opened_at: new Date(now.getTime() - 20 * MINUTE).toISOString(),
    submitted_at: null,
    items: ITEMS,
    time_limit_minutes: 60,
    sitting_ends_at: ends,
    answering_ends_at: ends,
    server_now: now.toISOString(),
    sitting_ended: false,
  };
}

const statement = {
  state: "statement",
  test_deadline: DEADLINE,
  opened_at: null,
  submitted_at: null,
  items: [],
  time_limit_minutes: 90,
  sitting_ends_at: null,
  answering_ends_at: null,
  server_now: new Date().toISOString(),
  sitting_ended: false,
};

async function standIn(page: Page, json: unknown) {
  await loginByApi(page, "student");
  await page.route(`**/api/me/class-sessions/${SESSION}/test`, (route) => route.fulfill({ status: 200, json }));
  await page.goto(`/individuell-test/${SESSION}`);
}

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

for (const vp of [
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
]) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("the statement names the limit and that the time cannot be paused, before the button; axe passes", async ({ page }) => {
      await standIn(page, statement);
      const section = page.getByRole("main").getByRole("region", { name: copy.statementHeading });
      await expect(section.locator("[data-time-limit]")).toHaveText(timed.limit(90));
      await expect(section).toContainText(timed.howItWorks);
      await expect(section).not.toContainText(copy.howItWorks);
      // The limit comes before the one primary button.
      const limitBox = await section.locator("[data-time-limit]").boundingBox();
      const buttonBox = await section.getByRole("button", { name: copy.accept }).boundingBox();
      expect(limitBox!.y).toBeLessThan(buttonBox!.y);
      await expectAccessible(page, vp.phone);
    });

    test("the time left stands at the top while the Student scrolls, in text; axe passes", async ({ page }) => {
      await standIn(page, openTimed(38 * MINUTE - 5_000));
      const bar = page.locator("[data-time-left]");
      await expect(bar).toHaveText(timed.timeLeft(38));
      // Not a live region, and nothing announced yet.
      await expect(bar.locator("[aria-live], [role=status]")).toHaveCount(0);
      await expect(page.locator("[data-time-warning]")).toHaveText("");
      await expectAccessible(page, vp.phone);
      await page.locator("[data-test-item]").last().scrollIntoViewIfNeeded();
      await expect(bar).toBeInViewport();
      const box = await bar.boundingBox();
      expect(box!.y).toBeLessThanOrEqual(1);
    });

    test("five minutes left: said once, politely; axe passes", async ({ page }) => {
      await standIn(page, openTimed(4 * MINUTE + 30_000));
      await expect(page.locator("[data-time-left]")).toHaveText(timed.timeLeft(5));
      await expect(page.locator("[data-time-warning]")).toHaveText(timed.fiveMinutes);
      await expect(page.locator("[data-time-warning]")).toHaveAttribute("role", "status");
      await expectAccessible(page, vp.phone);
    });

    test("the time is up: said so with focus, the answers read-only; axe passes", async ({ page }) => {
      await standIn(page, openTimed(-30_000));
      const line = page.locator("[data-submitted-line]");
      await expect(line).toHaveText(timed.ended);
      await expect(line).toBeFocused();
      await expect(page.locator("[data-time-left]")).toHaveCount(0);
      await expect(page.getByRole("main").locator("input, textarea")).toHaveCount(0);
      await expect(page.getByRole("button", { name: copy.submit.button })).toHaveCount(0);
      await expectAccessible(page, vp.phone);
    });

    test("handed in by the sweep at the sitting's end: said so; axe passes", async ({ page }) => {
      const ended = openTimed(-10 * MINUTE);
      await standIn(page, { ...ended, state: "auto_submitted", submitted_at: ended.sitting_ends_at, sitting_ended: true });
      await expect(page.locator("[data-submitted-line]")).toHaveText(timed.ended);
      await expect(page.locator("[data-time-left]")).toHaveCount(0);
      await expectAccessible(page, vp.phone);
    });
  });
}

const block = (page: Page) => page.locator("[data-test-sitting]");

test("the Klasseøkt: switched on, refused out of range with the range shown, saved and read back", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const klass = await freshClass(lecturer);
  const created = await lecturer.request.post(`/api/classes/${klass.id}/class-sessions`, { headers: CSRF });
  expect(created.status()).toBe(201);
  const { id, ai_mode } = await created.json();
  await lecturer.goto(`/klasseokter/${id}`);
  const toggle = block(lecturer).getByRole("switch");
  await expect(toggle).toHaveAccessibleName(`${sitting.heading} ${sitting.off}`);
  await expect(toggle).toHaveAttribute("aria-checked", "false");
  await expect(block(lecturer).getByRole("textbox")).toHaveCount(0);
  await expect(block(lecturer)).toContainText(sitting.help);

  await toggle.click();
  await expect(toggle).toHaveAccessibleName(`${sitting.heading} ${sitting.on}`);
  const field = block(lecturer).getByRole("textbox", { name: sitting.minutesLabel });
  await expect(field).toHaveValue("90");
  await expect(block(lecturer)).toContainText(sitting.range(15, 240));
  await field.fill("500");
  await field.blur();
  await expect(block(lecturer).getByRole("alert")).toHaveText(sitting.error(15, 240));
  // Pressed with the wrong value: nothing is sent.
  await lecturer.getByRole("button", { name: nb.sessions.save }).click();
  expect((await (await lecturer.request.get(`/api/class-sessions/${id}`)).json()).test_sitting.minutes).toBeNull();
  await expectAccessible(lecturer, false);

  await field.fill("75");
  await lecturer.getByRole("button", { name: nb.sessions.save }).click();
  await expect(lecturer.getByRole("status").filter({ hasText: nb.sessions.saved })).toBeVisible();
  expect((await (await lecturer.request.get(`/api/class-sessions/${id}`)).json()).test_sitting.minutes).toBe(75);
  await lecturer.reload();
  await expect(block(lecturer).getByRole("switch")).toHaveAttribute("aria-checked", "true");
  await expect(block(lecturer).getByRole("textbox", { name: sitting.minutesLabel })).toHaveValue("75");

  // The api's own refusal names the range too.
  const refused = await lecturer.request.put(`/api/class-sessions/${id}`, {
    data: { ai_mode, test_sitting: { minutes: 5 } },
    headers: CSRF,
  });
  expect(refused.status()).toBe(422);
  expect((await refused.json()).error).toMatchObject({ code: "invalid_session_values", fields: { test_sitting_minutes: "out_of_range" } });
});
