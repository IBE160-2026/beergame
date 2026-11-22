import { expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { orderProjection } from "../src/lib/preview";
import type { PlayEnvelope } from "../src/modules/games/api";
import short from "../src/modules/games/fixtures/play-replay-short.json";
import week11 from "../src/modules/games/fixtures/play-week-11.json";
import { formatNumber } from "../src/lib/number-format";
import { loginByApi, untilFontsLoaded } from "./support/auth";
import { expectAccessible, expectReflow } from "./support/classes";
import { alignment, labelProblems, projectionCrossings, projectionSumLines } from "./support/graph";

/** Playing the Replay (Story 10.4, FR-48, FR-49, FR-14, FR-73, NFR-6, AD-10, UX-DR19, UX-DR64): the
 * Epic 6 play screen with the dashed projection and its sentence, which only an envelope with
 * `projection` (the Replay's policy) draws. As in `graph-over-table.spec.ts`, the game and its
 * envelopes are stand-ins with the api's shapes: the engine's Grossist of a Classic game in Uke 11
 * and of a 1/1/1 game in Uke 9 (`backend/tests/games/test_play_fixture.py`); that the api sends
 * `projection` for a Replay and never for a Class game is `backend/tests/replay/test_play.py`. */
const GAME_ID = "01a1f8ee-34f2-70af-8800-f79281ed7a66";
const SESSION = "01a1f8ee-33b9-75e6-9502-79db27b37c0e";
const copy = nb.games.play;

type Envelope = PlayEnvelope;
const CLASS = week11 as unknown as Envelope;

const AI_SEATS = week11.table_status.seats.map((seat) =>
  seat.mine ? seat : { ...seat, holder: "ai", name: null, ordered: seat.role === "retailer" ? false : true },
);

async function openPlay(page: Page, envelope: Envelope, replay: boolean) {
  await loginByApi(page, "student");
  const week = envelope.seat_state.week;
  await page.route(`**/api/me/games/${GAME_ID}`, (route) =>
    route.fulfill({
      json: {
        id: GAME_ID,
        number: replay ? null : 17,
        replay,
        test_game: false,
        class_session_id: SESSION,
        role: "wholesaler",
        seats: envelope.table_status.seats,
        briefing_first: false,
        rules: { order_delay: 2, shipping_delay: 2, production_delay: 2, guided_weeks: 0, holding_cost: "0.50", backorder_cost: "1.00" },
        status: "running",
        week,
        server_now: envelope.server_now,
        seat_state: null,
        turn: null,
      },
    }),
  );
  await page.route(`**/api/me/games/${GAME_ID}/play`, (route) => route.fulfill({ json: envelope }));
  await page.goto(`/spill/${GAME_ID}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.week(week));
  await expect(page.locator('svg[data-chart="net"]:visible')).toHaveCount(1);
  await untilFontsLoaded(page);
}

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

const REPLAY: Envelope = { ...CLASS, projection: true, table_status: { seats: AI_SEATS as Envelope["table_status"]["seats"], can_pause: false } };

test.describe("1280 px at 200 % text", () => {
  test.use({ viewport: { width: 1280, height: 800 } });

  test("the play screen reflows to one column: the chart keeps the row, nothing is clipped", async ({ page }) => {
    await page.addInitScript(() => {
      document.addEventListener("DOMContentLoaded", () => {
        const style = document.createElement("style");
        style.textContent = "html { font-size: 200% !important; }";
        document.head.appendChild(style);
      });
    });
    await openPlay(page, REPLAY, true);
    const graph = page.locator('svg[data-chart="net"]:visible');
    const field = page.getByRole("textbox", { name: copy.order.label(11) });
    const [chart, order, main] = [await graph.boundingBox(), await field.boundingBox(), await page.getByRole("main").boundingBox()];
    // One column: the Ordrefelt under the chart; the Kjedebånd inside the page.
    expect(order!.y).toBeGreaterThan(chart!.y + chart!.height);
    const band = await page.locator("[data-chain-band]").boundingBox();
    expect(band!.x + band!.width).toBeLessThanOrEqual(main!.x + main!.width + 0.5);
    expect(await labelProblems(page)).toEqual([]);
    await expectReflow(page, false);
  });
});
const sentenceOf = (envelope: Envelope, order: number | null) => {
  const p = orderProjection(envelope.seat_state, order);
  return copy.graph.projection(
    p.horizon,
    formatNumber(p.position),
    order === null ? null : formatNumber(order),
    formatNumber(p.horizon),
    formatNumber(p.incoming),
    formatNumber(p.value),
  );
};

const VIEWPORTS = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
];

for (const vp of VIEWPORTS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("the Replay draws the projection to nå + 4 with its sentence; typing moves both; axe passes", async ({ page }) => {
      await openPlay(page, REPLAY, true);
      const main = page.getByRole("main");
      await expect(page.getByText(copy.roleReplay("Grossist"), { exact: true })).toBeVisible();
      const graph = page.locator('svg[data-chart="net"]:visible');
      const line = graph.locator("[data-mark=projection]");
      await expect(line).toHaveCount(1);
      await expect(line).toHaveAttribute("data-weeks", "11 15");
      await expect(line.locator("circle[data-projection-end]")).toHaveCount(1);
      // Its own stroke and marker, never colour alone (UX-DR76): dashed, a hollow dot.
      await expect(line.locator("path")).toHaveAttribute("stroke-dasharray", "5 4");
      // Every mark, the projection's two points included, within 1 px of its column.
      const found = await alignment(page);
      expect(found.off).toEqual([]);
      expect(Math.max(...found.drawn)).toBe(15); // the axis stops at nå + 4
      expect(await labelProblems(page)).toEqual([]);
      // Story 10.6: the line and its dot stay off «Restordre» and «Posisjon».
      expect(await projectionCrossings(page)).toEqual([]);
      const sentence = main.locator("[data-projection-sentence]");
      await expect(sentence).toHaveText(sentenceOf(REPLAY, null));
      // The graph rows are hidden from screen readers; the sentence is read (NFR-6).
      await expect(page.locator('tr[data-field="net"]').first()).toHaveAttribute("aria-hidden", "true");
      // Wraps inside the page at 320 px: no side scroll, nothing over it.
      await expectAccessible(page, vp.phone);
      const box = await sentence.boundingBox();
      expect(box!.x + box!.width).toBeLessThanOrEqual(vp.width);

      const field = page.getByRole("textbox", { name: copy.order.label(11) });
      await field.fill("24");
      await expect(sentence).toHaveText(sentenceOf(REPLAY, 24));
      expect(await projectionCrossings(page)).toEqual([]);
      await expectReflow(page, vp.phone);
      // An AI player's Setestatus row reads «venter» while it has not ordered (NFR-2); there is
      // no Pausevalg and no «Sett inn KI-spiller» (FR-49).
      const seats = main.getByRole("region", { name: nb.homes.student.seats }).getByRole("listitem");
      await expect(seats.filter({ hasText: "Detaljist" })).toContainText(nb.homes.student.status.waiting);
      await expect(seats.filter({ hasText: "Detaljist" })).toContainText(nb.homes.student.aiPlayer);
      await expect(main.getByText("Sett inn KI-spiller")).toHaveCount(0);
      // No briefing of its own: the way out is Hjem alone.
      await expect(main.getByRole("link", { name: nb.games.briefing.title })).toHaveCount(0);
      await expect(main.getByText(/Pause/)).toHaveCount(0);
    });

    test("a Class game draws no projection and no sentence", async ({ page }) => {
      await openPlay(page, CLASS, false);
      await expect(page.locator("[data-mark=projection]")).toHaveCount(0);
      await expect(page.locator("[data-projection-sentence]")).toHaveCount(0);
      await expect(page.getByText(copy.roleGame("Grossist", 17), { exact: true })).toBeVisible();
      await expect(page.getByRole("main").getByRole("link", { name: nb.games.briefing.title })).toHaveCount(1);
    });
  });
}

test("at 390 px the labels stay clear of the projection and its sum keeps to one line (Story 10.6)", async ({ page }) => {
  // The 10.4 visual check: «Restordre 20» struck through by the line and dot, and «−4 − 4 / × 10».
  await page.setViewportSize({ width: 390, height: 844 });
  await openPlay(page, REPLAY, true);
  expect(await projectionCrossings(page)).toEqual([]);
  expect(await labelProblems(page)).toEqual([]);
  expect(await projectionSumLines(page)).toBe(1);
  await page.getByRole("textbox", { name: copy.order.label(11) }).fill("24");
  await expect(page.locator("[data-projection-sentence]")).toHaveText(sentenceOf(REPLAY, 24));
  expect(await projectionCrossings(page)).toEqual([]);
  expect(await projectionSumLines(page)).toBe(1);
});

test("a Replay with shorter delays puts the dot at nå + 2 and says «om to uker»", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  const envelope = short as unknown as Envelope;
  await openPlay(page, envelope, true);
  const week = envelope.seat_state.week;
  const line = page.locator('svg[data-chart="net"]:visible [data-mark=projection]');
  await expect(line).toHaveAttribute("data-weeks", `${week} ${week + 2}`);
  const found = await alignment(page);
  expect(found.off).toEqual([]);
  const sentence = page.locator("[data-projection-sentence]");
  await expect(sentence).toHaveText(sentenceOf(envelope, null));
  await expect(sentence).toContainText("om to uker");
  await expect(sentence).toContainText(" − 2 × ");
  expect(await projectionCrossings(page)).toEqual([]);
  expect(await projectionSumLines(page)).toBe(1);
});

test.describe("Hjem and Stegene lead back to a running Replay", () => {
  for (const vp of [VIEWPORTS[0]!, VIEWPORTS[2]!]) {
    test(`«Fortsett Replay, Uke 9» at ${vp.name}`, async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await loginByApi(page, "student");
      await page.route("**/api/me/class-sessions", async (route) => {
        const response = await route.fetch();
        const classes = await (await page.request.get("/api/classes/enrolled")).json();
        const [klass] = classes.items;
        const item = {
          id: SESSION,
          class_id: klass.id,
          class_name: klass.name,
          number: 1,
          start_at: "2026-11-01T09:00:00Z",
          play_deadline: "2026-11-15T13:00:00Z",
          debrief_deadline: "2026-11-20T13:00:00Z",
          test_deadline: "2026-12-08T13:00:00Z",
          next_deadline: { kind: "test", at: "2026-12-08T13:00:00Z" },
          obligatory: false,
          lab_hours: [],
          seat_choice_open: false,
          drawn_seat: null,
          game: {
            id: "01a1f8ee-34f2-70af-8800-f79281ed777e",
            number: 17,
            role: "wholesaler",
            replay: false,
            test_game: false,
            class_session_id: SESSION,
            seats: week11.table_status.seats,
            briefing_first: false,
            status: "finished",
            week: null,
            server_now: "2026-11-22T10:00:00Z",
            seat_state: null,
            turn: null,
            debrief: "open",
            rules: { order_delay: 2, shipping_delay: 2, production_delay: 2, guided_weeks: 4, holding_cost: "0.50", backorder_cost: "1.00" },
          },
          steps: ["class_game", "debrief", "quiz", "replay", "test", "report"].map((step, i) => ({
            step,
            state: i < 3 ? "done" : i === 3 ? "current" : "locked",
            held: false,
            quiz_changed: false,
            group_open: false,
            closed: false,
          })),
          replay: {
            can_start: false,
            game: { id: GAME_ID, role: "wholesaler", status: "running", week: 9, server_now: "2026-11-22T10:00:00Z", seats: AI_SEATS },
          },
        };
        await route.fulfill({ response, json: { items: [item] } });
      });
      await page.goto("/hjem");
      const main = page.getByRole("main");
      const block = main.getByRole("region", { name: "Replay · Du er Grossist" });
      const resume = block.getByRole("link", { name: nb.homes.student.replay.resume(9) });
      await expect(resume).toHaveAttribute("href", `/spill/${GAME_ID}`);
      // Hjem's one primary (UX-DR8): the finished Class game has none, so the Replay's.
      await expect(main.locator("a.bg-ink, button.bg-ink")).toHaveCount(1);
      await expect(resume).toHaveClass(/\bbg-ink\b/);
      const step = main.getByRole("region", { name: nb.homes.student.steps }).getByRole("listitem").nth(3);
      await expect(step).toContainText(nb.homes.student.replayResume(9));
      await expect(step.getByRole("link")).toHaveCount(0);
      await expectAccessible(page, vp.phone);
    });
  }
});
