import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { loginByApi } from "./support/auth";
import { expectAccessible, freshClass, lecturerPage, test, VIEWPORTS } from "./support/classes";
import { textReadable } from "./support/graph";
import { liveClassGame, orderByApi } from "./support/live-game";

/** The Oversikt (Story 7.1, FR-39, FR-5, FR-14, FR-72, FR-73, NFR-6, UX-DR40) on the local stack:
 * a fresh Class game in which one of two Students has ordered waits for the other by name, at
 * 1440 px, 320 px and with 200 % text; before the Start date the page lists the allocation only;
 * a Student is refused. What the api stores and answers is `backend/tests/sessions/test_overview.py`
 * and `backend/tests/games/test_game_summaries.py`. */
const copy = nb.overview;
const live = copy.live;
const CSRF = { "X-Requested-With": "olspillet" };
const DAY = 24 * 60 * 60 * 1000;

/** Wait until the page's event stream has sent `ready`: from then on no change is missed. */
async function untilLive(page: Page) {
  await expect(page.locator("html")).toHaveAttribute("data-live", "live", { timeout: 10_000 });
}

test("the Class's Lecturer sees the game wait for the Student who has not ordered, at every width", async ({
  browser,
  lecturerSession,
}) => {
  const game = await liveClassGame(browser, lecturerSession, 2, { aiMode: "rule_based" });
  const [first, second] = game.students;
  await orderByApi(first!, game.gameId, 1, 4);
  for (const viewport of VIEWPORTS) {
    const page = await lecturerPage(browser, lecturerSession, viewport);
    await page.goto(`/klasseokter/${game.sessionId}/oversikt`);
    const main = page.getByRole("main");
    await expect(main.getByRole("heading", { level: 1, name: copy.title })).toBeVisible();
    await expect(main.getByText("0 ferdig · 0 pågår · 1 venter")).toBeVisible();
    await expect(main.getByText(/^Oppdatert \d\d:\d\d:\d\d$/)).toBeVisible();
    const group = main.getByRole("region", { name: `${copy.groups.waiting} 1` });
    await expect(group).toBeVisible();
    const row = group.getByRole("listitem").first();
    await expect(row).toContainText("Spill 1");
    await expect(row).toContainText("Uke 1");
    await expect(row).toContainText(new RegExp(`Venter på ${second!.name} \\([A-Za-zøå]+\\), (under 1 min|\\d+ min)`));
    await expect(row.getByRole("list", { name: copy.seatsLabel("Spill 1") }).getByRole("listitem")).toHaveCount(4);
    await expect(row.getByRole("list", { name: copy.seatsLabel("Spill 1") })).toContainText(/^Fabrikk: /);
    await expect(row).toContainText(/0\s?kr/);
    // No Week total and nothing that hints at the game's length (FR-14).
    await expect(main.getByText(/ av \d+ uker|Uke \d+ av/)).toHaveCount(0);
    await expectAccessible(page, viewport.phone);
    await page.context().close();
  }
});

