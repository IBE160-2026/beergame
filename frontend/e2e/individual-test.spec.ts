import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { loginByApi } from "./support/auth";
import { expectAccessible, test } from "./support/classes";
import { liveClassGame } from "./support/live-game";

/** Open the Individual test with the own-work statement (Story 11.3, FR-51, FR-5, NFR-6, UX-DR9,
 * UX-DR65) and answer its multiple-choice items with autosave (Story 11.4, FR-52, AD-10,
 * UX-DR76). The locked, statement, open and closed states at 320, 360 and 1440 px with axe use
 * stand-ins with the api's shapes; the gate, the one attempt and the closed follow-up are
 * `backend/tests/individual_test/test_open.py`. The last test runs on the stack, with no stand-in:
 * a fresh Class game, the Student's steps up to the Replay through the local dev route, Stegene's
 * test step, the statement, the open test, and a reload that does not ask again. */
const SESSION = "01a1f8ee-33b9-75e6-9502-79db27b37c0e";
const CSRF = { "X-Requested-With": "olspillet" };
const copy = nb.tests.individual;
const DEADLINE = "2026-12-18T22:59:00Z";
const ITEMS = [
  { id: "flervalg-1", number: 1, type: "choice", title: "Utkast: hva er et lager?", options: ["a", "b", "c"], answer: null },
  { id: "kolonne-1", number: 2, type: "table", title: "Utkast: fyll inn kolonnen for bakeriet.", options: [], answer: null },
  { id: "langsvar-1", number: 3, type: "long", title: "Utkast: forklar svingningene ut fra kjedens struktur.", options: [], answer: null },
] as const;
const SAVED_AT = "2026-11-22T20:14:00Z"; // «Lagret 21:14» in Oslo

const VIEWPORTS = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
];

const statement = { state: "statement", test_deadline: DEADLINE, opened_at: null, items: [] };
const opened = { state: "open", test_deadline: DEADLINE, opened_at: "2026-11-22T10:00:00Z", items: ITEMS };

/** The Student's page with the api's answer stood in: one GET, and the POST when `onOpen` is given. */
async function standIn(page: Page, answer: { status: number; json: unknown }, onOpen?: { status: number; json: unknown }) {
  await loginByApi(page, "student");
  await page.route(`**/api/me/class-sessions/${SESSION}/test`, (route) =>
    route.request().method() === "POST" && onOpen ? route.fulfill(onOpen) : route.fulfill(answer),
  );
  await page.goto(`/individuell-test/${SESSION}`);
}

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

