import { expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import week3 from "../src/modules/games/fixtures/play-week-3.json";
import week11 from "../src/modules/games/fixtures/play-week-11.json";
import week30 from "../src/modules/games/fixtures/play-week-30.json";
import { loginByApi, untilFontsLoaded } from "./support/auth";
import { expectAccessible } from "./support/classes";

/** Graf over tabell on the play screen (Story 6.7, AD-18 spike, FR-14, FR-23, FR-73, NFR-6,
 * UX-DR16, UX-DR18): the Netto lager and Posisjon graph and Kost per uke over the week table, on
 * the same columns. As in `week-table.spec.ts`, the game and its envelope are stand-ins with the
 * api's shapes: the engine's Grossist in an early, a middle and a late Uke of a Classic game
 * (`backend/tests/games/test_play_fixture.py` holds them to the engine). */
const GAME_ID = "01a1f8ee-34f2-70af-8800-f79281ed7a66";
const copy = nb.games.play;

type Envelope = typeof week11;

async function openPlay(page: Page, envelope: Envelope, text200 = false) {
  if (text200) {
    await page.addInitScript(() => {
      document.addEventListener("DOMContentLoaded", () => {
        const style = document.createElement("style");
        style.textContent = "html { font-size: 200% !important; }";
        document.head.appendChild(style);
      });
    });
  }
  await loginByApi(page, "student");
  const week = envelope.seat_state.week;
  await page.route(`**/api/me/games/${GAME_ID}`, (route) =>
    route.fulfill({
      json: {
        id: GAME_ID,
        number: 17,
        role: "wholesaler",
        seats: envelope.table_status.seats,
        briefing_first: false,
        rules: {
          order_delay: 2,
          shipping_delay: 2,
          production_delay: 2,
          guided_weeks: 4,
          holding_cost: "0.50",
          backorder_cost: "1.00",
        },
        status: "running",
        week,
      },
    }),
  );
  await page.route(`**/api/me/games/${GAME_ID}/play`, (route) => route.fulfill({ json: envelope }));
  await page.goto(`/spill/${GAME_ID}`);
  await expect(page.locator('svg[data-chart="net"]:visible')).toHaveCount(1);
  await untilFontsLoaded(page);
}

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

/** Every drawn Week mark's distance in px from the centre of its `th[scope=col]`, the now-line's
 * from the nå column's right edge, and the Uker drawn. */
function alignment(page: Page) {
  return page.evaluate(() => {
    const shown = (el: Element) => el.getClientRects().length > 0;
    const centres = new Map<number, number>();
    let nowRight = Number.NaN;
    for (const th of document.querySelectorAll<HTMLElement>("th[scope=col][data-col]")) {
      if (!shown(th)) continue;
      const r = th.getBoundingClientRect();
      centres.set(Number(th.dataset.col), r.left + r.width / 2);
      if (th.hasAttribute("data-now")) nowRight = r.right;
    }
    const off: { mark: string; week: number; by: number }[] = [];
    const drawn = new Set<number>();
    const at = (mark: string, week: number, x: number) => {
      drawn.add(week);
      const centre = centres.get(week);
      off.push({ mark, week, by: centre === undefined ? Number.POSITIVE_INFINITY : Math.abs(x - centre) });
    };
    for (const svg of document.querySelectorAll<SVGSVGElement>("svg[data-chart=net], svg[data-chart=cost]")) {
      if (!shown(svg)) continue;
      const left = svg.getBoundingClientRect().left;
      for (const el of svg.querySelectorAll<SVGElement>("[data-mark]")) {
        const mark = el.dataset.mark!;
        if (el.dataset.weeks) {
          const xs = el.dataset.x!.split(" ").map(Number);
          el.dataset.weeks.split(" ").forEach((week, i) => at(mark, Number(week), left + xs[i]!));
        } else if (mark === "cost") {
          for (const rect of el.querySelectorAll("rect")) {
            const r = rect.getBoundingClientRect();
            at(mark, Number(el.dataset.week), r.left + r.width / 2);
          }
        } else {
          const r = el.getBoundingClientRect();
          at(mark, Number(el.dataset.week), r.left + r.width / 2);
        }
      }
    }
    const line = document.querySelector<HTMLElement>("[data-now-line]")!.getBoundingClientRect();
    return {
      worst: Math.max(...off.map((o) => o.by)),
      off: off.filter((o) => o.by > 1),
      marks: off.length,
      drawn: [...drawn].sort((a, b) => a - b),
      nowLine: Math.abs(line.left + line.width / 2 - nowRight),
    };
  });
}

/** Pairs of graph labels (SVG text: axis ticks, «Nå», the direct labels) whose boxes overlap,
 * and labels that leave their SVG. */
function labelProblems(page: Page) {
  return page.evaluate(() => {
    const texts = [...document.querySelectorAll<SVGTextElement>("svg[data-chart] text")].filter(
      (t) => t.getClientRects().length > 0,
    );
    const boxes = texts.map((t) => ({ text: t.textContent, box: t.getBoundingClientRect(), svg: t.ownerSVGElement!.getBoundingClientRect() }));
    const problems: string[] = [];
    boxes.forEach((a, i) => {
      if (a.box.left < a.svg.left - 0.5 || a.box.right > a.svg.right + 0.5 || a.box.top < a.svg.top - 0.5 || a.box.bottom > a.svg.bottom + 0.5) {
        problems.push(`${a.text} leaves its chart`);
      }
      boxes.slice(i + 1).forEach((b) => {
        const w = Math.min(a.box.right, b.box.right) - Math.max(a.box.left, b.box.left);
        const h = Math.min(a.box.bottom, b.box.bottom) - Math.max(a.box.top, b.box.top);
        if (w > 0.5 && h > 0.5) problems.push(`${a.text} overlaps ${b.text}`);
      });
    });
    return problems;
  });
}

/** No text in the page below 13 px (SVG text included) and no table cell whose text is cut off. */
async function textReadable(page: Page) {
  const found = await page.evaluate(() => {
    const small = [...document.querySelectorAll<Element>("main *")]
      .filter((el) => el.getClientRects().length > 0 && [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent?.trim()))
      .filter((el) => parseFloat(getComputedStyle(el).fontSize) < 13)
      .map((el) => el.textContent?.trim());
    const clipped = [...document.querySelectorAll<HTMLElement>("main th, main td")]
      .filter((el) => el.getClientRects().length > 0 && (el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1))
      .map((el) => el.textContent?.trim());
    return { small, clipped };
  });
  expect(found).toEqual({ small: [], clipped: [] });
}

const VIEWPORTS = [
  { name: "320 px", width: 320, height: 640, phone: true, text200: false },
  { name: "360 px", width: 360, height: 740, phone: true, text200: false },
  { name: "1440 px", width: 1440, height: 900, phone: false, text200: false },
  { name: "320 px with 200 % text", width: 320, height: 640, phone: true, text200: true },
  { name: "360 px with 200 % text", width: 360, height: 740, phone: true, text200: true },
];

const WEEKS: [string, Envelope][] = [
  ["early (Uke 3)", week3 as Envelope],
  ["middle (Uke 11)", week11],
  ["late (Uke 30)", week30 as Envelope],
];

for (const vp of VIEWPORTS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    for (const [when, envelope] of WEEKS) {
      test(`${when}: every mark within 1 px of its column, labels apart, readable, accessible`, async ({ page }) => {
        await openPlay(page, envelope, vp.text200);
        const week = envelope.seat_state.week;
        const found = await alignment(page);
        expect(found.off).toEqual([]);
        expect(found.worst).toBeLessThanOrEqual(1);
        expect(found.nowLine).toBeLessThanOrEqual(1);
        // Both lines stop at nå; nothing is drawn right of it.
        expect(Math.max(...found.drawn)).toBe(week);
        const first = vp.phone ? Math.max(1, week - 7) : 1;
        expect(found.drawn[0]).toBe(first);
        expect(await labelProblems(page)).toEqual([]);
        await textReadable(page);
        await expectAccessible(page, vp.phone);
      });
    }
  });
}

