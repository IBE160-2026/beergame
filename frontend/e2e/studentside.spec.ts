import { type Browser, expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { nextMail } from "./support/auth";
import {
  expectAccessible,
  expectReflow,
  freshLecturer,
  lecturerPage,
  type Session,
  test,
  VIEWPORTS,
  type Viewport,
} from "./support/classes";
import { liveClassGame, orderByApi } from "./support/live-game";

/** The Studentside with «Fullføring» (Story 13.2, FR-63, FR-17, FR-5, UX-DR54, UX-DR55, NFR-6) on
 * the local stack: a fresh Obligatorisk Class game of three Weeks. The Lecturer opens the second
 * Student from Spillinnsikt and reads every block; when the game is played out at the Play
 * deadline the Klassespill row changes without a reload (AD-8). Spillinnsikt names the Student as a
 * link for an Assistant lecturer too, and the Roster leads to the same page, where the Assistant
 * reads the record without «Tilrettelegging» and «Frister». A Lecturer
 * of another Class sees the permission-denied page. Axe and reflow at 320 px, 1280 px with 200 %
 * text and 1440 px. The rules are `backend/tests/reports/test_studentside.py`. */
const CSRF = { "X-Requested-With": "olspillet" };
const PASSWORD = "spill-passord-1";
const copy = nb.reports.completion;
const record = nb.reports.record;

async function untilLive(page: Page) {
  await expect(page.locator("html")).toHaveAttribute("data-live", "live", { timeout: 10_000 });
}

/** An Assistant lecturer of the Class, from a mailed Invitation accepted through the api. */
async function assistantOf(browser: Browser, lecturerSession: Session, classId: string) {
  const lecturer = await lecturerPage(browser, lecturerSession, { width: 1280, height: 800 });
  const address = `assistent-${Date.now()}${Math.floor(Math.random() * 1e6)}@example.com`;
  const sent = await lecturer.request.post(`/api/classes/${classId}/staff/assistants`, {
    data: { email: address },
    headers: CSRF,
  });
  expect(sent.status()).toBe(201);
  const mail = await nextMail(lecturer, address, null);
  await lecturer.context().close();
  const token = mail.text.match(/\/invitasjon#([A-Za-z0-9_-]+)/)![1];
  const context = await browser.newContext({ baseURL: test.info().project.use.baseURL });
  const accepted = await context.request.post("/api/auth/invitation/accept", {
    data: { token, name: "Ada Assistent", password: PASSWORD },
    headers: CSRF,
  });
  expect(accepted.status()).toBe(200);
  return context;
}

async function textAt(page: Page, viewport: Viewport) {
  await page.setViewportSize({ width: viewport.width, height: viewport.height });
  if (viewport.text200) {
    await page.addStyleTag({ content: "html { font-size: 200% !important; }" });
  }
}

test("staff read one Student's Fullføring and record, and it follows the game live", async ({
  browser,
  lecturerSession,
}) => {
  test.slow(); // Invitations through the worker, a Class session, a lock and a playout
  const game = await liveClassGame(browser, lecturerSession, 2, {
    aiMode: "rule_based",
    obligatory: true,
    gameSettings: { weeks: 3, demand: { kind: "step", start: 4, new_level: 8, change_week: 2 } },
  });
  const [first, second] = game.students as [(typeof game.students)[0], (typeof game.students)[0]];
  const page = await lecturerPage(browser, lecturerSession, VIEWPORTS[2]!);
  try {
    // From Spillinnsikt, the Student's name leads to the Studentside.
    await page.goto(`/klasseokter/${game.sessionId}/oversikt/spill/${game.gameId}`);
    await page.locator("[data-insight-seats]").getByRole("link", { name: nb.reports.studentPage.linkLabel(second.name) }).click();
    await expect(page.getByRole("heading", { level: 1, name: second.name })).toBeVisible();
    const block = page.locator("[data-completion]");
    await expect(block.getByRole("heading", { level: 2, name: copy.title })).toBeVisible();
    await expect(block.locator("[data-step]")).toHaveCount(5);
    await expect(block.locator("[data-step] [data-step-status]")).toHaveText(Array(5).fill(copy.notDone));
    await expect(block.locator("[data-requirement]")).toHaveText(copy.notMet);
    await expect(page.locator("[data-participation]")).toContainText(copy.noOrders);
    await expect(page.locator("[data-participation]")).toContainText(copy.infoNote);
    const gamePart = page.locator('[data-record="game"]');
    await expect(gamePart).toContainText(record.game.state.running!);
    await expect(gamePart.getByRole("link", { name: record.game.insight })).toHaveAttribute(
      "href",
      `/klasseokter/${game.sessionId}/oversikt/spill/${game.gameId}`,
    );
    await expect(page.locator('[data-record="debrief"]')).toContainText(record.debrief.noExplanation);
    await expect(page.locator('[data-record="quiz"]')).toContainText(record.quiz.none);
    await expect(page.locator('[data-record="replay"]')).toContainText(record.replay.none);
    await expect(page.locator('[data-record="test"]')).toContainText(record.test.none);
    // Story 12.5's «KI-vurdering» from the record: no test handed in yet.
    const assessed = page.locator("[data-staff-assessment]");
    await expect(assessed.getByRole("heading", { level: 2 })).toHaveText(nb.assessment.staff.title);
    await expect(assessed.locator("[data-assessment-state]")).toHaveAttribute("data-assessment-state", "no_test");
    await expect(page.locator("[data-report-slot]")).toBeEmpty();
    // A Lecturer of the Class also has «Tilrettelegging» and «Frister».
    await expect(page.locator("[data-adjustment]")).toBeVisible();
    await expect(page.locator("[data-deadline]")).toBeVisible();
    await expectAccessible(page, false);
    const classId = await page.evaluate(
      async ([session, student]) =>
        (await (await fetch(`/api/class-sessions/${session}/students/${student}/record`)).json()).class_id as string,
      [game.sessionId, new URL(page.url()).pathname.split("/").pop()!],
    );

    // An Assistant lecturer of the Class also has the Student's name as a link on Spillinnsikt.
    const assistant = await assistantOf(browser, lecturerSession, classId);
    const helper = await assistant.newPage();
    await helper.setViewportSize({ width: 1440, height: 900 });
    await helper.goto(`/klasseokter/${game.sessionId}/oversikt/spill/${game.gameId}`);
    await expect(
      helper.locator("[data-insight-seats]").getByRole("link", { name: nb.reports.studentPage.linkLabel(second.name) }),
    ).toBeVisible();
    await untilLive(page);

    // The second Student orders Uke 1, then the game is played out at the Play deadline: the
    // finished game records the Klassespill step, and the open page reads it again by itself.
    await orderByApi(second, game.gameId, 1, 4);
    const played = await first.context.request.post(`/api/dev/games/${game.gameId}/playout`, { headers: CSRF });
    expect(played.status()).toBe(200);
    const classGame = block.locator('[data-step="class_game"]');
    await expect(classGame).toContainText(copy.notCounted.class_game!, { timeout: 15_000 });
    await expect(classGame).toContainText("Bestilte i 33 % av ukene. Kravet er 80 %.");
    await expect(classGame).toContainText("66 % av ukene ble spilt i utspillingen ved Spillfristen.");
    await expect(classGame.locator("[data-step-status]")).toHaveText(copy.notDone);
    await expect(page.locator("[data-participation]")).toContainText(/Tid på egne bestillinger: (under 1|\d+) min\./);
    await expect(page.locator("[data-participation]")).toContainText(copy.tooFew);
    await expect(gamePart).toContainText(record.game.playedOut);

    // The Roster leads to the same Studentside.
    await page.goto(`/klasser/${classId}`);
    await page
      .getByRole("link", { name: nb.reports.studentPage.rosterLinkLabel(second.email, 1) })
      .click();
    await expect(page.getByRole("heading", { level: 1, name: second.name })).toBeVisible();
    const studentPage = page.url();

    // The Assistant reads the record, without the Lecturer-only blocks. The game is played out,
    // so AI players hold the Seats now: the Assistant comes from the Roster.
    await helper.goto(`/klasser/${classId}`);
    await helper.getByRole("link", { name: nb.reports.studentPage.rosterLinkLabel(second.email, 1) }).click();
    await expect(helper.getByRole("heading", { level: 1, name: second.name })).toBeVisible();
    await expect(helper.locator('[data-completion] [data-step="class_game"]')).toContainText("Bestilte i 33 % av ukene.");
    await expect(helper.locator('[data-record="game"]')).toBeVisible();
    await expect(helper.locator("[data-adjustment]")).toHaveCount(0);
    await expect(helper.locator("[data-deadline]")).toHaveCount(0);
    await expectAccessible(helper, false);
    await assistant.close();

    // Each width: one column, no page scroll, axe clean.
    for (const viewport of VIEWPORTS) {
      const view = await lecturerPage(browser, lecturerSession, viewport);
      await textAt(view, viewport);
      await view.goto(studentPage);
      await expect(view.locator('[data-completion] [data-step="class_game"]')).toContainText(copy.notCounted.class_game!);
      if (viewport.text200) await textAt(view, viewport);
      await expectReflow(view, viewport.phone);
      await expectAccessible(view, viewport.phone);
      await view.context().close();
    }
  } finally {
    await page.context().close();
    await first.context.close();
    await second.context.close();
  }
});

/** Story 13.3 (FR-17, UX-DR54, AD-8): the Lecturer corrects the Klassespill step in place. The form
 * takes focus, «Avbryt» returns it, another block's form closes it, an empty «Begrunnelse» is
 * refused before any request, and once saved the result line «Gjort, rettet av … » takes focus with
 * the reason under it. The Student's Hjem, open all along, marks the step «rettet av faglærer»
 * without the reason. The rules are `backend/tests/reports/test_corrections.py`. */
test("a Lecturer corrects a step with a reason, and the Student's Hjem marks it", async ({ browser, lecturerSession }) => {
  test.slow(); // Invitations through the worker, a Class session and a lock
  const game = await liveClassGame(browser, lecturerSession, 2, {
    aiMode: "rule_based",
    obligatory: true,
    gameSettings: { weeks: 3, demand: { kind: "step", start: 4, new_level: 8, change_week: 2 } },
  });
  const [first, second] = game.students as [(typeof game.students)[0], (typeof game.students)[0]];
  const page = await lecturerPage(browser, lecturerSession, VIEWPORTS[2]!);
  const hjem = await second.context.newPage();
  const reason = "Holdt følge, men gruppen spilte sakte.";
  try {
    await hjem.goto("/hjem");
    const steps = hjem.getByRole("main").getByRole("region", { name: nb.homes.student.steps });
    await expect(steps).toBeVisible();
    await untilLive(hjem);

    await page.goto(`/klasseokter/${game.sessionId}/oversikt/spill/${game.gameId}`);
    await page.locator("[data-insight-seats]").getByRole("link", { name: nb.reports.studentPage.linkLabel(second.name) }).click();
    await expect(page.getByRole("heading", { level: 1, name: second.name })).toBeVisible();
    const row = page.locator('[data-completion] [data-step="class_game"]');
    const opener = row.getByRole("button", { name: copy.correct("Klassespill") });
    const form = page.locator('[data-correct-form="class_game"]');

    // In place, focus on the chosen Valgknapp («Gjort»: the step is not done); «Avbryt» returns it.
    await opener.click();
    await expect(form).toBeVisible();
    await expect(form.getByRole("radio", { name: copy.doneChoice, exact: true })).toBeFocused();
    await expect(form).toContainText(copy.logged);
    await form.getByRole("button", { name: copy.cancel }).click();
    await expect(form).toHaveCount(0);
    await expect(opener).toBeFocused();

    // One form at a time: «Endre tilrettelegging» closes it and keeps nothing.
    await opener.click();
    await form.getByLabel(copy.reasonLabel).fill("utkast");
    await page.getByRole("button", { name: nb.reports.adjustment.change }).click();
    await expect(form).toHaveCount(0);
    await expect(page.locator("[data-adjustment-form]")).toBeVisible();
    await opener.click();
    await expect(page.locator("[data-adjustment-form]")).toHaveCount(0);
    await expect(form.getByLabel(copy.reasonLabel)).toHaveValue("");

    // An empty reason: nothing is sent, the field says why and takes focus.
    let posted = 0;
    page.on("request", (request) => {
      if (request.method() === "POST" && request.url().includes("/corrections")) posted += 1;
    });
    await form.getByRole("button", { name: copy.save }).click();
    const field = form.getByLabel(copy.reasonLabel);
    await expect(field).toHaveAttribute("aria-invalid", "true");
    await expect(form).toContainText(copy.reasonError);
    await expect(field).toBeFocused();
    expect(posted).toBe(0);
    await expectAccessible(page, false);

    // Saved: the result line replaces the form and takes focus, the reason under it.
    await field.fill(reason);
    await form.getByRole("button", { name: copy.save }).click();
    await expect(form).toHaveCount(0);
    const status = row.locator("[data-step-status]");
    await expect(status).toHaveText(/^Gjort, rettet av .+ \d{1,2}\. [a-zæøå]+\.$/);
    await expect(status).toBeFocused();
    await expect(row.locator("[data-step-reason]")).toHaveText(reason);
    expect(posted).toBe(1);
    await expectAccessible(page, false);

    // The Student's Hjem reads it again by itself: the step is marked, the reason is not there.
    await expect(steps.getByText(nb.homes.student.corrected(true), { exact: true })).toBeVisible({ timeout: 15_000 });
    await expect(hjem.getByText(reason)).toHaveCount(0);
  } finally {
    await page.context().close();
    await first.context.close();
    await second.context.close();
  }
});

test("a Lecturer gives an Oppfølgingsspill, and the Student's Hjem shows it as a game of its own", async ({
  browser,
  lecturerSession,
}) => {
  test.slow(); // Invitations through the worker, a Class session and a lock
  const game = await liveClassGame(browser, lecturerSession, 2, {
    aiMode: "rule_based",
    obligatory: true,
    gameSettings: { weeks: 3, demand: { kind: "step", start: 4, new_level: 8, change_week: 2 } },
  });
  const [first, second] = game.students as [(typeof game.students)[0], (typeof game.students)[0]];
  const page = await lecturerPage(browser, lecturerSession, VIEWPORTS[0]!);
  const hjem = await second.context.newPage();
  try {
    await hjem.goto("/hjem");
    await expect(hjem.getByRole("main").getByRole("region", { name: nb.homes.student.steps })).toBeVisible();
    await untilLive(hjem);

    await page.goto(`/klasseokter/${game.sessionId}/oversikt/spill/${game.gameId}`);
    await page.locator("[data-insight-seats]").getByRole("link", { name: nb.reports.studentPage.linkLabel(second.name) }).click();
    await expect(page.getByRole("heading", { level: 1, name: second.name })).toBeVisible();
    const row = page.locator('[data-completion] [data-step="class_game"]');
    const opener = row.getByRole("button", { name: copy.makeup.give });
    const form = row.locator("[data-makeup-form]");

    // In place, with the consequence; focus on the primary; «Avbryt» returns it to the opener.
    await opener.click();
    await expect(form).toBeVisible();
    await expect(form.locator("p").first()).toHaveText(
      new RegExp(`^${second.name} får et eget Klassespill mot tre KI-spillere, åpent til Testfristen .+\\. ${second.name} får beskjed på Hjem og på e-post\\.$`),
    );
    const give = form.getByRole("button", { name: copy.makeup.give });
    await expect(give).toBeFocused();
    await form.getByRole("button", { name: copy.makeup.cancel }).click();
    await expect(form).toHaveCount(0);
    await expect(opener).toBeFocused();

    // One form at a time: opening «Rett Klassespill» closes it.
    await opener.click();
    await row.getByRole("button", { name: copy.correct("Klassespill") }).click();
    await expect(form).toHaveCount(0);
    await opener.click();
    await expect(page.locator("[data-correct-form]")).toHaveCount(0);
    await expectAccessible(page, true);

    // Given: the line replaces the form and takes focus; nothing more to give.
    await give.click();
    const line = row.locator("[data-makeup-given]");
    await expect(line).toHaveText(/^Oppfølgingsspill gitt \d{1,2}\. [a-zæøå]+\. Åpent til [a-zæøå]+\. \d{1,2}\. [a-zæøå]+\.$/);
    await expect(line).toBeFocused();
    await expect(row).toContainText(copy.makeup.state.ready!);
    await expect(opener).toHaveCount(0);
    await expectAccessible(page, true);

    // The Student's Hjem reads it by itself: a block of its own, under the Class game.
    const block = hjem.locator("[data-makeup]");
    await expect(block.getByRole("heading", { level: 3 })).toHaveText(/^Oppfølgingsspill · Du er \S+$/, { timeout: 15_000 });
    const rules = await block.getByRole("link", { name: nb.homes.student.rulesLink }).getAttribute("href");
    const makeupId = rules!.split("/")[2]!;
    // Started (the Starting task was done in the Class game): the Spillkort titled «Oppfølgingsspill».
    const started = await second.context.request.post(`/api/me/games/${makeupId}/start`, { headers: CSRF });
    expect(started.status()).toBe(200);
    await expect(block.getByRole("heading", { level: 4, name: new RegExp(`^${nb.homes.student.makeup.card}`) })).toBeVisible({
      timeout: 15_000,
    });
    await expectAccessible(hjem, true);
  } finally {
    await page.context().close();
    await first.context.close();
    await second.context.close();
  }
});

test("a Lecturer of another Class sees the permission-denied page, Student or not", async ({ page, browser }) => {
  const other = await freshLecturer(page, browser);
  for (const path of [
    `/klasseokter/${crypto.randomUUID()}/studenter/${crypto.randomUUID()}`,
    "/klasseokter/not-an-id/studenter/nobody",
  ]) {
    await other.goto(path);
    await expect(other.getByRole("heading", { level: 1, name: nb.access.denied })).toBeVisible();
  }
  const refused = await other.request.get(
    `/api/class-sessions/${crypto.randomUUID()}/students/${crypto.randomUUID()}/record`,
  );
  expect(refused.status()).toBe(403);
});
