import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import type { GameInsight } from "../src/modules/games/api";
import { expectAccessible, expectReflow, lecturerPage, test, VIEWPORTS } from "./support/classes";
import { liveClassGame, orderByApi } from "./support/live-game";

/** Spillinnsikt (Story 7.7, FR-62, FR-34, FR-5, FR-73, NFR-6, AD-8, UX-DR55) on the local stack: a
 * fresh Class game with two Students and two Rule-based players, opened from the Oversikt's wall
 * and from «Vis som tabell»; its header, Seats and per-Role tables show the api's stored values; a
 * new Week appears live; Back returns focus to the same game; a Student is refused. What the api
 * answers, every mark included, is `backend/tests/sessions/test_game_insight.py`. Story 7.8 adds
 * the charts over the tables and their «Vis som tabell». */
const copy = nb.insight;
const ROLES = [nb.terms.retailer, nb.terms.wholesaler, nb.terms.distributor, nb.terms.factory];
const charts = copy.charts;

/** Story 7.8: both charts above the per-Role tables, Fabrikk at the top, every number the api's,
 * and «Vis som tabell» swapping each for its table and back with focus kept on the button. */
async function expectCharts(page: Page, answer: GameInsight) {
  const main = page.getByRole("main");
  const weeks = answer.roles[0]!.weeks.length;
  const bars = main.getByRole("region", { name: charts.orders.region });
  await expect(bars.locator('[data-chart="order-bars"]')).toBeVisible();
  const rows = bars.locator("tbody tr");
  await expect(rows).toHaveCount(5);
  await expect(rows.first().locator("th")).toHaveText(nb.terms.factory);
  await expect(rows.last().locator("th")).toHaveText(charts.orders.customers);
  await expect(bars.getByText(charts.orders.amplification)).toHaveCount(0);
  // Fabrikk's Orders and the customers' demand, as the api gave them (an Order not placed is empty).
  const factory = answer.roles[3]!.weeks.map((w) => (w.order === null ? "" : String(w.order)));
  await expect(rows.first().locator("td")).toHaveText(factory);
  await expect(rows.last().locator("td")).toHaveText(answer.demand.map((d) => String(d.demand)));
  const stock = main.getByRole("region", { name: charts.stock.region });
  await expect(stock.locator('[data-chart="stock-backlog"] g[data-row]')).toHaveCount(4);
  await expect(stock.locator("th[data-col]")).toHaveCount(weeks);

  // «Vis som tabell» under the Ordre chart: the same numbers as a table, then back.
  const block = main.locator('[data-chart-block="orders"]');
  const show = block.getByRole("button", { name: charts.showTable });
  await show.click();
  const table = main.getByRole("group", { name: charts.orders.tableRegion });
  await expect(table.locator("tbody tr")).toHaveCount(5);
  await expect(table.locator("tbody tr").first().locator("td")).toHaveText(factory);
  const back = block.getByRole("button", { name: charts.showChart });
  await expect(back).toBeFocused();
  await back.click();
  await expect(bars).toBeVisible();
  // And under «Lager og restordre»: two rows per Role, Fabrikk's first.
  const stockBlock = main.locator('[data-chart-block="stock"]');
  await stockBlock.getByRole("button", { name: charts.showTable }).click();
  const stockTable = main.getByRole("group", { name: charts.stock.tableRegion });
  await expect(stockTable.locator("tbody tr")).toHaveCount(8);
  await expect(stockTable.locator("tbody tr").first().locator("th")).toHaveText(charts.stock.stockRow(nb.terms.factory));
  await stockBlock.getByRole("button", { name: charts.showChart }).click();
  await expect(stock).toBeVisible();
}

async function untilLive(page: Page) {
  await expect(page.locator("html")).toHaveAttribute("data-live", "live", { timeout: 10_000 });
}