test("the Matrisevegg reads every game Uke by Uke from the keyboard and keeps focus as the game moves on", async ({
  browser,
  lecturerSession,
}) => {
  const wall = nb.wall;
  const game = await liveClassGame(browser, lecturerSession, 2, { aiMode: "rule_based" });
  const [first, second] = game.students;
  for (const week of [1, 2, 3]) {
    await orderByApi(first!, game.gameId, week, 4);
    await orderByApi(second!, game.gameId, week, 4);
  }
  // Uke 4 is open and nobody has ordered: the game runs.
  for (const viewport of [VIEWPORTS[2]!, VIEWPORTS[0]!]) {
    const page = await lecturerPage(browser, lecturerSession, viewport);
    await page.goto(`/klasseokter/${game.sessionId}/oversikt`);
    const main = page.getByRole("main");
    await expect(main.getByRole("list", { name: wall.legend }).getByRole("listitem")).toHaveText([...wall.bins]);
    await expect(main.getByText(wall.minusNote)).toBeVisible();
    // Which Role and measure the cells show, on screen (Fabrikk until another is chosen).
    await expect(main.getByText(wall.shown(nb.terms.netInventory, nb.terms.factory), { exact: true })).toBeVisible();
    const region = main.getByRole("region", { name: wall.region });
    await expect(region).toHaveAttribute("tabindex", "0");
    const grid = region.getByRole("grid");
    await expect(grid.getByRole("rowheader", { name: `${copy.groups.running} 1`, exact: true })).toBeVisible();
    await expect(grid.getByRole("rowheader", { name: /^Spill 1, pågår, kjedekost \d[\d\s]*\skr$/ })).toBeVisible();
    await expect(grid.getByRole("columnheader")).toHaveCount(5); // Spill + Uke 1–4
    const cells = grid.locator("[data-row] [role=gridcell]");
    await expect(cells).toHaveCount(4);
    // Each cell is read where it stands, with the value also where it prints «−» or nothing.
    for (let week = 1; week <= 4; week++) {
      await expect(cells.nth(week - 1)).toHaveAccessibleName(new RegExp(`^Spill 1, Uke ${week}: Netto lager −?\\d+\\.$`));
    }
    // One Tab stop: from the region into the first cell, then out of the wall.
    await region.focus();
    await page.keyboard.press("Tab");
    await expect(cells.nth(0)).toBeFocused();
    await page.keyboard.press("ArrowRight");
    await expect(cells.nth(1)).toBeFocused();
    await page.keyboard.press("End");
    await expect(cells.nth(3)).toBeFocused();
    await page.keyboard.press("Home");
    await expect(cells.nth(0)).toBeFocused();
    await page.keyboard.press("ArrowRight");
    await expect(page.locator("[data-focus-ring]")).toHaveCount(1);
    await expectAccessible(page, viewport.phone);
    if (viewport === VIEWPORTS[0]) {
      // The game moves on and would change group while a cell has focus (Story 7.5, UX-DR44): its
      // values update in place, the row stays under «Pågår» and focus stays on Spill 1, Uke 2.
      await untilLive(page);
      await orderByApi(first!, game.gameId, 4, 4);
      await expect(main.locator("[data-headline]")).toHaveText("0 ferdig · 0 pågår · 1 venter", { timeout: 5_000 });
      await expect(grid.getByRole("rowheader", { name: `${copy.groups.running} 1`, exact: true })).toBeVisible();
      await expect(grid.getByRole("rowheader", { name: /^Spill 1, venter på / })).toBeVisible();
      await expect(page.locator(":focus")).toHaveAccessibleName(/^Spill 1, Uke 2: /);
      // Once focus leaves the wall, the row moves to its new group.
      await page.keyboard.press("Tab");
      await expect(grid.locator(":focus")).toHaveCount(0);
      await expect(grid.getByRole("rowheader", { name: `${copy.groups.waiting} 1`, exact: true })).toBeVisible();
    }
    await page.context().close();
  }
});

