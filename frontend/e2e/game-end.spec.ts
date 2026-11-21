import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { formatNumber } from "../src/lib/number-format";
import result from "../src/modules/games/fixtures/result-classic.json";
import { loginByApi } from "./support/auth";
import { expectAccessible, test } from "./support/classes";
import { liveClassGame, orderByApi } from "./support/live-game";
import { GAME_ID } from "./support/play";

/** «Spillet er ferdig» (Story 6.18, FR-28, FR-73, NFR-6, UX-DR30, UX-DR72, UX-DR73) with a
 * stand-in finished game and its result (`fixtures/result-classic.json`, the spine's Kjedens
 * regning); the api's result, its refusals and the step are `backend/tests/sessions/
 * test_game_end.py`. The last test ends a real two-Uke game on the local stack. */
const copy = nb.games.play;
const chain = copy.chain;
const kr = (value: string) => formatNumber(value, { kroner: true });
const money = (value: string) => formatNumber(value, { decimals: 2 });
const primaries = (page: Page) => page.getByRole("main").locator("a.bg-ink, button.bg-ink");

const SEATS = [
  { role: "factory", holder: "ai", name: null, mine: false, ordered: false, wait_started_at: null, mark: null },
  { role: "distributor", holder: "student", name: "Jonas Berg", mine: false, ordered: false, wait_started_at: null, mark: null },
  { role: "wholesaler", holder: "student", name: "Demo Student", mine: true, ordered: false, wait_started_at: null, mark: null },
  { role: "retailer", holder: "ai", name: null, mine: false, ordered: false, wait_started_at: null, mark: null },
];

async function openFinished(page: Page, { failFirst = false } = {}) {
  await loginByApi(page, "student");
  await page.route(`**/api/me/games/${GAME_ID}`, (route) =>
    route.fulfill({
      json: {
        id: GAME_ID,
        number: 17,
        role: "wholesaler",
        seats: SEATS,
        briefing_first: false,
        rules: { order_delay: 2, shipping_delay: 2, production_delay: 2, guided_weeks: 4, holding_cost: "0.50", backorder_cost: "1.00" },
        status: "finished",
        week: null,
        server_now: "2026-11-21T10:00:00Z",
        seat_state: null,
        turn: null,
      },
    }),
  );
  let failing = failFirst;
  await page.route(`**/api/me/games/${GAME_ID}/result`, (route) =>
    failing ? route.fulfill({ status: 500, json: { error: { code: "internal", message: "x" } } }) : route.fulfill({ json: result }),
  );
  await page.goto(`/spill/${GAME_ID}`);
  if (failFirst) {
    // A failed read of the result: the page-error line with «Prøv igjen», then the screen.
    const retry = page.getByRole("button", { name: nb.system.retry });
    await expect(page.getByText(nb.system.pageError)).toBeVisible();
    failing = false;
    await retry.click();
  }
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.end.title);
}

test("a failed read of the result shows the page-error line, and «Prøv igjen» shows the screen", async ({ page }) => {
  await openFinished(page, { failFirst: true });
  await expect(page.locator("[data-chain-total]")).toHaveText(kr("2266"));
});

