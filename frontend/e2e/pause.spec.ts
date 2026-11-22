import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { expectAccessible, expectReflow, lecturerPage, test, VIEWPORTS } from "./support/classes";
import { liveClassGame, orderByApi } from "./support/live-game";

/** «Ta pause» (Story 8.6, FR-89, FR-39, UX-DR26, UX-DR45, UX-DR62, NFR-6) on the local stack: a
 * fresh Class game with three Students. The Pausevalg opens in place, focus moves to its primary
 * and «Avbryt» gives it back; the confirmed Pause shows the line to every Student on Spill and Hjem
 * and moves the game into the Oversikt's «Pause» group; another Student's Order ends it, and the
 * line then names who ordered. The command's rules are `backend/tests/games/test_pause.py`. */
const copy = nb.homes.student.pause;
const WIDTHS = [320, 360, 1440];

async function untilLive(page: Page) {
  await expect(page.locator("html")).toHaveAttribute("data-live", "live", { timeout: 10_000 });
}

const line = (page: Page) => page.getByRole("main").locator("[data-pause-line] p");

test("a Student pauses the game, every Student reads it, and another Student's Order ends it", async ({
  browser,
  lecturerSession,
}) => {
  const game = await liveClassGame(browser, lecturerSession, 3, { aiMode: "rule_based" });
  const [sara, jonas, ida] = game.students as [(typeof game.students)[0], (typeof game.students)[0], (typeof game.students)[0]];
  const play = await sara.context.newPage();
  await play.goto(`/spill/${game.gameId}`);
  await expect(play.getByRole("heading", { level: 1 })).toHaveText(nb.games.play.week(1));
  const open = play.getByRole("main").getByRole("button", { name: copy.open });
  const form = play.locator("[data-pausevalg]");

  // The Pausevalg at each width: no date or time, the two lines, the primary focused; «Avbryt»
  // gives focus back to «Ta pause». Axe and reflow with the form open.
  for (const width of WIDTHS) {
    await play.setViewportSize({ width, height: 800 });
    await expect(open).toBeVisible();
    expect((await open.boundingBox())!.height).toBeGreaterThanOrEqual(44);
    await open.click();
    await expect(form).toContainText(copy.noTakeover);
    await expect(form).toContainText(copy.onlyLecturer);
    await expect(form.locator("input")).toHaveCount(0);
    const confirm = form.getByRole("button", { name: copy.confirm });
    await expect(confirm).toBeFocused();
    // One primary on the screen: «Bekreft ordre» steps back while the form is open.
    await expect(play.locator("[data-order-field] button.bg-ink")).toHaveCount(0);
    await expectAccessible(play, width < 1024);
    await form.getByRole("button", { name: copy.cancel }).click();
    await expect(form).toHaveCount(0);
    await expect(open).toBeFocused();
  }

  // Jonas has Hjem open; Ida has Spill open. Both are live before the Pause.
  const home = await jonas.context.newPage();
  await home.goto("/hjem");
  await untilLive(home);
  // Hjem too keeps one primary: its «Gå til Uke 1» steps back while the Pausevalg is open.
  const homeMain = home.getByRole("main");
  await expect(homeMain.locator(".bg-ink")).toHaveCount(1);
  await homeMain.getByRole("button", { name: copy.open }).click();
  await expect(homeMain.locator("[data-pausevalg] .bg-ink")).toHaveCount(1);
  await expect(homeMain.locator(".bg-ink")).toHaveCount(1);
  await homeMain.getByRole("button", { name: copy.cancel }).click();
  await expect(homeMain.locator(".bg-ink")).toHaveCount(1);
  await expect(homeMain.locator("[data-pausevalg]")).toHaveCount(0);
  const other = await ida.context.newPage();
  await other.goto(`/spill/${game.gameId}`);
  await untilLive(other);
  await untilLive(play);

  await open.click();
  await form.getByRole("button", { name: copy.confirm }).click();
  await expect(line(play)).toHaveText(copy.pausedByYou);
  await expect(line(play)).toBeFocused();
  await expect(open).toHaveCount(0);
  // Every Student reads it, above Setestatus, in a polite live region.
  for (const page of [home, other]) {
    await expect(line(page)).toHaveText(copy.pausedBy(sara.name));
    await expect(page.getByRole("main").locator("[data-pause-line]")).toHaveAttribute("aria-live", "polite");
    await expect(page.getByRole("main").getByRole("button", { name: copy.open })).toHaveCount(0);
  }
  for (const width of WIDTHS) {
    for (const page of [play, home]) {
      await page.setViewportSize({ width, height: 800 });
      await expectAccessible(page, width < 1024);
    }
  }

  // The Oversikt: the «Pause» group between Venter and Pågår, since when and by whom, counted.
  const lecturer = await lecturerPage(browser, lecturerSession, VIEWPORTS[2]!);
  await lecturer.goto(`/klasseokter/${game.sessionId}/oversikt`);
  const main = lecturer.getByRole("main");
  await expect(main.locator("[data-attention-band]")).toHaveCount(0);
  await expect(main.getByRole("heading", { name: `${nb.overview.groups.paused} 1` }).first()).toBeVisible();
  await expect(main.locator(`[data-game="${game.gameId}"]`)).toContainText(`satt av ${sara.name}.`);
  await expect(main).toContainText(nb.overview.counts.runningPaused(1, 1));
  await expectAccessible(lecturer, false);
  await lecturer.context().close();

  // Jonas orders: the Pause is over for everyone, and the line names him.
  await orderByApi(jonas, game.gameId, 1, 4);
  await expect(line(play)).toHaveText(copy.endedBy(jonas.name));
  await expect(line(other)).toHaveText(copy.endedBy(jonas.name));
  await expect(line(home)).toHaveText(copy.endedByYou);
  await expect(open).toBeVisible();
  for (const width of WIDTHS) {
    await play.setViewportSize({ width, height: 800 });
    await expectReflow(play, width < 1024);
  }
  await expectAccessible(play, false);
  for (const page of [play, home, other]) await page.close();
});