test("Spillinnsikt opens from the wall and the table, shows every Week as stored, follows the game and returns focus", async ({
  browser,
  lecturerSession,
}) => {
  test.slow(); // two Invitations through the worker, a Class session, a lock and a live game
  const game = await liveClassGame(browser, lecturerSession, 2, { aiMode: "rule_based" });
  const [first, second] = game.students;
  await orderByApi(first!, game.gameId, 1, 4);
  await orderByApi(second!, game.gameId, 1, 4);
  // Uke 2 is open and nobody has ordered: the game runs.
  const insightUrl = new RegExp(`/klasseokter/${game.sessionId}/oversikt/spill/${game.gameId}(\\?visning=tabell)?$`);

  // A Student of the game is refused the staff's read, the same as any other (FR-5).
  const refused = await first!.context.request.get(`/api/games/${game.gameId}/insight`);
  expect(refused.status()).toBe(403);

  const page = await lecturerPage(browser, lecturerSession, VIEWPORTS[2]!);
  await page.goto(`/klasseokter/${game.sessionId}/oversikt`);
  const main = page.getByRole("main");
  const grid = main.getByRole("region", { name: nb.wall.region }).getByRole("grid");
  await expect(grid.locator("[data-row] [role=gridcell][data-week]")).toHaveCount(2);

  // A click on the wall row opens the game.
  await grid.locator("[data-row] [role=gridcell][data-week]").first().click();
  await expect(page).toHaveURL(insightUrl);
  await expect(main.getByRole("heading", { level: 1, name: "Spill 1" })).toBeVisible();
  await expect(main.locator("[data-status]")).toHaveText(`${copy.statusLabel}: ${copy.status.running}`);
  const seats = main.getByRole("list", { name: copy.seatsLabel }).locator(":scope > li");
  await expect(seats).toHaveCount(4);
  await expect(seats.first()).toContainText(nb.terms.factory);
  await expect(seats.last()).toContainText(nb.terms.retailer);
  for (const student of [first!, second!]) await expect(main.getByRole("list", { name: copy.seatsLabel })).toContainText(student.name);
  await expect(seats.filter({ hasText: copy.aiPlayer })).toHaveCount(2);
  await expect(main.getByText(copy.noLinks)).toHaveCount(2);

  // One table per Role, Detaljist first, each in its own named region, every value the api's.
  const answer = await (await page.request.get(`/api/games/${game.gameId}/insight`)).json();
  const regions = main.getByRole("group", { name: / uke for uke$/ });
  await expect(regions).toHaveCount(4);
  for (const [index, role] of answer.roles.entries()) {
    const region = main.getByRole("group", { name: copy.region(ROLES[index]!) });
    const rows = region.locator("tbody tr");
    await expect(rows).toHaveCount(2);
    for (const [i, week] of role.weeks.entries()) {
      const cells = rows.nth(i).locator("td");
      await expect(rows.nth(i).locator("th")).toHaveText(String(week.week));
      await expect(cells.nth(0)).toHaveText(week.holder === "ai" ? copy.aiPlayer : week.name);
      await expect(cells.nth(1)).toHaveText(String(week.incoming_order));
      await expect(cells.nth(2)).toHaveText(String(week.incoming_delivery));
      await expect(cells.nth(3)).toHaveText(String(week.inventory));
      await expect(cells.nth(4)).toHaveText(String(week.backlog));
      await expect(cells.nth(4 + 1)).toHaveText(week.order === null ? copy.noOrder : String(week.order));
    }
  }
  await expectCharts(page, answer);
  // No Week total anywhere (FR-14 holds for the staff's page too).
  await expect(main.getByText(/ av \d+ uker|Uke \d+ av/)).toHaveCount(0);
  await expectAccessible(page, false);

  // The game moves on: the new Week appears without a reload (AD-8).
  await untilLive(page);
  await orderByApi(first!, game.gameId, 2, 5);
  await orderByApi(second!, game.gameId, 2, 5);
  await expect(main.getByRole("group", { name: copy.region(nb.terms.retailer) }).locator("tbody tr")).toHaveCount(3, {
    timeout: 5_000,
  });
  // The charts follow with the page: a third Uke column in both.
  await expect(main.getByRole("region", { name: charts.orders.region }).locator("th[data-col]")).toHaveCount(3);
  await expect(main.getByRole("region", { name: charts.stock.region }).locator("th[data-col]")).toHaveCount(3);

  // Back returns to the Oversikt with focus on the same game.
  await page.goBack();
  await expect(page.locator(":focus")).toHaveAccessibleName(/^Spill 1, Uke 1: /);
  // The address then drops the game, so a reload does not move focus again.
  await expect(page).toHaveURL(new RegExp(`/oversikt$`));

  // From «Vis som tabell»: Enter on the game's row header opens it; Back lands on that header.
  const toggle = main.getByRole("group", { name: nb.wall.table.view });
  await toggle.getByRole("radio", { name: nb.wall.table.table }).check();
  const header = main.getByRole("region", { name: nb.wall.region }).getByRole("rowheader", { name: "Spill 1", exact: true });
  await header.focus();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(insightUrl);
  await expect(main.getByRole("heading", { level: 1, name: "Spill 1" })).toBeVisible();
  // Its Oversikt crumb returns to the table too.
  await main.getByRole("navigation", { name: nb.navigation.breadcrumb }).getByRole("link", { name: nb.overview.crumb }).click();
  await expect(toggle.getByRole("radio", { name: nb.wall.table.table })).toBeChecked();
  await expect(header).toBeFocused();
  // A switch of view afterwards keeps focus on the Visningsbryter.
  await toggle.getByRole("radio", { name: nb.wall.table.wall }).check();
  await expect(toggle.getByRole("radio", { name: nb.wall.table.wall })).toBeFocused();
  await page.context().close();
});

test("at 320 px only the per-Role tables and the charts scroll sideways, each in its own region", async ({ browser, lecturerSession }) => {
  test.slow(); // an Invitation through the worker, a Class session, a lock and a live game
  const game = await liveClassGame(browser, lecturerSession, 1, { aiMode: "rule_based" });
  await orderByApi(game.students[0]!, game.gameId, 1, 4);
  const page = await lecturerPage(browser, lecturerSession, VIEWPORTS[0]!);
  await page.goto(`/klasseokter/${game.sessionId}/oversikt/spill/${game.gameId}`);
  const main = page.getByRole("main");
  await expect(main.getByRole("heading", { level: 1, name: "Spill 1" })).toBeVisible();
  const region = main.getByRole("group", { name: copy.region(nb.terms.retailer) });
  await expect(region.locator("tbody tr")).toHaveCount(2);
  // The table is wider than the phone: its region scrolls, the page does not.
  expect(await region.evaluate((element) => element.scrollWidth > element.clientWidth)).toBe(true);
  // Both charts and their «Vis som tabell» stand in regions of their own (Story 7.8).
  await expect(main.getByRole("region", { name: charts.orders.region }).locator("tbody tr")).toHaveCount(5);
  await expect(main.getByRole("region", { name: charts.stock.region })).toBeVisible();
  await expectAccessible(page, true);
  await main.locator('[data-chart-block="orders"]').getByRole("button", { name: charts.showTable }).click();
  await expect(main.getByRole("group", { name: charts.orders.tableRegion })).toBeVisible();
  await expectReflow(page, true);
  await page.context().close();
});