test("«Vis som tabell» prints every cell at 13 px, sorts with aria-sort and keeps focus on the same game", async ({
  browser,
  lecturerSession,
}) => {
  const wall = nb.wall;
  const view = wall.table;
  const game = await liveClassGame(browser, lecturerSession, 2, { aiMode: "rule_based" });
  const [first, second] = game.students;
  for (const week of [1, 2]) {
    await orderByApi(first!, game.gameId, week, 4);
    await orderByApi(second!, game.gameId, week, 4);
  }
  // Uke 3 is open and nobody has ordered: the game runs.
  for (const viewport of VIEWPORTS) {
    const page = await lecturerPage(browser, lecturerSession, viewport);
    await page.goto(`/klasseokter/${game.sessionId}/oversikt`);
    const main = page.getByRole("main");
    const toggle = main.getByRole("group", { name: view.view });
    await expect(toggle.getByRole("radio", { name: view.wall })).toBeChecked();
    await expect(main.getByRole("region", { name: wall.region }).getByRole("grid")).toBeVisible();
    // From the keyboard: the arrow key on the radios chooses the table.
    await toggle.getByRole("radio", { name: view.wall }).focus();
    await page.keyboard.press("ArrowRight");
    await expect(toggle.getByRole("radio", { name: view.table })).toBeChecked();
    const region = main.getByRole("region", { name: wall.region });
    const table = region.getByRole("table");
    await expect(table).toBeVisible();
    await expect(region.getByRole("grid")).toHaveCount(0);
    await expect(main.getByText(wall.minusNote)).toHaveCount(0);
    await expect(main.getByText(wall.shown(nb.terms.netInventory, nb.terms.factory), { exact: true })).toBeVisible();
    // Headers: Spill, Status, Venter på, Kjedekost and Uke 1–3; one row header per game.
    for (const name of ["Uke 1", "Uke 2", "Uke 3"]) {
      await expect(table.getByRole("columnheader", { name, exact: true })).toBeVisible();
    }
    const header = table.getByRole("rowheader", { name: "Spill 1", exact: true });
    await expect(header).toBeVisible();
    const cells = table.locator("tbody tr").first().locator("td[data-week]");
    await expect(cells).toHaveCount(3);
    for (let week = 1; week <= 3; week++) await expect(cells.nth(week - 1)).toHaveText(/^−?\d+$/);
    await expect(table.locator("tbody tr").first().locator("td").first()).toHaveText(wall.status.running);
    await expect(table.getByRole("columnheader", { name: view.status })).toHaveAttribute("aria-sort", "ascending");
    await textReadable(page);
    await expectAccessible(page, viewport.phone);
    if (viewport === VIEWPORTS[2]) {
      // Sorting by kjedekost, and again the other way; the header carries aria-sort.
      const cost = table.getByRole("columnheader", { name: wall.figureHeader });
      await cost.getByRole("button").click();
      await expect(cost).toHaveAttribute("aria-sort", "ascending");
      await expect(table.getByRole("columnheader", { name: view.status })).not.toHaveAttribute("aria-sort", /.*/);
      await cost.getByRole("button").click();
      await expect(cost).toHaveAttribute("aria-sort", "descending");

      // Focus on the game's row header stays there as the game moves on and waits.
      await header.focus();
      await orderByApi(first!, game.gameId, 3, 4);
      await expect(table.locator("tbody tr").first().locator("td").first()).toHaveText(wall.status.waiting);
      await expect(header).toBeFocused();
      // Switching views keeps the same game as the Tab stop: the wall's cell of Spill 1.
      await toggle.getByRole("radio", { name: view.wall }).check();
      await region.focus();
      await page.keyboard.press("Tab");
      await expect(page.locator(":focus")).toHaveAccessibleName(/^Spill 1, Uke 1: /);
      await page.keyboard.press("End");
      await toggle.getByRole("radio", { name: view.table }).check();
      await region.focus();
      await page.keyboard.press("Tab"); // the Spill sort button
      await page.keyboard.press("Tab");
      await page.keyboard.press("Tab");
      await page.keyboard.press("Tab");
      await page.keyboard.press("Tab");
      await expect(header).toBeFocused();
      await toggle.getByRole("radio", { name: view.wall }).check();
      await region.focus();
      await page.keyboard.press("Tab");
      await expect(page.locator(":focus")).toHaveAccessibleName(/^Spill 1, Uke 3: /);
    }
    await page.context().close();
  }
});

