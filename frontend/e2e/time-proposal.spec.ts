import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { loginByApi } from "./support/auth";
import { expectAccessible, test } from "./support/classes";
import { liveClassGame } from "./support/live-game";

/** The scheduling aid (Story 6.19, FR-22, FR-73, NFR-6, UX-DR78) on Hjem. The api's rules (one
 * open proposal, the range, the notice, AD-20) are `backend/tests/sessions/test_time_proposal.py`.
 * Here the demo Student's Class gets a stand-in game with a proposal laid over the real answer, so
 * the demo Class is never changed, at 320, 360 and 1440 px; the last test runs two fresh Students
 * on the local stack. */
const copy = nb.games.timeProposal;
const primaries = (page: Page) => page.getByRole("main").locator("a.bg-ink, button.bg-ink");

const GAME = {
  id: "01a1f8ee-34f2-70af-8800-f79281ed7190",
  number: 17,
  role: "wholesaler",
  seats: [
    { role: "factory", holder: "student", name: "Kari Nordmann", mine: false, ordered: null, wait_started_at: null, mark: null },
    { role: "distributor", holder: "ai", name: null, mine: false, ordered: null, wait_started_at: null, mark: null },
    { role: "wholesaler", holder: "student", name: "Demo Student", mine: true, ordered: null, wait_started_at: null, mark: null },
    { role: "retailer", holder: "student", name: "Per Hansen", mine: false, ordered: null, wait_started_at: null, mark: null },
  ],
  briefing_first: true,
  status: "ready",
  week: null,
  rules: { order_delay: 2, shipping_delay: 2, production_delay: 2, guided_weeks: 4, holding_cost: "0.50", backorder_cost: "1.00" },
  server_now: "2026-11-25T09:00:00Z",
  seat_state: null,
  turn: null,
  time_proposal: {
    id: "01a1f8ee-34f2-70af-8800-f79281ed7191",
    at: "2026-11-26T13:15:00Z",
    proposed_by: { name: "Kari Nordmann", mine: false },
    accepted_by: [{ name: "Per Hansen", mine: false }],
    can_accept: true,
  },
};

/** The demo Student's Class with one locked Class session holding `GAME`. */
async function withGame(page: Page) {
  await page.route("**/api/me/class-sessions", async (route) => {
    const response = await route.fetch();
    const [klass] = (await (await page.request.get("/api/classes/enrolled")).json()).items;
    const item = {
      id: "01a1f8ee-33b9-75e6-9502-79db27b37190",
      class_id: klass.id,
      class_name: klass.name,
      number: 1,
      start_at: "2026-11-24T09:00:00Z",
      play_deadline: "2026-12-08T13:00:00Z",
      debrief_deadline: null,
      test_deadline: null,
      next_deadline: { kind: "play", at: "2026-12-08T13:00:00Z" },
      obligatory: false,
      lab_hours: [],
      seat_choice_open: false,
      drawn_seat: null,
      game: GAME,
      steps: ["class_game", "debrief", "quiz", "replay", "test", "report"].map((step, i) => ({
        step,
        state: i === 0 ? "current" : "locked",
      })),
    };
    await route.fulfill({ response, json: { items: [item] } });
  });
}

