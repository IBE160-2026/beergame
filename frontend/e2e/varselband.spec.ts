import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { expectAccessible, lecturerPage, test, VIEWPORTS } from "./support/classes";
import { liveClassGame, orderByApi } from "./support/live-game";

/** The Varselbånd (Story 7.11, FR-39, FR-40, UX-DR41, UX-DR44, UX-DR45, NFR-6) on the local stack:
 * the api names the longest-waiting Class game; the band shows it with «Send Melding» preset to the
 * Student waited for, its row is tinted in the wall and the table, every row has «Melding», and the
 * band comes and goes live, announced without moving focus. Which game the api picks is
 * `backend/tests/sessions/test_overview_alert.py`; «Venter ellers» with several games is
 * `src/modules/games/overview-band.test.ts`. */
const copy = nb.overview;
const INK = "rgb(15, 42, 71)";
const RESTORDRE_FILL = "rgb(240, 213, 210)";

async function untilLive(page: Page) {
  await expect(page.locator("html")).toHaveAttribute("data-live", "live", { timeout: 10_000 });
}

test("the band names the game that waits, «Send Melding» writes to the Student, every row writes to its game", async ({
  browser,
  lecturerSession,
}) => {
  const game = await liveClassGame(browser, lecturerSession, 2, { aiMode: "rule_based" });
  const [first, second] = game.students;
  const overview = `/klasseokter/${game.sessionId}/oversikt`;
  const page = await lecturerPage(browser, lecturerSession, VIEWPORTS[2]!);
  await page.goto(overview);
  const main = page.getByRole("main");
  await expect(main.locator("[data-headline]")).toHaveText("0 ferdig · 1 pågår · 0 venter");
  // Nothing waits: no band and no primary button in its place.
  await expect(main.locator("[data-attention-band]")).toHaveCount(0);
  await expect(main.getByRole("link", { name: nb.messages.send })).toHaveCount(0);

  // The game starts to wait while the page is open: the band appears and is announced politely,
  // focus stays where it was (UX-DR44).
  await untilLive(page);
  const toggle = main.getByRole("switch");
  await toggle.focus();
  await orderByApi(first!, game.gameId, 1, 4);
  const band = main.locator(`[data-attention-band="${game.gameId}"]`);
  await expect(band).toBeVisible({ timeout: 5_000 });
  const role = "(Fabrikk|Distributør|Grossist|Detaljist)";
  await expect(band.locator("p")).toHaveText(
    new RegExp(`^Spill 1 venter på ${second!.name} \\(${role}\\) i (under\\s1\\smin|\\d+\\smin)\\.$`),
  );
  await expect(main.locator("[data-attention-announcement]")).toHaveText(
    new RegExp(`^Spill 1 venter på ${second!.name} \\(${role}\\)\\.$`),
  );
  await expect(toggle).toBeFocused();
  await expect(band).toHaveCSS("background-color", RESTORDRE_FILL);
  await expect(band.locator("p")).toHaveCSS("color", INK);
  await expect(band.getByRole("heading", { name: copy.band.label })).toBeAttached();

  // «Venter ellers» leaves the band's game out.
  const rail = main.getByRole("complementary", { name: copy.rail.label });
  await expect(rail.getByText(copy.rail.waiting.noneOther)).toBeVisible();

  // The wall: the band's row is tinted, its «Melding» is the row's last cell, reached from the
  // last Uke with the keyboard; Enter opens the Meldingsskjema for the Class game.
  const region = main.getByRole("region", { name: nb.wall.region });
  const grid = region.getByRole("grid");
  await expect(grid.locator(`[data-row="${game.gameId}"][data-tint]`)).toHaveCount(1);
  const wallLink = grid.locator("[data-link]");
  await expect(wallLink).toHaveCount(1);
  await expect(wallLink).toHaveAccessibleName(nb.messages.toGameLabel(1));
  await region.focus();
  await page.keyboard.press("Tab");
  await expect(grid.locator("[data-row] [role=gridcell][data-week]").first()).toBeFocused();
  await page.keyboard.press("End");
  await page.keyboard.press("ArrowRight");
  await expect(wallLink).toBeFocused();
  await expect(page.locator("[data-focus-ring]")).toHaveCount(1);
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { level: 1, name: nb.messages.title.classGame(1) })).toBeVisible();
  await page.goBack();

  // The table: a «Melding» column, the band's row tinted; a click on the link never opens Spillinnsikt.
  const views = main.getByRole("group", { name: nb.wall.table.view });
  await views.getByRole("radio", { name: nb.wall.table.wall }).focus();
  await page.keyboard.press("ArrowRight");
  await expect(views.getByRole("radio", { name: nb.wall.table.table })).toBeChecked();
  const table = main.getByRole("region", { name: nb.wall.region }).getByRole("table");
  await expect(table.locator(`tr[data-row="${game.gameId}"]`)).toHaveCSS("background-color", RESTORDRE_FILL);
  const tableLink = table.getByRole("link", { name: nb.messages.toGameLabel(1) });
  await expect(tableLink).toHaveCSS("color", INK);
  await tableLink.click();
  await expect(page).toHaveURL(new RegExp(`/melding\\?spill=${game.gameId}$`));
  await expect(page.getByRole("heading", { level: 1, name: nb.messages.title.classGame(1) })).toBeVisible();
  await page.goBack();

  // The game list under the wall: its row tinted with an ink «Melding».
  const listRow = main.locator(`li[data-game="${game.gameId}"][data-tint]`);
  await expect(listRow).toHaveCSS("background-color", RESTORDRE_FILL);
  await expect(listRow.getByRole("link", { name: nb.messages.toGameLabel(1) })).toHaveCSS("color", INK);
  await expectAccessible(page, false);

  // «Send Melding»: the Meldingsskjema for the Student waited for.
  await main.getByRole("link", { name: nb.messages.send }).click();
  await expect(page.getByRole("heading", { level: 1, name: nb.messages.title.student(second!.name, 1) })).toBeVisible();
  await page.context().close();

  // 320 CSS px: the text first, «Send Melding» under it at full width and in view.
  const narrow = await lecturerPage(browser, lecturerSession, VIEWPORTS[0]!);
  await narrow.goto(overview);
  const narrowBand = narrow.getByRole("main").locator("[data-attention-band]");
  const text = (await narrowBand.locator("p").boundingBox())!;
  const action = (await narrowBand.getByRole("link", { name: nb.messages.send }).boundingBox())!;
  const box = (await narrowBand.boundingBox())!;
  expect(action.y).toBeGreaterThanOrEqual(text.y + text.height);
  expect(action.width).toBeGreaterThan(box.width - 40);
  expect(action.x + action.width).toBeLessThanOrEqual(320);
  await expectAccessible(narrow, true);

  // The Student orders too: nothing waits, the band goes away live and nothing takes its place.
  await untilLive(narrow);
  await orderByApi(second!, game.gameId, 1, 4);
  await expect(narrowBand).toHaveCount(0, { timeout: 5_000 });
  await expect(narrow.getByRole("main").getByRole("link", { name: nb.messages.send })).toHaveCount(0);
  await narrow.context().close();
});
