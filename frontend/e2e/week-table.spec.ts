import { expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import week1 from "../src/modules/games/fixtures/play-week-1.json";
import week11 from "../src/modules/games/fixtures/play-week-11.json";
import { loginByApi } from "./support/auth";
import { expectAccessible } from "./support/classes";

/** The play screen's week table (Story 6.6, FR-14, FR-23, FR-73, NFR-1, NFR-6, UX-DR13, UX-DR17,
 * UX-DR18), on the local stack through the proxy as the demo Student. The envelope's shape and its
 * information boundary are pinned by `backend/tests/sessions/test_play.py`; a running Class game
 * needs its Start date and the sweep, so here the game and its envelope are stand-ins with the
 * api's shapes (as for Stories 6.2 to 6.5): the engine's Grossist in Uke 11 of a Classic game,
 * whose numbers `backend/tests/games/test_play_fixture.py` holds to the engine. */
const GAME_ID = "01a1f8ee-34f2-70af-8800-f79281ed7a66";
const copy = nb.games.play;

function game(week: number) {
  return {
    id: GAME_ID,
    number: 17,
    role: "wholesaler",
    seats: week11.table_status.seats,
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
  };
}

/** The demo Student's running game in Uke 11 and its envelope (Uke 1 with `week1`); the envelope
 * waits for `held` when given. */
async function withPlay(page: Page, envelope: typeof week11 = week11, held?: Promise<void>) {
  await page.route(`**/api/me/games/${GAME_ID}`, (route) => route.fulfill({ json: game(envelope.seat_state.week) }));
  await page.route(`**/api/me/games/${GAME_ID}/play`, async (route) => {
    await held;
    return route.fulfill({ json: envelope });
  });
}

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

/** The Uke columns the region shows in full, right of the sticky row labels. */
async function visibleWeeks(page: Page): Promise<number[]> {
  return page.evaluate(() => {
    const region = document.querySelector<HTMLElement>('[role="region"][aria-label="Graf og tabell"]')!;
    const box = region.getBoundingClientRect();
    const label = region.querySelector<HTMLElement>("th[scope=row]")!.getBoundingClientRect();
    return [...region.querySelectorAll<HTMLElement>("th[scope=col]")]
      .filter((th) => getComputedStyle(th).display !== "none")
      .filter((th) => {
        const r = th.getBoundingClientRect();
        return r.left >= label.right - 0.5 && r.right <= box.right + 0.5;
      })
      .map((th) => Number(th.textContent!.replace(/\D/g, "")));
  });
}

/** No text in the page below 13 px, and no table cell whose text is cut off. */
async function textReadable(page: Page) {
  const found = await page.evaluate(() => {
    const small = [...document.querySelectorAll<HTMLElement>("main *")]
      .filter((el) => el.offsetParent !== null && [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent?.trim()))
      .filter((el) => parseFloat(getComputedStyle(el).fontSize) < 13)
      .map((el) => el.textContent?.trim());
    const clipped = [...document.querySelectorAll<HTMLElement>("main th, main td")]
      .filter((el) => el.offsetParent !== null && (el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1))
      .map((el) => el.textContent?.trim());
    return { small, clipped };
  });
  expect(found).toEqual({ small: [], clipped: [] });
}

const VIEWPORTS = [
  { name: "320 px", width: 320, height: 640, phone: true, text200: false, weeks: [6, 7, 8, 9, 10, 11, 12, 13, 14, 15] },
  { name: "360 px", width: 360, height: 740, phone: true, text200: false, weeks: [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15] },
  { name: "320 px with 200 % text", width: 320, height: 640, phone: true, text200: true, weeks: null },
  { name: "360 px with 200 % text", width: 360, height: 740, phone: true, text200: true, weeks: null },
  { name: "1440 px", width: 1440, height: 900, phone: false, text200: false, weeks: null },
  // Tablets: the laptop layout in landscape (1024 px wide), the phone layout in portrait.
  { name: "tablet landscape", width: 1024, height: 768, phone: false, text200: false, weeks: null },
  { name: "tablet portrait", width: 768, height: 1024, phone: true, text200: false, weeks: null },
];

for (const vp of VIEWPORTS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("the Topplinje and the week table, nå in view and nothing scrolling outside the region", async ({ page }) => {
      if (vp.text200) {
        await page.addInitScript(() => {
          document.addEventListener("DOMContentLoaded", () => {
            const style = document.createElement("style");
            style.textContent = "html { font-size: 200% !important; }";
            document.head.appendChild(style);
          });
        });
      }
      await loginByApi(page, "student");
      await withPlay(page);
      await page.goto(`/spill/${GAME_ID}`);
      const main = page.getByRole("main");
      await expect(main.getByRole("heading", { level: 1 })).toHaveText(copy.week(11));
      await expect(main.getByText(copy.roleGame("Grossist", 17), { exact: true })).toBeVisible();
      await expect(main.getByText(nb.terms.totalCost, { exact: true })).toBeVisible();
      await expect(main.getByText("82,00 kr", { exact: true })).toBeVisible();
      const region = main.getByRole("region", { name: copy.table.region });
      await expect(region).toHaveAttribute("tabindex", "0");
      await expect(region.getByRole("columnheader")).toHaveText(
        Array.from({ length: vp.phone ? 12 : 15 }, (_, i) => `Uke ${(vp.phone ? 4 : 1) + i}`),
      );
      await expect(main.getByRole("link", { name: nb.games.briefing.title })).toHaveAttribute(
        "href",
        `/spill/${GAME_ID}/regler`,
      );
      await expectAccessible(page, vp.phone);

      const weeks = await visibleWeeks(page);
      if (vp.weeks) expect(weeks).toEqual(vp.weeks);
      expect(weeks).toContain(11);
      expect(weeks.at(-1)).toBeGreaterThan(11);
      if (vp.width === 320 || vp.text200) {
        // Earlier Uker are scrolled out of view.
        await expect(main.getByText(copy.table.swipe)).toBeVisible();
      } else {
        await expect(main.getByText(copy.table.swipe)).toHaveCount(0);
      }
      await textReadable(page);

      const rows = await region.locator("tbody tr").evaluateAll((trs) =>
        trs.filter((tr) => getComputedStyle(tr).display !== "none").map((tr) => tr.querySelector("th")!.textContent),
      );
      expect(rows).toEqual(
        vp.phone
          ? ["Ordre inn", "Levering", "Netto lager", "Posisjon", "Din ordre", "Kost, kr"]
          : ["Ordre inn", "Levering", "Sendt", "Netto lager", "På vei", "Posisjon", "Din ordre", "Kost, kr"],
      );
      if (!vp.phone) {
        // Two columns: the table at the left, «Setene» at the right of it.
        const table = (await region.boundingBox())!;
        const seats = (await main.getByRole("region", { name: nb.homes.student.seats }).boundingBox())!;
        expect(seats.x).toBeGreaterThan(table.x + table.width - 1);
      }
    });
  });
}

