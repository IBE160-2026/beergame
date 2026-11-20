import { expect, type Page, test } from "@playwright/test";

import { textWidth } from "../src/components/charts/chain-band-layout";
import { nb } from "../src/copy/nb";
import { bandEnds, bandLabels, type BandState } from "../src/modules/games/chain-band";
import classic from "../src/modules/games/fixtures/chain-band-classic.json";
import week3 from "../src/modules/games/fixtures/play-week-3.json";
import week11 from "../src/modules/games/fixtures/play-week-11.json";
import week30 from "../src/modules/games/fixtures/play-week-30.json";
import { loginByApi, untilFontsLoaded } from "./support/auth";
import { expectAccessible } from "./support/classes";
import { labelProblems, textReadable } from "./support/graph";

/** Kjedebånd on the play screen (Story 6.9, FR-14, FR-23, FR-73, NFR-6, UX-DR14, UX-DR15,
 * UX-DR73). As in `graph-over-table.spec.ts`, the game and its envelope are stand-ins with the
 * api's shapes: the engine's Grossist of a Classic game (held to the engine by
 * `backend/tests/games/test_play_fixture.py`). */
const GAME_ID = "01a1f8ee-34f2-70af-8800-f79281ed7a66";
const BAND = 'svg[data-chart="band"]';

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
  await page.route(`**/api/me/games/${GAME_ID}`, (route) =>
    route.fulfill({
      json: {
        id: GAME_ID,
        number: 17,
        role: "wholesaler",
        seats: envelope.table_status.seats,
        briefing_first: false,
        rules: { order_delay: 2, shipping_delay: 2, production_delay: 2, guided_weeks: 4, holding_cost: "0.50", backorder_cost: "1.00" },
        status: "running",
        week: envelope.seat_state.week,
      },
    }),
  );
  await page.route(`**/api/me/games/${GAME_ID}/play`, (route) => route.fulfill({ json: envelope }));
  await page.goto(`/spill/${GAME_ID}`);
  await expect(page.locator(BAND)).toHaveCount(1);
  await untilFontsLoaded(page);
}

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

/** Band labels whose rendered width exceeds the layout's estimate, which the layout relies on. */
function widerThanEstimated(page: Page) {
  return page.evaluate((selector) => {
    const svg = document.querySelector<SVGSVGElement>(selector)!;
    return [...svg.querySelectorAll<SVGTextElement>("text")]
      .filter((t) => t.getComputedTextLength() > Number(t.dataset.est) + 0.5)
      .map((t) => `${t.textContent}: ${t.getComputedTextLength()} > ${t.dataset.est}`);
  }, BAND);
}

for (const width of [320, 360, 1440]) {
  test.describe(`${width} px`, () => {
    test.use({ viewport: { width, height: 800 } });

    for (const envelope of [week3, week30] as Envelope[]) {
      test(`Uke ${envelope.seat_state.week}: the band fits, its labels are apart and readable, no axe violation`, async ({ page }) => {
        await openPlay(page, envelope);
        const fits = await page.evaluate((selector) => {
          const svg = document.querySelector<SVGSVGElement>(selector)!.getBoundingClientRect();
          return svg.left >= 0 && svg.right <= document.documentElement.clientWidth;
        }, BAND);
        expect(fits).toBe(true);
        expect(await widerThanEstimated(page)).toEqual([]);
        expect(await labelProblems(page)).toEqual([]);
        await textReadable(page);
        await expectAccessible(page, width < 1024);
      });
    }
  });
}

for (const width of [320, 360]) {
  test(`${width} px with 200 % text: the band is drawn at the doubled size, fits, and its labels stay apart`, async ({ page }) => {
    await page.setViewportSize({ width, height: 800 });
    await openPlay(page, week30 as Envelope, true);
    await expect(page.locator(BAND)).toHaveAttribute("font-size", "26");
    const fits = await page.evaluate((selector) => {
      const svg = document.querySelector<SVGSVGElement>(selector)!.getBoundingClientRect();
      return svg.left >= 0 && svg.right <= document.documentElement.clientWidth;
    }, BAND);
    expect(fits).toBe(true);
    expect(await widerThanEstimated(page)).toEqual([]);
    expect(await labelProblems(page)).toEqual([]);
  });
}