for (const viewport of [
  { width: 320, height: 640, phone: true },
  { width: 360, height: 740, phone: true },
  { width: 1440, height: 900, phone: false },
]) {
  test.describe(`${viewport.width} px`, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });

    test("the chain's Total cost first, then Kjedens regning per Role, the chart and «Gå til Debrief»", async ({ page }) => {
      await openFinished(page);
      const main = page.getByRole("main");
      await expect(main.getByText(copy.roleGame("Grossist", 17), { exact: true })).toBeVisible();
      // The spine's order (EXPERIENCE.md → Spillet er ferdig).
      const order = await main.evaluate((root, texts) => {
        // The hero total has a plain space before «kr», so «kr» can wrap at 200 % text.
        const plain = (text: string) => text.replace(/ /g, " ");
        const body = plain(root.textContent ?? "");
        return texts.map((text) => body.indexOf(plain(text)));
      }, [copy.end.totalLabel, kr("2266"), copy.end.totalNote, chain.bill, chain.overTime, copy.end.why, copy.end.toDebrief]);
      expect(order.every((at) => at >= 0)).toBe(true);
      expect(order).toEqual([...order].sort((a, b) => a - b));
      await expect(page.locator("[data-chain-total]")).toHaveText(kr("2266"));

      const bill = page.locator("[data-chain-bill] table");
      await expect(bill.locator("tbody th")).toHaveText(["Detaljist", "Grossist (deg)", "Distributør", "Fabrikk"]);
      await expect(bill.locator("tbody tr[data-own]")).toHaveCount(1);
      await expect(bill.locator("tbody tr").nth(1).locator("td")).toHaveText([money("154.5"), money("399"), money("553.5")]);
      await expect(bill.locator("tfoot tr")).toHaveText(new RegExp(`${chain.chain}.*${money("2266")}`));
      await expect(bill.locator("[data-bar]")).toHaveCount(4);

      // One primary: «Gå til Debrief», which leads to Hjem until the Debrief exists (Epic 9).
      await expect(primaries(page)).toHaveCount(1);
      await expect(primaries(page)).toHaveText(copy.end.toDebrief);
      await expect(primaries(page)).toHaveAttribute("href", "/hjem");

      // The chart, and «Vis som tabell» opens Uke / Lager / Restordre / Sum in place, and back.
      const chart = page.locator("[data-chain-cost-chart]");
      await expect(chart.locator("svg[data-chart=cost-area]")).toBeVisible();
      await expect(chart.locator("[data-mark=end-labels] text")).toHaveText([
        `${chain.backorder} ${money("1365")}`,
        `${chain.holding} ${money("901")}`,
      ]);
      await expectAccessible(page, viewport.phone);
      await chart.getByRole("button", { name: chain.showTable }).click();
      const table = chart.locator("[data-chain-cost-table]");
      await expect(table.locator("thead th")).toHaveText([nb.terms.week, chain.holding, chain.backorder, chain.sum]);
      await expect(table.locator("tbody tr")).toHaveCount(36);
      await expect(table.locator("tbody tr").last().locator("td")).toHaveText([money("901"), money("1365"), money("2266")]);
      await expect(chart.locator("svg")).toHaveCount(0);
      await chart.getByRole("button", { name: chain.showChart }).click();
      await expect(chart.locator("svg[data-chart=cost-area]")).toBeVisible();
    });
  });
}

test("live: the last Order ends the game on «Spillet er ferdig», and Hjem shows it finished", async ({
  browser,
  lecturerSession,
}) => {
  test.slow(); // an Invitation through the worker, a Class session and a lock
  const game = await liveClassGame(browser, lecturerSession, 1, {
    aiMode: "rule_based",
    gameSettings: { weeks: 2, demand: { kind: "step", start: 4, new_level: 8, change_week: 2 } },
  });
  const [me] = game.students as [(typeof game.students)[0]];
  try {
    const page = await me.context.newPage();
    await page.goto(`/spill/${game.gameId}`);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.week(1));
    await expect(page.locator("html")).toHaveAttribute("data-live", "live", { timeout: 10_000 });
    await orderByApi(me, game.gameId, 1, 4);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.week(2));
    // The last Order: the page turns to «Spillet er ferdig» without a reload.
    await orderByApi(me, game.gameId, 2, 4);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.end.title);
    await expect(page.locator("[data-chain-total]")).toHaveText(/\d,\d\d/);
    await expect(page.locator("[data-chain-bill] tbody tr[data-own]")).toHaveCount(1);
    await expect(page.locator("[data-chain-cost-table], [data-chain-cost-chart] svg")).toHaveCount(1);

    await page.goto("/hjem");
    await expect(page.getByRole("main").getByText(nb.homes.student.finished, { exact: true })).toBeVisible();
    await expect(page.getByRole("main").getByRole("link", { name: nb.homes.student.toResult })).toHaveAttribute(
      "href",
      `/spill/${game.gameId}`,
    );
  } finally {
    await me.context.close();
  }
});
