import { expect } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { expectAccessible, test, VIEWPORTS } from "./support/classes";
import { liveClassGame, orderByApi } from "./support/live-game";

/** Completion on the Student's Hjem (Story 13.1, FR-17, FR-14, UX-DR29) on the local stack: in an
 * Obligatorisk Klasseøkt Stegene's steps come with whether they count, and one line says whether
 * the requirement is met. A Student who ordered in one Uke of three before the Play deadline
 * playout finished the game sees «ferdig» turned into the line that says the step does not count,
 * and never a number of Uker or a share. The rules themselves are pinned by
 * `backend/tests/analysis/test_completion.py` and `backend/tests/reports/`. Axe at 320 px, 1280 px
 * with 200 % text and 1440 px. */
const copy = nb.homes.student;
const CSRF = { "X-Requested-With": "olspillet" };

test("live: a played-out Class game does not count, and Hjem says the requirement is not met", async ({
  browser,
  lecturerSession,
}) => {
  test.slow(); // an Invitation through the worker, a Class session, a lock and a playout
  const game = await liveClassGame(browser, lecturerSession, 2, {
    aiMode: "rule_based",
    obligatory: true,
    gameSettings: { weeks: 3, demand: { kind: "step", start: 4, new_level: 8, change_week: 2 } },
  });
  const [me, other] = game.students as [(typeof game.students)[0], (typeof game.students)[0]];
  try {
    const page = await me.context.newPage();
    await page.goto("/hjem");
    const main = page.getByRole("main");
    // While the game runs: the requirement line, and no number of Uker anywhere (FR-14).
    await expect(main.locator("[data-requirement]")).toHaveText(copy.requirement.notMet);
    await expect(main.getByText(/\d+ (uker|Uker)/)).toHaveCount(0);

    await orderByApi(me, game.gameId, 1, 4);
    const played = await other.context.request.post(`/api/dev/games/${game.gameId}/playout`, { headers: CSRF });
    expect(played.status()).toBe(200);

    await page.reload();
    const steps = main.getByRole("region", { name: copy.steps });
    await expect(steps.getByText(copy.notCounted.class_game!, { exact: true })).toBeVisible();
    await expect(main.locator("[data-requirement]")).toHaveText(copy.requirement.notMet);
    await expect(main.getByText(/\d+ (uker|Uker)|\d+ ?%/)).toHaveCount(0);

    for (const viewport of VIEWPORTS) {
      const view = await me.context.newPage();
      await view.setViewportSize({ width: viewport.width, height: viewport.height });
      if (viewport.text200) {
        await view.addInitScript(() => {
          document.addEventListener("DOMContentLoaded", () => {
            const style = document.createElement("style");
            style.textContent = "html { font-size: 200% !important; }";
            document.head.appendChild(style);
          });
        });
      }
      await view.goto("/hjem");
      await expect(view.getByRole("main").getByText(copy.notCounted.class_game!, { exact: true })).toBeVisible();
      await expectAccessible(view, viewport.phone);
      await view.close();
    }
    await page.close();
  } finally {
    await me.context.close();
    await other.context.close();
  }
});