test("the cells: nå bold, Netto lager on its matrix step, arrivals boxed and labelled, Din ordre dashed", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  await loginByApi(page, "student");
  await withPlay(page);
  await page.goto(`/spill/${GAME_ID}`);
  const region = page.getByRole("region", { name: copy.table.region });
  const header = region.getByRole("columnheader");
  await expect(header.filter({ hasText: /^Uke 11$/ })).toHaveCSS("font-weight", "700");
  await expect(header.filter({ hasText: /^Uke 10$/ })).toHaveCSS("font-weight", "400");
  const cells = (row: string) => region.locator(`tr[data-row="${row}"] td:visible`);
  // Uke 4 … 15 at 360 px: index 7 is nå.
  await expect(cells("netInventory").nth(7)).toHaveText("−20");
  await expect(cells("netInventory").nth(7)).toHaveCSS("background-color", "rgb(181, 66, 58)"); // net-neg-3
  await expect(cells("netInventory").nth(7)).toHaveCSS("color", "rgb(255, 255, 255)");
  await expect(cells("netInventory").nth(4)).toHaveText("0");
  await expect(cells("netInventory").nth(0)).toHaveCSS("background-color", "rgb(106, 154, 200)"); // 12: net-pos-2
  await expect(cells("netInventory").nth(0)).toHaveCSS("font-weight", "400");
  await expect(cells("position").nth(7)).toHaveText("−4");
  await expect(cells("position").nth(7)).toHaveCSS("background-color", "rgba(0, 0, 0, 0)");
  await expect(cells("incomingDelivery").nth(8)).toHaveText(`4, ${copy.table.arrival}`);
  await expect(cells("incomingDelivery").nth(10)).toHaveText(`8, ${copy.table.arrival}`);
  await expect(cells("incomingDelivery").nth(11)).toHaveText("");
  await expect(cells("order").nth(7).locator("span[aria-hidden]")).toHaveCSS("border-top-style", "dashed");
  await expect(cells("order").nth(7)).toHaveText(copy.table.noOrderYet);
  await expect(cells("order").nth(6)).toHaveText("8");
  await expect(cells("cost").nth(7)).toHaveText("20");
  await expect(page.getByText(copy.table.arrivalKey)).toBeVisible();
  // The cells take no focus; the region does.
  expect(await region.locator("[tabindex]").count()).toBe(0);
});

