import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { expectAccessible, expectReflow, lecturerPage, test, VIEWPORTS } from "./support/classes";
import { liveClassGame, orderByApi } from "./support/live-game";

/** «Sett inn KI-spiller i alle seter som blir ventet på» (Story 8.12, FR-37, UX-DR52) on the local
 * stack: a fresh Class game with four Students, Uke 1 open; one orders, so the game waits for the
 * other three, one of whom has Tilrettelegging. On Spillinnsikt the Lecturer reads the consequence,
 * «… (2)» and «Ikke med (tilrettelegging): …», and presses: «2 KI-spillere satt inn.» takes focus.
 * With the Tilrettelegging removed, the Oversikt header offers «… (1)», whose page lists the Seat
 * with its wait and «Sett inn 1 KI-spiller»; the Oversikt then reads «1 KI-spiller er satt inn.» and
 * the Lenke is gone. The api's rules are `backend/tests/sessions/test_fill_seats_view.py`. */
const one = nb.spillstyring.fill;
const all = nb.overview.fill;
const CSRF = { "X-Requested-With": "olspillet" };

async function untilLive(page: Page) {
  await expect(page.locator("html")).toHaveAttribute("data-live", "live", { timeout: 10_000 });
}

test("a Lecturer fills the waited-for Seats of one game and then from the Oversikt", async ({
  browser,
  lecturerSession,
}) => {
  const game = await liveClassGame(browser, lecturerSession, 4, { aiMode: "rule_based" });
  const [first, ...waited] = game.students as [(typeof game.students)[0], ...typeof game.students];
  const overviewPath = `/klasseokter/${game.sessionId}/oversikt`;
  const insightPath = `${overviewPath}/spill/${game.gameId}`;
  await orderByApi(first, game.gameId, 1, 4);

  // Tilrettelegging for the last of the three: left out.
  const page = await lecturerPage(browser, lecturerSession, VIEWPORTS[2]!);
  const seats = (await (await page.request.get(`/api/games/${game.gameId}/insight`)).json()).seats as {
    name: string | null;
    user_id: string | null;
  }[];
  const extra = waited[2]!;
  const extraId = seats.find((seat) => seat.name === extra.name)!.user_id!;
  const adjustment = `/api/class-sessions/${game.sessionId}/students/${extraId}/adjustment`;
  expect((await page.request.put(adjustment, { data: { time_factor: 2 }, headers: CSRF })).status()).toBe(200);

  // 320 CSS px: the consequence above the full-width secondary button, then the left-out line.
  const narrow = await lecturerPage(browser, lecturerSession, VIEWPORTS[0]!);
  await narrow.goto(insightPath);
  const narrowBlock = narrow.locator("[data-spillstyring-fill]");
  await expect(narrowBlock.getByRole("button", { name: one.button(2) })).toBeVisible();
  await expect(narrowBlock.locator("[data-fill-left-out]")).toHaveText(one.leftOut(extra.name));
  const width = (await narrowBlock.getByRole("button", { name: one.button(2) }).boundingBox())!.width;
  expect(width).toBeGreaterThanOrEqual(240);
  await expectAccessible(narrow, true);
  await narrow.context().close();

  // 1440 px: one press, no dialog; the result line replaces the button and takes focus.
  await page.goto(insightPath);
  const block = page.locator("[data-spillstyring]");
  const consequence = block.locator("[data-fill-consequence]");
  await expect(consequence).toContainText(waited[0]!.name);
  await expect(consequence).toContainText(waited[1]!.name);
  await expect(consequence).not.toContainText(extra.name);
  await expectAccessible(page, false);
  await untilLive(page);
  await block.getByRole("button", { name: one.button(2) }).click();
  const done = block.locator("[data-fill-result]");
  await expect(done).toHaveText(one.done(2));
  await expect(done).toBeFocused();
  await expect(block.getByRole("button", { name: one.button(2) })).toHaveCount(0);
  const marks = (await (await page.request.get(`/api/games/${game.gameId}/insight`)).json()).seats as {
    holder: string;
    mark: string | null;
  }[];
  expect(marks.filter((seat) => seat.mark === "takeover_staff")).toHaveLength(2);

  // Without the Tilrettelegging the Seat is the Oversikt's to fill.
  expect((await page.request.put(adjustment, { data: { time_factor: 1 }, headers: CSRF })).status()).toBe(200);
  await page.goto(overviewPath);
  const link = page.locator("[data-fill-seats-link]");
  await expect(link).toHaveText(all.link(1));
  await untilLive(page);
  await link.click();
  await expect(page).toHaveURL(new RegExp(`${overviewPath}/sett-inn$`));
  const listed = page.locator("[data-fill-seats-page] li[data-seat]");
  await expect(listed).toHaveCount(1);
  await expect(listed).toContainText(`${extra.name}, `);
  await expect(page.locator("[data-fill-consequence]")).toHaveText(all.consequence);
  await expectAccessible(page, false);
  const narrowPage = await lecturerPage(browser, lecturerSession, VIEWPORTS[0]!);
  await narrowPage.goto(`${overviewPath}/sett-inn`);
  await expect(narrowPage.locator("[data-fill-seats-page] li[data-seat]")).toHaveCount(1);
  await expectAccessible(narrowPage, true);
  await narrowPage.context().close();

  await untilLive(page);
  await page.getByRole("button", { name: all.confirm(1) }).click();
  await expect(page).toHaveURL(new RegExp(`${overviewPath}$`));
  const line = page.locator("[data-seats-filled]");
  await expect(line).toHaveText(all.done(1));
  await expect(line).toBeFocused();
  await expect(page.locator("[data-fill-seats-link]")).toHaveCount(0);
  await expectReflow(page, false);
  await page.context().close();
});
