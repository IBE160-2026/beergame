import { expect, type Page, type Route } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { expectAccessible, lecturerPage, test, VIEWPORTS } from "./support/classes";
import { liveClassGame, orderByApi } from "./support/live-game";

/** The game closest to Takeover on the Oversikt (Story 8.3, FR-34, FR-36, FR-39, UX-DR41, UX-DR45,
 * NFR-6) on the local stack: the Varselbånd counts down to the api's stored due time; an hour before
 * it (the api's answer with its due time moved, the browser clock never decides); and once the local
 * dev route has run the real Takeover at the stored due time (never by waiting), the game leaves the
 * band and its Seat is marked in text on the Oversikt and Spillinnsikt. Which game the api picks is
 * `backend/tests/sessions/test_overview_alert.py`. */
const CSRF = { "X-Requested-With": "olspillet" };
const HOUR = 60 * 60 * 1000;
const ROLE = "(Fabrikk|Distributør|Grossist|Detaljist)";
const MARK = nb.insight.marks.takeover_inactivity;

async function untilLive(page: Page) {
  await expect(page.locator("html")).toHaveAttribute("data-live", "live", { timeout: 10_000 });
}

/** The overview answer with the band's due time one hour (and a little) after the api's clock. */
async function anHourBefore(route: Route) {
  // Without the ETag: a 304 would keep the answer the page holds, unchanged.
  const headers = Object.fromEntries(
    Object.entries(route.request().headers()).filter(([name]) => name.toLowerCase() !== "if-none-match"),
  );
  const response = await route.fetch({ headers });
  const body = await response.json();
  if (body.alert) {
    body.alert.takeover_due_at = new Date(Date.parse(body.server_now) + HOUR + 30_000).toISOString();
  }
  await route.fulfill({ response, json: body });
}

test("the band counts down to the Takeover, and a Seat taken over is marked and leaves the band", async ({
  browser,
  lecturerSession,
}) => {
  const game = await liveClassGame(browser, lecturerSession, 2, { aiMode: "rule_based" });
  const [first, second] = game.students;
  const overview = `/klasseokter/${game.sessionId}/oversikt`;
  const api = `**/api/class-sessions/${game.sessionId}/overview`;
  await orderByApi(first!, game.gameId, 1, 4);

  // The live band: the wait and the countdown to the stored due time, an Inactivity limit away.
  const page = await lecturerPage(browser, lecturerSession, VIEWPORTS[2]!);
  await page.goto(overview);
  const main = page.getByRole("main");
  const band = main.locator(`[data-attention-band="${game.gameId}"]`);
  await expect(band.locator("p")).toHaveText(
    new RegExp(`^Spill 1 venter på ${second!.name} \\(${ROLE}\\) i (under\\s1\\smin|\\d+\\smin)\\. KI overtar om \\d+\\st\\.$`),
  );
  await expect(band.getByRole("heading", { name: nb.overview.band.label })).toBeAttached();

  // One hour from Takeover, at 1440 px and at 320 CSS px: the text wraps, the page passes axe.
  await page.route(api, anHourBefore);
  await page.reload();
  await expect(band.locator("p")).toHaveText(/ KI overtar om 1\st\.$/);
  await expectAccessible(page, false);
  const narrow = await lecturerPage(browser, lecturerSession, VIEWPORTS[0]!);
  await narrow.route(api, anHourBefore);
  await narrow.goto(overview);
  const narrowBand = narrow.getByRole("main").locator("[data-attention-band]");
  await expect(narrowBand.locator("p")).toHaveText(/ KI overtar om 1\st\.$/);
  const text = (await narrowBand.locator("p").boundingBox())!;
  expect(text.x + text.width).toBeLessThanOrEqual(320);
  await expectAccessible(narrow, true);
  await narrow.unrouteAll({ behavior: "wait" });
  await narrow.context().close();
  await page.unrouteAll({ behavior: "wait" });
  await page.reload();
  await expect(band).toBeVisible();

  // The real Takeover at the Seat's stored due time (the dev route; nobody waits): the game leaves
  // the band live, and nothing takes its place.
  await untilLive(page);
  const answer = await (await page.request.get(`/api/class-sessions/${game.sessionId}/overview`)).json();
  expect(answer.alert, "the game waits for the absent Student").not.toBeNull();
  const role = answer.alert.role as string;
  const taken = await page.request.post(`/api/dev/games/${game.gameId}/seats/${role}/takeover`, { headers: CSRF });
  expect(taken.status()).toBe(200);
  await expect(main.locator("[data-attention-band]")).toHaveCount(0, { timeout: 5_000 });
  await expect(main.getByRole("link", { name: nb.messages.send })).toHaveCount(0);

  // The Seat reads «KI-spiller» with the Takeover and its reason, in the game list and the wall row.
  const roleText = new RegExp(`^${ROLE}: KI-spiller \\(${MARK}\\)$`);
  await expect(main.locator(`li[data-game="${game.gameId}"]`).getByRole("listitem").filter({ hasText: MARK })).toHaveText(
    roleText,
  );
  const row = main.getByRole("region", { name: nb.wall.region }).locator(`[data-row="${game.gameId}"]`);
  await expect(row.locator("[data-detail]")).toContainText(MARK);
  await expectAccessible(page, false);
  await page.context().close();

  // At 320 CSS px after the Takeover: no band, no page-level scroll, axe passes.
  const after = await lecturerPage(browser, lecturerSession, VIEWPORTS[0]!);
  await after.goto(overview);
  await expect(after.getByRole("main").locator(`li[data-game="${game.gameId}"]`)).toContainText(MARK);
  await expect(after.getByRole("main").locator("[data-attention-band]")).toHaveCount(0);
  await expectAccessible(after, true);

  // Spillinnsikt marks the Seat the same, in text.
  await after.goto(`${overview}/spill/${game.gameId}`);
  const seat = after.getByRole("main").locator(`[data-insight-seats] [data-role="${role}"]`);
  await expect(seat.locator("[data-seat-mark]")).toHaveText(MARK);
  await expect(seat).toContainText(nb.insight.aiPlayer);
  await after.context().close();
});