test("Veggfiltre change wall and table at once, with the class median over the wall and under it", async ({
  browser,
  lecturerSession,
}) => {
  const wall = nb.wall;
  const view = wall.table;
  const game = await liveClassGame(browser, lecturerSession, 2, { aiMode: "rule_based" });
  const [first, second] = game.students;
  for (const week of [1, 2]) {
    await orderByApi(first!, game.gameId, week, 4);
    await orderByApi(second!, game.gameId, week, 4);
  }
  await orderByApi(first!, game.gameId, 3, 4); // Uke 3: the game waits for the second Student
  for (const viewport of [{ name: "1280 px", width: 1280, height: 800, phone: false }, ...VIEWPORTS]) {
    const page = await lecturerPage(browser, lecturerSession, viewport);
    const requests: string[] = [];
    page.on("request", (request) => requests.push(request.url()));
    await page.goto(`/klasseokter/${game.sessionId}/oversikt`);
    const main = page.getByRole("main");
    const region = main.getByRole("region", { name: wall.region });
    const grid = region.getByRole("grid");
    // Fabrikk, Netto lager and every game until another is chosen; counts after each status.
    const roles = main.getByRole("group", { name: wall.filters.role });
    const cellsFilter = main.getByRole("group", { name: wall.filters.cells });
    const status = main.getByRole("group", { name: wall.filters.status });
    await expect(roles.getByRole("button", { name: nb.terms.factory })).toHaveAttribute("aria-pressed", "true");
    await expect(roles.getByRole("button", { name: nb.terms.retailer })).toHaveAttribute("aria-pressed", "false");
    await expect(cellsFilter.getByRole("button", { name: nb.terms.netInventory })).toHaveAttribute("aria-pressed", "true");
    await expect(status.getByRole("button")).toHaveText([`${wall.filters.all}1`, `${wall.status.waiting}1`, `${wall.filters.withAi}1`]);
    // The median rows under the wall, from the api; with one game the median is its value.
    const median = grid.getByRole("row").filter({ has: page.getByRole("rowheader", { name: wall.median.row(nb.terms.factory) }) });
    await expect(median).toHaveCount(1);
    await expect(grid.getByRole("rowheader", { name: wall.median.chainRow })).toBeVisible();
    const firstCell = grid.locator("[data-row] [role=gridcell]").first();
    const value = /: Netto lager (−?\d+)\.$/.exec((await firstCell.getAttribute("aria-label")) ?? "")![1]!;
    await expect(median.getByRole("gridcell").first()).toHaveAccessibleName(
      `Uke 1: median ${value}, midterste halvdel ${value} til ${value}, 1 spill.`,
    );
    await expect(region.locator("[data-median-graph]")).toHaveCount(1);
    await expect(main.locator("[data-median-key]")).toContainText(wall.median.band);
    if (viewport.width === 1280 && !("text200" in viewport)) {
      // The Visningsbryter is a compact control at the right of the heading line, not a block.
      const toggle = main.getByRole("group", { name: view.view });
      const heading = main.getByText(wall.shown(nb.terms.netInventory, nb.terms.factory), { exact: true });
      const [toggleBox, headingBox, regionBox] = await Promise.all([toggle.boundingBox(), heading.boundingBox(), region.boundingBox()]);
      expect(toggleBox!.height).toBeLessThanOrEqual(60);
      expect(toggleBox!.x).toBeGreaterThan(headingBox!.x + headingBox!.width);
      expect(toggleBox!.y + toggleBox!.height).toBeLessThanOrEqual(regionBox!.y);

      // Filters apply at once and fetch no game's weeks again: only the aggregates of the choice.
      const weeksBefore = requests.filter((url) => /\/api\/games\/[^/]+\/weeks/.test(url)).length;
      await roles.getByRole("button", { name: nb.terms.retailer }).click();
      await cellsFilter.getByRole("button", { name: nb.terms.order }).click();
      await expect(cellsFilter.getByRole("button", { name: nb.terms.order })).toHaveAttribute("aria-pressed", "true");
      await expect(main.getByText(wall.shown(nb.terms.order, nb.terms.retailer), { exact: true })).toBeVisible();
      await expect(main.getByRole("list", { name: wall.flowLegend(nb.terms.order) }).getByRole("listitem")).toHaveText([...wall.flowBins]);
      await expect(main.getByText(wall.minusNote)).toHaveCount(0);
      await expect(grid.locator("[data-row] [role=gridcell]").first()).toHaveAccessibleName(/^Spill 1, Uke 1: Ordre \d+\.$/);
      await expect(grid.locator("[data-row] [data-step^=flow-]").first()).toBeVisible();
      await expect(grid.getByRole("rowheader", { name: wall.median.row(nb.terms.retailer) })).toBeVisible();
      await expect.poll(() => requests.some((url) => url.includes("/overview/aggregates?role=retailer&cells=order&status=all"))).toBe(true);
      // Status: only the waiting games; the group's count follows.
      await status.getByRole("button", { name: new RegExp(`^${wall.status.waiting}`) }).click();
      await expect(grid.getByRole("rowheader", { name: `${copy.groups.waiting} 1`, exact: true })).toBeVisible();
      await expect.poll(() => requests.some((url) => url.includes("cells=order&status=waiting"))).toBe(true);
      expect(requests.filter((url) => /\/api\/games\/[^/]+\/weeks/.test(url)).length).toBe(weeksBefore);

      // The table: as wide as its region, «Venter på» on one line, the median rows in its foot.
      await toggle.getByRole("radio", { name: view.table }).check();
      const table = region.getByRole("table");
      await expect(table.locator("tfoot").getByRole("rowheader", { name: wall.median.row(nb.terms.retailer) })).toBeVisible();
      await expect(table.locator("tfoot").getByRole("rowheader", { name: wall.median.chainRow })).toBeVisible();
      const widths = await region.evaluate((box) => ({ region: box.clientWidth, table: box.querySelector("table")!.offsetWidth }));
      expect(widths.table).toBeGreaterThanOrEqual(widths.region - 1);
      const waitCell = table.locator("tbody tr").first().locator("td").nth(1);
      await expect(waitCell).toContainText(second!.name);
      const lines = await waitCell.evaluate((cell) => {
        const range = document.createRange();
        range.selectNodeContents(cell);
        return new Set([...range.getClientRects()].map((rect) => Math.round(rect.top))).size;
      });
      expect(lines).toBe(1);
      await textReadable(page);

      // The aggregates cannot be read: a line says so, and the games stay on screen.
      const failing = "**/overview/aggregates?*cells=cost*";
      await page.route(failing, (route) => route.fulfill({ status: 500, body: "" }));
      await cellsFilter.getByRole("button", { name: nb.terms.costPerWeek }).click();
      await expect(main.getByRole("status").filter({ hasText: wall.median.failed })).toBeVisible();
      await expect(table.getByRole("rowheader", { name: "Spill 1", exact: true })).toBeVisible();
      await page.unroute(failing);
    }
    await expectAccessible(page, viewport.phone);
    await page.context().close();
  }
});

