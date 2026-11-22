import { expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import type { PlayEnvelope } from "../src/modules/games/api";
import week11 from "../src/modules/games/fixtures/play-week-11.json";
import { expectAccessible, expectReflow } from "./support/classes";
import { GAME_ID, openPlay, type PlayStub } from "./support/play";

/** «Sett inn KI-spiller for Jonas» (Story 8.8, FR-89, FR-37, UX-DR27, AD-10). Stand-in envelopes
 * of the api's shape over the demo Student's login: whether the control shows, the insert times
 * and the command are the api's (`backend/tests/games/test_peer_insert.py`,
 * `backend/tests/sessions/test_peer_insert_view.py`); here only what the Students see and where
 * focus goes. */
const copy = nb.homes.student;
type Seat = PlayEnvelope["table_status"]["seats"][number];
const INSERT_PATH = `/api/me/games/${GAME_ID}/seats/distributor/takeover`;

const region = (page: Page) => page.getByRole("main").getByRole("region", { name: copy.seats });
const jonasRow = (page: Page) => region(page).getByRole("listitem").nth(1);
const button = (page: Page) => region(page).getByRole("button", { name: nb.spillstyring.takeover("Jonas Berg") });

/** Uke 11, paused by the demo Student, with Jonas Berg's Distributør Seat changed by `change`. */
function withJonas(change: Partial<Seat>) {
  return {
    ...week11,
    table_status: {
      can_pause: false,
      pause: { state: "paused", name: "Demo Student", mine: true, staff: false, resume_at: null },
      seats: (week11.table_status.seats as unknown as Seat[]).map((seat) =>
        seat.role === "distributor" ? { ...seat, ...change } : seat,
      ),
    },
  };
}

/** Monday 23 November 2026 in Oslo, ahead of the envelope's `server_now` (Friday 20 November). */
const before = withJonas({ insert_at: "2026-11-23T09:00:00Z", insert_agreed: false });
const agreed = withJonas({ insert_at: "2026-11-23T18:00:00Z", insert_agreed: true });
const available = withJonas({ can_insert: true });
const takenBy = (name: string | null) =>
  withJonas({
    holder: "ai",
    name: null,
    ordered: true,
    wait_started_at: null,
    mark: "takeover_peer",
    taken_over: true,
    ordering_for: "Jonas Berg",
    inserted_by: name,
  });

/** The game as the api answers a press: Hjem's shape, with the Seats of `envelope`. */
function gameOf(envelope: ReturnType<typeof withJonas>) {
  return {
    id: GAME_ID,
    number: 17,
    role: "wholesaler",
    seats: envelope.table_status.seats,
    briefing_first: false,
    rules: { order_delay: 2, shipping_delay: 2, production_delay: 2, guided_weeks: 4, holding_cost: "0.50", backorder_cost: "1.00" },
    status: "running",
    week: 11,
    server_now: week11.server_now,
  };
}

async function show(page: Page, stub: PlayStub, envelope: unknown) {
  stub.envelope = envelope;
  await page.evaluate(() => window.dispatchEvent(new Event("online")));
}

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

for (const { width, phone } of [
  { width: 320, phone: true },
  { width: 360, phone: true },
  { width: 1440, phone: false },
]) {
  test.describe(`${width} px`, () => {
    test.use({ viewport: { width, height: 800 } });

    test("before the insert time the row states it; once passed the control shows; a press puts the AI player in", async ({
      page,
    }) => {
      const stub = await openPlay(page);
      await show(page, stub, before);
      await expect(jonasRow(page)).toContainText("Etter ma. 10:00 kan dere sette inn en KI-spiller.");
      await expect(button(page)).toHaveCount(0);
      if (width === 1440) await expectAccessible(page, phone);
      else await expectReflow(page, phone);
      await show(page, stub, agreed);
      await expect(jonasRow(page)).toContainText("Avtalt tid ma. 19:00. Etter det kan dere sette inn en KI-spiller.");

      await show(page, stub, available);
      await expect(button(page)).toBeVisible();
      await expect(jonasRow(page)).toContainText(nb.spillstyring.thisWeek("Jonas Berg"));
      await expectAccessible(page, phone);

      const done = takenBy("Demo Student");
      await page.route(`**${INSERT_PATH}`, async (route) => {
        stub.envelope = done;
        await route.fulfill({ json: gameOf(done) });
      });
      await button(page).click();
      // No dialog: the row now reads the AI player and takes focus.
      await expect(page.getByRole("dialog")).toHaveCount(0);
      await expect(button(page)).toHaveCount(0);
      const row = jonasRow(page).locator("[data-row-focus]");
      await expect(row).toHaveText(/^Distributør\s*KI-spiller\s*bestiller for Jonas Berg$/);
      await expect(row).toBeFocused();
      if (width === 1440) await expectAccessible(page, phone);
      else await expectReflow(page, phone);
    });
  });
}

test.describe("two Students at once", () => {
  test.use({ viewport: { width: 1440, height: 800 } });

  test("the second press is told who came first, and focus moves to that line", async ({ page }) => {
    const stub = await openPlay(page);
    await show(page, stub, available);
    await expect(button(page)).toBeVisible();
    await page.route(`**${INSERT_PATH}`, async (route) => {
      stub.envelope = takenBy("Sara Lie");
      await route.fulfill({
        status: 409,
        json: {
          error: {
            code: "takeover_exists",
            message: "No AI player was put in.",
            fields: { acted_by: { kind: "student", user_id: "u" }, acted_at: "2026-11-20T12:00:00Z" },
          },
        },
      });
    });
    await button(page).click();
    const line = jonasRow(page).getByRole("status");
    await expect(line).toHaveText("Sara Lie har allerede satt inn en KI-spiller.");
    await expect(line).toBeFocused();
    await expect(button(page)).toHaveCount(0);
  });

  test("any other refusal is said inline and the button stays", async ({ page }) => {
    const stub = await openPlay(page);
    await show(page, stub, available);
    await page.route(`**${INSERT_PATH}`, (route) =>
      route.fulfill({
        status: 409,
        json: { error: { code: "insert_not_allowed_yet", message: "No AI player was put in.", fields: {} } },
      }),
    );
    await button(page).click();
    await expect(jonasRow(page)).toContainText(copy.insert.refusals.insert_not_allowed_yet);
    await expect(button(page)).toBeEnabled();
    await expect(jonasRow(page).locator("[data-insert-result]")).toHaveCount(0);
  });
});
