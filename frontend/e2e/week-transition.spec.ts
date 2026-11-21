import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { expectAccessible, test } from "./support/classes";
import { confirmButton, GAME_ID, openPlay, orderField, refetchPlay, week12 } from "./support/play";

/** The Uke-overgang (Story 6.15, UX-DR23, UX-DR78, NFR-5, NFR-6) on the play screen with stand-in
 * envelopes (`support/play.ts`): the page shows Uke 11, the envelope then holds Uke 12 and is read
 * again, as a `game:` event or a reconnect makes it. The real live path and its 2 s are
 * `week-advance.spec.ts`; the numbers' source is `src/modules/games/week-summary.test.ts`. */
const copy = nb.games.play;
const summary = (page: Page) => page.locator("[data-week-summary]");
const skip = (page: Page) => page.getByRole("button", { name: copy.summary.skip });
const moves = (page: Page) =>
  page.locator("[data-now-line]").first().evaluate((el) => el.getAnimations().filter((a) => a.playState === "running").length);

/** Moves the stub on to Uke 12 and reads the envelope again; waits for the new heading. */
async function advance(page: Page, stub: { envelope: unknown }, ordered = 24) {
  stub.envelope = week12(ordered);
  await refetchPlay(page);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.week(12));
}

test("the Uke moves on: the summary from the api's numbers, announced, the now-line moves and «Hopp over» ends it, focus kept", async ({
  page,
}) => {
  await page.setViewportSize({ width: 360, height: 740 });
  const stub = await openPlay(page);
  // Uke 11 already shows the summary of Uke 10, from stored state, and reads nothing on load.
  await expect(summary(page).getByRole("heading", { name: "Uke 10 er ferdig regnet" })).toBeVisible();
  await expect(page.locator("[data-week-announce]")).toHaveText("");
  await expect(skip(page)).toHaveCount(0);
  const region = page.getByRole("region", { name: copy.table.region });
  await region.focus();

  await advance(page, stub);
  const block = summary(page);
  await expect(block.getByRole("heading", { name: "Uke 11 er ferdig regnet" })).toBeVisible();
  await expect(block.locator("dl > div")).toHaveText(["Levering4", "Ordre inn11", "Sendt4", "Restordre20 blir 27"]);
  await expect(block.getByText("Denne uka: 27 restordre × 1,00 = 27,00 kr")).toBeVisible();
  await expect(block.getByRole("link")).toHaveCount(0); // «Kostnad så langt» comes with Story 6.16
  await expect(page.locator("[data-week-announce]")).toHaveText(
    "Uke 11 er ferdig regnet. Levering 4. Ordre inn 11. Sendt 4. Restordre 20 blir 27. Denne uka: 27 restordre × 1,00 = 27,00 kr.",
  );
  await expect(region).toBeFocused();
  // The summary stands above the Ordrefelt, which is usable while the line moves.
  const field = orderField(page, 12);
  expect((await block.boundingBox())!.y).toBeLessThan((await field.boundingBox())!.y);
  await expect(skip(page)).toBeVisible();
  expect(await moves(page)).toBe(1);
  await field.fill("5");
  await expect(confirmButton(page)).toHaveText(copy.order.confirmOn("5"));
  await skip(page).click();
  await expect(skip(page)).toHaveCount(0);
  expect(await moves(page)).toBe(0);
  // The new column: Levering and Ordre inn filled, the dashed empty Din ordre cell at nå, and nå
  // and «Nå» in view in the region.
  const now = page.locator("thead th[data-now]");
  await expect(now).toHaveText(/12/);
  const box = (await region.boundingBox())!;
  const at = (await now.boundingBox())!;
  expect(at.x).toBeGreaterThanOrEqual(box.x);
  expect(at.x + at.width).toBeLessThanOrEqual(box.x + box.width + 1);

  // The own Order sent: the summary is gone.
  await page.route(`**/api/me/games/${GAME_ID}/weeks/12/order`, (route) => {
    stub.envelope = { ...week12(), turn: { guided: false, order: 5, viewed: false } };
    return route.fulfill({ status: 204 });
  });
  await confirmButton(page).click();
  await expect(page.locator("[data-order-sent]")).toBeVisible();
  await expect(summary(page)).toHaveCount(0);
});

test("with reduced motion nothing moves and there is no «Hopp over»; the summary shows at once", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 360, height: 740 });
  const stub = await openPlay(page);
  await advance(page, stub);
  await expect(summary(page).getByRole("heading", { name: "Uke 11 er ferdig regnet" })).toBeVisible();
  await expect(skip(page)).toHaveCount(0);
  expect(await moves(page)).toBe(0);
  await expectAccessible(page, true);
});

test("a typed Order not sent when its Uke closed is dropped with a line saying so, until the next keystroke", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  const stub = await openPlay(page);
  await orderField(page).fill("24");
  // The Seat's Order of Uke 11 came from another device: 8, not the 24 typed here.
  await advance(page, stub, 8);
  const line = page.locator("[data-draft-dropped]");
  await expect(line).toHaveText(copy.summary.draftDropped(11, "24"));
  await expect(orderField(page, 12)).toHaveValue("");
  await orderField(page, 12).fill("3");
  await expect(line).toHaveText("");
});

for (const width of [320, 360, 1440]) {
  test(`the Uke-overgang at ${width} px reflows without page scroll and passes axe`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    const stub = await openPlay(page);
    await advance(page, stub);
    await expect(skip(page)).toBeVisible();
    await expectAccessible(page, width < 1024);
    // With reduced motion the same screen, without «Hopp over»: it still reflows.
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.reload();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.week(12));
    await expect(summary(page)).toBeVisible();
    await expect(skip(page)).toHaveCount(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBe(false);
  });
}
