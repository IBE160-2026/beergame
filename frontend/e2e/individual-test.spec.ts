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
 * test step, the statement, the open test, and a reload that does not ask again. Table and number
 * Interactive items (Story 11.5, FR-80, UX-DR38, UX-DR75): the value table answered by keyboard
 * alone at 320, 360 and 1440 px and with 200 % text, in its own scrolling region with a sticky
 * label column, «Skriv et helt tall.» on leaving an invalid cell and nothing sent; the column of a
 * number item and of a Starting task item. Long answers (Story 11.6, FR-51, FR-73, AD-10, UX-DR65):
 * the question as the field's label, typing saved once after the pause, on leaving the field and
 * when the page is hidden, the save-failed and restored-draft states at 320, 360 and 1440 px with
 * axe, the larger-screen advice on phones only, and a draft kept through an ended session. */
const SESSION = "01a1f8ee-33b9-75e6-9502-79db27b37c0e";
const CSRF = { "X-Requested-With": "olspillet" };
const copy = nb.tests.individual;
const DEADLINE = "2026-12-18T22:59:00Z";
const WEEKS = ["Uke 1", "Uke 2", "Uke 3", "Uke 4", "Uke 5", "Uke 6"];
const TABLE = {
  prompt: "Utkast: Et bakeri har 10 enheter på lager før uke 1. Fyll inn lageret ved slutten av hver uke.",
  hint: null,
  caption: "Utkast: Bakeriets lager per uke, i enheter",
  rows: WEEKS,
  columns: [
    { label: "Bestilt", values: [20, 20, 25, 25, 20, 20] },
    { label: "Inn", values: [20, 20, 25, 25, 20, 20] },
    { label: "Ut", values: [22, 24, 20, 18, 25, 21] },
  ],
  asked_label: "Lager",
  negative: false,
};
const COLUMN = {
  prompt: "Utkast: Et verksted mangler deler i fire uker. Hvor mange enheter må legges til?",
  hint: null,
  caption: "Utkast: Mangler per uke, i enheter",
  rows: [
    { label: "Uke 1", value: 3 },
    { label: "Uke 2", value: 5 },
  ],
  asked_label: "Legg til",
  negative: false,
  starting_task: false,
};
const STARTING = {
  prompt: "Regn ut posisjonen for uka.",
  hint: "Lager − Restordre + På vei",
  caption: "Kolonne 11",
  rows: [
    { label: "Lager", value: 0 },
    { label: "Restordre", value: 13 },
    { label: "På vei", value: 16 },
  ],
  asked_label: "Posisjon",
  negative: true,
  starting_task: true,
};
const PLAIN = { table: null, column: null, answer: null };
const ITEMS = [
  { id: "flervalg-1", number: 1, type: "choice", title: "Utkast: hva er et lager?", options: ["a", "b", "c"], ...PLAIN },
  { id: "kolonne-1", number: 2, type: "table", title: "Utkast: fyll inn kolonnen for bakeriet.", options: [], ...PLAIN, table: TABLE },
  { id: "langsvar-1", number: 3, type: "long", title: "Utkast: forklar svingningene ut fra kjedens struktur.", options: [], ...PLAIN },
  { id: "tall-1", number: 4, type: "number", title: "Utkast: tall fra et verksted.", options: [], ...PLAIN, column: COLUMN },
  { id: "startoppgave-1", number: 5, type: "number", title: "Utkast: Startoppgaven, posisjonen.", options: [], ...PLAIN, column: STARTING },
] as const;
const SAVED_AT = "2026-11-22T20:14:00Z"; // «Lagret 21:14» in Oslo
const ANSWERS = `**/api/me/class-sessions/${SESSION}/test/answers/*`;
const UNAVAILABLE = { status: 503, json: { error: { code: "unavailable", message: "x", fields: {} } } };
const EXPIRED = { status: 401, json: { error: { code: "session_expired", message: "x", fields: {} } } };

