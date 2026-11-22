import { expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import type { MyGame, PlayEnvelope } from "../src/modules/games/api";
import week11 from "../src/modules/games/fixtures/play-week-11.json";
import { loginByApi } from "./support/auth";
import { expectAccessible, expectReflow } from "./support/classes";
import { GAME_ID } from "./support/play";

/** «Ta tilbake setet» (Story 8.4, FR-37, UX-DR62, UX-DR76): the Student whose Seat an AI player
 * took over asks for it back on Spill and Hjem. Stand-in envelopes of the api's shape over the demo
 * Student's login: the queued request, the Week opening that hands the Seat back and the refusals
 * are `backend/tests/games/test_reclaim.py` and `backend/tests/sessions/test_reclaim_view.py`. */
const copy = nb.homes.student.takeover;
type Seat = PlayEnvelope["table_status"]["seats"][number];
const RECLAIM_PATH = `**/api/me/games/${GAME_ID}/seats/wholesaler/reclaim`;

/** The demo Student's Grossist Seat, taken over; the AI player's Order is 9. */
function seats(queued: boolean): Seat[] {
  return (week11.table_status.seats as unknown as Seat[]).map((seat) =>
    seat.mine
      ? {
          ...seat,
          holder: "ai",
          name: null,
          ordered: true,
          wait_started_at: null,
          mark: "takeover_inactivity",
          taken_over: true,
          ordering_for: null,
          reclaim_queued: queued,
        }
      : seat,
  );
}

const envelope = (queued: boolean) => ({ ...week11, turn: { ...week11.turn, order: 9 }, table_status: { seats: seats(queued) } });

function game(queued: boolean, status: MyGame["status"] = "running") {
  return {
    id: GAME_ID,
    number: 17,
    role: "wholesaler",
    class_session_id: "01a1f8ee-33b9-75e6-9502-79db27b37c00",
    seats: seats(queued),
    briefing_first: false,
    rules: { order_delay: 2, shipping_delay: 2, production_delay: 2, guided_weeks: 4, holding_cost: "0.50", backorder_cost: "1.00" },
    status,
    week: status === "running" ? 11 : null,
    server_now: week11.server_now,
    seat_state: status === "running" ? week11.seat_state : null,
    turn: status === "running" ? { ...week11.turn, order: 9 } : null,
    obligatory: true,
  };
}

/** The play screen with the Seat taken over; after a press the api answers the queued request. */
async function openTakenOver(page: Page) {
  await loginByApi(page, "student");
  const stub = { queued: false };
  await page.route(`**/api/me/games/${GAME_ID}`, (route) => route.fulfill({ json: game(stub.queued) }).catch(() => undefined));
  await page.route(`**/api/me/games/${GAME_ID}/play`, (route) =>
    route.fulfill({ json: envelope(stub.queued) }).catch(() => undefined),
  );
  await page.goto(`/spill/${GAME_ID}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(nb.games.play.week(11));
  return stub;
}

const button = (page: Page) => page.getByRole("main").getByRole("button", { name: copy.reclaim });
const queuedLine = (page: Page) => page.locator("[data-reclaim-queued]");

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

for (const width of [320, 360, 1440]) {
  test.describe(`${width} px`, () => {
    test.use({ viewport: { width, height: 800 } });

    test("«Ta tilbake setet» stands under the note; a press queues it and the line takes focus", async ({ page }) => {
      const stub = await openTakenOver(page);
      const note = page.locator("[data-taken-over]");
      await expect(note).toContainText(copy.takenOver);
      await expect(note.getByRole("button", { name: copy.reclaim })).toBeVisible();
      const box = (await button(page).boundingBox())!;
      expect(box.height).toBeGreaterThanOrEqual(44);
      // «Alle rader og kostnad» is one tap away at every width, above the note (Story 8.2 check).
      const link = page.locator("[data-all-rows-link]");
      await expect(link).toHaveText(nb.games.play.allRows.link);
      await expect(link).toBeVisible();
      expect((await link.boundingBox())!.y).toBeLessThan((await note.boundingBox())!.y);
      // The Kjedebånd names the AI player's Order as such, never «Din ordre».
      await expect(page.locator("[data-chain-band] svg")).toContainText("KI-ordre 9");
      await expect(page.locator("[data-chain-band] svg")).not.toContainText("Din ordre");
      await expectAccessible(page, width < 1024);

      await page.route(RECLAIM_PATH, async (route) => {
        stub.queued = true;
        await route.fulfill({ json: game(true) });
      });
      await button(page).click();
      await expect(queuedLine(page)).toHaveText(copy.reclaimQueued);
      await expect(queuedLine(page)).toBeFocused();
      await expect(button(page)).toHaveCount(0);
      await expectReflow(page, width < 1024);
    });
  });
}

test("a refused press is said inline and the button stays", async ({ page }) => {
  await openTakenOver(page);
  await page.route(RECLAIM_PATH, (route) =>
    route.fulfill({ status: 409, json: { error: { code: "seat_not_yours", message: "x" } } }),
  );
  await button(page).click();
  await expect(page.getByRole("main").getByRole("alert")).toHaveText(copy.reclaimRefusals.seat_not_yours);
  await expect(button(page)).toBeVisible();
  await expect(button(page)).not.toHaveAttribute("aria-disabled", "true");
  await expect(queuedLine(page)).toHaveCount(0);
});

test("a request already queued reads the line on load, with no button", async ({ page }) => {
  const stub = await openTakenOver(page);
  stub.queued = true;
  await page.reload();
  await expect(queuedLine(page)).toHaveText(copy.reclaimQueued);
  await expect(button(page)).toHaveCount(0);
});

/** Hjem with the one Class session whose game is `game`. */
async function openHjem(page: Page, shown: object) {
  await loginByApi(page, "student");
  await page.route("**/api/me/class-sessions", async (route) => {
    const response = await route.fetch();
    const classes = await (await page.request.get("/api/classes/enrolled")).json();
    const [klass] = classes.items;
    const items = [
      {
        id: "01a1f8ee-33b9-75e6-9502-79db27b37c00",
        class_id: klass.id,
        class_name: klass.name,
        number: 1,
        start_at: "2026-11-24T09:00:00Z",
        play_deadline: "2026-12-08T13:00:00Z",
        debrief_deadline: null,
        test_deadline: null,
        next_deadline: { kind: "play", at: "2026-12-08T13:00:00Z" },
        obligatory: true,
        lab_hours: [],
        seat_choice_open: false,
        drawn_seat: null,
        steps: [{ step: "class_game", state: "current" }],
        game: shown,
      },
    ];
    await route.fulfill({ response, json: { items } });
  });
  await page.goto("/hjem");
}

test("on Hjem the button stands under the note, and a finished game shows none", async ({ page }) => {
  await openHjem(page, game(false));
  const note = page.getByRole("main").locator("[data-taken-over]");
  await expect(note).toContainText(copy.requirementWarning);
  await expect(note.getByRole("button", { name: copy.reclaim })).toBeVisible();
  await page.unrouteAll({ behavior: "ignoreErrors" });
  await openHjem(page, game(false, "finished"));
  await expect(page.getByRole("main").getByRole("heading", { level: 3 }).first()).toBeVisible();
  await expect(button(page)).toHaveCount(0);
});
