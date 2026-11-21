import { expect, type Locator, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { formatNumber } from "../src/lib/number-format";
import week11 from "../src/modules/games/fixtures/play-week-11.json";
import { loginByApi } from "./support/auth";
import { expectAccessible, test } from "./support/classes";
import { alignment, textReadable } from "./support/graph";
import { liveClassGame, orderByApi } from "./support/live-game";
import { confirmedWeek11, GAME_ID } from "./support/play";

/** Hjem's Spillkort (Story 6.17, FR-25, UX-DR28, `04-student-hjem.png`). The stubbed tests lay a
 * running game over the demo Student's real Class, so the demo Class is never changed. The numbers
 * are the engine's Grossist in Uke 11 (`play-week-11.json`). That the api gives Hjem the play
 * envelope's `seat_state` and turn is pinned by `backend/tests/sessions/test_play.py`. The last
 * test plays a real game on the local stack for the live updates. */
const copy = nb.homes.student;
const card = copy.card;
const LIVE_MS = 2_000;

const RULES = { order_delay: 2, shipping_delay: 2, production_delay: 2, guided_weeks: 4, holding_cost: "0.50", backorder_cost: "1.00" };

type Envelope = Omit<typeof week11, "turn"> & { turn: { guided: boolean; order: number | null; viewed: boolean } };

function running(envelope: Envelope, id = GAME_ID, number = 17) {
  return {
    id,
    number,
    role: "wholesaler",
    seats: envelope.table_status.seats,
    briefing_first: false,
    rules: RULES,
    status: "running",
    week: envelope.seat_state.week,
    server_now: envelope.server_now,
    seat_state: envelope.seat_state,
    turn: envelope.turn,
  };
}

/** The demo Student's Class with one Class session per game, as the api answers it. */
async function withGames(page: Page, games: ReturnType<typeof running>[]) {
  await page.route("**/api/me/class-sessions", async (route) => {
    const response = await route.fetch();
    const classes = await (await page.request.get("/api/classes/enrolled")).json();
    const [klass] = classes.items;
    const items = games.map((game, i) => ({
      id: `01a1f8ee-33b9-75e6-9502-79db27b37c0${i}`,
      class_id: klass.id,
      class_name: klass.name,
      number: i + 1,
      start_at: "2026-11-24T09:00:00Z",
      play_deadline: "2026-12-08T13:00:00Z",
      debrief_deadline: null,
      test_deadline: null,
      next_deadline: { kind: "play", at: "2026-12-08T13:00:00Z" },
      obligatory: false,
      lab_hours: [],
      seat_choice_open: false,
      drawn_seat: null,
      steps: [{ step: "class_game", state: "current" }],
      game,
    }));
    await route.fulfill({ response, json: { items } });
  });
}

const cards = (page: Page) => page.getByRole("main").locator("[data-game-card]");
/** Hjem's primary buttons: links or buttons in the primary style (`bg-ink`). */
const primaries = (page: Page) => page.getByRole("main").locator("a.bg-ink, button.bg-ink");

async function expectWaitsForYou(one: Locator, net: string, week: number, total: string) {
  await expect(one.getByRole("heading", { level: 4 })).toHaveText(`${card.waitsForYou}, ${card.week(week)}`);
  await expect(one.getByText(card.total(total))).toBeVisible();
  await expect(one.getByText(card.net(net, week))).toHaveCount(1);
}

const WIDTHS = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
];