test("the marks, labels and key at Uke 11", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  await openPlay(page, week11);
  const graph = page.locator('svg[data-chart="net"]:visible');
  await expect(graph.locator("text[data-label=net]")).toHaveText("Restordre 20");
  await expect(graph.locator("text[data-label=position]")).toHaveText("Posisjon −4");
  await expect(graph.locator("text[data-label=now]")).toHaveText(copy.graph.now);
  await expect(graph.locator("title")).toHaveText(copy.graph.netSvg);
  // Posisjon: a square at every Uke from nå − 7 to nå.
  await expect(graph.locator("[data-mark=position]")).toHaveCount(8);
  const cost = page.locator('svg[data-chart="cost"]:visible');
  await expect(cost.locator("[data-mark=cost]")).toHaveCount(8);
  await expect(page.locator('svg[data-chart="axis"]:visible text')).toHaveText(["−20", "0", "20", "40", "40 kr"]);
  const key = page.getByRole("cell", { name: /Kost per uke/ }).filter({ visible: true });
  await expect(key).toContainText("restordre 1,00");
  await expect(key).toContainText("lager 0,50");
  await expect(page.getByText(copy.graph.netTitle).filter({ visible: true })).toBeVisible();
  // The graph is hidden from screen readers: the table is its alternative.
  const unhidden = await page.evaluate(
    () => [...document.querySelectorAll("svg[data-chart]")].filter((svg) => !svg.closest('[aria-hidden="true"]')).length,
  );
  expect(unhidden).toBe(0);
  // Nå bold ink, the other Uke numbers grey (Issue #124).
  const header = page.getByRole("region", { name: copy.table.region }).getByRole("columnheader");
  await expect(header.filter({ hasText: /^Uke 11$/ })).toHaveCSS("color", "rgb(15, 42, 71)");
  await expect(header.filter({ hasText: /^Uke 10$/ })).toHaveCSS("color", "rgb(94, 111, 130)");
  await expect(header.filter({ hasText: /^Uke 12$/ })).toHaveCSS("color", "rgb(94, 111, 130)");
});

