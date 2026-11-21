import { expect } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { loginByApi } from "./support/auth";
import { expectAccessible, freshClass, lecturerPage, test, VIEWPORTS } from "./support/classes";
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
    const cells = grid.getByRole("gridcell");
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
