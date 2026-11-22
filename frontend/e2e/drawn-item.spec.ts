import { expect, type Locator, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { loginByApi } from "./support/auth";
import { expectAccessible, test } from "./support/classes";

/** Answer drawn Interactive items in a graph (Story 11.14, FR-80, AD-18, UX-DR38, UX-DR75,
 * UX-DR76, NFR-6): one graph over the item's value table, the Uker as the table's columns, each
 * point a slider over its Uke's column. At 320, 360 and 1440 px and at 320 px with 200 % text,
 * with axe: points placed by keyboard (Tab into the graph, Up, Page Up, Tab on into the table)
 * and by pointer (a tap in a column, a drag), each written into the cell and saved through the
 * autosave path; a typed cell moves its point; the points stand within 1 px of their columns, and
 * graph and table scroll as one region. The api's side (the load, the shape a save takes, the
 * same score for the same values) is `backend/tests/individual_test/test_drawn.py`; the api is
 * stood in here with its shapes. */
const SESSION = "01a1f8ee-33b9-75e6-9502-79db27b37c0e";
const copy = nb.tests.individual;
const drawn = copy.drawn;
const DEADLINE = "2026-12-18T22:59:00Z";
const WEEKS = ["Uke 1", "Uke 2", "Uke 3", "Uke 4", "Uke 5", "Uke 6"];
const TABLE = {
  prompt: "Utkast: Et bakeri har 10 enheter på lager før uke 1. Tegn lageret ved slutten av hver uke.",
  hint: null,
  caption: "Utkast: Bakeriets lager per uke, i enheter",
  rows: WEEKS,
  columns: [
    { label: "Inn", values: [20, 20, 25, 25, 20, 20] },
    { label: "Ut", values: [22, 24, 20, 18, 25, 21] },
  ],
  asked_label: "Lager",
  negative: false,
  axis: { min: 0, max: 40 },
};
const SAVED_AT = "2026-11-22T20:14:00Z"; // «Lagret 21:14» in Oslo
const ITEM = {
  id: "graf-1",
  number: 1,
  type: "drawn",
  title: "Utkast: tegn lageret.",
  options: [],
  table: TABLE,
  column: null,
  wording: null,
  answer: { value: [12, 20, null, null, null, null], revision: 1, saved_at: SAVED_AT },
};
const opened = { state: "open", test_deadline: DEADLINE, opened_at: "2026-11-22T10:00:00Z", items: [ITEM] };

const VIEWPORTS = [
  { name: "320 px", width: 320, height: 640, phone: true, text200: false },
  { name: "360 px", width: 360, height: 740, phone: true, text200: false },
  { name: "1440 px", width: 1440, height: 900, phone: false, text200: false },
  { name: "320 px with 200 % text", width: 320, height: 640, phone: true, text200: true },
];

type Save = { value: (number | null)[]; revision: number };

async function text200(page: Page) {
  await page.addInitScript(() => {
    document.addEventListener("DOMContentLoaded", () => {
      const style = document.createElement("style");
      style.textContent = "html { font-size: 200% !important; }";
      document.head.appendChild(style);
    });
  });
}

/** The Student's page with the api stood in; every PUT of an answer stored at once as sent. */
async function standIn(page: Page, test: unknown = opened): Promise<Save[]> {
  const saves: Save[] = [];
  await loginByApi(page, "student");
  await page.route(`**/api/me/class-sessions/${SESSION}/test/answers/*`, async (route) => {
    const body = route.request().postDataJSON() as Save;
    saves.push(body);
    await route.fulfill({ status: 200, json: { item_id: ITEM.id, ...body, saved_at: SAVED_AT } });
  });
  await page.route(`**/api/me/class-sessions/${SESSION}/test`, (route) => route.fulfill({ status: 200, json: test }));
  await page.goto(`/individuell-test/${SESSION}`);
  return saves;
}

const centreX = async (locator: Locator) => {
  const box = (await locator.boundingBox())!;
  return box.x + box.width / 2;
};
/** Scroll a column to the middle of its region and of the screen: «if needed» counts a column
 * under the sticky row-label column as in view, and a click there misses the graph. */
const centreInView = (locator: Locator) =>
  locator.evaluate((element) => element.scrollIntoView({ block: "nearest", inline: "center", behavior: "instant" }));
/** The locator's centre once a scroll into view has stopped moving it (a slow CI runner may still
 * be scrolling when the next pointer action measures). */
const settledX = async (locator: Locator) => {
  let last = Number.NaN;
  await expect
    .poll(async () => {
      const now = await centreX(locator);
      const still = Math.abs(now - last) < 0.5;
      last = now;
      return still;
    })
    .toBe(true);
  return last;
};
const centreY = async (locator: Locator) => {
  const box = (await locator.boundingBox())!;
  return box.y + box.height / 2;
};

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

for (const vp of VIEWPORTS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("a drawn item: points by keyboard and by pointer, one answer with the table; axe passes", async ({ page }) => {
      if (vp.text200) await text200(page);
      const saves = await standIn(page);
      const item = page.locator("[data-test-item=graf-1]");
      const region = item.getByRole("region", { name: drawn.region(TABLE.caption) });
      const graph = region.getByRole("group", { name: drawn.graph });
      const sliders = graph.getByRole("slider");
      const points = graph.locator("[data-mark=point]");
      const cells = region.getByRole("textbox");
      const status = item.getByRole("status");

      // Idle: the introduction, the prompt, a slider per Uke, a point per answered Uke, a line.
      await expect(item.getByRole("heading", { level: 3 })).toHaveText(`${copy.item(1)}${copy.types.drawn}`);
      await expect(item).toContainText(copy.interactive.intro);
      await expect(item).toContainText(drawn.howTo);
      await expect(region.getByRole("table", { name: TABLE.caption })).toBeVisible();
      await expect(sliders).toHaveCount(WEEKS.length);
      await expect(sliders.first()).toHaveAccessibleName("Uke 1");
      await expect(sliders.first()).toHaveAttribute("aria-valuetext", drawn.valueText("Uke 1", "12", 12));
      await expect(sliders.nth(2)).toHaveAttribute("aria-valuetext", drawn.notAnsweredText("Uke 3"));
      await expect(points).toHaveCount(2);
      await expect(graph.locator("[data-mark=line]")).toHaveCount(1);
      await expect(cells).toHaveCount(WEEKS.length);
      await expect(cells.first()).toHaveValue("12");
      await expect(cells.first()).toHaveAccessibleName(copy.interactive.cell("Lager", "Uke 1"));
      await expect(region.locator("[data-not-answered]")).toHaveCount(WEEKS.length - 2);
      for (const slider of await sliders.all()) {
        const box = (await slider.boundingBox())!;
        expect(Math.min(box.width, box.height)).toBeGreaterThanOrEqual(44);
      }

      // Each point within 1 px of its Uke's column; the page itself never scrolls sideways.
      const columnOf = (week: number) => region.locator(`th[scope=col][data-col="${week}"]`);
      await expect.poll(async () => Math.abs((await centreX(points.first())) - (await centreX(columnOf(1))))).toBeLessThan(1);
      expect(Math.abs((await centreX(points.nth(1))) - (await centreX(columnOf(2))))).toBeLessThan(1);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
      await expectAccessible(page, vp.phone);

      // Graph and table scroll as one region.
      const wide = await region.evaluate((el) => el.scrollWidth > el.clientWidth);
      if (vp.phone) expect(wide).toBe(true);
      if (wide) {
        const before = { point: await centreX(points.first()), column: await centreX(columnOf(1)) };
        await region.evaluate((el) => (el.scrollLeft = 80));
        await expect.poll(async () => before.point - (await centreX(points.first()))).toBeGreaterThan(40);
        expect(Math.abs((await centreX(points.first())) - (await centreX(columnOf(1))))).toBeLessThan(1);
        expect(before.column - (await centreX(columnOf(1)))).toBeGreaterThan(40);
        await region.evaluate((el) => (el.scrollLeft = 0));
      }

      // Keyboard alone: Tab into the graph, Up by 1, Page Up by 10, Tab point to point.
      await region.focus();
      await page.keyboard.press("Tab");
      await expect(sliders.first()).toBeFocused();
      await page.keyboard.press("ArrowUp");
      await expect(cells.first()).toHaveValue("13");
      await expect(sliders.first()).toHaveAttribute("aria-valuetext", drawn.valueText("Uke 1", "13", 13));
      await page.keyboard.press("PageUp");
      await expect(cells.first()).toHaveValue("23");
      await expect(status).toHaveText(copy.saved("21:14"));
      await expect.poll(() => saves.at(-1)?.value).toEqual([23, 20, null, null, null, null]);
      // An unanswered Uke starts from the Uke before it.
      await page.keyboard.press("Tab");
      await page.keyboard.press("Tab");
      await expect(sliders.nth(2)).toBeFocused();
      await page.keyboard.press("ArrowDown");
      await expect(cells.nth(2)).toHaveValue("19");
      await expect(points).toHaveCount(3);
      await expect.poll(() => saves.at(-1)?.value).toEqual([23, 20, 19, null, null, null]);
      // A key with Alt, Ctrl or Meta is the browser's, not the point's.
      await page.keyboard.press("Alt+ArrowUp");
      await expect(cells.nth(2)).toHaveValue("19");
      // After the last point, Tab goes into the table.
      for (let i = 3; i < WEEKS.length; i++) await page.keyboard.press("Tab");
      await expect(sliders.last()).toBeFocused();
      await page.keyboard.press("Tab");
      await expect(cells.first()).toBeFocused();

      // Typing in a cell moves its point.
      await cells.nth(3).focus();
      await page.keyboard.type("30");
      await expect(points).toHaveCount(4);
      await expect.poll(() => saves.at(-1)?.value).toEqual([23, 20, 19, 30, null, null]);
      const fourth = graph.locator("[data-mark=point][data-week='4']");
      expect(await centreY(fourth)).toBeLessThan(await centreY(graph.locator("[data-mark=point][data-week='2']")));

      // Pointer: a tap in Uke 5's column at Uke 2's height places 20 there.
      await centreInView(columnOf(5));
      const x5 = await settledX(columnOf(5));
      const level20 = await centreY(graph.locator("[data-mark=point][data-week='2']"));
      await page.mouse.click(x5, level20);
      await expect(cells.nth(4)).toHaveValue("20");
      await expect.poll(() => saves.at(-1)?.value).toEqual([23, 20, 19, 30, 20, null]);
      await expect(sliders.nth(4)).toBeFocused();
      // A drag in Uke 6's column: pressed at 20, moved down to the bottom, it ends at 0.
      await centreInView(columnOf(6));
      const x6 = await settledX(columnOf(6));
      const bottom = (await graph.boundingBox())!;
      // Measured again: the scroll may have moved the graph up or down the page.
      await page.mouse.move(x6, await centreY(graph.locator("[data-mark=point][data-week='2']")));
      await page.mouse.down();
      await expect(cells.nth(5)).toHaveValue("20");
      await page.mouse.move(x6, bottom.y + bottom.height - 2, { steps: 4 });
      await page.mouse.up();
      await expect(cells.nth(5)).toHaveValue("0");
      await expect.poll(() => saves.at(-1)?.value).toEqual([23, 20, 19, 30, 20, 0]);
      await expect(points).toHaveCount(WEEKS.length);
      // Revisions rise from the stored one, one save after another.
      const revisions = saves.map((save) => save.revision);
      expect(revisions[0]).toBe(2);
      expect(revisions.every((revision, i) => i === 0 || revision > revisions[i - 1]!)).toBe(true);
      // No right or wrong state (FR-54).
      await expect(item.locator("[data-quiz-mark]")).toHaveCount(0);
      await expectAccessible(page, vp.phone);
    });
  });
}