for (const vp of VIEWPORTS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("before the Replay: the lock line and the way home; axe passes", async ({ page }) => {
      await standIn(page, { status: 403, json: { error: { code: "replay_required", message: "x", fields: {} } } });
      const main = page.getByRole("main");
      await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.title);
      await expect(main.locator("[data-test-state=locked]")).toHaveText(nb.homes.student.locked.test);
      await expect(main.getByRole("button")).toHaveCount(0);
      await expectAccessible(page, vp.phone);
    });

    test("the own-work statement first, one primary named by its effect, then the items with focus; axe passes", async ({ page }) => {
      await standIn(page, { status: 200, json: statement }, { status: 201, json: opened });
      const main = page.getByRole("main");
      const section = main.getByRole("region", { name: copy.statementHeading });
      await expect(section).toContainText(copy.statement);
      await expect(section).toContainText(/^.*Testfrist fr\. 18\. des\. kl\.\s23:59\./u);
      await expect(main.locator("[data-test-item]")).toHaveCount(0);
      await expect(main.locator("a.bg-ink, button.bg-ink")).toHaveCount(1);
      const accept = main.getByRole("button", { name: copy.accept });
      await expect(accept).toHaveClass(/\bbg-ink\b/);
      await expectAccessible(page, vp.phone);

      await accept.click();
      const heading = main.getByRole("heading", { name: copy.itemsHeading });
      await expect(heading).toBeFocused();
      await expect(main.getByRole("region", { name: copy.statementHeading })).toHaveCount(0);
      const items = main.locator("[data-test-item]");
      await expect(items).toHaveCount(ITEMS.length);
      await expect(items.nth(0).getByRole("heading", { level: 3 })).toHaveText(`${copy.item(1)}${copy.types.choice}`);
      await expect(items.nth(2)).toContainText(copy.types.long);
      await expect(items.nth(2)).toContainText(ITEMS[2].title);
      await expectAccessible(page, vp.phone);
    });

    test("a refused open stays in words under the active button", async ({ page }) => {
      await standIn(
        page,
        { status: 200, json: statement },
        { status: 409, json: { error: { code: "test_deadline_passed", message: "x", fields: {} } } },
      );
      const accept = page.getByRole("button", { name: copy.accept });
      await accept.click();
      await expect(page.getByRole("main").getByRole("alert")).toHaveText(copy.errors.test_deadline_passed);
      await expect(accept).not.toHaveAttribute("aria-disabled", "true");
    });

    test("after the Testfrist with no attempt: not handed in; axe passes", async ({ page }) => {
      await standIn(page, { status: 200, json: { ...statement, state: "closed" } });
      const main = page.getByRole("main");
      await expect(main.locator("[data-test-state=closed]")).toHaveText(copy.closed);
      await expect(main.getByRole("button")).toHaveCount(0);
      await expectAccessible(page, vp.phone);
    });

    test("a multiple-choice item: idle, selected, saved and save-failed by keyboard, 44 px rows; axe passes", async ({ page }) => {
      // Each save waits for the test to let it through, so the selected state is seen before it is stored.
      const saves: { value: string; revision: number }[] = [];
      let answer: { status: number; json: unknown } = { status: 200, json: {} };
      let release: () => void = () => {};
      await page.route(`**/api/me/class-sessions/${SESSION}/test/answers/*`, async (route) => {
        const body = route.request().postDataJSON() as { value: string; revision: number };
        saves.push(body);
        await new Promise<void>((go) => (release = go));
        const reply = answer.status === 200 ? { status: 200, json: { item_id: "flervalg-1", ...body, saved_at: SAVED_AT } } : answer;
        await route.fulfill(reply);
      });
      await standIn(page, { status: 200, json: opened });
      const item = page.locator("[data-test-item=flervalg-1]");
      const group = item.getByRole("group", { name: ITEMS[0].title });
      const status = item.getByRole("status");
      const radios = group.getByRole("radio");

      // Idle: three options, none chosen, nothing said; each row a 44 px tap target.
      await expect(radios).toHaveCount(3);
      await expect(group.getByRole("radio", { name: copy.option("b") })).toBeVisible();
      for (const box of await item.locator("[data-quiz-option]").all()) {
        expect((await box.boundingBox())!.height).toBeGreaterThanOrEqual(44);
      }
      await expect(group.getByRole("radio", { checked: true })).toHaveCount(0);
      await expect(status).toHaveText("");
      await expect(item).not.toContainText(nb.quizChoice.right);
      await expectAccessible(page, vp.phone);

      // Selected by keyboard alone, before the api has stored it.
      await radios.first().focus();
      await page.keyboard.press("Space");
      await expect(radios.first()).toBeChecked();
      await expect.poll(() => saves.length).toBe(1);
      await expectAccessible(page, vp.phone);

      // Saved: «Lagret 21:14», in the polite status region, focus left where it was.
      release();
      await expect(status).toHaveText(copy.saved("21:14"));
      await expect(radios.first()).toBeFocused();
      expect(saves[0]).toEqual({ value: "a", revision: 1 });
      await expectAccessible(page, vp.phone);

      // Save failed: the spine's line, the choice kept on this device.
      answer = { status: 503, json: { error: { code: "unavailable", message: "x", fields: {} } } };
      await page.keyboard.press("ArrowDown");
      await expect(radios.nth(1)).toBeChecked();
      await expect.poll(() => saves.length).toBe(2);
      release();
      await expect(status).toHaveText(copy.notSaved);
      await expect(radios.nth(1)).toBeChecked();
      expect(saves[1]).toEqual({ value: "b", revision: 2 });
      // No right or wrong state in any state before the AI assessment (FR-54).
      await expect(item).not.toContainText(nb.quizChoice.right);
      await expect(item).not.toContainText(nb.quizChoice.wrong);
      await expect(item.locator("[data-quiz-mark]")).toHaveCount(0);
      await expectAccessible(page, vp.phone);

      // Back online: the same answer is sent again and stored.
      answer = { status: 200, json: {} };
      await page.evaluate(() => window.dispatchEvent(new Event("online")));
      await expect.poll(() => saves.length).toBe(3);
      release();
      await expect(status).toHaveText(copy.saved("21:14"));
      expect(saves[2]).toEqual({ value: "b", revision: 2 });
    });
  });
}

