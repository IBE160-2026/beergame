import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { formatNumber } from "../src/lib/number-format";
import { expectAccessible, test } from "./support/classes";
import { liveClassGame, orderByApi } from "./support/live-game";

/** The shared screen (Story 9.13, FR-74, FR-43, AD-8, AD-12, AD-21, UX-DR34, UX-DR35). Two
 * Students of one real two-Uke Class game: Sara opens the Group debrief and Ida joins. Sara's
 * laptop opens «Delt skjerm: hele kjeden» from her Debrief page: locked while Ida writes, open over
 * the event stream once Ida sends, with the chain, Netto lager per Role and «Kostnad, kr» per Role
 * and the chain's total, no name anywhere, its scrubber its own, and only the shared endpoint
 * read. At 1440 and 320 px with axe. Anyone not joined gets the plain permission denial. */
const shared = nb.debrief.shared;
const CSRF = { "X-Requested-With": "olspillet" };

async function live(page: Page) {
  await expect(page.locator("html")).toHaveAttribute("data-live", "live", { timeout: 10_000 });
}

test("a joined Student puts the chain on a shared screen, locked until everyone has sent", async ({ browser, lecturerSession }) => {
  test.slow(); // two Invitations through the worker, a Class session, a lock and a played game
  const game = await liveClassGame(browser, lecturerSession, 2, {
    aiMode: "rule_based",
    gameSettings: { weeks: 2, demand: { kind: "step", start: 4, new_level: 8, change_week: 2 } },
  });
  const [sara, ida] = game.students as [(typeof game.students)[0], (typeof game.students)[0]];
  const staff = await browser.newContext({ storageState: lecturerSession });
  try {
    for (const week of [1, 2]) {
      await orderByApi(sara, game.gameId, week, 4);
      await orderByApi(ida, game.gameId, week, 4);
    }
    // Sara opens the Group debrief and Ida joins, through the api; then Sara sends on her phone.
    const debrief = await (await sara.context.request.post(`/api/me/class-sessions/${game.sessionId}/debrief`, { headers: CSRF })).json();
    expect(debrief.group).toMatchObject({ joined: true, opener: true });
    expect((await ida.context.request.post(`/api/me/class-sessions/${game.sessionId}/debrief`, { headers: CSRF })).status()).toBe(200);
    expect((await ida.context.request.post(`/api/debriefs/${debrief.id}/join`, { headers: CSRF })).status()).toBe(200);
    const phone = await sara.context.newPage();
    await phone.setViewportSize({ width: 360, height: 740 });
    await phone.goto(`/debrief/${game.sessionId}`);
    const link = phone.getByRole("link", { name: nb.debriefEntry.group.sharedScreen });
    await expect(link).toBeVisible();
    await phone.getByRole("textbox", { name: nb.debriefEntry.explanation.prompt }).fill("Jeg bestilte for mye etter restordren.");
    await phone.getByRole("button", { name: nb.debriefEntry.explanation.send }).click();
    await expect(phone.locator("[data-group-bar]")).toBeVisible();
    const href = await link.getAttribute("href");
    expect(href).toBe(`/delt-skjerm/${debrief.id}`);
    await phone.close();

    // Her laptop: the shared screen, locked, without a name or a chart.
    const screen = await sara.context.newPage();
    await screen.setViewportSize({ width: 1440, height: 900 });
    const reads: string[] = [];
    screen.on("request", (request) => {
      const path = new URL(request.url()).pathname;
      if (/^\/api\/(debriefs|games|me\/games|me\/class-sessions)\b/.test(path)) reads.push(path);
    });
    await screen.goto(href!);
    await expect(screen.getByRole("heading", { level: 1, name: shared.title })).toBeVisible();
    await expect(screen.locator("[data-shared-locked]")).toHaveText(shared.locked);
    await expect(screen.locator("[data-shared-net-role]")).toHaveCount(0);
    for (const student of game.students) await expect(screen.locator("body")).not.toContainText(student.name);

    // Ida sends: the screen opens over the event stream, without reload.
    await live(screen);
    const sent = await ida.context.request.post(`/api/debriefs/${debrief.id}/explanation`, { data: { text: "Min." }, headers: CSRF });
    expect(sent.status()).toBe(201);
    await expect(screen.locator("[data-shared-screen='open']")).toBeVisible();
    await expect(screen.locator("[data-shared-step='2']")).toBeVisible();
    await expect(screen.locator("[data-chain-band] svg")).toBeVisible();
    await expect(screen.locator("[data-shared-net-role]")).toHaveCount(4);
    await expect(screen.locator("[data-shared-net-role]").first()).toHaveAttribute("data-shared-net-role", "factory");
    await expect(screen.locator("[data-chart='net-over-game']")).toHaveCount(4);
    const bill = screen.locator("[data-chain-bill]");
    await expect(bill.getByRole("heading", { name: shared.costTitle })).toBeVisible();
    await expect(bill.locator("[data-role]")).toHaveCount(4);
    await expect(bill.locator("[data-role]").first()).toHaveAttribute("data-role", "factory");
    const result = await (await sara.context.request.get(`/api/me/games/${game.gameId}/result`)).json();
    await expect(bill.locator("[data-chain-row]")).toContainText(formatNumber(result.chain.total_cost, { decimals: 2 }));
    for (const student of game.students) await expect(screen.locator("body")).not.toContainText(student.name);
    await expect(screen.locator("body")).not.toContainText("Jeg bestilte for mye");

    // The scrubber is this screen's own: the chain at Uke 1, its dashed line on each Role.
    await screen.getByRole("slider", { name: nb.debrief.chain.scrubber }).focus();
    await screen.keyboard.press("Home");
    await expect(screen.locator("[data-shared-at]")).toHaveText(shared.at(1));
    await expect(screen.locator("[data-mark='marker']")).toHaveCount(4);
    await screen.getByRole("button", { name: shared.showTable }).click();
    await expect(screen.locator("[data-shared-net-table] tbody tr")).toHaveCount(2);
    await screen.getByRole("button", { name: shared.showChart }).click();
    await expectAccessible(screen, false);

    // Only the shared endpoint was read for the Debrief and the game.
    expect(reads.length).toBeGreaterThan(1);
    expect(new Set(reads)).toEqual(new Set([`/api/debriefs/${debrief.id}/shared`]));

    await screen.setViewportSize({ width: 320, height: 740 });
    await expectAccessible(screen, true);
    await screen.close();

    // Anyone not joined: the plain permission denial, the same for an id that is not one.
    for (const [context, id] of [
      [staff, debrief.id],
      [sara.context, "00000000-0000-4000-8000-000000000000"],
    ] as const) {
      const refused = await context.request.get(`/api/debriefs/${id}/shared`);
      expect([refused.status(), (await refused.json()).error.code]).toEqual([403, "forbidden"]);
    }
  } finally {
    await staff.close();
    await sara.context.close();
    await ida.context.close();
  }
});
