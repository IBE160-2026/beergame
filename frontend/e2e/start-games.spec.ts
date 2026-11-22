import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { expectAccessible, lecturerPage, test, VIEWPORTS } from "./support/classes";
import { lockedClassGames } from "./support/live-game";

/** «Start spillet» and «Start spill» (Story 8.10, FR-22, UX-DR52, NFR-6) on the local stack: a fresh
 * Class session locked through the local dev lock, its two Class games not started. The Lecturer
 * starts one from Spillstyring on Spillinnsikt; the result line takes focus. The Oversikt header then
 * offers «Start spill som ikke har startet (1)», whose page lists the other game and starts it; the
 * Oversikt reads «1 spill er startet.» and the Lenke is gone. A second page, still showing that game
 * as not started, presses «Start spillet» and is told who started it first. The command's and the api's rules are
 * `backend/tests/games/test_start_actor.py` and `backend/tests/sessions/test_lecturer_start.py`. */
const one = nb.spillstyring.start;
const all = nb.overview.start;

async function untilLive(page: Page) {
  await expect(page.locator("html")).toHaveAttribute("data-live", "live", { timeout: 10_000 });
}

test("a Lecturer starts one game in Spillstyring and the rest from «Start spill»", async ({
  browser,
  lecturerSession,
}) => {
  const locked = await lockedClassGames(browser, lecturerSession, 5, { aiMode: "rule_based" });
  expect(locked.gameIds).toHaveLength(2);
  const [first, second] = locked.gameIds as [string, string];
  const overviewPath = `/klasseokter/${locked.sessionId}/oversikt`;
  const insightPath = `${overviewPath}/spill/${first}`;

  // 320 CSS px: the consequence above the one primary button, full width; axe passes.
  const narrow = await lecturerPage(browser, lecturerSession, VIEWPORTS[0]!);
  await narrow.goto(insightPath);
  const narrowStart = narrow.locator("[data-spillstyring-start]");
  await expect(narrowStart.locator("[data-start-consequence]")).toHaveText(one.consequence);
  const narrowButton = (await narrowStart.getByRole("button", { name: one.button }).boundingBox())!;
  expect(narrowButton.width).toBeGreaterThanOrEqual(240);
  await expectAccessible(narrow, true);
  // The «Start spill» page at 320 px, before anything starts: both games, one column.
  await narrow.goto(`${overviewPath}/start`);
  await expect(narrow.locator("[data-start-games] li[data-game]")).toHaveCount(2);
  await expectAccessible(narrow, true);
  await narrow.context().close();

  // 1440 px: «Start spillet»; no dialog; the result line replaces it and takes focus.
  const page = await lecturerPage(browser, lecturerSession, VIEWPORTS[2]!);
  await page.goto(insightPath);
  const block = page.locator("[data-spillstyring]");
  await expect(block.locator("[data-start-consequence]")).toHaveText(one.consequence);
  await expectAccessible(page, false);
  await untilLive(page);
  await block.getByRole("button", { name: one.button }).click();
  const done = block.locator("[data-start-result]");
  await expect(done).toHaveText(one.done);
  await expect(done).toBeFocused();
  await expect(block.getByRole("button", { name: one.button })).toHaveCount(0);
  // The game runs: Spillinnsikt shows its first Uke, and it names who started it.
  const answer = await (await page.request.get(`/api/games/${first}/insight`)).json();
  expect(answer.status).not.toBe("not_started");
  expect(answer.started_by).toBeTruthy();

  // A second page holds the other game's Spillinnsikt as it was, its reads held back until its
  // press: the batch below starts that game first, and the press is then told who did.
  const stale = await lecturerPage(browser, lecturerSession, VIEWPORTS[2]!);
  let held: unknown = null;
  let holding = true;
  await stale.route(`**/api/games/${second}/insight`, async (route) => {
    if (!holding || route.request().method() !== "GET") return route.fallback();
    if (held === null) held = await (await route.fetch()).json();
    await route.fulfill({ json: held });
  });
  await stale.route(`**/api/games/${second}/start`, async (route) => {
    holding = false;
    await route.continue();
  });
  await stale.goto(`${overviewPath}/spill/${second}`);
  await expect(stale.locator("[data-spillstyring]").getByRole("button", { name: one.button })).toBeVisible();

  // The Oversikt counts the game left; its page lists it with the line and «Start 1 spill».
  await page.goto(overviewPath);
  const link = page.getByRole("link", { name: all.link(1) });
  await expect(link).toBeVisible();
  await untilLive(page);
  await link.click();
  await expect(page.getByRole("heading", { level: 1, name: all.title })).toBeVisible();
  const list = page.locator("[data-start-games]");
  await expect(list.locator("li[data-game]")).toHaveCount(1);
  await expect(list.locator(`li[data-game="${second}"]`)).toBeVisible();
  await expect(list.locator("[data-start-games-consequence]")).toHaveText(all.consequence);
  await expectAccessible(page, false);
  await list.getByRole("button", { name: all.confirm(1) }).click();

  // Back on the Oversikt: the real count, focused; the address drops it; the Lenke is gone.
  const said = page.locator("[data-games-started]");
  await expect(said).toHaveText(all.done(1));
  await expect(said).toBeFocused();
  await expect(page).toHaveURL(new RegExp(`${overviewPath}$`));
  await expect(page.locator("[data-start-games-link]")).toHaveCount(0);
  const started = await (await page.request.get(`/api/games/${second}/insight`)).json();
  expect(started.status).not.toBe("not_started");

  // The stale page's press: the api answers that the game was started first, and the line read
  // again names who did, with focus.
  await untilLive(stale);
  await stale.locator("[data-spillstyring]").getByRole("button", { name: one.button }).click();
  const lost = stale.locator("[data-start-result]");
  await expect(lost).toHaveText(one.startedBy(started.started_by));
  await expect(lost).toBeFocused();
  await stale.unrouteAll({ behavior: "ignoreErrors" });
});
