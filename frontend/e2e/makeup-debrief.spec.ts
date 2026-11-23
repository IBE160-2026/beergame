import { expect } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { expectAccessible, lecturerPage, test } from "./support/classes";
import { liveClassGame, orderByApi } from "./support/live-game";

/** From the last Order of an Oppfølgingsspill to step 1 of its Debrief (Story 13.5, FR-17, AD-13,
 * NFR-6) on the local stack: a fresh Class game of two Weeks, a make-up given to each Student by
 * the api, its first Week ordered by the api. On the play screen the Student sends the last Order;
 * «Spillet er ferdig» follows with «Gå til Debrief», which opens a Personal debrief of the make-up
 * at step 1. One Student at 360 px, the other at 1440 px, axe on both screens. The rules (which
 * game is the Student's, the step event, the started Debrief kept) are
 * `backend/tests/reports/test_makeup_continue.py`. */
const CSRF = { "X-Requested-With": "olspillet" };
const play = nb.games.play;
const entry = nb.debriefEntry;

test("the last Order of an Oppfølgingsspill leads through «Spillet er ferdig» to its Debrief", async ({
  browser,
  lecturerSession,
}) => {
  test.slow(); // Invitations through the worker, a Class session, a lock and two make-ups
  const game = await liveClassGame(browser, lecturerSession, 2, {
    aiMode: "rule_based",
    gameSettings: { weeks: 2, demand: { kind: "step", start: 4, new_level: 8, change_week: 2 } },
  });
  const lecturer = await lecturerPage(browser, lecturerSession, { width: 1280, height: 800 });
  try {
    for (const [student, viewport] of [
      [game.students[0]!, { width: 360, height: 740, phone: true }],
      [game.students[1]!, { width: 1440, height: 900, phone: false }],
    ] as const) {
      const me = (await (await student.context.request.get("/api/auth/me")).json()) as { user: { id: string } };
      const given = await lecturer.request.post(`/api/class-sessions/${game.sessionId}/students/${me.user.id}/makeup`, {
        headers: CSRF,
      });
      expect(given.status()).toBe(200);
      const makeupId = (await given.json()).makeup.game_id as string;
      // The Starting task was done in the Class game: the Student starts it at once.
      const started = await student.context.request.post(`/api/me/games/${makeupId}/start`, { headers: CSRF });
      expect(started.status()).toBe(200);
      await orderByApi(student, makeupId, 1, 4);

      const page = await student.context.newPage();
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto(`/spill/${makeupId}`);
      await expect(page.getByRole("heading", { level: 1 })).toHaveText(play.week(2));
      await page.getByRole("textbox", { name: play.order.label(2) }).fill("6");
      await page.getByRole("button", { name: /^Bekreft ordre/ }).click();

      // The last Order finishes the make-up: «Spillet er ferdig» with the one primary.
      await expect(page.getByRole("heading", { level: 1 })).toHaveText(play.end.title, { timeout: 15_000 });
      await expect(page.getByRole("main").getByText(/^\S+, Oppfølgingsspill$/)).toBeVisible();
      const toDebrief = page.getByRole("link", { name: play.end.toDebrief });
      await expect(toDebrief).toHaveAttribute("href", `/debrief/${game.sessionId}`);
      await expectAccessible(page, viewport.phone);

      // «Gå til Debrief»: a Personal debrief of the make-up, at step 1.
      await toDebrief.click();
      await expect(page.getByRole("heading", { level: 1 })).toHaveText(entry.makeupTitle);
      await expect(page.getByRole("main").locator("p").getByText(/^\S+, Oppfølgingsspill$/)).toBeVisible();
      await expect(page.getByRole("main").getByRole("heading", { level: 2 })).toContainText(entry.firstStep);
      const opened = await (
        await student.context.request.post(`/api/me/class-sessions/${game.sessionId}/debrief`, { headers: CSRF })
      ).json();
      expect([opened.game_id, opened.step, opened.group, opened.makeup]).toEqual([makeupId, 1, null, true]);
      await expectAccessible(page, viewport.phone);
      await page.close();
    }
  } finally {
    await lecturer.context().close();
    for (const student of game.students) await student.context.close();
  }
});
