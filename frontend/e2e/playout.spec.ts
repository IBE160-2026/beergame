import { expect } from "@playwright/test";

import { nb } from "../src/copy/nb";
import week11 from "../src/modules/games/fixtures/play-week-11.json";
import { loginByApi } from "./support/auth";
import { expectAccessible, test, VIEWPORTS } from "./support/classes";
import { liveClassGame, orderByApi } from "./support/live-game";
import { GAME_ID, orderField } from "./support/play";

/** The Play deadline playout (Story 8.14, FR-38, UX-DR62) on the local stack: a real Class game is
 * played out by the local dev route at its Class session's Play deadline (the sweep's own due
 * action, at the injected clock; `backend/tests/games/test_playout.py`), and the Student's open
 * play screen turns live to «Spillet er ferdig» with the line that it ended at the Spillfrist, then
 * «Gå til Debrief»; Hjem says it is finished. Axe at 320 px, 1280 px with 200 % text and 1440 px. */
const copy = nb.games.play;
const CSRF = { "X-Requested-With": "olspillet" };

test("live: the playout ends the game at the Spillfrist and the Student is led on to the Debrief", async ({
  browser,
  lecturerSession,
}) => {
  test.slow(); // an Invitation through the worker, a Class session and a lock
  const game = await liveClassGame(browser, lecturerSession, 2, {
    aiMode: "rule_based",
    gameSettings: { weeks: 3, demand: { kind: "step", start: 4, new_level: 8, change_week: 2 } },
  });
  const [me, other] = game.students as [(typeof game.students)[0], (typeof game.students)[0]];
  try {
    const page = await me.context.newPage();
    await page.goto(`/spill/${game.gameId}`);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.week(1));
    await expect(page.locator("html")).toHaveAttribute("data-live", "live", { timeout: 10_000 });
    // The Student has ordered; the other never does, so the game waits at the deadline.
    await orderByApi(me, game.gameId, 1, 4);

    const played = await other!.context.request.post(`/api/dev/games/${game.gameId}/playout`, { headers: CSRF });
    expect(played.status()).toBe(200);
    expect(await played.json()).toEqual({ played_out: true });
    // A person's Order after it is refused.
    const late = await me.context.request.post(`/api/me/games/${game.gameId}/weeks/2/order`, {
      data: { order: 4 },
      headers: CSRF,
    });
    expect(late.status()).toBe(409);
    expect((await late.json()).error.code).toBe("play_deadline_passed");

    // The open page turns to «Spillet er ferdig» without a reload, with the playout's line.
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.end.title);
    await expect(page.locator("[data-game-end-note]")).toHaveText(copy.end.playedOut);
    await expect(page.locator("[data-chain-total]")).toHaveText(/\d,\d\d/);
    await expect(page.getByRole("main").getByRole("link", { name: copy.end.toDebrief })).toBeVisible();
    await expect(page.getByRole("main").getByText(/\d+ (uker|Uker)/)).toHaveCount(0);

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
      await view.goto(`/spill/${game.gameId}`);
      await expect(view.locator("[data-game-end-note]")).toHaveText(copy.end.playedOut);
      await expectAccessible(view, viewport.phone);
      await view.close();
    }

    await page.goto("/hjem");
    await expect(page.getByRole("main").getByText(nb.homes.student.finished, { exact: true })).toBeVisible();
  } finally {
    await me.context.close();
    await other!.context.close();
  }
});

test("while AI players play the game out, Spill has no Ordrefelt and says so", async ({ page }) => {
  // A stand-in game in `playing_out` (the api's shape; `backend/tests/sessions/test_playout.py`
  // reads `played_out` while it lasts): the own Seat is held by the playout's AI player.
  const seats = week11.table_status.seats.map((seat) =>
    seat.mine ? { ...seat, holder: "ai", name: null, ordered: true, wait_started_at: null, mark: "playout" } : seat,
  );
  await loginByApi(page, "student");
  await page.route(`**/api/me/games/${GAME_ID}`, (route) =>
    route.fulfill({
      json: {
        id: GAME_ID,
        number: 17,
        role: "wholesaler",
        test_game: false,
        class_session_id: "01a1f8ee-34f2-70af-8800-f79281ed7a00",
        seats,
        briefing_first: false,
        obligatory: false,
        can_pause: false,
        played_out: true,
        rules: { order_delay: 2, shipping_delay: 2, production_delay: 2, guided_weeks: 4, holding_cost: "0.50", backorder_cost: "1.00", capacity: [] },
        status: "running",
        week: 11,
        server_now: week11.server_now,
        seat_state: null,
        turn: null,
      },
    }),
  );
  await page.route(`**/api/me/games/${GAME_ID}/play`, (route) =>
    route.fulfill({ json: { ...week11, table_status: { seats } } }).catch(() => undefined),
  );
  await page.goto(`/spill/${GAME_ID}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.week(11));
  await expect(page.locator("[data-playing-out]")).toHaveText(nb.homes.student.playingOut);
  await expect(orderField(page)).toHaveCount(0);
  await expect(page.getByRole("main").locator("a.bg-ink, button.bg-ink")).toHaveCount(0);
  await expectAccessible(page, false);
  await page.unrouteAll({ behavior: "ignoreErrors" });
});