test("an answer not stored is kept on this device through a reload and sent until it is", async ({ page }) => {
  const saves: { value: string; revision: number }[] = [];
  let failing = true;
  await page.route(`**/api/me/class-sessions/${SESSION}/test/answers/*`, async (route) => {
    const body = route.request().postDataJSON() as { value: string; revision: number };
    saves.push(body);
    if (failing) await route.abort("internetdisconnected");
    else await route.fulfill({ status: 200, json: { item_id: "flervalg-1", ...body, saved_at: SAVED_AT } });
  });
  await standIn(page, { status: 200, json: opened });
  const item = page.locator("[data-test-item=flervalg-1]");
  await item.getByRole("radio", { name: copy.option("c") }).check();
  await expect(item.getByRole("status")).toHaveText(copy.notSaved);

  failing = false;
  await page.reload();
  // The api still has no answer; the draft shows and goes at once.
  await expect(item.getByRole("radio", { name: copy.option("c") })).toBeChecked();
  await expect(item.getByRole("status")).toHaveText(copy.saved("21:14"));
  expect(saves.at(-1)).toEqual({ value: "c", revision: 1 });
});

test("a change made while a save runs goes after it, and a failed save is tried again after 5 s", async ({ page }) => {
  await page.clock.install();
  const saves: { value: string; revision: number }[] = [];
  const held: (() => void)[] = [];
  let failNext = false;
  await page.route(`**/api/me/class-sessions/${SESSION}/test/answers/*`, async (route) => {
    const body = route.request().postDataJSON() as { value: string; revision: number };
    saves.push(body);
    if (failNext) {
      failNext = false;
      await route.fulfill({ status: 503, json: { error: { code: "unavailable", message: "x", fields: {} } } });
      return;
    }
    await new Promise<void>((go) => held.push(go));
    await route.fulfill({ status: 200, json: { item_id: "flervalg-1", ...body, saved_at: SAVED_AT } });
  });
  await standIn(page, { status: 200, json: opened });
  const item = page.locator("[data-test-item=flervalg-1]");
  const status = item.getByRole("status");

  // A, then B before A is stored: one save at a time, B (revision 2) sent once A returns.
  await item.getByRole("radio", { name: copy.option("a") }).check();
  await expect.poll(() => saves.length).toBe(1);
  await item.getByRole("radio", { name: copy.option("b") }).check();
  held.shift()!();
  await expect.poll(() => saves.length).toBe(2);
  expect(saves).toEqual([
    { value: "a", revision: 1 },
    { value: "b", revision: 2 },
  ]);
  held.shift()!();
  await expect(status).toHaveText(copy.saved("21:14"));
  await expect(item.getByRole("radio", { name: copy.option("b") })).toBeChecked();

  // C fails once; with no online event and no reload, it goes again after RETRY_MS.
  failNext = true;
  await item.getByRole("radio", { name: copy.option("c") }).check();
  await expect(status).toHaveText(copy.notSaved);
  expect(saves).toHaveLength(3);
  await page.clock.fastForward(5_000);
  await expect.poll(() => saves.length).toBe(4);
  expect(saves[3]).toEqual({ value: "c", revision: 3 });
  held.shift()!();
  await expect(status).toHaveText(copy.saved("21:14"));
});

