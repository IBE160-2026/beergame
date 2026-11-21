import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { osloWeekdayTime, toOsloInput } from "../src/modules/sessions/dates";
import { expectAccessible, expectReflow, lecturerPage, test, VIEWPORTS } from "./support/classes";
import { liveClassGame, orderByApi } from "./support/live-game";

/** The Lecturer's Pause with an agreed time (Story 8.7, FR-89, UX-DR45, UX-DR52, UX-DR62, NFR-6) on
 * the local stack: a fresh Class game whose first Student has ordered Uke 1. Spillstyring's «Pause
 * spillet» opens the form in place with focus in «Dato», «Avbryt» gives focus back, a time after the
 * Spillfrist is said under the field, and a valid one pauses the game: the result line takes focus,
 * Spillinnsikt reads the paused line with «Endre avtalt tid» and «Avslutt pausen», and the Student
 * reads «Pause til …, satt av faglæreren.». The Varselbånd's form keeps one primary on the screen.
 * The command's rules are `backend/tests/games/test_staff_pause.py`. */
const copy = nb.spillstyring.pause;

async function untilLive(page: Page) {
  await expect(page.locator("html")).toHaveAttribute("data-live", "live", { timeout: 10_000 });
}

/** The Class session's Spillfrist, read from Spillinnsikt. */
async function playDeadline(page: Page, gameId: string): Promise<string> {
  const insight = await (await page.request.get(`/api/games/${gameId}/insight`)).json();
  expect(insight.play_deadline).toBeTruthy();
  return insight.play_deadline as string;
}

/** A whole minute two hours before `iso`, as the two fields take it. */
function fieldsBefore(iso: string): { date: string; time: string; at: string } {
  const at = new Date(Date.parse(iso) - 2 * 60 * 60 * 1000);
  at.setUTCSeconds(0, 0);
  const [date, time] = toOsloInput(at.toISOString()).split("T") as [string, string];
  return { date, time: time.slice(0, 5), at: at.toISOString() };
}

test("Spillstyring pauses the game with an agreed time, and the Student reads it", async ({
  browser,
  lecturerSession,
}) => {
  const game = await liveClassGame(browser, lecturerSession, 2, { aiMode: "rule_based" });
  const [first, second] = game.students;
  await orderByApi(first!, game.gameId, 1, 4);
  const path = `/klasseokter/${game.sessionId}/oversikt/spill/${game.gameId}`;

  const page = await lecturerPage(browser, lecturerSession, VIEWPORTS[2]!);
  await page.goto(path);
  const block = page.locator("[data-spillstyring]");
  const open = block.getByRole("button", { name: copy.open });
  await expect(open).toBeVisible();
  await untilLive(page);
  const deadline = await playDeadline(page, game.gameId);

  // Open: focus in «Dato»; «Avbryt» gives it back to «Pause spillet».
  await open.click();
  const form = block.locator("[data-staff-pause]");
  await expect(form.getByLabel(copy.date)).toBeFocused();
  await expect(form).toContainText(copy.noTakeover);
  await expect(form).toContainText(copy.afterTime);
  await expect(form.getByRole("button", { name: copy.confirm })).toBeVisible();
  await form.getByRole("button", { name: copy.cancel }).click();
  await expect(form).toHaveCount(0);
  await expect(open).toBeFocused();

  // A time after the Spillfrist is said under the field on leaving it; nothing is sent.
  await open.click();
  const after = fieldsBefore(new Date(Date.parse(deadline) + 48 * 60 * 60 * 1000).toISOString());
  await form.getByLabel(copy.date).fill(after.date);
  await form.getByLabel(copy.time).fill(after.time);
  await form.getByLabel(copy.date).focus();
  const range = form.locator('[role="alert"]');
  await expect(range).toContainText("Spillfristen");
  await expectAccessible(page, false);
  await expectReflow(page, false);

  // A valid time: the primary names it; the press pauses the game.
  const valid = fieldsBefore(deadline);
  await form.getByLabel(copy.date).fill(valid.date);
  await form.getByLabel(copy.time).fill(valid.time);
  const when = osloWeekdayTime(valid.at);
  const confirm = form.getByRole("button", { name: copy.confirmAt(when) });
  await expect(confirm).toBeVisible();
  await confirm.click();
  const done = block.locator("[data-pause-result]");
  await expect(done).toHaveText(copy.doneAt(when));
  await expect(done).toBeFocused();
  await expect(block.locator("[data-insight-pause]")).toContainText(copy.agreed(when));
  await expect(block.getByRole("button", { name: copy.change })).toBeVisible();
  await expect(block.getByRole("button", { name: copy.end })).toBeVisible();
  await expectAccessible(page, false);

  // The Student reads the Lecturer's line with the agreed time on Hjem.
  const home = await second!.context.newPage();
  await home.goto("/hjem");
  await expect(home.getByRole("main").locator("[data-pause-line] p")).toHaveText(
    nb.homes.student.pause.pausedUntil(when),
  );

  // «Endre avtalt tid» saves a new time; the Student's line follows it live.
  await untilLive(home);
  const later = fieldsBefore(new Date(Date.parse(deadline) - 60 * 60 * 1000).toISOString());
  const laterWhen = osloWeekdayTime(later.at);
  await block.getByRole("button", { name: copy.change }).click();
  const changeAt = block.locator("[data-staff-pause]");
  await changeAt.getByLabel(copy.date).fill(later.date);
  await changeAt.getByLabel(copy.time).fill(later.time);
  await changeAt.getByRole("button", { name: copy.saveAt(laterWhen) }).click();
  await expect(done).toHaveText(copy.doneAt(laterWhen));
  await expect(done).toBeFocused();
  await expect(block.locator("[data-insight-pause]")).toContainText(copy.agreed(laterWhen));
  await expect(home.getByRole("main").locator("[data-pause-line] p")).toHaveText(
    nb.homes.student.pause.pausedUntil(laterWhen),
    { timeout: 10_000 },
  );
  // …and «Uten avtalt tid» clears it: the line then names the Lecturer without a time.
  await block.getByRole("button", { name: copy.change }).click();
  await block.locator("[data-staff-pause]").getByLabel(copy.noTime).check();
  await block.getByRole("button", { name: copy.saveNoTime }).click();
  await expect(done).toHaveText(copy.doneNoTime);
  await expect(home.getByRole("main").locator("[data-pause-line] p")).toHaveText(
    nb.homes.student.pause.pausedByLecturer,
    { timeout: 10_000 },
  );
  // The time again, for the narrow page's prefilled form below.
  await block.getByRole("button", { name: copy.change }).click();
  const again = block.locator("[data-staff-pause]");
  await again.getByLabel(copy.date).fill(valid.date);
  await again.getByLabel(copy.time).fill(valid.time);
  await again.getByRole("button", { name: copy.saveAt(when) }).click();
  await expect(done).toHaveText(copy.doneAt(when));

  // 320 CSS px: the paused state reflows, its actions full width, axe passes.
  const narrow = await lecturerPage(browser, lecturerSession, VIEWPORTS[0]!);
  await narrow.goto(path);
  const narrowBlock = narrow.locator("[data-spillstyring]");
  const change = narrowBlock.getByRole("button", { name: copy.change });
  await expect(change).toBeVisible();
  expect((await change.boundingBox())!.width).toBeGreaterThanOrEqual(240);
  expect((await change.boundingBox())!.height).toBeGreaterThanOrEqual(44);
  await expectAccessible(narrow, true);
  await expectReflow(narrow, true);
  // «Endre avtalt tid» opens prefilled, with focus in «Dato».
  await change.click();
  const changeForm = narrowBlock.locator("[data-staff-pause]");
  await expect(changeForm.getByLabel(copy.date)).toBeFocused();
  await expect(changeForm.getByLabel(copy.date)).toHaveValue(valid.date);
  await expectAccessible(narrow, true);
  await expectReflow(narrow, true);
  await narrow.context().close();

  // «Avslutt pausen»: one press; the result line takes focus, and the Student reads the end.
  await untilLive(page);
  await block.getByRole("button", { name: copy.end }).click();
  const ended = block.locator("[data-pause-result]");
  await expect(ended).toHaveText(copy.ended);
  await expect(ended).toBeFocused();
  await expect(block.getByRole("button", { name: copy.open })).toBeVisible();
  await expect(home.getByRole("main").locator("[data-pause-line] p")).toHaveText(
    nb.homes.student.pause.endedByLecturer,
    { timeout: 10_000 },
  );
  await page.context().close();
});