test("a changed width brings nå back into view", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await loginByApi(page, "student");
  await withPlay(page);
  await page.goto(`/spill/${GAME_ID}`);
  await expect(page.getByRole("region", { name: copy.table.region })).toBeVisible();
  await page.setViewportSize({ width: 320, height: 640 });
  await expect.poll(() => visibleWeeks(page)).toEqual([6, 7, 8, 9, 10, 11, 12, 13, 14, 15]);
  await expect(page.getByText(copy.table.swipe)).toBeVisible();
});

test("Uke 1: the columns start at Uke 1 and run to Uke 5", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  await loginByApi(page, "student");
  await withPlay(page, week1);
  await page.goto(`/spill/${GAME_ID}`);
  const region = page.getByRole("region", { name: copy.table.region });
  await expect(region.getByRole("columnheader")).toHaveText(["Uke 1", "Uke 2", "Uke 3", "Uke 4", "Uke 5"]);
  await expect(page.getByText("6,00 kr", { exact: true })).toBeVisible();
});

test("on a throttled 4G profile the Skjelett shows in the real columns, then the data within 3 s", async ({
  page,
  browserName,
}) => {
  test.skip(browserName !== "chromium", "network throttling is a Chromium protocol");
  await page.setViewportSize({ width: 360, height: 740 });
  await loginByApi(page, "student");
  // The envelope is held until the play page's Skjelett has been seen, then let through.
  let release = () => {};
  await withPlay(page, week11, new Promise<void>((resolve) => (release = resolve)));
  const cdp = await page.context().newCDPSession(page);
  await cdp.send("Network.enable");
  // Lighthouse's mobile profile: 150 ms round trip, 1.6 Mbit/s down, 750 kbit/s up.
  await cdp.send("Network.emulateNetworkConditions", {
    offline: false,
    latency: 150,
    downloadThroughput: (1.6 * 1024 * 1024) / 8,
    uploadThroughput: (750 * 1024) / 8,
  });
  const started = Date.now();
  await page.goto(`/spill/${GAME_ID}`, { waitUntil: "commit" });
  // The Skjelett in the table's real rows («Uke» and the six phone rows) and twelve columns.
  await expect(page.locator("[data-skeleton] .border-l")).toHaveCount(7 * 12);
  release();
  await expect(page.getByRole("region", { name: copy.table.region })).toBeVisible({ timeout: 3_000 });
  expect(Date.now() - started).toBeLessThan(3_000);
});