test("the late Uke: the cost axis has grown past 40 kr and no bar is cut", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await openPlay(page, week30 as Envelope);
  await expect(page.locator('svg[data-chart="axis"]:visible text').last()).toHaveText("80 kr");
  const cut = await page.evaluate(() => {
    const svg = [...document.querySelectorAll<SVGSVGElement>('svg[data-chart="cost"]')].find((s) => s.getClientRects().length)!;
    const top = svg.getBoundingClientRect().top;
    return [...svg.querySelectorAll("rect")].filter((r) => r.getBoundingClientRect().top < top - 0.5).length;
  });
  expect(cut).toBe(0);
  // No line says the axis grows: it grew in an earlier Uke.
  await expect(page.getByText(/Aksen går nå til/)).toHaveCount(0);
});

test("scrolled at 360 px with 200 % text, the axis labels and captions stay in the sticky column and every mark over its column", async ({
  page,
}) => {
  await page.setViewportSize({ width: 360, height: 740 });
  await openPlay(page, week11, true);
  const region = page.getByRole("region", { name: copy.table.region });
  const offsets = () =>
    page.evaluate(() => {
      const region = document.querySelector<HTMLElement>('[role="region"][aria-label="Graf og tabell"]')!;
      const left = region.getBoundingClientRect().left;
      const shown = (el: Element) => el.getClientRects().length > 0;
      const axes = [...document.querySelectorAll<SVGSVGElement>('svg[data-chart="axis"]')].filter(shown);
      const captions = [...region.querySelectorAll<HTMLElement>("td[colspan] > div.sticky")].filter(shown);
      return {
        scrolled: region.scrollLeft,
        off: [...axes, ...captions].map((el) => Math.round(Math.abs(el.getBoundingClientRect().left - left))),
      };
    });
  // On load the region is scrolled to nå (earlier Uker hidden): the labels still sit at its left.
  const loaded = await offsets();
  expect(loaded.scrolled).toBeGreaterThan(0);
  expect(loaded.off.length).toBe(4);
  expect(Math.max(...loaded.off)).toBeLessThanOrEqual(1);
  expect((await alignment(page)).off).toEqual([]);
  await region.evaluate((el) => {
    el.scrollLeft = 0;
  });
  await expect(page.getByText(copy.table.swipe)).toHaveCount(0);
  expect(Math.max(...(await offsets()).off)).toBeLessThanOrEqual(1);
  expect((await alignment(page)).off).toEqual([]);
});

test("after a change of width or text size the graph is measured again and every mark is back over its column", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await openPlay(page, week11);
  // The laptop layout draws Uke 1 … 11; the phone layout, after the switch, Uke 4 … 11.
  await expect.poll(async () => (await alignment(page)).drawn[0]).toBe(1);
  await page.setViewportSize({ width: 320, height: 640 });
  await expect.poll(async () => (await alignment(page)).drawn[0]).toBe(4);
  expect((await alignment(page)).off).toEqual([]);
  await page.addStyleTag({ content: "html { font-size: 200% !important; }" });
  await expect.poll(async () => (await alignment(page)).off).toEqual([]);
  expect((await alignment(page)).worst).toBeLessThanOrEqual(1);
  expect(await labelProblems(page)).toEqual([]);
});
