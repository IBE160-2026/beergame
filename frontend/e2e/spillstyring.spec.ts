import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { expectAccessible, expectReflow, lecturerPage, test, VIEWPORTS } from "./support/classes";
import { liveClassGame, orderByApi } from "./support/live-game";

/** «Sett inn KI-spiller for …» (Story 8.5, FR-37, UX-DR45, UX-DR52, NFR-6) on the local stack: a
 * fresh Class game whose first Student has ordered Uke 1. Spillstyring on Spillinnsikt offers
 * both Student Seats with their consequences; a press puts the AI player in through the real api
 * and the result line takes focus; a second, stale page is told who came first, named from the view
 * it reads again. The Varselbånd offers the same Takeover for the Student the game waits for. The
 * command's rules are `backend/tests/games/test_staff_takeover.py`. */
const copy = nb.spillstyring;

async function untilLive(page: Page) {
  await expect(page.locator("html")).toHaveAttribute("data-live", "live", { timeout: 10_000 });
}

test("Spillstyring puts an AI player in one Seat, and a stale page is told who came first", async ({
  browser,
  lecturerSession,
}) => {
  const game = await liveClassGame(browser, lecturerSession, 2, { aiMode: "rule_based" });
  const [first, second] = game.students;
  await orderByApi(first!, game.gameId, 1, 4);
  const path = `/klasseokter/${game.sessionId}/oversikt/spill/${game.gameId}`;
  const insightApi = `**/api/games/${game.gameId}/insight`;

  // 320 CSS px: the block reflows, every action full width and a 44 px target, axe passes.
  const narrow = await lecturerPage(browser, lecturerSession, VIEWPORTS[0]!);
  await narrow.goto(path);
  const narrowBlock = narrow.locator("[data-spillstyring]");
  await expect(narrowBlock.getByRole("heading", { name: copy.title })).toBeVisible();
  // The two per-Seat actions (the Lecturer also has «Pause spillet», Story 8.7).
  await expect(narrowBlock.locator("li").getByRole("button")).toHaveCount(2);
  const button = (await narrowBlock.getByRole("button", { name: copy.takeover(second!.name) }).boundingBox())!;
  expect(button.width).toBeGreaterThanOrEqual(240);
  await expectAccessible(narrow, true);

  // A second lecturer page holds Spillinnsikt as it was, its live reads held back until its press.
  const stale = await lecturerPage(browser, lecturerSession, VIEWPORTS[2]!);
  let held: unknown = null;
  let holding = true;
  await stale.route(insightApi, async (route) => {
    if (!holding || route.request().method() !== "GET") return route.fallback();
    if (held === null) held = await (await route.fetch()).json();
    await route.fulfill({ json: held });
  });
  // Its press lets the reads through again, so the refusal's read names who came first.
  await stale.route("**/api/games/*/seats/*/takeover", async (route) => {
    holding = false;
    await route.continue();
  });
  await stale.goto(path);
  await expect(stale.locator("[data-spillstyring] li").getByRole("button")).toHaveCount(2);

  // 1440 px: one row per Student Seat, its consequence right above its button.
  const page = await lecturerPage(browser, lecturerSession, VIEWPORTS[2]!);
  await page.goto(path);
  const block = page.locator("[data-spillstyring]");
  const absentRow = block.locator("li").filter({ hasText: second!.name });
  await expect(absentRow.locator("[data-takeover-consequence]")).toHaveText(copy.thisWeek(second!.name));
  await expect(block.locator("li").filter({ hasText: first!.name }).locator("[data-takeover-consequence]")).toHaveText(
    copy.nextWeek(first!.name),
  );
  await expectAccessible(page, false);
  await untilLive(page);

  // The press: no dialog; the result line replaces the button and takes focus.
  await absentRow.getByRole("button", { name: copy.takeover(second!.name) }).click();
  const done = absentRow.locator("[data-takeover-result]");
  await expect(done).toHaveText(copy.done(second!.name));
  await expect(done).toBeFocused();
  await expect(absentRow.getByRole("button")).toHaveCount(0);
  // The Seat names who put the AI player in (resolved at read time).
  const answer = await (await page.request.get(`/api/games/${game.gameId}/insight`)).json();
  const taken = (answer.seats as { role: string; mark_by: string | null; holder: string }[]).find(
    (s) => s.holder === "ai" && s.mark_by,
  )!;
  const mark = page.locator(`[data-insight-seats] [data-role="${taken.role}"] [data-seat-mark]`);
  await expect(mark).toHaveText(nb.insight.markedBy(taken.mark_by!));
  await expectReflow(page, false);
  await page.context().close();

  // The stale page presses too: 409 `takeover_exists`, and the name comes from its fresh read.
  const staleRow = stale.locator("[data-spillstyring] li").filter({ hasText: second!.name });
  const refused = stale.waitForResponse((r) => r.url().includes("/takeover") && r.request().method() === "POST");
  await staleRow.getByRole("button", { name: copy.takeover(second!.name) }).click();
  expect((await refused).status()).toBe(409);
  const line = staleRow.locator("[data-takeover-result]");
  await expect(line).toHaveText(copy.taken(taken.mark_by!), { timeout: 5_000 });
  await expect(line).toBeFocused();
  await stale.unrouteAll({ behavior: "wait" });
  await stale.context().close();
  await narrow.context().close();
});

test("the Varselbånd puts an AI player in for the Student the game waits for", async ({ browser, lecturerSession }) => {
  const game = await liveClassGame(browser, lecturerSession, 2, { aiMode: "rule_based" });
  const [first, second] = game.students;
  await orderByApi(first!, game.gameId, 1, 4);
  const page = await lecturerPage(browser, lecturerSession, VIEWPORTS[2]!);
  await page.goto(`/klasseokter/${game.sessionId}/oversikt`);
  const band = page.getByRole("main").locator(`[data-attention-band="${game.gameId}"]`);
  await expect(band.locator("[data-band-consequence]")).toHaveText(copy.thisWeek(second!.name));
  // «Send Melding» stays the one primary; the Takeover is secondary.
  await expect(band.getByRole("link", { name: nb.messages.send })).toBeVisible();
  const press = band.getByRole("button", { name: copy.takeover(second!.name) });
  await expect(press).toBeVisible();
  await expectAccessible(page, false);
  await untilLive(page);

  await press.click();
  const line = page.getByRole("main").locator("[data-takeover-result]");
  await expect(line).toHaveText(copy.done(second!.name));
  await expect(line).toBeFocused();
  // The game no longer waits: it leaves the band, and nothing takes its place.
  await expect(page.getByRole("main").locator("[data-attention-band]")).toHaveCount(0, { timeout: 5_000 });
  await expectReflow(page, false);
  await page.context().close();

  // 320 CSS px with the band and its two actions stacked full width: a fresh game.
  const other = await liveClassGame(browser, lecturerSession, 2, { aiMode: "rule_based" });
  await orderByApi(other.students[0]!, other.gameId, 1, 4);
  const narrow = await lecturerPage(browser, lecturerSession, VIEWPORTS[0]!);
  await narrow.goto(`/klasseokter/${other.sessionId}/oversikt`);
  const narrowBand = narrow.getByRole("main").locator("[data-attention-band]");
  const action = (await narrowBand.getByRole("button", { name: copy.takeover(other.students[1]!.name) }).boundingBox())!;
  expect(action.width).toBeGreaterThanOrEqual(240);
  await expectAccessible(narrow, true);
  await narrow.context().close();
});