const VIEWPORTS = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
];
/** The table item also at 200 % text (WCAG 1.4.4), on the narrowest phone. */
const TABLE_VIEWPORTS = [...VIEWPORTS.map((vp) => ({ ...vp, text200: false })), { name: "320 px with 200 % text", width: 320, height: 640, phone: true, text200: true }];

async function text200(page: Page) {
  await page.addInitScript(() => {
    document.addEventListener("DOMContentLoaded", () => {
      const style = document.createElement("style");
      style.textContent = "html { font-size: 200% !important; }";
      document.head.appendChild(style);
    });
  });
}

type Save = { value: unknown; revision: number };

/** Every PUT of an answer, stored at once as sent. */
async function storeSaves(page: Page): Promise<Save[]> {
  const saves: Save[] = [];
  await page.route(`**/api/me/class-sessions/${SESSION}/test/answers/*`, async (route) => {
    const body = route.request().postDataJSON() as Save;
    saves.push(body);
    const itemId = route.request().url().split("/").at(-1);
    await route.fulfill({ status: 200, json: { item_id: itemId, ...body, saved_at: SAVED_AT } });
  });
  return saves;
}

/** Every PUT of an answer: stored as sent, or failed while `failing()` says so. */
async function saveOrFail(page: Page, failing: () => boolean): Promise<Save[]> {
  const saves: Save[] = [];
  await page.route(ANSWERS, async (route) => {
    const body = route.request().postDataJSON() as Save;
    saves.push(body);
    if (failing()) return route.fulfill(UNAVAILABLE);
    const itemId = route.request().url().split("/").at(-1);
    return route.fulfill({ status: 200, json: { item_id: itemId, ...body, saved_at: SAVED_AT } });
  });
  return saves;
}

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

    test("number items: an Interactive column and a Starting task item, saved by keyboard with no result; axe passes", async ({ page }) => {
      const saves = await storeSaves(page);
      await standIn(page, { status: 200, json: opened });
      const own = page.locator("[data-test-item=tall-1]");
      await expect(own).toContainText(copy.interactive.intro);
      await expect(own).toContainText(COLUMN.prompt);
      const field = own.getByRole("textbox", { name: COLUMN.asked_label });
      await field.focus();
      // A minus where the item takes no negative quantity: the error on leaving, nothing sent.
      await page.keyboard.type("-3");
      await page.keyboard.press("Tab");
      await expect(own.getByRole("alert")).toHaveText(copy.interactive.wholeNumber);
      await expect(field).toHaveAttribute("aria-invalid", "true");
      expect(saves).toEqual([]);
      await expectAccessible(page, vp.phone);
      await field.focus();
      await page.keyboard.press("ControlOrMeta+a");
      await page.keyboard.type("16");
      await expect(own.getByRole("status")).toHaveText(copy.saved("21:14"));
      await expect(own.getByRole("alert")).toHaveCount(0);
      // Each valid change is saved: «1», then «16» (the item's revisions 1 and 2).
      expect(saves.at(-1)).toEqual({ value: 16, revision: 2 });
      // Emptied: the answer is cleared, sent as null.
      await page.keyboard.press("ControlOrMeta+a");
      await page.keyboard.press("Backspace");
      await expect.poll(() => saves.length).toBe(3);
      expect(saves.at(-1)).toEqual({ value: null, revision: 3 });
      await expect(own.getByRole("status")).toHaveText(copy.saved("21:14"));

      // A Starting task item: its column and hint, no Interactive introduction, a negative answer.
      const starting = page.locator("[data-test-item=startoppgave-1]");
      await expect(starting).not.toContainText(copy.interactive.intro);
      await expect(starting).toContainText(STARTING.prompt);
      await expect(starting).toContainText(STARTING.hint);
      await starting.getByRole("textbox", { name: STARTING.asked_label }).focus();
      await page.keyboard.type("-13");
      await expect(starting.getByRole("status")).toHaveText(copy.saved("21:14"));
      expect(saves.at(-1)).toEqual({ value: -13, revision: 2 }); // «-» holds no value: nothing new to send
      // No right or wrong line from the Startoppgave (FR-54).
      await expect(starting).not.toContainText("Riktig");
      await expect(starting).not.toContainText("Ikke riktig");
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

    test("a long answer: typing, saved after the pause, save-failed and restored draft; advice on phones; axe passes", async ({ page }) => {
      let failing = false;
      const saves = await saveOrFail(page, () => failing);
      await standIn(page, { status: 200, json: opened });
      const item = page.locator("[data-test-item=langsvar-1]");
      // The question, as the pinned set words it, is the label above the field.
      const field = item.getByRole("textbox", { name: ITEMS[2].title, exact: true });
      const status = item.getByRole("status");
      const advice = item.getByText(copy.long.largerScreen);
      await expect(field).toBeVisible();
      const label = item.locator("label", { hasText: ITEMS[2].title });
      expect((await label.boundingBox())!.y).toBeLessThan((await field.boundingBox())!.y);
      // The api's limit (`commands.LONG_ANSWER_MAX`): the field stops where a save would be refused.
      await expect(field).toHaveAttribute("maxlength", "20000");
      if (vp.phone) {
        await expect(advice).toBeVisible();
        expect((await advice.boundingBox())!.y).toBeLessThan((await field.boundingBox())!.y);
      } else {
        await expect(advice).toBeHidden();
      }
      await expect(status).toHaveText("");

      // Typing: kept on this device at once, one save for the whole word once typing pauses.
      await field.focus();
      await page.keyboard.type("Forsinkelse");
      await expect(field).toHaveValue("Forsinkelse");
      await expectAccessible(page, vp.phone);
      await expect(status).toHaveText(copy.saved("21:14"));
      expect(saves).toEqual([{ value: "Forsinkelse", revision: 11 }]);
      await expect(field).toBeFocused();
      await expectAccessible(page, vp.phone);

      // Save failed on leaving the field: the spine's line, the text kept.
      failing = true;
      await page.keyboard.type(" gir");
      await page.keyboard.press("Tab");
      await expect(status).toHaveText(copy.notSaved);
      expect(saves.at(-1)).toEqual({ value: "Forsinkelse gir", revision: 15 });
      await expect(field).toHaveValue("Forsinkelse gir");
      await expectAccessible(page, vp.phone);

      // Restored draft: after a reload the text kept on this device shows and goes again.
      await page.reload();
      await expect(field).toHaveValue("Forsinkelse gir");
      await expect(status).toHaveText(copy.notSaved);
      expect(saves.at(-1)).toEqual({ value: "Forsinkelse gir", revision: 15 });
      await expectAccessible(page, vp.phone);
      failing = false;
      await page.evaluate(() => window.dispatchEvent(new Event("online")));
      await expect(status).toHaveText(copy.saved("21:14"));
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

for (const vp of TABLE_VIEWPORTS) {
  test.describe(`${vp.name}: «Fyll inn kolonnen»`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("the value table answered by keyboard alone, its own scroll and sticky labels; axe passes", async ({ page }) => {
      if (vp.text200) await text200(page);
      const saves = await storeSaves(page);
      await standIn(page, { status: 200, json: opened });
      const item = page.locator("[data-test-item=kolonne-1]");
      const table = item.getByRole("table", { name: TABLE.caption });
      const status = item.getByRole("status");

      // Idle: the introduction, the prompt, one row per Uke with «Ikke besvart», no graph.
      await expect(item.getByRole("heading", { level: 3 })).toHaveText(`${copy.item(2)}${copy.types.table}`);
      await expect(item).toContainText(copy.interactive.intro);
      await expect(item).toContainText(TABLE.prompt);
      await expect(table.locator("th[scope=col]")).toHaveText([copy.interactive.rowHeader, "Bestilt", "Inn", "Ut", "Lager"]);
      await expect(table.locator("th[scope=row]")).toHaveCount(WEEKS.length);
      await expect(table.locator("[data-not-answered]")).toHaveCount(WEEKS.length);
      await expect(item.locator("svg")).toHaveCount(0);
      await expect(item.getByRole("slider")).toHaveCount(0);
      const cells = table.getByRole("textbox");
      await expect(cells).toHaveCount(WEEKS.length);
      await expect(cells.first()).toHaveAccessibleName(copy.interactive.cell("Lager", "Uke 1"));
      await expect(cells.first()).toHaveValue("");
      for (const cell of await cells.all()) {
        expect((await cell.boundingBox())!.height).toBeGreaterThanOrEqual(44);
      }
      await expectAccessible(page, vp.phone);

      // The region scrolls on its own when the table is wider than the screen; the labels stay.
      const region = item.getByRole("group", { name: TABLE.caption });
      const wide = await region.evaluate((el) => el.scrollWidth > el.clientWidth);
      if (vp.phone && vp.text200) expect(wide).toBe(true);
      if (wide) {
        await region.evaluate((el) => (el.scrollLeft = el.scrollWidth));
        const label = table.locator("th[scope=row]").first();
        await expect
          .poll(async () => Math.abs((await label.boundingBox())!.x - (await region.boundingBox())!.x))
          .toBeLessThan(2);
        await region.evaluate((el) => (el.scrollLeft = 0));
      }

      // Keyboard alone: type, Tab to the next Uke, a decimal left behind, then corrected.
      await cells.first().focus();
      await page.keyboard.type("8");
      await expect(status).toHaveText(copy.saved("21:14"));
      expect(saves).toEqual([{ value: [8, null, null, null, null, null], revision: 1 }]);
      await page.keyboard.press("Tab");
      await expect(cells.nth(1)).toBeFocused();
      await page.keyboard.type("1,5");
      await page.keyboard.press("Tab");
      await expect(cells.nth(2)).toBeFocused();
      await expect(item.getByRole("alert")).toHaveText(copy.interactive.wholeNumber);
      await expect(cells.nth(1)).toHaveAttribute("aria-invalid", "true");
      await expect(cells.nth(1)).toHaveValue("1,5");
      // «1» was a whole number and was saved as typed; from «1,» the Uke holds no value, and the
      // text itself is never sent.
      expect(saves).toEqual([
        { value: [8, null, null, null, null, null], revision: 1 },
        { value: [8, 1, null, null, null, null], revision: 2 },
        { value: [8, null, null, null, null, null], revision: 3 },
      ]);
      await expect(table.locator("[data-not-answered]")).toHaveCount(WEEKS.length - 1);
      await expectAccessible(page, vp.phone);

      await page.keyboard.press("Shift+Tab");
      await page.keyboard.press("ControlOrMeta+a");
      await page.keyboard.type("4");
      await expect(item.getByRole("alert")).toHaveCount(0);
      await expect.poll(() => saves.length).toBe(4);
      expect(saves[3]).toEqual({ value: [8, 4, null, null, null, null], revision: 4 });
      await expect(status).toHaveText(copy.saved("21:14"));
      await expect(table.locator("[data-not-answered]")).toHaveCount(WEEKS.length - 2);
      // Emptying a cell clears its value.
      await page.keyboard.press("Backspace");
      await expect.poll(() => saves.length).toBe(5);
      expect(saves[4]).toEqual({ value: [8, null, null, null, null, null], revision: 5 });
      await expect(table.locator("[data-not-answered]")).toHaveCount(WEEKS.length - 1);
      // No right or wrong state (FR-54).
      await expect(item.locator("[data-quiz-mark]")).toHaveCount(0);
      await expectAccessible(page, vp.phone);
    });
  });
}

test("a stored table answer shows in its cells, and a refused change brings it back", async ({ page }) => {
  await page.route(`**/api/me/class-sessions/${SESSION}/test/answers/*`, (route) =>
    route.fulfill({ status: 409, json: { error: { code: "attempt_submitted", message: "x", fields: {} } } }),
  );
  const stored = { value: [8, 4, null, null, null, null], revision: 2, saved_at: SAVED_AT };
  const items = ITEMS.map((i) => (i.id === "kolonne-1" ? { ...i, answer: stored } : i));
  await standIn(page, { status: 200, json: { ...opened, items } });
  const item = page.locator("[data-test-item=kolonne-1]");
  const cells = item.getByRole("textbox");
  await expect(cells.nth(0)).toHaveValue("8");
  await expect(cells.nth(1)).toHaveValue("4");
  await expect(cells.nth(2)).toHaveValue("");
  await expect(item.locator("[data-not-answered]")).toHaveCount(WEEKS.length - 2);
  await cells.nth(0).fill("9");
  await expect(item.getByRole("status")).toHaveText(copy.saveErrors.attempt_submitted!);
  await expect(cells.nth(0)).toHaveValue("8");
});

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

test("a long answer is saved at once when the page is hidden, and after the pause otherwise", async ({ page }) => {
  await page.clock.install({ time: new Date("2026-11-22T20:00:00Z") });
  const saves = await saveOrFail(page, () => false);
  await standIn(page, { status: 200, json: opened });
  const field = page.locator("[data-test-item=langsvar-1]").getByRole("textbox", { name: ITEMS[2].title, exact: true });
  await expect(field).toBeVisible();
  // The clock stands still: no pause ends unless the test moves it.
  await page.clock.pauseAt(new Date("2026-11-22T20:00:30Z"));
  await field.fill("Svar");
  await expect(field).toHaveValue("Svar");
  expect(saves).toEqual([]);
  await page.evaluate(() => {
    Object.defineProperty(document, "visibilityState", { value: "hidden", configurable: true });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  await expect.poll(() => saves.length).toBe(1);
  expect(saves[0]).toEqual({ value: "Svar", revision: 1 });
  await page.evaluate(() => {
    Object.defineProperty(document, "visibilityState", { value: "visible", configurable: true });
  });
  await field.fill("Svar to");
  await expect(field).toHaveValue("Svar to");
  expect(saves).toHaveLength(1);
  await page.clock.runFor(1_500);
  await expect.poll(() => saves.length).toBe(2);
  expect(saves[1]).toEqual({ value: "Svar to", revision: 2 });
});

test("a long answer is saved at once when the page is left, and a reply during typing waits for the pause", async ({ page }) => {
  await page.clock.install({ time: new Date("2026-11-22T20:00:00Z") });
  const saves: Save[] = [];
  const held: (() => void)[] = [];
  let replied = 0;
  await page.route(ANSWERS, async (route) => {
    const body = route.request().postDataJSON() as Save;
    saves.push(body);
    await new Promise<void>((go) => held.push(go));
    await route.fulfill({ status: 200, json: { item_id: "langsvar-1", ...body, saved_at: SAVED_AT } });
    replied += 1;
  });
  await standIn(page, { status: 200, json: opened });
  const field = page.locator("[data-test-item=langsvar-1]").getByRole("textbox", { name: ITEMS[2].title, exact: true });
  await expect(field).toBeVisible();
  await page.clock.pauseAt(new Date("2026-11-22T20:00:30Z"));
  // `pagehide` (the tab closed or the page left): sent at once.
  await field.fill("En");
  await page.evaluate(() => window.dispatchEvent(new Event("pagehide")));
  await expect.poll(() => saves.length).toBe(1);
  // More typing while that save runs; its reply comes inside the pause: nothing more goes yet.
  await field.fill("En to");
  held.shift()!();
  await expect.poll(() => replied).toBe(1);
  await page.waitForTimeout(500); // real time; the page's clock stands still
  expect(saves).toHaveLength(1);
  await page.clock.runFor(1_500);
  await expect.poll(() => saves.length).toBe(2);
  expect(saves).toEqual([
    { value: "En", revision: 1 },
    { value: "En to", revision: 2 },
  ]);
  held.shift()!();
  await expect(page.locator("[data-test-item=langsvar-1]").getByRole("status")).toHaveText(copy.saved("21:14"));
});

test("a long answer still in its pause is saved when the Student leaves the page in the app", async ({ page }) => {
  await page.clock.install({ time: new Date("2026-11-22T20:00:00Z") });
  const saves = await saveOrFail(page, () => false);
  await standIn(page, { status: 200, json: opened });
  const field = page.locator("[data-test-item=langsvar-1]").getByRole("textbox", { name: ITEMS[2].title, exact: true });
  await expect(field).toBeVisible();
  await page.clock.pauseAt(new Date("2026-11-22T20:00:30Z"));
  await field.fill("Skrevet rett før jeg gikk.");
  expect(saves).toEqual([]);
  // In-app navigation home: the item leaves the page and its pending text goes.
  await page.getByRole("main").getByRole("link", { name: nb.navigation.toHome }).click();
  await expect.poll(() => saves.length).toBe(1);
  expect(saves[0]).toEqual({ value: "Skrevet rett før jeg gikk.", revision: 1 });
});

test("a long answer written after the session ended is kept, and saved with a higher revision after login", async ({ page }) => {
  let ended = true;
  const saves: Save[] = [];
  await page.route(ANSWERS, async (route) => {
    const body = route.request().postDataJSON() as Save;
    saves.push(body);
    if (ended) return route.fulfill(EXPIRED);
    return route.fulfill({ status: 200, json: { item_id: "langsvar-1", ...body, saved_at: SAVED_AT } });
  });
  await loginByApi(page, "student");
  let reads = 0;
  await page.route(`**/api/me/class-sessions/${SESSION}/test`, (route) => {
    reads += 1;
    // The session has ended by the time the test is read again.
    return ended && reads > 1 ? route.fulfill(EXPIRED) : route.fulfill({ status: 200, json: opened });
  });
  await page.goto(`/individuell-test/${SESSION}`);
  const text = "Skrevet etter at økten gikk ut.";
  const field = page.locator("[data-test-item=langsvar-1]").getByRole("textbox");
  await field.fill(text);
  await field.blur();
  // To «Logg inn», with the way back; the text stays on this device.
  await expect(page).toHaveURL(/\/logg-inn/);
  expect(saves).toEqual([{ value: text, revision: 1 }]);

  ended = false;
  await loginByApi(page, "student");
  await page.goto(`/individuell-test/${SESSION}`);
  const item = page.locator("[data-test-item=langsvar-1]");
  await expect(item.getByRole("textbox")).toHaveValue(text);
  await expect(item.getByRole("status")).toHaveText(copy.saved("21:14"));
  // Sent again with its revision, above the stored one (none).
  expect(saves.at(-1)).toEqual({ value: text, revision: 1 });
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

  // A «Fyll inn kolonnen» item answered: stored, and there again after a reload (Story 11.5).
  const table = page.locator("[data-test-item]").filter({ has: page.locator("[data-value-table]") }).first();
  const first = table.getByRole("textbox").first();
  await first.fill("8");
  await expect(table.getByRole("status")).toHaveText(/^Lagret \d{2}:\d{2}$/);
  await page.reload();
  await expect(first).toHaveValue("8");

  // A long answer written: saved after the pause, and there again after a reload (Story 11.6).
  const long = page.locator("[data-test-item]").filter({ has: page.locator("textarea") }).first();
  const text = "Et langsvar\n\nmed to avsnitt.";
  await long.getByRole("textbox").fill(text);
  await expect(long.getByRole("status")).toHaveText(/^Lagret \d{2}:\d{2}$/);
  await page.reload();
  await expect(long.getByRole("textbox")).toHaveValue(text);
  await page.close();
});
