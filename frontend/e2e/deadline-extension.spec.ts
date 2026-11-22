import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { osloDateText, toOsloInput } from "../src/modules/sessions/dates";
import { deadlineLine } from "../src/modules/tests/individual-test";
import { expectAccessible, expectReflow, lecturerPage, test, VIEWPORTS } from "./support/classes";
import { liveClassGame } from "./support/live-game";

/** Extend one Student's Test deadline (Story 11.13, FR-18, NFR-6) on the local stack: a fresh
 * Class game of two Students. The Lecturer follows the second Student's name from Spillinnsikt to
 * the Studentside, opens «Forleng testfrist» in place (one form open at a time with
 * «Tilrettelegging»), is refused a date that is not later than the Class's on the field, saves a
 * later one and reads the result line with focus; at 360 px the block and the form pass axe. The
 * Student then reads their own Testfrist on the Individual test's statement, the other Student the
 * Class's, at 360 and 1440 px with axe. The rules, the gates, the sweep and the reminders are
 * `backend/tests/individual_test/test_extension.py`. */
const copy = nb.reports.deadline;
const CSRF = { "X-Requested-With": "olspillet" };
const DAY = 24 * 60 * 60 * 1000;
const PHONE = { width: 360, height: 740 };

async function untilLive(page: Page) {
  await expect(page.locator("html")).toHaveAttribute("data-live", "live", { timeout: 10_000 });
}

test("a Lecturer extends one Student's Test deadline, and the Student reads their own date", async ({
  browser,
  lecturerSession,
}) => {
  test.slow(); // Invitations through the worker, a Class session, a lock, a started game
  const game = await liveClassGame(browser, lecturerSession, 2, { aiMode: "rule_based" });
  const [first, second] = game.students;

  // 1440 px: from Spillinnsikt the Student's name leads to the Studentside and its «Frister».
  const page = await lecturerPage(browser, lecturerSession, VIEWPORTS[2]!);
  await page.goto(`/klasseokter/${game.sessionId}/oversikt/spill/${game.gameId}`);
  await page.locator("[data-insight-seats]").getByRole("link", { name: nb.reports.studentPage.linkLabel(second!.name) }).click();
  await expect(page).toHaveURL(/\/studenter\//);
  const studentPath = new URL(page.url()).pathname;
  const userId = studentPath.split("/").at(-1)!;
  const read = await page.request.get(`/api/class-sessions/${game.sessionId}/students/${userId}`);
  const classTest = ((await read.json()) as { deadlines: { class_test_deadline: string } }).deadlines.class_test_deadline;
  const block = page.locator("[data-deadline]");
  const summary = block.locator("[data-deadline-summary]");
  await expect(summary).toContainText(copy.test(osloDateText(classTest)));
  await expect(summary).toContainText(copy.asClass);
  await untilLive(page);

  // The form opens in place with focus on the field; «Avbryt» returns focus to the opener.
  const opener = block.getByRole("button", { name: copy.change });
  await opener.click();
  const form = block.locator("[data-deadline-form]");
  const field = form.getByLabel(copy.fieldLabel);
  await expect(field).toBeFocused();
  await expect(form.getByText(copy.hint(osloDateText(classTest)))).toBeVisible();
  await expect(form.getByText(copy.scope(second!.name))).toBeVisible();
  await expectAccessible(page, false);
  await form.locator("[data-deadline-cancel]").click();
  await expect(opener).toBeFocused();

  // One form at a time: opening «Tilrettelegging» closes this one, keeping nothing.
  await opener.click();
  await expect(form).toHaveCount(1);
  await page.locator("[data-adjustment]").getByRole("button", { name: nb.reports.adjustment.change }).click();
  await expect(page.locator("[data-adjustment-form]")).toHaveCount(1);
  await expect(form).toHaveCount(0);

  // A date that is not later than the Class's is refused on the field, which takes focus.
  await block.getByRole("button", { name: copy.change }).click();
  await expect(page.locator("[data-adjustment-form]")).toHaveCount(0);
  await field.fill(toOsloInput(classTest));
  await form.getByRole("button", { name: copy.save }).click();
  await expect(form.getByText(copy.errors.not_later(osloDateText(classTest)))).toBeVisible();
  await expect(field).toBeFocused();

  // Two days later: saved, the result line replaces the form and takes focus.
  const own = new Date(Date.parse(classTest) + 2 * DAY).toISOString();
  await field.fill(toOsloInput(own));
  const saved = page.waitForResponse((r) => r.url().endsWith("/deadline") && r.request().method() === "PUT");
  await form.getByRole("button", { name: copy.save }).click();
  expect((await saved).status()).toBe(200);
  await expect(summary).toContainText(copy.saved(second!.name, osloDateText(own)));
  await expect(summary).toContainText(copy.test(osloDateText(own)));
  await expect(summary).toContainText(copy.extended(osloDateText(classTest)));
  await expect(summary).toBeFocused();
  await expect(form).toHaveCount(0);
  await expectReflow(page, false);
  await page.context().close();

  // 360 px: the block and the open form are one column with no page scroll, and pass axe.
  const narrow = await lecturerPage(browser, lecturerSession, PHONE);
  await narrow.goto(studentPath);
  const narrowBlock = narrow.locator("[data-deadline]");
  await expect(narrowBlock.locator("[data-deadline-summary]")).toContainText(copy.test(osloDateText(own)));
  await expectAccessible(narrow, true);
  await narrowBlock.getByRole("button", { name: copy.change }).click();
  await expect(narrowBlock.getByLabel(copy.fieldLabel)).toHaveValue(toOsloInput(own));
  await expectAccessible(narrow, true);
  await narrow.context().close();

  // The Students, through the Replay by the local dev route: each statement names their own Testfrist.
  for (const [student, deadline] of [
    [second!, own],
    [first!, classTest],
  ] as const) {
    const done = await student.context.request.post(`/api/dev/class-sessions/${game.sessionId}/replay-done`, { headers: CSRF });
    expect(done.status()).toBe(204);
    const mine = await student.context.newPage();
    for (const size of [PHONE, { width: 1440, height: 900 }]) {
      await mine.setViewportSize(size);
      await mine.goto(`/individuell-test/${game.sessionId}`);
      await expect(mine.locator("[data-test-state=statement]")).toContainText(deadlineLine({ test_deadline: deadline })!);
      await expectAccessible(mine, size.width < 1024);
    }
    await mine.close();
  }
  await first!.context.close();
  await second!.context.close();
});