test("«Oppdater automatisk» shows an Order within 5 s, holds the page when off, and «Oppdater» applies it", async ({
  browser,
  lecturerSession,
}) => {
  const game = await liveClassGame(browser, lecturerSession, 2, { aiMode: "rule_based" });
  const [first, second] = game.students;
  const page = await lecturerPage(browser, lecturerSession, { width: 1280, height: 800 });
  const reads: { status: number; revalidated: boolean }[] = [];
  page.on("response", (response) => {
    if (new URL(response.url()).pathname.endsWith("/overview")) {
      reads.push({ status: response.status(), revalidated: Boolean(response.request().headers()["if-none-match"]) });
    }
  });
  await page.goto(`/klasseokter/${game.sessionId}/oversikt`);
  const main = page.getByRole("main");
  const headline = main.locator("[data-headline]");
  const said = page.locator("[data-counts-announcement]");
  const cells = main.getByRole("region", { name: nb.wall.region }).locator("[data-row] [role=gridcell]");
  await expect(headline).toHaveText("0 ferdig · 1 pågår · 0 venter");
  await expect(cells).toHaveCount(1);
  await untilLive(page);
  const on = main.getByRole("switch", { name: `${live.label} ${live.on}` });
  await expect(on).toHaveAttribute("aria-checked", "true");
  await expect(main.getByText(/^Oppdatert \d\d:\d\d:\d\d$/)).toBeVisible();
  await expect(said).toHaveText("");

  // On: an Order reaches the page within 5 s through `session:<id>` (coalesced to one per 2 s),
  // read again with the list's ETag; the counts are said politely.
  await orderByApi(first!, game.gameId, 1, 4);
  await expect(headline).toHaveText("0 ferdig · 0 pågår · 1 venter", { timeout: 5_000 });
  expect(reads.at(-1)).toEqual({ status: 200, revalidated: true });
  await expect(said).toHaveText("0 ferdig · 0 pågår · 1 venter");

  // Off: the page holds what it shows while the changes are counted.
  await on.click();
  const off = main.getByRole("switch", { name: `${live.label} ${live.off}` });
  await expect(off).toHaveAttribute("aria-checked", "false");
  await orderByApi(second!, game.gameId, 1, 4); // the Week is complete: Uke 2 opens
  const waiting = main.getByText(/^1 endring siden \d\d:\d\d$/);
  await expect(waiting).toBeVisible({ timeout: 5_000 });
  await expect(headline).toHaveText("0 ferdig · 0 pågår · 1 venter");
  await expect(cells).toHaveCount(1);
  await expect(main.getByText(/^Oppdatert \d\d:\d\d:\d\d$/)).toBeVisible();
  await expectAccessible(page, false);
  await main.getByRole("button", { name: live.apply, exact: true }).click();
  await expect(headline).toHaveText("0 ferdig · 1 pågår · 0 venter");
  await expect(cells).toHaveCount(2);
  await expect(waiting).toHaveCount(0);
  await expect(off).toHaveAttribute("aria-checked", "false");
  // At most once a minute: the change back is not said yet.
  await expect(said).toHaveText("0 ferdig · 0 pågår · 1 venter");

  // The connection drops and returns: everything visible is read again, the unchanged list
  // answers 304, and «Tilkoblet igjen.» shows.
  const before = reads.length;
  await page.context().setOffline(true);
  await expect(page.getByRole("status").filter({ hasText: nb.system.offline })).toBeVisible();
  await page.context().setOffline(false);
  await expect(page.getByRole("status").filter({ hasText: nb.system.reconnected })).toBeVisible();
  await expect.poll(() => reads.slice(before).some((read) => read.status === 304 && read.revalidated)).toBe(true);
  await expect(headline).toHaveText("0 ferdig · 1 pågår · 0 venter");
  await untilLive(page);

  // A read that fails keeps the page as it is and says so; the next change clears it.
  await off.click();
  await expect(on).toHaveAttribute("aria-checked", "true");
  const failing = `**/api/class-sessions/${game.sessionId}/overview`;
  await page.route(failing, (route) => route.fulfill({ status: 500, body: "" }));
  await orderByApi(first!, game.gameId, 2, 4);
  const failed = page.getByRole("status").filter({ hasText: /^Ikke oppdatert siden \d\d:\d\d\.Prøv igjen$/ });
  await expect(failed).toBeVisible({ timeout: 5_000 });
  await expect(headline).toHaveText("0 ferdig · 1 pågår · 0 venter");
  await expect(cells).toHaveCount(2);
  await page.unroute(failing);
  await orderByApi(second!, game.gameId, 2, 4);
  await expect(failed).toHaveCount(0, { timeout: 5_000 });
  await expect(cells).toHaveCount(3);
  await page.context().close();

  // A missed heartbeat: the Oversikt's own Tilkoblingslinje, the wall kept as it is. A failed
  // week read is tried again by itself.
  const later = await lecturerPage(browser, lecturerSession, VIEWPORTS[0]!);
  await later.clock.install();
  let failedOnce = false;
  const weeks = "**/api/games/*/weeks";
  await later.route(weeks, async (route) => {
    if (failedOnce) return route.continue();
    failedOnce = true;
    await route.fulfill({ status: 500, body: "" });
  });
  await later.goto(`/klasseokter/${game.sessionId}/oversikt`);
  const laterMain = later.getByRole("main");
  const laterCells = laterMain.getByRole("region", { name: nb.wall.region }).locator("[data-row] [role=gridcell]");
  await expect(laterMain.locator("[data-headline]")).toHaveText("0 ferdig · 1 pågår · 0 venter");
  await expect.poll(() => failedOnce).toBe(true);
  await expect(laterCells).toHaveCount(0);
  await later.clock.fastForward(11_000);
  await expect(laterCells).toHaveCount(3);
  await later.unroute(weeks);
  await untilLive(later);
  await later.clock.fastForward(25_000);
  const stale = later
    .getByRole("status")
    .filter({ hasText: /^Ikke oppdatert siden \d\d:\d\d\. Prøver igjen\.Last inn på nytt$/ });
  await expect(stale).toBeVisible();
  await expect(stale.getByRole("button", { name: live.reload })).toBeVisible();
  await expect(laterCells).toHaveCount(3);
  await expectAccessible(later, true);
  await later.context().close();
});

