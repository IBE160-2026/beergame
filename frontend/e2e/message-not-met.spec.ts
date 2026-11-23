import { expect } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { nextMail } from "./support/auth";
import { expectAccessible, lecturerPage, test, VIEWPORTS } from "./support/classes";
import { liveClassGame } from "./support/live-game";

/** Story 13.6 (FR-17, FR-40, UX-DR46, UX-DR54, NFR-6) on the local stack: a fresh Obligatorisk Class
 * game of two Students, the first of whom meets the requirement by corrections of all five steps.
 * Under the Oversikt's Trakt the Lenke «Send Melding til 1 som ikke har oppfylt kravet» opens the
 * Meldingsskjema for that recipient, with the table of the second Student above the field (the name
 * a Lenke to the Studentside); the send reaches that Student by e-mail and its result line says so.
 * Axe and reflow at 320 px and 1440 px. What the api stores and refuses is
 * `backend/tests/reports/test_message_not_met.py`. */
const copy = nb.messages;
const CSRF = { "X-Requested-With": "olspillet" };
const STEPS = ["class_game", "debrief", "quiz_passed", "replay", "test_submitted"];

test("the Oversikt's Lenke writes to those who have not met the requirement", async ({ browser, lecturerSession }) => {
  test.slow(); // Invitations through the worker, a Class session and a lock
  const game = await liveClassGame(browser, lecturerSession, 2, {
    aiMode: "rule_based",
    obligatory: true,
    gameSettings: { weeks: 3, demand: { kind: "step", start: 4, new_level: 8, change_week: 2 } },
  });
  const [first, second] = game.students as [(typeof game.students)[number], (typeof game.students)[number]];
  const firstId = ((await (await first.context.request.get("/api/auth/me")).json()) as { user: { id: string } }).user.id;
  const page = await lecturerPage(browser, lecturerSession, VIEWPORTS[2]!);
  try {
    for (const step of STEPS) {
      const saved = await page.request.post(`/api/class-sessions/${game.sessionId}/students/${firstId}/corrections`, {
        data: { step, done: true, reason: "Gjort i timen." },
        headers: CSRF,
      });
      expect(saved.status()).toBe(200);
    }

    // Under the Trakt: the Lenke with the count of those who have not met the requirement.
    await page.goto(`/klasseokter/${game.sessionId}/oversikt`);
    const funnel = page.locator('[data-rail="funnel"]');
    const link = funnel.getByRole("link", { name: nb.overview.rail.funnel.notMet(1) });
    await expect(link).toBeVisible();
    await link.click();
    await expect(page).toHaveURL(new RegExp(`/klasseokter/${game.sessionId}/melding\\?krav=ikke-oppfylt$`));
    const main = page.getByRole("main");
    await expect(main.getByRole("heading", { level: 1, name: copy.title.requirementNotMet })).toBeVisible();
    await expect(main).toContainText(copy.reach(1));

    // The table above the field: one row, the name a Lenke to the Studentside, the shares.
    const table = main.getByRole("table", { name: copy.notMet.caption });
    await expect(table.getByRole("columnheader")).toHaveText([
      copy.notMet.student,
      copy.notMet.ordered,
      copy.notMet.required,
      copy.notMet.playout,
    ]);
    const rows = table.locator("[data-not-met-row]");
    await expect(rows).toHaveCount(1);
    const name = rows.getByRole("rowheader").getByRole("link", { name: second.name });
    await expect(name).toHaveAttribute("href", new RegExp(`/klasseokter/${game.sessionId}/studenter/[0-9a-f-]+$`));
    await expect(rows.locator("td").nth(1)).toHaveText("80 %");
    const field = main.getByRole("textbox", { name: copy.field });
    expect(
      await table.evaluate((node, input) => !!(node.compareDocumentPosition(input!) & Node.DOCUMENT_POSITION_FOLLOWING), await field.elementHandle()),
    ).toBe(true);
    await expectAccessible(page, false);
    await page.setViewportSize({ width: VIEWPORTS[0]!.width, height: VIEWPORTS[0]!.height });
    await expectAccessible(page, true);
    await page.setViewportSize({ width: VIEWPORTS[2]!.width, height: VIEWPORTS[2]!.height });

    // «Send Melding»: the second Student gets it by e-mail, the result line takes focus.
    const text = `Husk Debriefen ${Date.now()}`;
    await field.fill(text);
    await main.getByRole("button", { name: copy.send }).click();
    const result = main.getByRole("status").filter({ hasText: copy.sent(1) });
    await expect(result).toBeFocused();
    // Waits for the Melding's own mail: the obligatory notice queued at the lock may still arrive later.
    expect((await nextMail(page, second.email, null, text)).text).toContain(text);

    // Once everyone has met the requirement, the Oversikt has no such Lenke.
    const secondId = ((await (await second.context.request.get("/api/auth/me")).json()) as { user: { id: string } }).user.id;
    for (const step of STEPS) {
      const saved = await page.request.post(`/api/class-sessions/${game.sessionId}/students/${secondId}/corrections`, {
        data: { step, done: true, reason: "Gjort i timen." },
        headers: CSRF,
      });
      expect(saved.status()).toBe(200);
    }
    // The Lenke's own read has answered (none left) before its absence is judged.
    const read = page.waitForResponse((r) => r.url().includes("/messages/form?recipient=requirement_not_met"));
    await page.goto(`/klasseokter/${game.sessionId}/oversikt`);
    expect((await (await read).json()).students).toBe(0);
    await expect(page.locator('[data-rail="funnel"] [data-funnel]')).toBeVisible();
    await expect(page.locator("[data-not-met-link]")).toHaveCount(0);
  } finally {
    await page.context().close();
    await first.context.close();
    await second.context.close();
  }
});
