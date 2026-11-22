import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { expectAccessible, expectReflow, lecturerPage, test, VIEWPORTS } from "./support/classes";
import { liveClassGame, orderByApi } from "./support/live-game";

/** Tilrettelegging (Story 8.9, FR-17, UX-DR52, UX-DR53, NFR-6) on the local stack: a fresh Class
 * game whose first Student has ordered Uke 1, so the game waits for the second. The Lecturer
 * follows the second Student's name from Spillinnsikt to the Studentside, gives 2 × and a share of
 * 60 % in the in-place form, and reads the saved line; Spillstyring then marks the Seat, and the
 * Student alone reads the lines on Hjem. The rules and the recomputed due times are
 * `backend/tests/sessions/test_adjustment.py` and `backend/tests/games/test_turn_factor.py`. */
const copy = nb.reports.adjustment;

async function untilLive(page: Page) {
  await expect(page.locator("html")).toHaveAttribute("data-live", "live", { timeout: 10_000 });
}

test("a Lecturer gives one Student more time from the Studentside", async ({ browser, lecturerSession }) => {
  const game = await liveClassGame(browser, lecturerSession, 2, { aiMode: "rule_based" });
  const [first, second] = game.students;
  await orderByApi(first!, game.gameId, 1, 4);

  // 1440 px: from Spillinnsikt the Student's name leads to the Studentside.
  const page = await lecturerPage(browser, lecturerSession, VIEWPORTS[2]!);
  await page.goto(`/klasseokter/${game.sessionId}/oversikt/spill/${game.gameId}`);
  await page.locator("[data-insight-seats]").getByRole("link", { name: nb.reports.studentPage.linkLabel(second!.name) }).click();
  await expect(page).toHaveURL(/\/studenter\//);
  await expect(page.getByRole("heading", { level: 1, name: second!.name })).toBeVisible();
  const block = page.locator("[data-adjustment]");
  await expect(block.locator("[data-adjustment-summary]")).toHaveText(copy.none);
  await expectAccessible(page, false);
  await untilLive(page);

  // The form opens in place, focus on the chosen Valgknapp; «Avbryt» returns it to the opener.
  const opener = block.getByRole("button", { name: copy.change });
  await opener.click();
  const form = block.locator("[data-adjustment-form]");
  await expect(form.getByRole("radio", { name: copy.asClass })).toBeFocused();
  await expect(form.getByText(copy.scope(second!.name))).toBeVisible();
  await expect(form.getByText(copy.classShare("80 %"))).toBeVisible();
  await expectAccessible(page, false);
  await form.locator("[data-adjustment-cancel]").click();
  await expect(opener).toBeFocused();

  // A share above the class share is refused on the field, which takes focus.
  await opener.click();
  const share = form.getByRole("textbox", { name: copy.shareLabel });
  await share.fill("81");
  await form.getByRole("button", { name: copy.save }).click();
  await expect(form.getByText(copy.shareError(80))).toBeVisible();
  await expect(share).toBeFocused();

  // 2 × and 60 %: saved, the line and the summary replace the form and take focus.
  await form.getByRole("radio", { name: /^2\s×$/ }).check();
  await share.fill("60");
  const saved = page.waitForResponse((r) => r.url().endsWith("/adjustment") && r.request().method() === "PUT");
  await form.getByRole("button", { name: copy.save }).click();
  expect((await saved).status()).toBe(200);
  const summary = block.locator("[data-adjustment-summary]");
  await expect(summary).toContainText(copy.saved);
  await expect(summary).toContainText("Mer tid: 2 ×. Andel uker: 60 %.");
  await expect(summary).toBeFocused();
  await expect(form).toHaveCount(0);
  await expectReflow(page, false);

  // Spillstyring marks the Seat for the Lecturer.
  await page.goto(`/klasseokter/${game.sessionId}/oversikt/spill/${game.gameId}`);
  const row = page.locator("[data-spillstyring] li").filter({ hasText: second!.name });
  await expect(row.locator("[data-extra-time]")).toHaveText(nb.spillstyring.extraTime(second!.name));
  await expect(page.locator("[data-spillstyring] [data-extra-time]")).toHaveCount(1);
  await page.context().close();

  // 320 px: the block and the open form are one column with no page scroll, and pass axe.
  const narrow = await lecturerPage(browser, lecturerSession, VIEWPORTS[0]!);
  await narrow.goto(`/klasseokter/${game.sessionId}/oversikt/spill/${game.gameId}`);
  await narrow.locator("[data-insight-seats]").getByRole("link", { name: nb.reports.studentPage.linkLabel(second!.name) }).click();
  const narrowBlock = narrow.locator("[data-adjustment]");
  await expect(narrowBlock.locator("[data-adjustment-summary]")).toHaveText("Mer tid: 2 ×. Andel uker: 60 %.");
  await expectAccessible(narrow, true);
  await narrowBlock.getByRole("button", { name: copy.change }).click();
  await expect(narrowBlock.locator("[data-adjustment-form]").getByRole("radio", { name: /^2\s×$/ })).toBeFocused();
  await expectAccessible(narrow, true);
  await narrow.context().close();

  // Only the Student concerned reads the lines on Hjem.
  const own = await second!.context.newPage();
  await own.goto("/hjem");
  const lines = own.locator("[data-own-adjustment]");
  await expect(lines).toContainText(nb.homes.student.adjustment.moreTime("2 ×"));
  await expect(lines).toContainText(nb.homes.student.adjustment.share("60 %"));
  const other = await first!.context.newPage();
  await other.goto("/hjem");
  await expect(other.getByRole("heading", { name: nb.homes.student.steps }).first()).toBeVisible();
  await expect(other.locator("[data-own-adjustment]")).toHaveCount(0);
  await first!.context.close();
  await second!.context.close();
});
