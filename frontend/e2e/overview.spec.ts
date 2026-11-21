import { expect } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { loginByApi } from "./support/auth";
import { expectAccessible, freshClass, lecturerPage, test, VIEWPORTS } from "./support/classes";
import { liveClassGame, orderByApi } from "./support/live-game";

/** The Oversikt (Story 7.1, FR-39, FR-5, FR-14, FR-72, FR-73, NFR-6, UX-DR40) on the local stack:
 * a fresh Class game in which one of two Students has ordered waits for the other by name, at
 * 1440 px, 320 px and with 200 % text; before the Start date the page lists the allocation only;
 * a Student is refused. What the api stores and answers is `backend/tests/sessions/test_overview.py`
 * and `backend/tests/games/test_game_summaries.py`. */
const copy = nb.overview;
const CSRF = { "X-Requested-With": "olspillet" };
const DAY = 24 * 60 * 60 * 1000;

test("the Class's Lecturer sees the game wait for the Student who has not ordered, at every width", async ({
  browser,
  lecturerSession,
}) => {
  const game = await liveClassGame(browser, lecturerSession, 2, { aiMode: "rule_based" });
  const [first, second] = game.students;
  await orderByApi(first!, game.gameId, 1, 4);
  for (const viewport of VIEWPORTS) {
    const page = await lecturerPage(browser, lecturerSession, viewport);
    await page.goto(`/klasseokter/${game.sessionId}/oversikt`);
    const main = page.getByRole("main");
    await expect(main.getByRole("heading", { level: 1, name: copy.title })).toBeVisible();
    await expect(main.getByText("0 ferdig · 0 pågår · 1 venter")).toBeVisible();
    await expect(main.getByText(/^Oppdatert \d\d:\d\d:\d\d$/)).toBeVisible();
    const group = main.getByRole("region", { name: `${copy.groups.waiting} 1` });
    await expect(group).toBeVisible();
    const row = group.getByRole("listitem").first();
    await expect(row).toContainText("Spill 1");
    await expect(row).toContainText("Uke 1");
    await expect(row).toContainText(new RegExp(`Venter på ${second!.name} \\([A-Za-zøå]+\\), (under 1 min|\\d+ min)`));
    await expect(row.getByRole("list", { name: copy.seatsLabel("Spill 1") }).getByRole("listitem")).toHaveCount(4);
    await expect(row.getByRole("list", { name: copy.seatsLabel("Spill 1") })).toContainText(/^Fabrikk: /);
    await expect(row).toContainText(/0\s?kr/);
    // No Week total and nothing that hints at the game's length (FR-14).
    await expect(main.getByText(/ av \d+ uker|Uke \d+ av/)).toHaveCount(0);
    await expectAccessible(page, viewport.phone);
    await page.context().close();
  }
});

test("before the Start date the page lists the allocation only, reached from the Klasseøkt", async ({
  browser,
  lecturerSession,
}) => {
  const lecturer = await lecturerPage(browser, lecturerSession, { width: 1280, height: 800 });
  const klass = await freshClass(lecturer);
  const created = await lecturer.request.post(`/api/classes/${klass.id}/class-sessions`, { headers: CSRF });
  expect(created.status()).toBe(201);
  const sessionId = (await created.json()).id as string;
  const [start_at, play_deadline, debrief_deadline, test_deadline] = [3, 17, 20, 27].map((d) =>
    new Date(Date.now() + d * DAY).toISOString(),
  );
  const saved = await lecturer.request.put(`/api/class-sessions/${sessionId}`, {
    data: { ai_mode: "rule_based", dates: { start_at, play_deadline, debrief_deadline, test_deadline } },
    headers: CSRF,
  });
  expect(saved.status()).toBe(200);
  await lecturer.goto(`/klasseokter/${sessionId}`);
  await lecturer.getByRole("main").getByRole("link", { name: copy.open, exact: true }).click();
  await expect(lecturer).toHaveURL(new RegExp(`/klasseokter/${sessionId}/oversikt$`));
  const main = lecturer.getByRole("main");
  await expect(main.getByText(/^Spillene starter .+\. Til da vises bare fordelingen\.$/)).toBeVisible();
  await expect(main.getByText(copy.beforeStart.empty)).toBeVisible();
  // No headline counts and no cost before the Start date.
  await expect(main.getByText(/ ferdig · /)).toHaveCount(0);
  await expect(main.getByText(/\bkr\b/)).toHaveCount(0);

  // A Student is refused the same as for a page that does not exist (FR-5).
  const student = await browser.newContext({ baseURL: test.info().project.use.baseURL });
  const page = await student.newPage();
  await loginByApi(page, "student");
  await page.goto(`/klasseokter/${sessionId}/oversikt`);
  await expect(page.getByRole("heading", { level: 1, name: nb.access.denied })).toBeVisible();
});
