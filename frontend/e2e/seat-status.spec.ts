import { expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import type { PlayEnvelope } from "../src/modules/games/api";
import week11 from "../src/modules/games/fixtures/play-week-11.json";
import { loginByApi } from "./support/auth";
import { expectAccessible } from "./support/classes";
import { confirmButton as button, GAME_ID, openPlay, orderField as field, refetchPlay } from "./support/play";

/** The Setestatus (Story 6.14, FR-24, FR-25, FR-34, NFR-6, UX-DR25, UX-DR62, UX-DR69): who has
 * ordered this Uke and whom the game waits for, under the Ordrefelt and on Hjem. The stand-in play
 * screen of `support/play.ts`, whose Uke 11 envelope has Jonas Berg waited for since 11:57 on the
 * server's 12:00. What the api stores and sends is `backend/tests/sessions/test_seat_status.py`;
 * the passing of time is Playwright's clock, never waited for. */
const copy = nb.homes.student;
type Seat = PlayEnvelope["table_status"]["seats"][number];

const region = (page: Page) => page.getByRole("main").getByRole("region", { name: copy.seats });
const rows = (page: Page) => region(page).getByRole("listitem");
const announce = (page: Page) => page.locator("[data-seat-status-announce]");

/** Uke 11 with the Seats changed by `change`. */
function week11With(change: (seat: Seat) => Seat, extra: object = {}) {
  const seats = week11.table_status.seats as Seat[];
  return { ...week11, ...extra, table_status: { seats: seats.map(change) } };
}

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

for (const width of [320, 360, 1440]) {
  test.describe(`${width} px`, () => {
    test.use({ viewport: { width, height: 800 } });

    test("every Seat in words under the Ordrefelt, the wait ticking on the server's clock, no axe violation", async ({
      page,
    }) => {
      await page.clock.install();
      const stub = await openPlay(page);
      await expect(rows(page)).toHaveText([
        /^Fabrikk\s*KI-spiller\s*har bestilt$/,
        /^Distributør\s*Jonas Berg\s*venter, 3 min$/,
        /^Grossist\s*Demo Student \(deg\)\s*venter \(deg\)$/,
        /^Detaljist\s*KI-spiller\s*har bestilt$/,
      ]);
      // A filled dot for ordered, a hollow one for waiting; the text says it too.
      await expect(region(page).locator("li[data-state]")).toHaveCount(4);
      expect(await region(page).locator("li").evaluateAll((els) => els.map((el) => el.dataset.state))).toEqual([
        "ordered",
        "waiting",
        "waiting",
        "ordered",
      ]);
      await expect(region(page).locator("svg[aria-hidden='true']")).toHaveCount(4);
      // Right under the Ordrefelt and its button, before the Lenker; no «Venter på» line drawn.
      const order = await page.evaluate(() => {
        const field = document.querySelector("[data-order-field]")!;
        const seats = document.querySelector("[data-seat-status]")!;
        const link = [...document.querySelectorAll("main a")].find((a) => a.textContent === "Regler før første ordre");
        return {
          after: !!(field.compareDocumentPosition(seats) & Node.DOCUMENT_POSITION_FOLLOWING),
          beforeLinks: !link || !!(seats.compareDocumentPosition(link) & Node.DOCUMENT_POSITION_FOLLOWING),
        };
      });
      expect(order).toEqual({ after: true, beforeLinks: true });
      // «Venter på: …» is the screen-reader announcement only.
      await expect(page.getByText(/Venter på:/)).toHaveCount(1);
      await expect(page.getByText(/Venter på:/)).toHaveClass(/sr-only/);
      await expect(announce(page)).toHaveText(copy.waitingOn("Jonas Berg (3 min) og deg"));

      // Students and AI players in both states: an AI player still thinking, one the Play guard
      // switched, and the Student's own Order sent.
      const mixed = (mine: boolean) =>
        week11With((seat) =>
          seat.role === "factory"
            ? { ...seat, ordered: false, wait_started_at: "2026-11-20T11:57:00Z" }
            : seat.role === "retailer"
              ? { ...seat, mark: "guard_switch" }
              : seat.mine
                ? { ...seat, ordered: mine }
                : seat,
        );
      stub.envelope = mixed(false);
      stub.answer = async (route) => {
        stub.envelope = { ...mixed(true), turn: { ...week11.turn, order: 24 } };
        await route.fulfill({ status: 204 });
      };
      await refetchPlay(page);
      await expect(rows(page).nth(0)).toHaveText(/^Fabrikk\s*KI-spiller\s*venter$/);
      await field(page).fill("24");
      await button(page).click();
      await expect(page.locator("[data-order-sent]")).toHaveText(
        nb.games.play.order.sentWaiting("24", "Fabrikk og Jonas Berg (3 min)"),
      );
      await expect(rows(page)).toHaveText([
        /^Fabrikk\s*KI-spiller\s*venter$/,
        /^Distributør\s*Jonas Berg\s*venter, 3 min$/,
        /^Grossist\s*Demo Student \(deg\)\s*har bestilt$/,
        /^Detaljist\s*KI-spiller \(regelbasert\)\s*har bestilt$/,
      ]);
      await expect(announce(page)).toHaveText(copy.waitingOn("Fabrikk og Jonas Berg (3 min)"));
      await expectAccessible(page, width < 1024);

      // Two minutes on: the wait counts on from the stored start; the announcement stays put.
      await page.clock.fastForward("02:00");
      await expect(rows(page).nth(1)).toHaveText(/venter, 5 min$/);
      await expect(announce(page)).toHaveText(copy.waitingOn("Fabrikk og Jonas Berg (3 min)"));
    });
  });
}

test.describe("1440 px", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("another Seat orders: the rows update without moving focus, and «Venter på» is announced", async ({ page }) => {
    const stub = await openPlay(page);
    await field(page).fill("24");
    await expect(field(page)).toBeFocused();
    stub.envelope = week11With((seat) => (seat.role === "distributor" ? { ...seat, ordered: true, wait_started_at: null } : seat));
    await refetchPlay(page);
    await expect(rows(page).nth(1)).toHaveText(/^Distributør\s*Jonas Berg\s*har bestilt$/);
    await expect(announce(page)).toHaveText(copy.waitingOn("deg"));
    await expect(field(page)).toBeFocused();
    await expect(field(page)).toHaveValue("24");
  });

  test("the confirmed message names whom the game waits for, with the wait", async ({ page }) => {
    await openPlay(page);
    await field(page).fill("24");
    await button(page).click();
    const sent = page.locator("[data-order-sent]");
    await expect(sent).toHaveText(nb.games.play.order.sentWaiting("24", "Jonas Berg (3 min)"));
    await expect(sent).toBeFocused();
    await expect(rows(page).nth(2)).toHaveText(/^Grossist\s*Demo Student \(deg\)\s*har bestilt$/);
    await expect(announce(page)).toHaveText(copy.waitingOn("Jonas Berg (3 min)"));
  });

  test("an AI player not yet ordered reads «venter» with no duration; a guard switch says rule-based", async ({ page }) => {
    await page.clock.install();
    const stub = await openPlay(page);
    // The AI player's Order is due 30 s on (`next_change_at`): the screen reads again then.
    stub.envelope = week11With(
      (seat) =>
        seat.role === "factory"
          ? { ...seat, ordered: false, wait_started_at: "2026-11-20T11:57:00Z" }
          : seat.role === "retailer"
            ? { ...seat, mark: "guard_switch" }
            : seat,
      { next_change_at: "2026-11-20T12:00:30Z" },
    );
    await refetchPlay(page);
    await expect(rows(page).nth(0)).toHaveText(/^Fabrikk\s*KI-spiller\s*venter$/);
    await expect(rows(page).nth(3)).toHaveText(/^Detaljist\s*KI-spiller \(regelbasert\)\s*har bestilt$/);
    await expect(announce(page)).toHaveText(copy.waitingOn("Fabrikk, Jonas Berg (3 min) og deg"));
    await expect(page.getByText("LLM")).toHaveCount(0);
    stub.envelope = week11;
    await page.clock.fastForward("00:31");
    await expect(rows(page).nth(0)).toHaveText(/^Fabrikk\s*KI-spiller\s*har bestilt$/);
  });

  test("Hjem shows the same Setestatus for a running game", async ({ page }) => {
    await loginByApi(page, "student");
    await page.route("**/api/me/class-sessions", async (route) => {
      const response = await route.fetch();
      const classes = await (await page.request.get("/api/classes/enrolled")).json();
      const [klass] = classes.items;
      const item = {
        id: "01a1f8ee-33b9-75e6-9502-79db27b37c0e",
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
        steps: [],
        game: {
          id: GAME_ID,
          number: 17,
          role: "wholesaler",
          seats: week11.table_status.seats,
          briefing_first: false,
          rules: { order_delay: 2, shipping_delay: 2, production_delay: 2, guided_weeks: 4, holding_cost: "0.50", backorder_cost: "1.00" },
          status: "running",
          week: 11,
          server_now: week11.server_now,
        },
      };
      await route.fulfill({ response, json: { items: [item] } });
    });
    await page.goto("/hjem");
    await expect(rows(page)).toHaveText([
      /^Fabrikk\s*KI-spiller\s*har bestilt$/,
      /^Distributør\s*Jonas Berg\s*venter, 3 min$/,
      /^Grossist\s*Demo Student \(deg\)\s*venter \(deg\)$/,
      /^Detaljist\s*KI-spiller\s*har bestilt$/,
    ]);
  });
});