test("before the Start date the page lists the allocation only, reached from the Klasseøkt", async ({
  browser,
  lecturerSession,
}) => {
  const lecturer = await lecturerPage(browser, lecturerSession, { width: 1280, height: 800 });
  const klass = await freshClass(lecturer);
  const created = await lecturer.request.post(`/api/classes/${klass.id}/class-sessions`, { headers: CSRF });
  expect(created.status()).toBe(201);
  const sessionId = (await created.json()).id as string;
  const [start_at, play_deadline, debrief_deadline, test_deadline] = [3, 17, 20, 27].map((d) =>
    new Date(Date.now() + d * DAY).toISOString(),
  );
  const saved = await lecturer.request.put(`/api/class-sessions/${sessionId}`, {
    data: { ai_mode: "rule_based", dates: { start_at, play_deadline, debrief_deadline, test_deadline } },
    headers: CSRF,
  });
  expect(saved.status()).toBe(200);
  await lecturer.goto(`/klasseokter/${sessionId}`);
  await lecturer.getByRole("main").getByRole("link", { name: copy.open, exact: true }).click();
  await expect(lecturer).toHaveURL(new RegExp(`/klasseokter/${sessionId}/oversikt$`));
  const main = lecturer.getByRole("main");
  await expect(main.getByText(/^Spillene starter .+\. Til da vises bare fordelingen\.$/)).toBeVisible();
  await expect(main.getByText(copy.beforeStart.empty)).toBeVisible();
  // No headline counts and no cost before the Start date.
  await expect(main.getByText(/ ferdig · /)).toHaveCount(0);
  await expect(main.getByText(/\bkr\b/)).toHaveCount(0);

  // A Student is refused the same as for a page that does not exist (FR-5).
  const student = await browser.newContext({ baseURL: test.info().project.use.baseURL });
  const page = await student.newPage();
  await loginByApi(page, "student");
  await page.goto(`/klasseokter/${sessionId}/oversikt`);
  await expect(page.getByRole("heading", { level: 1, name: nb.access.denied })).toBeVisible();
});