test("Uke 11 at 360 px: the Seat's own link, read as one sentence, before the graph", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await openPlay(page, week11);
  const state = week11.seat_state;
  const band = page.locator(BAND);
  const label = (key: string) => band.locator(`text[data-label="${key}"]`);
  await expect(label("upstream")).toHaveText("Distributør");
  await expect(label("downstream")).toHaveText("Detaljist");
  await expect(label("order")).toHaveText("Din ordre");
  await expect(label("incoming")).toHaveText(`Ordre inn ${state.incoming_order}`);
  await expect(label("delivery")).toHaveText(`Levering ${state.incoming_delivery}`);
  await expect(label("shipped")).toHaveText(`Sendt ${state.shipped}`);
  await expect(label("stock")).toHaveText(`Restordre ${state.backlog}`);
  await expect(label("supplyLine")).toHaveText(`På vei ${state.supply_line}`);
  await expect(band.locator("[data-mark=arrival]")).toHaveCount(state.supply_line_slots.filter((s) => s.quantity > 0).length);
  await expect(band.locator("[data-mark=backlog]")).toHaveCount(1);
  await expect(band.locator("title")).toHaveText(nb.games.play.band.svg);
  // Screen readers get one sentence; the SVG is hidden from them and takes no focus.
  const sentence = `Ordre inn ${state.incoming_order}, Levering ${state.incoming_delivery}, Sendt ${state.shipped}, Restordre ${state.backlog}, På vei ${state.supply_line}`;
  await expect(page.locator("[data-chain-band] p.sr-only")).toHaveText(sentence);
  expect(await band.evaluate((svg) => svg.closest('[aria-hidden="true"]') !== null)).toBe(true);
  // Reading order: Topplinje, Kjedebånd, Graf over tabell.
  const order = await page.evaluate(() => {
    const h1 = document.querySelector("main h1, h1")!;
    const bandEl = document.querySelector("[data-chain-band]")!;
    const region = document.querySelector('[role="region"][aria-label="Graf og tabell"]')!;
    const before = (a: Element, b: Element) => (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
    return before(h1, bandEl) && before(bandEl, region);
  });
  expect(order).toBe(true);
  // On the phone På vei is in the band, not a table row.
  await expect(page.getByRole("rowheader", { name: nb.terms.supplyLine, exact: true })).toBeHidden();
});

test("the layout's width estimate holds for every label of the fixture game, at 100 % and 200 % text", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await openPlay(page, week11);
  const roles = ["factory", "distributor", "wholesaler", "retailer"] as const;
  const items = new Map<string, { text: string; weight: number }>();
  for (const state of classic as BandState[]) {
    const labels = bandLabels(state, bandEnds(state.role, roles));
    const add = (text: string | null, weight: number) => text !== null && items.set(`${text}|${weight}`, { text, weight });
    add(labels.upstream, 400);
    add(labels.downstream, 400);
    add(labels.order, 600);
    add(labels.incoming, 600);
    add(labels.delivery, 400);
    add(labels.shipped, 400);
    labels.stock.forEach((text) => add(text, 700));
    add(labels.supplyLine, 600);
    add(labels.overdue, 600);
  }
  const all = [...items.values()];
  const measured = await page.evaluate(
    ({ all, sizes }) => {
      const svg = document.querySelector<SVGSVGElement>('svg[data-chart="band"]')!;
      const probe = document.createElementNS("http://www.w3.org/2000/svg", "text");
      svg.appendChild(probe);
      const out: { text: string; weight: number; size: number; width: number }[] = [];
      for (const size of sizes) {
        for (const { text, weight } of all) {
          probe.setAttribute("font-size", String(size));
          probe.setAttribute("font-weight", String(weight));
          probe.textContent = text;
          out.push({ text, weight, size, width: probe.getComputedTextLength() });
        }
      }
      probe.remove();
      return out;
    },
    { all, sizes: [13, 26] },
  );
  const over = measured
    .filter((m) => m.width > textWidth(m.text, m.size, m.weight as 400 | 600 | 700) + 0.5)
    .map((m) => `${m.text} (${m.weight}, ${m.size} px): ${m.width.toFixed(1)}`);
  expect(over).toEqual([]);
});