for (const viewport of [
  { width: 320, height: 640, phone: true },
  { width: 360, height: 740, phone: true },
  { width: 1440, height: 900, phone: false },
]) {
  test.describe(`${viewport.width} px`, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });

    test("the proposal by name with «Godta tidspunktet», and «Foreslå tidspunkt» in place by keyboard", async ({
      page,
    }) => {
      await loginByApi(page, "student");
      await withGame(page);
      await page.goto("/hjem");
      const block = page.locator("[data-time-proposal]");
      await expect(block.getByText("Kari Nordmann foreslår å spille to. 26. nov. kl. 14:15.")).toBeVisible();
      await expect(block.getByText("Godtatt av Per Hansen.")).toBeVisible();
      await expect(block.getByRole("button", { name: copy.accept })).toBeVisible();

      // By keyboard: the control opens the form in place, focus on «Dato»; only a date and a time.
      const opener = block.getByRole("button", { name: copy.open });
      await opener.focus();
      await page.keyboard.press("Enter");
      const form = block.getByRole("form", { name: copy.title });
      await expect(form.getByLabel(copy.date)).toBeFocused();
      await expect(form.locator("input")).toHaveCount(2);
      await expect(form.locator("input[type=date]")).toHaveCount(1);
      await expect(form.locator("input[type=time]")).toHaveCount(1);
      await expect(form.locator("textarea, input[type=text], [contenteditable]")).toHaveCount(0);
      await expect(form.getByText(`${copy.consequence} ${copy.replaces}`)).toBeVisible();
      // Hjem keeps one primary: the form's, which states its effect.
      await expect(primaries(page)).toHaveCount(1);
      await expect(primaries(page)).toHaveText(copy.send);

      // A time after the Play deadline: the range error under the time field, nothing sent.
      await form.getByLabel(copy.date).fill("2026-12-09");
      await form.getByLabel(copy.time).fill("14:00");
      await form.getByRole("button", { name: copy.send }).press("Enter");
      const time = form.getByLabel(copy.time);
      await expect(form.getByText("Velg et tidspunkt mellom nå og Spillfristen, ti. 8. des. kl. 14:00.")).toBeVisible();
      await expect(time).toHaveAttribute("aria-invalid", "true");
      await expect(time).toBeFocused();
      await expectAccessible(page, viewport.phone);

      // «Avbryt» closes the form and gives focus back to «Foreslå tidspunkt».
      await form.getByRole("button", { name: copy.cancel }).press("Enter");
      await expect(form).toHaveCount(0);
      await expect(block.getByRole("button", { name: copy.open })).toBeFocused();
      await expect(primaries(page)).toHaveText(nb.homes.student.readRules);
    });
  });
}

/** The date field's value («2026-11-26») `days` from now, in Europe/Oslo. */
function osloDate(days: number): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Oslo" }).format(new Date(Date.now() + days * 86_400_000));
}

test("live: one Student proposes on Hjem, the other sees it at once and accepts, and both see who accepted", async ({
  browser,
  lecturerSession,
}) => {
  test.slow(); // Invitations through the worker, a Class session and a lock
  const game = await liveClassGame(browser, lecturerSession, 2, { aiMode: "rule_based" });
  const [a, b] = game.students as [(typeof game.students)[0], (typeof game.students)[0]];
  try {
    const pageA = await a.context.newPage();
    const pageB = await b.context.newPage();
    await pageB.goto("/hjem");
    await expect(pageB.locator("html")).toHaveAttribute("data-live", "live", { timeout: 10_000 });
    await pageA.goto("/hjem");
    const blockA = pageA.locator("[data-time-proposal]");
    await blockA.getByRole("button", { name: copy.open }).click();
    const form = blockA.getByRole("form", { name: copy.title });
    await form.getByLabel(copy.date).fill(osloDate(2));
    await form.getByLabel(copy.time).fill("14:15");
    await form.getByRole("button", { name: copy.send }).click();
    await expect(blockA.getByRole("status")).toHaveText(copy.sent);
    await expect(blockA.getByText(/^Du foreslår å spille .* kl\. 14:15\.$/)).toBeVisible();
    await expect(blockA.getByText(copy.noneAccepted)).toBeVisible();

    // B's open Hjem shows it by name without a reload, and B accepts with one press.
    const blockB = pageB.locator("[data-time-proposal]");
    await expect(blockB.getByText(new RegExp(`^${a.name} foreslår å spille .* kl\\. 14:15\\.$`))).toBeVisible();
    await blockB.getByRole("button", { name: copy.accept }).click();
    await expect(blockB.getByText("Godtatt av deg.")).toBeVisible();
    await expect(blockB.getByRole("button", { name: copy.accept })).toHaveCount(0);
    // A sees who accepted, live.
    await expect(blockA.getByText(`Godtatt av ${b.name}.`)).toBeVisible();
  } finally {
    await a.context.close();
    await b.context.close();
  }
});
