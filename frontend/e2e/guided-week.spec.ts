import { expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import type { PlayTurn } from "../src/modules/games/api";
import week3 from "../src/modules/games/fixtures/play-week-3.json";
import week11 from "../src/modules/games/fixtures/play-week-11.json";
import { loginByApi } from "./support/auth";
import { expectAccessible } from "./support/classes";

/** The Veiledet uke on the play screen (Story 6.10, FR-14, FR-24, FR-73, NFR-6, UX-DR20, UX-DR62).
 * As in `chain-band.spec.ts`, the game and its envelope are stand-ins with the api's shapes: the
 * engine's Grossist of a Classic game in Uke 3 (a Guided Week) and Uke 11, held to the engine by
 * `backend/tests/games/test_play_fixture.py`. The view the page sends is caught here; the api's
 * side is `backend/tests/sessions/test_guided_weeks.py`. */
const GAME_ID = "01a1f8ee-34f2-70af-8800-f79281ed7a66";
const copy = nb.games.play;

type Envelope = Omit<typeof week11, "turn"> & { turn: PlayTurn };

/** Opens the play screen on `envelope` and returns the Weeks the page reported as viewed (each
 * answered 204), unless the test answers the views itself (`catchViews` false). */
async function openPlay(page: Page, envelope: Envelope, catchViews = true): Promise<number[]> {
  const viewed: number[] = [];
  await loginByApi(page, "student");
  await page.route(`**/api/me/games/${GAME_ID}`, (route) =>
    route.fulfill({
      json: {
        id: GAME_ID,
        number: 17,
        role: "wholesaler",
        seats: envelope.table_status.seats,
        briefing_first: false,
        rules: { order_delay: 2, shipping_delay: 2, production_delay: 2, guided_weeks: 4, holding_cost: "0.50", backorder_cost: "1.00" },
        status: "running",
        week: envelope.seat_state.week,
      },
    }),
  );
  await page.route(`**/api/me/games/${GAME_ID}/play`, (route) => route.fulfill({ json: envelope }));
  if (catchViews) {
    await page.route(`**/api/me/games/${GAME_ID}/weeks/*/view`, (route) => {
      viewed.push(Number(route.request().url().split("/weeks/")[1].split("/")[0]));
      return route.fulfill({ status: 204 });
    });
  }
  await page.goto(`/spill/${GAME_ID}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.week(envelope.seat_state.week));
  return viewed;
}

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

for (const width of [320, 360, 1440]) {
  test.describe(`${width} px`, () => {
    test.use({ viewport: { width, height: 800 } });

    test("Veiledet uke: the fixed Order read-only, no button, the page views the Week once", async ({ page }) => {
      const viewed = await openPlay(page, week3 as Envelope);
      const field = page.getByLabel(copy.order.label(3));
      await expect(field).toHaveValue("4");
      await expect(field).toHaveAttribute("readonly", "");
      await expect(field).toHaveAccessibleDescription(copy.order.guided);
      await expect(page.getByText(copy.order.guided)).toBeVisible();
      await expect(page.getByRole("button", { name: /Bekreft/ })).toHaveCount(0);
      // The read-only state's tokens: `future-tint` fill, `ink-muted` value (DESIGN.md → Ordrefelt).
      const look = await field.evaluate((el) => {
        const style = getComputedStyle(el);
        return [style.backgroundColor, style.color];
      });
      expect(look).toEqual(["rgb(242, 245, 248)", "rgb(94, 111, 130)"]);
      // The fixed Order also stands in Din ordre at nå, not the empty dashed cell.
      const orderRow = page.locator('tr[data-row="order"]');
      await expect(orderRow.getByText(copy.table.noOrderYet)).toHaveCount(0);
      await expect(orderRow.locator("td").nth(2)).toHaveText("4"); // the columns start at Uke 1
      await expect.poll(() => viewed).toEqual([3]);
      // Reading order: the field comes after the week table (phone) and before the links.
      const order = await page.evaluate(() => {
        const nodes = [...document.querySelectorAll("[data-chart='band'], [data-order-field], main a")];
        return nodes.map((n) => (n.matches("[data-order-field]") ? "order" : n.matches("a") ? "link" : "band"));
      });
      expect(order.indexOf("band")).toBeLessThan(order.indexOf("order"));
      expect(order.indexOf("order")).toBeLessThan(order.indexOf("link"));
      await expectAccessible(page, width < 1024);
      expect(viewed).toEqual([3]);
    });
  });
}

test("Uke 11, past the Guided Weeks: no Veiledet uke field and no view", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  const viewed = await openPlay(page, week11);
  await expect(page.locator('svg[data-chart="band"]')).toHaveCount(1);
  await expect(page.locator("[data-order-field]")).toHaveCount(0);
  await expect(page.getByText(copy.order.guided)).toHaveCount(0);
  expect(viewed).toEqual([]);
});

test("a view that fails for a passing reason is sent again; a refused one is not", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  await page.clock.install();
  const answers = [500, 409];
  const sent: number[] = [];
  await page.route(`**/api/me/games/${GAME_ID}/weeks/*/view`, (route) => {
    const status = answers[sent.length] ?? 204;
    sent.push(status);
    return route.fulfill(
      status === 204 ? { status } : { status, json: { error: { code: status === 409 ? "week_not_open" : "internal_error", message: "x" } } },
    );
  });
  await openPlay(page, week3 as Envelope, false);
  await expect.poll(() => sent).toEqual([500]);
  await page.clock.runFor(5000);
  await expect.poll(() => sent).toEqual([500, 409]);
  await page.clock.runFor(10000);
  expect(sent).toEqual([500, 409]);
});

test("a viewed Veiledet uke shows the field and sends no view again", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  const viewed = await openPlay(page, { ...(week3 as Envelope), turn: { guided: true, order: 4, viewed: true } });
  await expect(page.getByLabel(copy.order.label(3))).toHaveValue("4");
  expect(viewed).toEqual([]);
});
