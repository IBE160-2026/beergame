import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { expectAccessible, freshClass, lecturerPage, test, type Session } from "./support/classes";
import { confirmButton, orderField } from "./support/play";

/** A Lecturer's private test Game (Story 6.20, FR-87, FR-34, UX-DR70), on the local stack with
 * `FEATURE_LECTURER_TEST_GAME` on (compose's default): «Testspill» on a fresh Klasseøkt before its
 * Start date, the Student play screen labelled «Testspill», and the end screen leading back. The
 * flag off, the refusals and the lists that leave the game out are `backend/tests/sessions/
 * test_test_game.py`. */
const CSRF = { "X-Requested-With": "olspillet" };
const DAY = 24 * 60 * 60 * 1000;
const copy = nb.sessions.testGame;
const play = nb.games.play;

/** A fresh Class session of `weeks` Uker and no Veiledede uker, Rule-based, its Start date in
 * three days; the Klasseøkt opened on a page of the Lecturer's own. */
async function freshSession(browser: Parameters<typeof lecturerPage>[0], session: Session, width: number, weeks = 3) {
  const page = await lecturerPage(browser, session, { width, height: 900 });
  const klass = await freshClass(page);
  const created = await page.request.post(`/api/classes/${klass.id}/class-sessions`, { headers: CSRF });
  expect(created.status()).toBe(201);
  const sessionId = (await created.json()).id as string;
  const [start_at, play_deadline, debrief_deadline, test_deadline] = [3, 17, 20, 27].map((d) =>
    new Date(Date.now() + d * DAY).toISOString(),
  );
  const saved = await page.request.put(`/api/class-sessions/${sessionId}`, {
    data: {
      ai_mode: "rule_based",
      dates: { start_at, play_deadline, debrief_deadline, test_deadline },
      // The Classic step demand changes in a Uke inside so short a game.
      game_settings: { weeks, guided_weeks: 0, demand: { kind: "step", start: 4, new_level: 8, change_week: 2 } },
    },
    headers: CSRF,
  });
  expect(saved.status(), await saved.text()).toBe(200);
  await page.goto(`/klasseokter/${sessionId}`);
  const block = page.locator("[data-test-game]");
  await expect(block.getByRole("heading", { name: copy.title })).toBeVisible();
  return { page, sessionId, block };
}

async function startAs(page: Page, roleName: string) {
  const block = page.locator("[data-test-game]");
  await block.getByRole("radio", { name: roleName }).check();
  await block.getByRole("button", { name: copy.start }).click();
  await expect(page).toHaveURL(/\/spill\/[0-9a-f-]+$/);
  await expect(page.getByRole("heading", { level: 1, name: play.week(1) })).toBeVisible();
}

test("at 360 px the Lecturer starts a test game and plays it on the Student play screen", async ({
  browser,
  lecturerSession,
}) => {
  const { page, block } = await freshSession(browser, lecturerSession, 360);
  await expect(block.getByText(copy.lead)).toBeVisible();
  await expect(block.getByRole("radio", { name: "Detaljist" })).toBeChecked();
  await expectAccessible(page, true);

  await startAs(page, "Grossist");
  // The Topplinje's label is plain text, «Testspill», never «Demodata» (UX-DR70).
  await expect(page.getByText(play.roleGame("Grossist", null), { exact: true })).toBeVisible();
  await expect(page.getByText("Demodata")).toHaveCount(0);
  // The three other Seats read «KI-spiller» (FR-34); the own one «Deg».
  const seats = page.getByRole("main");
  await expect(seats.getByText(nb.homes.student.aiPlayer, { exact: true })).toHaveCount(3);
  await expect(seats.getByText(nb.homes.student.youAlone, { exact: true })).toHaveCount(1);
  await expect(page.getByRole("link", { name: play.toClassSession })).toBeVisible();
  await expect(page.getByRole("link", { name: nb.games.briefing.title })).toHaveCount(0);
  await expectAccessible(page, true);
  await page.context().close();
});

test("at 1440 px the test game ends on «Spillet er ferdig» and leads back to the Klasseøkt", async ({
  browser,
  lecturerSession,
}) => {
  const { page, block } = await freshSession(browser, lecturerSession, 1440, 2);
  await startAs(page, "Fabrikk");
  for (const week of [1, 2]) {
    await expect(page.getByRole("heading", { level: 1, name: play.week(week) })).toBeVisible();
    await orderField(page, week).fill("4");
    await confirmButton(page).click();
  }
  await expect(page.getByRole("heading", { level: 1, name: play.end.title })).toBeVisible();
  await expect(page.getByText(play.roleGame("Fabrikk", null), { exact: true })).toBeVisible();
  await expect(page.locator("[data-chain-total]")).toBeVisible();
  await expect(page.getByText(play.end.why)).toHaveCount(0);
  await expect(page.getByRole("link", { name: play.end.toDebrief })).toHaveCount(0);
  await expectAccessible(page, false);

  await page.getByRole("link", { name: play.toClassSession }).click();
  await expect(block.getByRole("link", { name: copy.previous })).toBeVisible();
  // Finished, another may start: the Valgknapper and «Start testspill» are back.
  await expect(block.getByRole("button", { name: copy.start })).toBeVisible();
  await page.context().close();
});