test("the Varselbånd's «Pause spillet» opens the form under the band with one primary", async ({
  browser,
  lecturerSession,
}) => {
  const game = await liveClassGame(browser, lecturerSession, 2, { aiMode: "rule_based" });
  await orderByApi(game.students[0]!, game.gameId, 1, 4);
  const phone = { name: "360 px", width: 360, height: 800, phone: true };
  for (const viewport of [VIEWPORTS[2]!, phone]) {
    const page = await lecturerPage(browser, lecturerSession, viewport);
    await page.goto(`/klasseokter/${game.sessionId}/oversikt`);
    const main = page.getByRole("main");
    const band = main.locator(`[data-attention-band="${game.gameId}"]`);
    const open = band.getByRole("button", { name: copy.open });
    await expect(open).toBeVisible();
    await expect(band.locator("[data-band-message].bg-ink")).toHaveCount(1);
    await open.click();
    const form = main.locator("[data-staff-pause]");
    await expect(form.getByLabel(copy.date)).toBeFocused();
    // The form's primary is the one primary: «Send Melding» shows as secondary.
    await expect(band.locator("[data-band-message].bg-ink")).toHaveCount(0);
    await expect(form.locator("[data-staff-pause-confirm].bg-ink")).toHaveCount(1);
    await expectAccessible(page, viewport.phone);
    await expectReflow(page, viewport.phone);
    await form.getByRole("button", { name: copy.cancel }).click();
    await expect(open).toBeFocused();
    await expect(band.locator("[data-band-message].bg-ink")).toHaveCount(1);
    if (viewport === VIEWPORTS[2]) {
      await page.context().close();
      continue;
    }
    // Paused without a time: the game leaves the band, and the result line stands under it.
    await untilLive(page);
    await open.click();
    await form.getByLabel(copy.noTime).check();
    await form.getByRole("button", { name: copy.confirmNoTime }).click();
    const done = main.locator("[data-pause-result]");
    await expect(done).toHaveText(copy.doneNoTime);
    await expect(done).toBeFocused();
    await expect(main.locator("[data-attention-band]")).toHaveCount(0, { timeout: 5_000 });
    await page.context().close();
  }
});