test.describe("360 px, touch and hand-in", () => {
  test.use({ viewport: { width: 360, height: 740 } });

  test("on a touch screen a sideways swipe places nothing, a tap and a vertical drag place a point", async ({ page }) => {
    const saves = await standIn(page);
    const item = page.locator("[data-test-item=graf-1]");
    const graph = item.getByRole("group", { name: drawn.graph });
    const cells = item.getByRole("region", { name: drawn.region(TABLE.caption) }).getByRole("textbox");
    await expect(graph.getByRole("slider")).toHaveCount(WEEKS.length);
    const box = (await graph.boundingBox())!;
    const x = await centreX(item.locator('th[scope=col][data-col="2"]'));
    const touch = (type: string, clientY: number, buttons = 1) =>
      graph.dispatchEvent(type, { pointerType: "touch", pointerId: 7, isPrimary: true, button: 0, buttons, clientX: x, clientY });
    // A press that turns into a sideways swipe: the browser scrolls and cancels the pointer.
    await touch("pointerdown", box.y + box.height / 2);
    await touch("pointercancel", box.y + box.height / 2, 0);
    await expect(cells.nth(1)).toHaveValue("20");
    // A tap places the point where the finger lifted from.
    await touch("pointerdown", box.y + box.height - 30);
    await touch("pointerup", box.y + box.height - 30, 0);
    await expect.poll(() => saves.at(-1)?.value?.[1]).toBeLessThan(20);
    const tapped = saves.at(-1)!.value[1]!;
    await expect(cells.nth(1)).toHaveValue(String(tapped));
    // A vertical drag moves it while the finger is down.
    await touch("pointerdown", box.y + box.height - 30);
    await touch("pointermove", box.y + 30);
    await touch("pointerup", box.y + 30, 0);
    await expect.poll(() => saves.at(-1)?.value?.[1]).toBeGreaterThan(tapped);
    expect(saves.every((save) => save.value[0] === 12)).toBe(true);
  });

  test("a handed-in drawn item shows its values in its table, read-only", async ({ page }) => {
    await standIn(page, { ...opened, state: "submitted", submitted_at: "2026-12-18T20:40:00Z" });
    const item = page.locator("[data-test-item=graf-1]");
    const table = item.getByRole("table");
    await expect(table).toBeVisible();
    await expect(table.locator("tbody tr").first()).toContainText("12");
    await expect(table.locator("tbody tr").nth(1)).toContainText("20");
    await expect(item.getByRole("textbox")).toHaveCount(0);
    await expect(item.getByRole("slider")).toHaveCount(0);
    await expectAccessible(page, true);
  });
});