for (const vp of WIDTHS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("a game that waits for the Student and one that waits for others: the card, one primary, no axe violation", async ({
      page,
    }) => {
      await loginByApi(page, "student");
      await withGames(page, [running(week11), running(confirmedWeek11, "01a1f8ee-34f2-70af-8800-f79281ed7a68", 18)]);
      await page.goto("/hjem");
      const [waits, ordered] = [cards(page).nth(0), cards(page).nth(1)];
      await expect(cards(page)).toHaveCount(2);

      // Waits for you: title, Uke, the three rows over nå − 7 … nå + 4, Totalkostnad, «Gå til Uke 11».
      await expectWaitsForYou(waits, formatNumber(-20), 11, formatNumber("82.00", { kroner: true }));
      const table = waits.getByRole("region", { name: card.region(17) });
      await expect(table.getByRole("rowheader")).toHaveText([nb.terms.week, nb.terms.netInventory, nb.games.play.table.order]);
      await expect(table.getByRole("columnheader")).toHaveText(Array.from({ length: 12 }, (_, i) => `Uke ${i + 4}`));
      await expect(table.locator("tr[data-row=netInventory] td").first()).toHaveText("12");
      await expect(table.locator("tr[data-row=netInventory] td").nth(7)).toHaveText(formatNumber(-20));
      await expect(table.locator("tr[data-row=order] td").nth(6)).toHaveText("8");
      await expect(table.locator("tr[data-field]")).toHaveAttribute("aria-hidden", "true");
      await expect(waits.locator("[data-mark=position], [data-label=position], [data-label=net]")).toHaveCount(0);
      await expect(waits.getByRole("link", { name: nb.games.start.toWeek(11) })).toHaveAttribute("href", `/spill/${GAME_ID}`);

      // Waits for others: the draft title, the Order at nå, and «Gå til Uke 11» as a Lenke only.
      await expect(ordered.getByRole("heading", { level: 4 })).toHaveText(`${card.ordered}, ${card.week(11)}`);
      await expect(ordered.locator("tr[data-row=order] td").nth(7)).toHaveText("24");
      await expect(primaries(page)).toHaveCount(1);
      // The card holds the game's action: no second «Gå til Uke 11» under Setene.
      await expect(page.getByRole("main").getByRole("link", { name: nb.games.start.toWeek(11) })).toHaveCount(2);
      await expect(waits.locator("a.bg-ink")).toHaveCount(1);

      // Card above Setene, as drawn; the card text never says how many Uker are left.
      const seats = page.getByRole("main").getByRole("region", { name: copy.seats }).first();
      expect((await waits.boundingBox())!.y).toBeLessThan((await seats.boundingBox())!.y);
      await expect(waits).not.toContainText(/av \d+|\d+ %|igjen/);

      const aligned = await alignment(page);
      expect(aligned.worst).toBeLessThanOrEqual(1);
      await expectAccessible(page, vp.phone);
      await textReadable(page);
    });
  });
}

test("waiting for others only: Hjem has no primary button", async ({ page }) => {
  await loginByApi(page, "student");
  await withGames(page, [running(confirmedWeek11)]);
  await page.goto("/hjem");
  await expect(cards(page).getByRole("heading", { level: 4 })).toHaveText(`${card.ordered}, ${card.week(11)}`);
  await expect(cards(page).getByRole("link", { name: nb.games.start.toWeek(11) })).toBeVisible();
  await expect(primaries(page)).toHaveCount(0);
});

test("live: another Seat's Order and the new Uke reach the card within 2 s, and focus stays put", async ({
  browser,
  lecturerSession,
}) => {
  test.slow(); // two Invitations through the worker, a Class session and a lock
  const game = await liveClassGame(browser, lecturerSession, 2, { aiMode: "rule_based" });
  const [me, other] = game.students as [(typeof game.students)[0], (typeof game.students)[0]];
  try {
    const page = await me.context.newPage();
    await page.goto("/hjem");
    const one = cards(page);
    await expect(one.getByRole("heading", { level: 4 })).toHaveText(`${card.waitsForYou}, ${card.week(1)}`);
    await expect(page.locator("html")).toHaveAttribute("data-live", "live", { timeout: 10_000 });
    const region = one.getByRole("region", { name: /^Graf og tabell, Spill / });
    // Uke 1: no history, so Uke 1 … 5 and a graph of one point.
    await expect(region.getByRole("columnheader")).toHaveText(["Uke 1", "Uke 2", "Uke 3", "Uke 4", "Uke 5"]);
    await expect(region.locator("[data-mark=net]")).toHaveAttribute("data-weeks", "1");
    await region.focus();
    const otherRow = page.getByRole("main").getByRole("region", { name: copy.seats }).getByRole("listitem").filter({ hasText: other.name });
    await expect(otherRow).toContainText(copy.status.waiting);

    await orderByApi(other, game.gameId, 1, 4);
    await expect(otherRow).toContainText(copy.status.ordered, { timeout: LIVE_MS });

    // The Student's own Order completes Uke 1 (the AI players have ordered): the card shows Uke 2.
    await orderByApi(me, game.gameId, 1, 5);
    await expect(one.getByRole("heading", { level: 4 })).toHaveText(`${card.waitsForYou}, ${card.week(2)}`, { timeout: LIVE_MS });

    // Ordered in Uke 2, the other not yet: the waiting title and no primary button.
    await orderByApi(me, game.gameId, 2, 6);
    await expect(one.getByRole("heading", { level: 4 })).toHaveText(`${card.ordered}, ${card.week(2)}`, { timeout: LIVE_MS });
    await expect(primaries(page)).toHaveCount(0);
    await expect(region).toBeFocused();
  } finally {
    for (const student of game.students) await student.context.close();
  }
});