test("a save refused once the test is handed in shows why and the stored answer", async ({ page }) => {
  await page.route(`**/api/me/class-sessions/${SESSION}/test/answers/*`, (route) =>
    route.fulfill({ status: 409, json: { error: { code: "attempt_submitted", message: "x", fields: {} } } }),
  );
  const stored = { value: "a", revision: 1, saved_at: SAVED_AT };
  await standIn(page, { status: 200, json: { ...opened, items: [{ ...ITEMS[0], answer: stored }, ...ITEMS.slice(1)] } });
  const item = page.locator("[data-test-item=flervalg-1]");
  await expect(item.getByRole("radio", { name: copy.option("a") })).toBeChecked();
  await item.getByRole("radio", { name: copy.option("b") }).check();
  await expect(item.getByRole("status")).toHaveText(copy.saveErrors.attempt_submitted!);
  await expect(item.getByRole("radio", { name: copy.option("a") })).toBeChecked();
});

test("another Student's session shows the permission-denied page", async ({ page }) => {
  await standIn(page, { status: 403, json: { error: { code: "forbidden", message: "x", fields: {} } } });
  await expect(page.getByRole("heading", { level: 1 })).not.toHaveText(copy.title);
  await expect(page.locator("[data-test-state]")).toHaveCount(0);
});

test("live: Stegene leads to the statement, which opens the test once; a reload shows the items", async ({
  browser,
  lecturerSession,
}) => {
  test.slow(); // an Invitation through the worker, a Class session, a lock
  const game = await liveClassGame(browser, lecturerSession, 1, { aiMode: "rule_based" });
  const [student] = game.students;
  const page = await student!.context.newPage();
  // Before the Replay: Stegene's test step is locked with its line and no link, and the page says so.
  await page.goto("/hjem");
  const locked = page.getByRole("main").getByRole("region", { name: nb.homes.student.steps });
  await expect(locked.getByText(nb.homes.student.locked.test, { exact: true })).toBeVisible();
  await expect(locked.getByRole("link", { name: nb.homes.student.stepNames.test })).toHaveCount(0);
  await page.goto(`/individuell-test/${game.sessionId}`);
  await expect(page.locator("[data-test-state=locked]")).toHaveText(nb.homes.student.locked.test);

  const done = await student!.context.request.post(`/api/dev/class-sessions/${game.sessionId}/replay-done`, { headers: CSRF });
  expect(done.status()).toBe(204);
  await page.goto("/hjem");
  const steps = page.getByRole("main").getByRole("region", { name: nb.homes.student.steps });
  await steps.getByRole("link", { name: new RegExp(nb.homes.student.stepNames.test) }).click();
  await expect(page).toHaveURL(new RegExp(`/individuell-test/${game.sessionId}$`));
  await page.getByRole("button", { name: copy.accept }).click();
  await expect(page.getByRole("heading", { name: copy.itemsHeading })).toBeFocused();
  const count = await page.locator("[data-test-item]").count();
  expect(count).toBeGreaterThan(0);

  // A multiple-choice item answered: stored, and there again after a reload (Story 11.4).
  const choice = page.locator("[data-test-item]").filter({ has: page.getByRole("radio") }).first();
  await choice.getByRole("radio").nth(1).check();
  await expect(choice.getByRole("status")).toHaveText(/^Lagret \d{2}:\d{2}$/);

  await page.reload();
  await expect(page.locator("[data-test-item]")).toHaveCount(count);
  await expect(page.getByRole("button", { name: copy.accept })).toHaveCount(0);
  await expect(choice.getByRole("radio").nth(1)).toBeChecked();
  await expect(choice.getByRole("status")).toHaveText("");
  await page.close();
});
