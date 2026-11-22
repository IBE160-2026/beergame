import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { osloClock } from "../src/modules/games/in-room";
import { expectAccessible, expectReflow, lecturerPage, test, VIEWPORTS } from "./support/classes";
import { liveClassGame, orderByApi } from "./support/live-game";

/** «I rommet» (Story 8.11, FR-36, UX-DR8, UX-DR52, UX-DR62, NFR-6) on the local stack: a fresh
 * Class game whose first Student has ordered Uke 1. Outside a Labtime «Marker som i rommet» is
 * unavailable with its reason; in one it opens the form in place with focus in «Ventetid i rommet»,
 * «Avbryt» gives focus back, a value outside 2 to 120 is said under the field, and a valid one marks
 * the game: the result line takes focus, Spillstyring reads the mark with «Ikke i rommet lenger»,
 * the wall's row label carries «I rommet», and the Students read the line above Setestatus, which
 * goes live when the Lecturer ends it. The command's rules are `backend/tests/games/test_in_room.py`. */
const copy = nb.spillstyring.inRoom;
const CSRF = { "X-Requested-With": "olspillet" };
const MINUTE = 60 * 1000;

async function untilLive(page: Page) {
  await expect(page.locator("html")).toHaveAttribute("data-live", "live", { timeout: 10_000 });
}

test("a Lecturer marks a game «I rommet» in a Labtime, the Students read it, and it ends", async ({
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
  const open = block.locator("[data-in-room-open]");

  // No Labtime: shown unavailable, with its reason read with it.
  await expect(open).toHaveAttribute("aria-disabled", "true");
  await expect(block.locator("[data-in-room-unavailable]")).toHaveText(copy.onlyInLabHour);
  // A press does nothing (UX-DR8): the button keeps focus and opens no form.
  await open.click({ force: true });
  await expect(block.locator("[data-in-room-form]")).toHaveCount(0);
  await expect(open).toBeFocused();

  // A Labtime on now.
  const added = await page.request.post(`/api/class-sessions/${game.sessionId}/lab-hours`, {
    data: {
      starts_at: new Date(Date.now() - 5 * MINUTE).toISOString(),
      ends_at: new Date(Date.now() + 60 * MINUTE).toISOString(),
      place: "Datalab A2",
    },
    headers: CSRF,
  });
  expect(added.status()).toBe(201);
  const until = osloClock((await added.json()).ends_at as string);
  await page.reload();
  await expect(open).not.toHaveAttribute("aria-disabled", "true");
  await expect(block.locator("[data-in-room-unavailable]")).toHaveCount(0);
  await untilLive(page);

  // 320 CSS px: the form opens in place, its primary full width, axe passes.
  const small = await lecturerPage(browser, lecturerSession, VIEWPORTS[0]!);
  await small.goto(path);
  await small.locator("[data-spillstyring] [data-in-room-open]").click();
  const smallForm = small.locator("[data-in-room-form]");
  await expect(smallForm.getByLabel(copy.field)).toBeFocused();
  const smallConfirm = smallForm.getByRole("button", { name: copy.confirm(10) });
  expect((await smallConfirm.boundingBox())!.width).toBeGreaterThanOrEqual(240);
  await expectAccessible(small, true);
  await expectReflow(small, true);
  await small.context().close();

  // Open: focus in the field (10); «Avbryt» gives it back to the opener.
  await open.click();
  const form = block.locator("[data-in-room-form]");
  const field = form.getByLabel(copy.field);
  await expect(field).toBeFocused();
  await expect(field).toHaveValue("10");
  await expect(form).toContainText(copy.consequence(until));
  await expect(form.getByRole("button", { name: copy.confirm(10) })).toBeVisible();
  await form.getByRole("button", { name: copy.cancel }).click();
  await expect(form).toHaveCount(0);
  await expect(open).toBeFocused();

  // A value out of range is said under the field on leaving it (the Ordrefelt pattern).
  await open.click();
  await field.fill("1");
  await form.getByRole("button", { name: copy.confirm(null) }).focus();
  await expect(form.locator('[role="alert"]')).toHaveText(copy.error);
  await expectAccessible(page, false);

  // A Student of the game has Spill open, live, with no line yet.
  const play = await second!.context.newPage();
  await play.goto(`/spill/${game.gameId}`);
  const line = play.getByRole("main").locator("[data-in-room-line]");
  await expect(line).toHaveAttribute("aria-live", "polite");
  await expect(line).toHaveAttribute("data-in-room-line", "");
  await untilLive(play);

  // A valid value marks the game: the result line takes focus, and the block reads the mark.
  await field.fill("10");
  await form.getByRole("button", { name: copy.confirm(10) }).click();
  const done = block.locator("[data-in-room-result]");
  await expect(done).toHaveText(copy.done(until));
  await expect(done).toBeFocused();
  await expect(done).toHaveClass(/sr-only/); // the marked line says it; not shown twice
  await expect(block.locator("[data-in-room-marked]")).toHaveText(copy.marked(until, 10));
  await expect(block.getByRole("button", { name: copy.end })).toBeVisible();
  await expectAccessible(page, false);

  // The Student's line above Setestatus comes live, in its polite region.
  await expect(line.locator("p")).toHaveText(nb.homes.student.inRoom.line(until, 10), { timeout: 10_000 });
  // Hjem shows the same line above Setestatus (Epic 8 close-out).
  const hjem = await play.context().newPage();
  await hjem.goto("/hjem");
  await expect(hjem.getByRole("main").locator('[data-in-room-line="on"] p')).toHaveText(
    nb.homes.student.inRoom.line(until, 10),
  );
  await hjem.close();

  // The wall's row label carries «I rommet».
  const board = await lecturerPage(browser, lecturerSession, VIEWPORTS[2]!);
  await board.goto(`/klasseokter/${game.sessionId}/oversikt`);
  await expect(board.getByRole("main")).toContainText("· I rommet");
  await board.context().close();

  // 320 CSS px: the mark reflows, its action full width, axe passes.
  const narrow = await lecturerPage(browser, lecturerSession, VIEWPORTS[0]!);
  await narrow.goto(path);
  const end = narrow.locator("[data-spillstyring]").getByRole("button", { name: copy.end });
  await expect(end).toBeVisible();
  expect((await end.boundingBox())!.width).toBeGreaterThanOrEqual(240);
  await expectAccessible(narrow, true);
  await expectReflow(narrow, true);
  await narrow.context().close();

  // «Ikke i rommet lenger»: the result line takes focus; the Student's line goes, read out.
  await block.getByRole("button", { name: copy.end }).click();
  await expect(done).toHaveText(copy.ended);
  await expect(done).toBeFocused();
  await expect(open).toBeVisible();
  await expect(line).toHaveAttribute("data-in-room-line", "ended", { timeout: 10_000 });
  await expect(line.locator("p")).toHaveText(nb.homes.student.inRoom.ended);
  await expect(line.locator("p")).toHaveClass(/sr-only/);
  await page.context().close();
});
