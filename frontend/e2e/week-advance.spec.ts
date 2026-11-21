import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { test } from "./support/classes";
import { instrument, liveClassGame, type LiveStudent, orderByApi, timing } from "./support/live-game";

/** The new Uke within 2 s, on any device (Story 6.15, FR-26, NFR-1, NFR-5), on the real local
 * stack: a real Class game (`support/live-game.ts`), live updates over SSE, the real play envelope.
 * The 2 s are counted from the last Order's press to the moment each page's heading reads the new
 * Uke, on one clock. Each test also records where the time went (the SSE event, the envelope's
 * answer) as annotations. The transaction behind it is pinned by
 * `backend/tests/sessions/test_week_advance.py`. */
const copy = nb.games.play;
const LIMIT_MS = 2_000;

async function untilLive(page: Page) {
  await expect(page.locator("html")).toHaveAttribute("data-live", "live", { timeout: 10_000 });
}

/** Each Student's play screen at Uke `week`, live, timing Uke `week + 1`. */
async function openAll(students: LiveStudent[], gameId: string, week: number): Promise<Page[]> {
  return Promise.all(
    students.map(async (student) => {
      const page = await student.context.newPage();
      await instrument(page, week + 1);
      await page.goto(`/spill/${gameId}`);
      await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.week(week));
      await untilLive(page);
      return page;
    }),
  );
}

/** The last Student confirms `value` on the page; returns the press time. */
async function confirmLast(page: Page, week: number, value: number): Promise<number> {
  await page.getByRole("textbox", { name: copy.order.label(week) }).fill(String(value));
  const button = page.getByRole("button", { name: copy.order.confirmOn(String(value)) });
  await expect(button).toBeVisible();
  const pressed = Date.now();
  await button.click();
  return pressed;
}

/** Waits for every page to show Uke `week`, then checks each within `LIMIT_MS` of `pressed` and
 * records the breakdown per page: event (first SSE event after the press), read (last envelope
 * answer before the heading changed) and shown, each in ms after the press. */
async function expectWithinLimit(pages: Page[], week: number, pressed: number) {
  await Promise.all(pages.map((page) => expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.week(week))));
  const lines: string[] = [];
  for (const [i, page] of pages.entries()) {
    const t = await timing(page);
    const event = t.events.find((at) => at >= pressed);
    const read = t.playRead.filter((at) => at >= pressed && at <= t.shown).at(-1);
    const rel = (at: number | undefined) => (at === undefined ? "-" : `${at - pressed}`);
    lines.push(`page ${i}: event ${rel(event)} ms, envelope ${rel(read)} ms, shown ${rel(t.shown)} ms [events ${t.events.filter((a) => a >= pressed).map(rel).join(",")}; reads ${t.playRead.filter((a) => a >= pressed).map(rel).join(",")}]`);
    expect(t.shown, `page ${i} recorded when Uke ${week} showed`).toBeDefined();
    expect(t.shown - pressed, `page ${i} shows Uke ${week} within 2 s`).toBeLessThan(LIMIT_MS);
  }
  test.info().annotations.push({ type: "timing", description: lines.join("; ") });
}

test("four Students: the last Order brings Uke 2 to every screen within 2 s, and a reload or another device resumes it", async ({
  browser,
  lecturerSession,
}) => {
  test.slow(); // four Invitations through the worker, a Class session and a lock
  const game = await liveClassGame(browser, lecturerSession, 4);
  try {
    const pages = await openAll(game.students, game.gameId, 1);
    for (const student of game.students.slice(0, 3)) await orderByApi(student, game.gameId, 1, 4);
    // The others' screens are Confirmed: the last Student's press completes the Uke.
    await expect(pages[0]!.locator("[data-order-sent]")).toBeVisible();
    await pages[1]!.getByRole("link", { name: nb.games.briefing.title }).focus();
    const pressed = await confirmLast(pages[3]!, 1, 6);
    await expectWithinLimit(pages, 2, pressed);
    // Live updates never move focus; the Student's own press moves it to the new Uke.
    await expect(pages[1]!.getByRole("link", { name: nb.games.briefing.title })).toBeFocused();
    await expect(pages[3]!.getByRole("heading", { level: 1 })).toBeFocused();

    // Uke 2: the second Student orders, then reloads and opens the game on a laptop as well.
    const second = pages[1]!;
    await second.getByRole("textbox", { name: copy.order.label(2) }).fill("7");
    await second.getByRole("button", { name: copy.order.confirmOn("7") }).click();
    await expect(second.locator("[data-order-sent]")).toBeFocused();
    await second.reload();
    await expect(second.getByRole("heading", { level: 1 })).toHaveText(copy.week(2));
    await expect(second.locator("[data-order-sent]")).toHaveText(/Ordren på 7 er sendt/);
    const laptop = await browser.newContext({
      baseURL: test.info().project.use.baseURL,
      viewport: { width: 1440, height: 900 },
      storageState: await game.students[1]!.context.storageState(),
    });
    const other = await laptop.newPage();
    await other.goto(`/spill/${game.gameId}`);
    await expect(other.getByRole("heading", { level: 1 })).toHaveText(copy.week(2));
    await expect(other.locator("[data-order-sent]")).toHaveText(/Ordren på 7 er sendt/);
    // The Uke 1 history stands: the Order of 4 in Din ordre in the column of Uke 1.
    await expect(other.locator('tr[data-row="order"] td').first()).toHaveText("4");
    await laptop.close();
  } finally {
    for (const student of game.students) await student.context.close();
  }
});

test("two Students and two mock AI players: once the AI players have ordered, the last Order brings Uke 2 within 2 s", async ({
  browser,
  lecturerSession,
}) => {
  test.slow();
  const game = await liveClassGame(browser, lecturerSession, 2, { aiMode: "llm" });
  try {
    const pages = await openAll(game.students, game.gameId, 1);
    await orderByApi(game.students[0]!, game.gameId, 1, 4);
    // The AI players' thinking time is not counted: wait until both have ordered.
    await expect
      .poll(
        async () => {
          const envelope = await (await game.students[1]!.context.request.get(`/api/me/games/${game.gameId}/play`)).json();
          return (envelope.table_status.seats as { holder: string; ordered: boolean }[]).filter(
            (seat) => seat.holder === "ai" && seat.ordered,
          ).length;
        },
        { timeout: 20_000 },
      )
      .toBe(2);
    const pressed = await confirmLast(pages[1]!, 1, 5);
    await expectWithinLimit(pages, 2, pressed);
  } finally {
    for (const student of game.students) await student.context.close();
  }
});
