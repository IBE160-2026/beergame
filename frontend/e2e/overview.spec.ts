import { expect } from "@playwright/test";

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
const CSRF = { "X-Requested-With": "olspillet" };
const DAY = 24 * 60 * 60 * 1000;

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
      // The game moves on and changes group while a cell has focus: focus stays on Spill 1, Uke 2.
      await orderByApi(first!, game.gameId, 4, 4);
      await expect(grid.getByRole("rowheader", { name: `${copy.groups.waiting} 1`, exact: true })).toBeVisible();
      await expect(page.locator(":focus")).toHaveAccessibleName(/^Spill 1, Uke 2: /);
      await page.keyboard.press("Tab");
      await expect(grid.locator(":focus")).toHaveCount(0);
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
